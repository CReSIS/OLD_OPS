from django.http import HttpResponse
from django.db.models import get_model
from django.db import connection,DatabaseError
from django.contrib.gis.gdal import SpatialReference, CoordTransform
from django.contrib.gis.geos import Point,LineString,WKBReader
from authip import *
from functools import wraps
from decimal import Decimal
import math,collections,string,random,traceback,sys,ujson,json

def response(status,data):
	""" Creates an HttpResponse with OPS formatted JSON data.
	
	Input:
		status: (integer) 0:failure 1:success 2:warning
		data: (dictionary) a dictionary of key value pairs
		
	Output:
		HttpResponse: http response object returned to web server
	
	"""
	return HttpResponse(ujson.dumps({'status':status,'data':data}),content_type='application/json')

def ipAuth():
	""" Creates a Django decorator for validating the remote address on a list of valid IPs.
	
	Input:
		none
		
	Output:
		decorator: (decorator) a Django decorator object
		
	To apply this decorator add @ipAuth before a Django view
	
	"""
	def decorator(view):
		@wraps(view)
		def wrapper(request, *args, **kwargs):
			requestIp = request.META['REMOTE_ADDR']
			if requestIp in AUTHORIZED_IPS:
				return view(request, *args, **kwargs)
			else:
				return HttpResponse(status=403,content='403: Forbidden')
		return wrapper
	return decorator

def errorCheck(sys):
	""" Creates a human readable error string from a system error object.
	
	Input:
		sys: a system error object occuring after a python exception
		
	Output:
		none: see response()
	
	"""
	try:
		error = sys.exc_info()
		errorStr = error[1][0]
		errorLine = traceback.extract_tb(error[2])[0][1]
		errorType = error[0]
		errorFile = traceback.extract_tb(error[2])[0][0]
		errorMod = traceback.extract_tb(error[2])[0][2]
		errorOut = str(errorType)+' ERROR IN '+errorFile+'/'+ errorMod+' AT LINE '+str(errorLine)+':: ERROR: '+errorStr
		return response(0, ujson.dumps(errorOut))
	except:
		return response(0, 'ERROR: ERROR CHECK FAILED ON EXCEPTION.')

def epsgFromLocation(locationName):
	""" Gets an epsg code based on a mapped string location name.
	
	Input:
		locationName: (string) name of the location
		
	Output:
		epsg: (integer) an epsg code
		
	Current only locations 'arctic' and 'antarctic' are mapped to epsg codes
	
	"""
	if locationName == 'arctic':
		return 3413
	elif locationName == 'antarctic':
		return 3031
	else:
		return response(0,'ERROR. ONLY MAPPED FOR (antarctic or arctic).')

def twttToElev(surfTwtt,layerTwtt):
	""" Convert a layers two-way travel time to wgs1984 elevation in meters.
	
	Input:
		surfTwtt: (float) the two-way travel time of the surface for the given value
		layerTwtt: (float) the two-way travel time of the layer for the given value
		
	Output:
		surfElev: (float) the wgs1984 elevation in meters of the input surfaceTwtt
		layerElev: (float) the wgs1984 elevation in meters of the input layerTwtt
	
	"""
	myC = Decimal(299792458.0)
	surfElev = surfTwtt*(myC/Decimal(2.0))
	layerElev = surfElev + ((layerTwtt-surfTwtt)*(myC/Decimal((math.sqrt(3.15)*2.0))))
	return surfElev,layerElev

def randId(size):
	""" Generates a random string of letters and integers.
		
	Input:
		size: (integer) the number of random charactersto generate
		
	Output:
		randId: (string) a string of length size composed of randomly selected letters and digits
	
	"""
	return ''.join(random.choice(string.ascii_letters+string.digits) for _ in range(size))

def getQuery(request):
	""" Gets the query string from the input POST.
	
	Input:
		request: (object) HTTPRequest object.
		
	Output:
		SQL query string
	
	"""
	if request.method == 'POST':
		try:
			query = request.POST.get('query')

			if query is not None:
				return query
			else:
				response(0,'VALUE ''query'' IS NOT VALID OR EMPTY')
		except:
			return errorCheck(sys)
	else:
		response(0,'method must be POST')

def getData(request):
	""" Gets data from POST.
	
	Input:
		request: (object) HTTPRequest object.
		
	Output:
		app: (string) application name
		data: (String) JSON encoded data
	
	"""
	if request.method == 'POST':
		try:
			app = request.POST.get('app')
			data = request.POST.get('data')
			if data is not None and app is not None:
				return app,data
			else:
				response(0,'ERROR: INPUT VARIABLE ''data'' OR ''app'' IS EMPTY'),''
		except:
			response(0,'ERROR: COULD NOT GET POST'),''
	else:
		response(0,'ERROR: METHOD MUST BE POST'),''

def getAppModels(app):
	""" Gets the Django models for a specified application.
	
	Input:
		app: (string) application name
		
	Output:
		models: (named tuple) django model objects for the given application

	"""
	models = collections.namedtuple('model',['locations','seasons','radars','segments','frames','point_paths','crossovers','layer_groups','layers','layer_links','layer_points','landmarks'])
	
	locations = get_model(app,'locations')
	seasons = get_model(app,'seasons')
	radars = get_model(app,'radars')
	segments = get_model(app,'segments')
	frames = get_model(app,'frames')
	point_paths = get_model(app,'point_paths')
	crossovers = get_model(app,'crossovers')
	layer_groups = get_model(app,'layer_groups')
	layers = get_model(app,'layers')
	layer_links = get_model(app,'layer_links')
	layer_points = get_model(app,'layer_points')
	landmarks = get_model(app,'landmarks')

	return models(locations,seasons,radars,segments,frames,point_paths,crossovers,layer_groups,layers,layer_links,layer_points,landmarks)

def getInput(request):
	""" Wrapper for getData that gets the application models and decodes the JSON
	
	Input:
		request: HTTPRequest object
		
	Output:
		models: (named tuple) django model objects for the given application
		data: (dictionary) decoded JSON data
		app: (string) application name
	
	"""
	app,jsonData = getData(request)

	models = getAppModels(app)

	try:
		data = json.loads(jsonData,parse_float=Decimal)
	except:
		return errorCheck(sys)
	
	return models,data,app

def forceList(var):
	""" Forces a variable to be a list.
	
	Input:
		var: (any) any variable type that can be converted to a list
		
	Output:
		var: (list) a list of the given object (or the object itself if it's already a list)
	
	"""
	if not isinstance(var,list):
		if isinstance(var,tuple) or isinstance(var,(set)):
			out = list(var)
		else:
			out = []
			out.append(var)
		return out
	else:
		return var

def forceTuple(var):
	""" Forces a variable to be a tuple.
	
	Input:
		var: (any) any variable type that can be converted to a tuple
		
	Output:
		var: (tuple) a tuple of the given object (or the object itself if it's already a tuple)
	
	"""
	if not isinstance(var,tuple):
		if isinstance(var,list) or isinstance(var,set):
			return tuple(var)
		else:
			return (var,)
	else:
		return var

def buildEchogramList(app,seasonName,frameName):
	""" Builds a list of echogram URLs using the known structure of the CReSIS FTP
	
	Input:
		app: (string) application name
		seasonName: (string) season name
		frameName: (string) frame name
		
	Output:
		var: (list of strings) two URLs to the 1echo and 2echo_picks JPEG images on the server
	
	"""
	baseEchoURl = 'ftp://data.cresis.ku.edu/data/'+app+'/'+seasonName+'/images/'+frameName[:-4]+'/'+frameName
	return [baseEchoURl+'_1echo.jpg',baseEchoURl+'_2echo_pics.jpg']

def crossovers(app,models, path_id, location):
	cursor = connection.cursor()
	try:	
		#Get the correct srid for the locaiton
		proj = epsgFromLocation(location)
		# Create a GEOS Well Known Binary reader and initialize vars                 
		wkb_r = WKBReader()
		cross_pts = []; cross_angles = []; point_path_1_id = []; point_path_2_id = [];
		
		##FIND ALL NON SELF-INTERSECTING CROSSOVERS
		# Get the points of intersection, the closest point_path_id, and the angle in degrees for the current segment.
		sql_str = "WITH pts AS (SELECT row_number() over (ORDER BY gps_time) AS rn, id,geom FROM {app}_point_paths WHERE segment_id = {seg} ORDER BY gps_time), line AS (SELECT ST_MakeLine(ST_GeomFromText('POINTZ('||ST_X(pts.geom)||' '||ST_Y(pts.geom)||' '||pts.rn||')',4326)) AS ln FROM pts), i_pts AS (SELECT (ST_Dump(ST_Intersection(ST_Transform(line.ln,{proj}),ST_Transform(o.geom,{proj})))).geom AS i_pt FROM line, {app}_segments AS o WHERE o.id != {seg}) SELECT ST_Transform(ST_Force_2D(i_pt),4326) AS i, pts1.id, degrees(ST_Azimuth(i_pt,ST_Transform(pts2.geom,{proj}))) FROM i_pts, pts AS pts1, pts AS pts2 WHERE pts1.rn = ST_Z(i_pt)::int AND pts2.rn = ST_Z(i_pt)::int + 1 ORDER BY i;".format(app=app,proj=proj,seg=path_id)
		cursor.execute(sql_str)
		cross_info1 = cursor.fetchall()
		
		#Only perform second query and processing if the above had results.
		if cross_info1:
			# Get the closest point_path_id and the angle in degrees for the other segments
			sql_str = "WITH pts AS (SELECT row_number() over (ORDER BY gps_time) AS rn, geom, id, segment_id FROM {app}_point_paths WHERE segment_id IN (SELECT s2.id FROM {app}_segments AS s1, {app}_segments AS s2 WHERE s1.id = {seg} AND s2.id != {seg} AND ST_Intersects(s1.geom,s2.geom)) ORDER BY gps_time), line AS (SELECT ST_MakeLine(ST_GeomFromText('POINTZ('||ST_X(pts.geom)||' '||ST_Y(pts.geom)||' '||pts.rn||')',4326)) AS ln FROM pts GROUP BY pts.segment_id), i_pts AS (SELECT (ST_Dump(ST_Intersection(ST_Transform(line.ln,{proj}),ST_Transform(o.geom,{proj})))).geom AS i_pt FROM line, {app}_segments AS o WHERE o.id = {seg}) SELECT pts1.id, degrees(ST_Azimuth(i_pt,ST_Transform(pts2.geom,{proj}))) FROM i_pts, pts AS pts1, pts AS pts2 WHERE pts1.rn = ST_Z(i_pt)::int AND pts2.rn = ST_Z(i_pt)::int + 1 ORDER BY ST_Transform(ST_Force_2D(i_pt),4326);".format(app=app,proj=proj,seg=path_id)
			cursor.execute(sql_str)
			cross_info2 = cursor.fetchall()
			
			if cross_info2:
				#Extract all crossovers from above results.
				for idx in range(len(cross_info1)):
					cross_pts.append(cross_info1[idx][0])
					point_path_1_id.append(cross_info1[idx][1])
					point_path_2_id.append(cross_info2[idx][0])
					#Determine the angle of intersection
					angle1 = cross_info1[idx][2]
					angle2 = cross_info2[idx][1]
					angle = math.fabs(angle1-angle2)
					#Only record the acute angle.
					if angle > 90:
						angle = math.fabs(180 - angle)
						if angle > 90:
							angle = math.fabs(180 - angle)
					cross_angles.append(angle)
					
			else:
				# This should not occur.
				response(0, "ERROR FINDING MATCHING CROSSOVER POINT PATHS ON INTERSECTING LINES")
		
		##FIND ALL SELF-INTERSECTING CROSSOVERS:
		#Fetch the given line path from the db as a multilinestring.
		# 'ST_UnaryUnion' results in a multilinestring with the last point of
		# every linestring except the last linestring as a crossover and the
		# first point of every linestring except the first linestring as a
		# crossover.
		sql_str = "WITH pts AS (SELECT id, geom FROM {app}_point_paths WHERE segment_id = {seg} ORDER BY gps_time) SELECT ST_UnaryUnion(ST_Transform(ST_MakeLine(ST_GeomFromText('POINTZ('||ST_X(pts.geom)||' '||ST_Y(pts.geom)||' '||pts.id||')',4326)),{proj})) FROM pts;".format(app=app, proj=proj, seg=path_id)
		cursor.execute(sql_str)
		line = cursor.fetchone()
		
	
		#Create a GEOS geometry from the result fetched above.
		lines = wkb_r.read(line[0])
		#Check if resulting object is a multilinestring, indicating crossovers.
		if lines.geom_type.encode('ascii', 'ignore') == 'MultiLineString':
			#Get the point_path_ids for all points for the given segment:
			pt_ids = models.point_paths.objects.filter(segment_id=path_id).values_list('id',flat=True)
			#Create a dictionary to keep track of crossovers and point ids. 
			self_crosses = {}
			#Create a dictionary for managing next points (the point after the crossover along the flight path)
			nxt_pts = {}
			#Loop through all linestrings created by ST_UnaryUnion 
			for idx in range(len(lines) - 1): 
				#Set the value of idx2:
				idx2 = idx + 1
				
				#Keep track of intersection point w/ dictionary:
				i_point = lines[idx][-1]
				if  i_point not in self_crosses.keys():
					self_crosses[i_point] = []
					nxt_pts[i_point] = []
				
				#Fall back/forward to point w/ z in pt_ids.
				#For the point before the crossover:
				coord_idx = -1 #Include the crossover pt in the search (could be on top of point_path geom)
				while lines[idx][coord_idx][2] not in pt_ids:
					coord_idx -= 1
					if math.fabs(coord_idx) > len(lines[idx].coords):
						coord_idx = -1
						idx -= 1
				pt_1 = lines[idx][coord_idx]
				#For the point after the crossover:
				coord_idx = 1 #Start after the crossover point. 
				while lines[idx2][coord_idx][2] not in pt_ids:
					coord_idx += 1
					if coord_idx > len(lines[idx2].coords):
						coord_idx = 0
						idx2 += 1
				pt_2 = lines[idx2][coord_idx]
				
				#select pt closest to current intersection point
				if LineString(pt_1,i_point).length <= LineString(i_point,pt_2).length:
					self_crosses[i_point].append(pt_1[2])
					
				else:
					self_crosses[i_point].append(pt_2[2])
				nxt_pts[i_point].append(pt_2)
				
			#Extract information from self-intersecting crossovers dict and determine the angle of intersection
			for i_pt in self_crosses:
				cross_pts.append(Point(i_pt[0],i_pt[1],srid=proj).transform(CoordTransform(SpatialReference(proj),SpatialReference(4326)),True))
				point_path_1_id.append(self_crosses[i_pt][0])
				point_path_2_id.append(self_crosses[i_pt][1])
				
				#Find the angle of self-intersection
				change_x1 = i_pt[0] - nxt_pts[i_pt][0][0]
				change_y1 = i_pt[1] - nxt_pts[i_pt][0][1]
				change_x2 = i_pt[0] - nxt_pts[i_pt][1][0]
				change_y2 = i_pt[1] - nxt_pts[i_pt][1][1]
				angle1 = math.degrees(math.atan2(change_y1,change_x1))
				angle2 = math.degrees(math.atan2(change_y2,change_x2))
				angle = math.fabs(angle1-angle2)
				#Get the acute angle:
				if angle > 90:
					angle = math.fabs(180 - angle)
					if angle > 90:
						angle = math.fabs(180-angle)
				cross_angles.append(angle)

		# Check if any crossovers were found. 
		if len(point_path_1_id) > 0:
			crossovers = []
			#If so, package for bulk insert.
			for i in range(len(point_path_1_id)):
				crossovers.append(models.crossovers(point_path_1_id=point_path_1_id[i], point_path_2_id=point_path_2_id[i], angle=cross_angles[i], geom=cross_pts[i]))
			#Bulk insert found crossovers into the database. 
			_ = models.crossovers.objects.bulk_create(crossovers)

	except: 
		errorCheck(sys)
	finally:
		cursor.close()
