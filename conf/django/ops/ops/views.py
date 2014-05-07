from django.db import connection,DatabaseError
from django.contrib.gis.geos import GEOSGeometry,Point,LineString,WKBReader
from django.contrib.gis.gdal import SpatialReference,CoordTransform
from django.contrib.auth import authenticate,login,logout
from django.contrib.auth.models import User
from django.http import HttpResponse
from utility import ipAuth
from decimal import Decimal
import utility,sys,os,datetime,line_profiler,simplekml,ujson,csv,time,math
from scipy.io import savemat
import numpy as np
from collections import OrderedDict

# =======================================
# DATA INPUT/DELETE FUNCTIONS
# =======================================

@ipAuth()
def createPath(request):
	""" Creates/Updates entries in the segments, point paths, seasons, locations, and radars tables.
	
	Input:
		geometry: (geojson) {'type':'LineString','coordinates',[longitude latitude]}
		elev: (list of floats) elevation for each point in the geometry
		gps_time: (list of floats) gps_time for each point in the geometry
		roll: (list of floats) roll for each point in the geometry
		pitch: (list of floats) pitch for each point in the geometry
		heading: (list of floats) heading for each point in the geometry
		season: (string) name of the season
		season_group: (string) name of the season group
		location: (string) name of the location
		radar: (string) name of the radar
		segment: (string) name of the segment
		frame_count: (integer) number of frames for the given segment
		frame_start_gps_time: (list of floats) start gps time for each frame for the given segment
		
	Output:
		status: (integer) 0:error 1:success 2:warning
		data: string status message
	
	"""
	models,data,app,cookies = utility.getInput(request) # get the input and models
	
	userProfileObj,status = utility.getUserProfile(cookies)
	if status:
		if not userProfileObj.createData:
			return utility.response(0,'ERROR: USER NOT AUTHORIZED TO CREATE DATA.',{})
	else:
		return utility.response(0,userProfileObj,{});
	
	# parse the data input
	try:
	
		inLinePath = data['geometry']
		inGpsTime = data['properties']['gps_time']
		inElevation = data['properties']['elev']
		inRoll = data['properties']['roll']
		inPitch = data['properties']['pitch']
		inHeading = data['properties']['heading']
		inSeason = data['properties']['season']
		inSeasonGroup = data['properties']['season_group']
		inLocationName = data['properties']['location']
		inRadar = data['properties']['radar']
		inSegment = data['properties']['segment']
		inFrameCount = data['properties']['frame_count']
		inFrameStartGpsTimes = utility.forceList(data['properties']['frame_start_gps_time'])
		
	except:
		return utility.errorCheck(sys)
	
	try:

		locationsObj,_ = models.locations.objects.get_or_create(name=inLocationName.lower()) # get or create the location 
		seasonGroupsObj,_ = models.season_groups.objects.get_or_create(name=inSeasonGroup) # get or create the season  
		seasonsObj,_ = models.seasons.objects.get_or_create(name=inSeason,season_group_id=seasonGroupsObj.pk,location_id=locationsObj.pk) # get or create the season   
		radarsObj,_ = models.radars.objects.get_or_create(name=inRadar.lower()) # get or create the radar
		
		linePathGeom = GEOSGeometry(ujson.dumps(inLinePath)) # create a geometry object
		
		# get or create the segments object
		segmentsObj,_ = models.segments.objects.get_or_create(season_id=seasonsObj.pk,radar_id=radarsObj.pk,name=inSegment,geom=linePathGeom)

		frmPks = []
		for frmId in range(int(inFrameCount)):
			frameName = inSegment+("_%03d"%(frmId+1))
			frmObj,_ = models.frames.objects.get_or_create(name=frameName,segment_id=segmentsObj.pk) # get or create the frame object
			frmPks.append(frmObj.pk) # store the pk for use in point paths

		# build the point path objects for bulk create
		pointPathObjs = []
		for ptIdx,ptGeom in enumerate(linePathGeom):
			
			# get the frame pk (based on start gps time list)
			frmId = frmPks[max([gpsIdx for gpsIdx in range(len(inFrameStartGpsTimes)) if inFrameStartGpsTimes[gpsIdx] <= inGpsTime[ptIdx]])]
			
			# prepare the gps time and perform exact comparison in the database
			curGpsTime = Decimal(inGpsTime[ptIdx]).quantize(Decimal('.000001'))
			pointPathExists = models.point_paths.objects.filter(location_id=locationsObj.pk,season_id=seasonsObj.pk,segment_id=segmentsObj.pk,frame_id=frmId,gps_time=curGpsTime).exists()
			
			if not pointPathExists:
				
				# add a point path object to the output list
				pointPathGeom = GEOSGeometry('POINT Z ('+repr(ptGeom[0])+' '+repr(ptGeom[1])+' '+str(inElevation[ptIdx])+')',srid=4326) # create a point geometry object
				pointPathObjs.append(models.point_paths(location_id=locationsObj.pk,season_id=seasonsObj.pk,segment_id=segmentsObj.pk,frame_id=frmId,gps_time=inGpsTime[ptIdx],roll=inRoll[ptIdx],pitch=inPitch[ptIdx],heading=inHeading[ptIdx],geom=pointPathGeom))
		
		if len(pointPathObjs) > 0:
			_ = models.point_paths.objects.bulk_create(pointPathObjs) # bulk create the point paths objects
		
		# calculate and insert crossovers
		cursor = connection.cursor()
		try:	
			#Get the correct srid for the locaiton
			proj = utility.epsgFromLocation(inLocationName)
			# Create a GEOS Well Known Binary reader and initialize vars                 
			wkb_r = WKBReader()
			cross_pts = []; cross_angles = []; point_path_1_id = []; point_path_2_id = [];
			
			##FIND ALL NON SELF-INTERSECTING CROSSOVERS
			# Get the points of intersection, the closest point_path_id, and the angle in degrees for the current segment.
			sql_str = "WITH pts AS (SELECT row_number() over (ORDER BY gps_time) AS rn, id,geom FROM {app}_point_paths WHERE segment_id = {seg} ORDER BY gps_time), line AS (SELECT ST_MakeLine(ST_GeomFromText('POINTZ('||ST_X(pts.geom)||' '||ST_Y(pts.geom)||' '||pts.rn||')',4326)) AS ln FROM pts), i_pts AS (SELECT (ST_Dump(ST_Intersection(ST_Transform(line.ln,{proj}),ST_Transform(o.geom,{proj})))).geom AS i_pt FROM line, {app}_segments AS o WHERE o.id != {seg}) SELECT ST_Transform(ST_Force_2D(i_pt),4326) AS i, pts1.id, degrees(ST_Azimuth(i_pt,ST_Transform(pts2.geom,{proj}))) FROM i_pts, pts AS pts1, pts AS pts2 WHERE pts1.rn = ST_Z(i_pt)::int AND pts2.rn = ST_Z(i_pt)::int + 1 ORDER BY i;".format(app=app,proj=proj,seg=segmentsObj.pk)
			cursor.execute(sql_str)
			cross_info1 = cursor.fetchall()
			
			#Only perform second query and processing if the above had results.
			if cross_info1:
				# Get the closest point_path_id and the angle in degrees for the other segments
				sql_str = "WITH pts AS (SELECT row_number() over (ORDER BY gps_time) AS rn, geom, id, segment_id FROM {app}_point_paths WHERE segment_id IN (SELECT s2.id FROM {app}_segments AS s1, {app}_segments AS s2 WHERE s1.id = {seg} AND s2.id != {seg} AND ST_Intersects(s1.geom,s2.geom)) ORDER BY gps_time), line AS (SELECT ST_MakeLine(ST_GeomFromText('POINTZ('||ST_X(pts.geom)||' '||ST_Y(pts.geom)||' '||pts.rn||')',4326)) AS ln FROM pts GROUP BY pts.segment_id), i_pts AS (SELECT (ST_Dump(ST_Intersection(ST_Transform(line.ln,{proj}),ST_Transform(o.geom,{proj})))).geom AS i_pt FROM line, {app}_segments AS o WHERE o.id = {seg}) SELECT pts1.id, degrees(ST_Azimuth(i_pt,ST_Transform(pts2.geom,{proj}))) FROM i_pts, pts AS pts1, pts AS pts2 WHERE pts1.rn = ST_Z(i_pt)::int AND pts2.rn = ST_Z(i_pt)::int + 1 ORDER BY ST_Transform(ST_Force_2D(i_pt),4326);".format(app=app,proj=proj,seg=segmentsObj.pk)
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
					return utility.response(0, "ERROR FINDING MATCHING CROSSOVER POINT PATHS ON INTERSECTING LINES",{})
			
			##FIND ALL SELF-INTERSECTING CROSSOVERS:
			#Fetch the given line path from the db as a multilinestring.
			# 'ST_UnaryUnion' results in a multilinestring with the last point of
			# every linestring except the last linestring as a crossover and the
			# first point of every linestring except the first linestring as a
			# crossover.
			sql_str = "WITH pts AS (SELECT id, geom FROM {app}_point_paths WHERE segment_id = {seg} ORDER BY gps_time) SELECT ST_UnaryUnion(ST_Transform(ST_MakeLine(ST_GeomFromText('POINTZ('||ST_X(pts.geom)||' '||ST_Y(pts.geom)||' '||pts.id||')',4326)),{proj})) FROM pts;".format(app=app, proj=proj, seg=segmentsObj.pk)
			cursor.execute(sql_str)
			line = cursor.fetchone()
			
			#Create a GEOS geometry from the result fetched above.
			lines = wkb_r.read(line[0])
			#Check if resulting object is a multilinestring, indicating crossovers.
			if lines.geom_type.encode('ascii', 'ignore') == 'MultiLineString':
				#Get the point_path_ids for all points for the given segment:
				pt_ids = models.point_paths.objects.filter(segment_id=segmentsObj.pk).values_list('id',flat=True)
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
						if coord_idx >= len(lines[idx2].coords):
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
			return utility.errorCheck(sys)
		finally:
			cursor.close()
		
		return utility.response(1,'SUCCESS: PATH INSERTION COMPLETED.',{})
		
	except:
		return utility.errorCheck(sys)

@ipAuth()
def createLayer(request): 
	""" Creates an entry in the layers table (or modifies the status of an existing layer).
	
	Input:
		lyr_name: name of the input layer
		
	Optional Inputs:
		lyr_group_name: (string) name of the layer group
			default: 'ungrouped'
		lyr_description: (string) description of the input layer
			default: null
		
	Output:
		status: (integer) 0:error 1:success 2:warning
		data: 
			lyr_id: (integer) id of the created/updated layer
			lyr_group_id: (integer) id of the created/used layer group
		
	"""	
	models,data,app,cookies = utility.getInput(request) # get the input and models
	
	userProfileObj,status = utility.getUserProfile(cookies)
	if status:
		if not userProfileObj.createData:
			return utility.response(0,'ERROR: USER NOT AUTHORIZED TO CREATE DATA.',{})
	else:
		return utility.response(0,userProfileObj,{});
	
	# parse the data input
	try:
	
		inLyrName = data['properties']['lyr_name']
	
		# parse the optional data input
		try:
			inLyrGroupName = data['properties']['lyr_group_name']
		except:
			inLyrGroupName = 'ungrouped'
		
		try:
			inLyrDescription = data['properties']['lyr_description']
		except:
			inLyrDescription = None
			
		try:
			inGroupStatus = data['properties']['public']
		except:
			inGroupStatus = False
	
	except:
		return utility.errorCheck(sys)
		
	# perform the function logic
	try:
		
		lyrObjCount = models.layers.objects.filter(name=inLyrName,deleted=False).count() # make sure layer name is unique (ignoring groups)
		if lyrObjCount > 0:
			return utility.response(0,'ERROR: LAYER WITH THE SAME NAME EXISTS. (LAYER NAMES MUST BE UNIQUE, EVEN ACROSS GROUPS)',{}) # throw error, trying to create a duplicate layer
		
		lyrGroupsObj,isNew = models.layer_groups.objects.get_or_create(name=inLyrGroupName) # get or create the layer group
		if isNew:
			lyrGroupsObj.public = inGroupStatus
			lyrGroupsObj.save(update_fields=['public'])
		
		lyrObj,isNew = models.layers.objects.get_or_create(name=inLyrName,layer_group_id=lyrGroupsObj.pk) # get or create the layer
			
		if not isNew: # if layer is not new and deleted, set deleted = False
			if lyrObj.deleted == True:
				lyrObj.deleted = False
				lyrObj.save(update_fields=['deleted'])
				
			else:
				return utility.response(0,'ERROR: LAYER WITH THE SAME NAME EXISTS (WITHIN THE GROUP) AND IS NOT DELETED',{}) # throw error, trying to create a duplicate layer
		
		else:
			lyrObj.description = inLyrDescription
			lyrObj.save(update_fields=['description'])
			
		# return the output
		return utility.response(1,{'lyr_id':lyrObj.pk,'lyr_group_id':lyrGroupsObj.pk},{})
	
	except:
		return utility.errorCheck(sys)

@ipAuth()
def deleteLayer(request): 
	""" Changes a layers deleted value to True
	
	Input:
		lyr_name: (string) name of layer to delete
		
	Output:
		status: (integer) 0:error 1:success 2:warning
		data:
			lyr_id: (integer) id of the deleted layer
		
	No actual data is removed from the database, instead the layer entry is updated as deleted=True
	
	"""	
	models,data,app,cookies = utility.getInput(request) # get the input and models
	
	# parse the data input
	try:
		
		inLyrName = data['properties']['lyr_name']
	
	except:
		return utility.errorCheck(sys)
	
	# perform the function logic
	try:
		
		lyrObjs = models.layers.objects.get(name=inLyrName) # get the layers object
		lyrObjs.deleted = True
		lyrObjs.save(update_fields=['deleted']) # update the deleted field
		
		# return the output
		return utility.response(1,{'lyr_id':lyrObjs.pk},{})
		
	except:
		return utility.errorCheck(sys)

@ipAuth()
def createLayerPoints(request): 
	""" Creates entries in layer points.
	
	Input:
		point_path_id: (integer or list of integers) point path ids to update or create layer points on
		lyr_name: (string) name of the layer for the points
		twtt: (float or list of floats) two-way travel time of the points
		type: (integer or list of integers) pick type of the points (1:manual 2:auto)
		quality: (integer or list of integers) quality value of the points (1:good 2:moderate 3:derived)
		
	Output:
		status: (integer) 0:error 1:success 2:warning
		data: string status message
	
	"""	
	models,data,app,cookies = utility.getInput(request) # get the input and models
	
	userProfileObj,status = utility.getUserProfile(cookies)
	if status:
		if not userProfileObj.createData:
			return utility.response(0,'ERROR: USER NOT AUTHORIZED TO CREATE DATA.',{})
	else:
		return utility.response(0,userProfileObj,{});
	
	# parse the data input
	try:
	
		inPointPathIds = utility.forceList(data['properties']['point_path_id'])
		inLyrName = data['properties']['lyr_name']
		inTwtt = utility.forceList(data['properties']['twtt'])
		inType = utility.forceList(data['properties']['type'])
		inQuality = utility.forceList(data['properties']['quality'])
		inUserName = cookies['userName']
	
	except:
		return utility.errorCheck(sys)
	
	# perform the function logic
	try:
	
		layerId = models.layers.objects.filter(name=inLyrName,deleted=False).values_list('pk',flat=True)[0] # get the layer object
		
		layerPointsObjs = []
		for ptIdx in range(len(inPointPathIds)):
			
			layerPointsObj = models.layer_points.objects.filter(layer_id=layerId,point_path_id=inPointPathIds[ptIdx]) # get any current entry from the database
			
			if len(layerPointsObj) > 0:
			
				if inTwtt[ptIdx] is None: # delete the point if MATLAB passed a NaN TWTT
					layerPointsObj.delete()
				else:
					layerPointsObj.update(twtt=inTwtt[ptIdx],type=inType[ptIdx],quality=inQuality[ptIdx],user=inUserName,last_updated=datetime.datetime.now()) # update the current entry
				
				if len(layerPointsObj) > 1:
					
					for idx in range(layerPointsObj)[1:]: # delete duplicate entries (likely will never occur)
						layerPointsObj[idx].delete()
						
			else: # there is no existing object to update, create it
			
				# build a list of objects for bulk create
				layerPointsObjs.append(models.layer_points(layer_id=layerId,point_path_id=inPointPathIds[ptIdx],twtt=inTwtt[ptIdx],type=inType[ptIdx],quality=inQuality[ptIdx],user=inUserName))
		
		if len(layerPointsObjs) > 0:
			_ = models.layer_points.objects.bulk_create(layerPointsObjs) # bulk create the layer points objects
			
		return utility.response(1,'SUCCESS: LAYER POINTS INSERTION COMPLETED.',{})
		
	except:
		return utility.errorCheck(sys)

@ipAuth()
def deleteLayerPoints(request): 
	""" Deletes entries from layer points.
	
	Input:
		start_point_path_id: (integer) the start point path id of the points for deletion
		stop_point_path_id: (integer) the stop point path id of the points for deletion
		min_twtt: (float) the minimum two-way travel time of the points for deletion
		max_twtt: (float) the maximum two-way travel time of the points for deletion
		lyr_name: (string) the name of the layer of the points for deletion
			OR
		start_gps_time: (float) the start gps time of the points for deletion
		stop_gps_time: (float) the stop gps time of the points for deletion
		min_twtt: (float) the minimum two-way travel time of the points for deletion
		max_twtt: (float) the maximum two-way travel time of the points for deletion
		lyr_name: (string) the name of the layer of the points for deletion
		segment: (string) the name of the segment of the points for deletion
		location: (string) the name of the location of the points for deletion
		
	Output:
		status: (integer) 0:error 1:success 2:warning
		data: string status message
	
	"""	
	models,data,app,cookies = utility.getInput(request) # get the input and models
	
	# parse the data input
	try:
	
		inMinTwtt = data['properties']['min_twtt']
		inMaxTwtt = data['properties']['max_twtt']
		inLyrName = data['properties']['lyr_name']
		
		# parse the optional inputs
		try:
		
			useGpsTimes = True
			inStartGpsTime = data['properties']['start_gps_time']
			inStopGpsTime = data['properties']['stop_gps_time']
			inSegmentName = data['properties']['segment'] 
			inLocationName = data['properties']['location'] 
		
		except:
		
				useGpsTimes = False
				inStartPointPathId = data['properties']['start_point_path_id']
				inStopPointPathId = data['properties']['stop_point_path_id']
				
	except:
		return utility.errorCheck(sys)	
	
	# perform the function logic
	try:
	
		if useGpsTimes:
		
			inStartGpsTimeN = inStartGpsTime.next_minus() # get the next possible value (ensures boundary points are deleted)
			inStopGpsTimeN = inStopGpsTime.next_plus()
			
			# get the point path ids
			inPointPathIds = models.point_paths.objects.filter(segment__name=inSegmentName,location__name=inLocationName,gps_time__range=(inStartGpsTimeN,inStopGpsTimeN)).values_list('pk',flat=True)
		
		else:
			
			# get the point path ids
			inPointPathIds = models.point_paths.objects.filter(pk__range=(inStartPointPathId,inStopPointPathId)).values_list('pk',flat=True)

		# get the next possible value after properly quantizing twtt (ensures boundary points are deleted)
		minTwttN = inMinTwtt.quantize(Decimal(10) ** -11).next_minus()
		maxTwttN = inMaxTwtt.quantize(Decimal(10) ** -11).next_plus()
		
		# get the layer points objects for deletion
		layerPointsObj = models.layer_points.objects.filter(point_path_id__in=inPointPathIds,twtt__range=(minTwttN,maxTwttN),layer__name=inLyrName)
		
		if len(layerPointsObj) == 0:
		
			return utility.response(2,'NO LAYER POINTS WERE REMOVED. (NO POINTS MATCHED THE REQUEST)',{})
		
		else:
			
			layerPointsObj.delete() # delete the layer points
			
			# return the output
			return utility.response(1,'SUCCESS: LAYER POINTS DELETION COMPLETED.',{})
	
	except:
		return utility.errorCheck(sys)

@ipAuth()
def deleteBulk(request): 
	""" Delete data in large chunks at either the segment or season level.
	
	Input:
		season: (string or list of strings) name of season to delete data from
		
	Optional Inputs:
		segment: (string or list of strings) names of segments to delete
		only_layer_points: (boolean) if true only layer points are deleted
		
	Output:
		status: (integer) 0:error 1:success 2:warning
		data: string status message
	
	If no segment is given all segments for the given season are deleted.
	If full is not given only layer points are deleted
	
	"""
	models,data,app,cookies = utility.getInput(request) # get the input and models
	
	# parse the data input
	try:
	
		inSeasonNames = utility.forceList(data['properties']['season'])
	
		# parse the optional input
		try:
		
			useAllSegments = False
			inSegmentNames = utility.forceList(data['properties']['segment'])
		
		except:
		
				useAllSegments = True
				
		try:
		
			deleteFull=data['properties']['only_layer_points']
			
		except:
		
			deleteFull=True
			
	except:
		return utility.errorCheck(sys)
	
	# perform the function logic
	try:
		
		if useAllSegments:
		
			inSegmentNames = models.segments.objects.filter(season__name__in=inSeasonNames).values_list('name',flat=True) # get all the segments for the given seasons
			
		# delete layer points
		_ = models.layer_points.objects.filter(point_path__season__name__in=inSeasonNames,point_path__segment__name__in=inSegmentNames).delete()
		
		if deleteFull:
		
			_ = models.segments.objects.filter(name__in=inSegmentNames).delete() # delete segments
			
			if not models.segments.objects.filter(season__name__in=inSeasonNames):
			
				_ = models.seasons.objects.filter(name__in=inSeasonNames).delete() # delete seasons (if there are no segments left for the specified seasons)
			
		# return the output
		return utility.response(1,'SUCCESS: BULK DELETION COMPLETED',{})		
	
	except:
		return utility.errorCheck(sys)

@ipAuth()
def releaseLayerGroup(request):
	""" Sets the status of a layer group to public.
	
	Input:
		lyr_group_name: (string) name of the layer group

	Output:
		status: (integer) 0:error 1:success 2:warning
		data: string status message

	"""
	models,data,app,cookies = utility.getInput(request) # get the input and models
	
	# parse the data input
	try:
	
		inLyrGroupName = data['properties']['lyr_group_name']
	
	except:
		return utility.errorCheck(sys)
	
	# perform the function logic
	try:
		
		# update the groups public status
		lyrGroupsObj = models.layer_groups.objects.filter(name=inLyrGroupName).update(public=True)
		
		# return the output
		return utility.response(1,'SUCCESS: LAYER GROUP IS NOW PUBLIC',{});
	
	except:
		return utility.errorCheck(sys)

# =======================================
# DATA OUTPUT FUNCTIONS
# =======================================

def getPath(request): 
	""" Gets a point path/s data from the OPS database.
	
	Input:
		location: (string) region of point path/s to retrieve
		season: (string) season of point path/s to retrieve
		start_gps_time: (float) start gps time of point path/s to retrieve
		stop_gps_time: (float) stop gps time of point path/s to retrieve
		
	Output:
		status: (integer) 0:error 1:success 2:warning
		data:
			id: (integer) id of point path/s
			gps_time: (float) gps time of point path/s
			elev: (float) elev of point path/s
			X: (float) x value of point path/s
			Y: (float) y value of point path/s
	
	"""
	models,data,app,cookies = utility.getInput(request) # get the input and models
	
	# parse the data input
	try:
	
		inLocationName = data['properties']['location']
		inSeasonName = data['properties']['season']
		inStartGpsTime = data['properties']['start_gps_time']
		inStopGpsTime = data['properties']['stop_gps_time']
		
		# parse optional inputs
		try:
			nativeGeom = data['properties']['nativeGeom']
		except:
			nativeGeom = False
		
	except:
		return utility.errorCheck(sys)
		
	try:
		
		epsg = utility.epsgFromLocation(inLocationName) # get epsg for the input location
		
		# get point paths based on input 
		if nativeGeom:
			pointPathsObj = models.point_paths.objects.filter(season_id__name=inSeasonName, location_id__name=inLocationName, gps_time__gte=inStartGpsTime, gps_time__lte=inStopGpsTime).order_by('gps_time').values_list('pk','gps_time','geom')
		else:
			pointPathsObj = models.point_paths.objects.filter(season_id__name=inSeasonName, location_id__name=inLocationName, gps_time__gte=inStartGpsTime, gps_time__lte=inStopGpsTime).transform(epsg).order_by('gps_time').values_list('pk','gps_time','geom')
		
		# unzip the data for output
		pks,gpsTimes,pointPaths = zip(*pointPathsObj)
		xCoords,yCoords,elev = zip(*pointPaths)
		
		# return the output
		return utility.response(1,{'id':pks,'gps_time':gpsTimes,'elev':elev,'X':xCoords,'Y':yCoords},{})
		
	except:
		return utility.errorCheck(sys)

def getFrameClosest(request): 
	""" Gets the closest frame from the OPS database.
	
	Input:
		location: (string) region of frame to retrieve
		x: (float) x value of point to find the closest frame to
		y: (float) y value of point to find the closest frame to
		
	Optional Input:
		season: (string or list of strings) season/s of frame to retrieve
		startseg: (string) minimum segment name the output frame can belong to
		stopseg: (string) maximum segment name the output frame can belong to
		
	Output:
		status: (integer) 0:error 1:success 2:warning
		data:
			season: (string) the season name of the closest frame
			segment_id: (integer) the segment id of the closest frame
			start_gps_time: (float) the start gps time of the closest frame
			stop_gps_time: (float) the stop gps time of the closest frame 
			frame: (string) the name of the closest frame
			X: (list of floats) the x coordinates of the closest frame
			Y: (list of floats) the y coordinates of the closest frame
			gps_time: (list of floats) the gps times of the closest frame
			echograms: (list of strings) urls of the ftp echograms of the closest frame
	
	"""
	models,data,app,cookies = utility.getInput(request) # get the input and models
	
	# parse the data input
	try:
		inLocationName = data['properties']['location']
		inPointX = data['properties']['x']
		inPointY = data['properties']['y']
	
		# parse the optional data input
		try:
			inSeasonNames = utility.forceList(data['properties']['season'])
			useAllSeasons = False
		except:
			useAllSeasons = True
		
		try:
			inStartSeg = data['properties']['startseg']
			inStopSeg = data['properties']['stopseg']
		except:
			inStartSeg = '00000000_00'
			inStopSeg = '99999999_99'
			
		"""
		try:
			inSeasonStatus = data['properties']['status']
		except:
			inSeasonStatus = [True]
		"""
		
	except:
		return utility.errorCheck(sys)
	
	try:
		
		if useAllSeasons:
		
			inSeasonNames = models.seasons.objects.filter(location_id__name=inLocationName,season_group__public=True).values_list('name',flat=True) # get all the public seasons
		
		epsg = utility.epsgFromLocation(inLocationName) # get the input epsg
		inPoint = GEOSGeometry('POINT ('+str(inPointX)+' '+str(inPointY)+')', srid=epsg) # create a point geometry object
		
		# get the frame id of the closest segment
		closestFrameId = models.segments.objects.filter(season_id__name__in=inSeasonNames,name__range=(inStartSeg,inStopSeg)).transform(epsg).distance(inPoint).order_by('distance').values_list('pk','distance')[0][0]
		
		# get the frame name,segment id, season name, path, and gps_time from point_paths for the frame id above
		pointPathsObj = models.point_paths.objects.select_related('frames__name','seasons_name').filter(frame_id=closestFrameId).transform(epsg).order_by('gps_time').values_list('frame__name','segment_id','season__name','geom','gps_time')
		
		# get the (x,y,z) coords from pointPathsObj
		pointPathsGeoms = [(pointPath[3].x,pointPath[3].y,pointPath[4]) for pointPath in pointPathsObj]
		xCoords,yCoords,gpsTimes = zip(*pointPathsGeoms)
		
		# build the echogram image urls list
		outEchograms = utility.buildEchogramList(app,pointPathsObj[0][2],pointPathsObj[0][0])
		
		# returns the output
		return utility.response(1,{'season':pointPathsObj[0][2],'segment_id':pointPathsObj[0][1],'start_gps_time':min(gpsTimes),'stop_gps_time':max(gpsTimes),'frame':pointPathsObj[0][0],'echograms':outEchograms,'X':xCoords,'Y':yCoords,'gps_time':gpsTimes},{})
		
	except:
		return utility.errorCheck(sys)

def getLayers(request): 
	""" Returns all layers that are public and not deleted.
	
	Input:
		FROM GEOPORTAL: (none)
		FROM MATLAB:
			mat: (boolean) true
			userName: (string) username of an authenticated user (or anonymous)
			isAuthenticated (boolean) authentication status of a user
		
	Output:
		status: (integer) 0:error 1:success 2:warning
		data:
			lyr_id: (list of integers) a list of layer ids
			lyr_name: (list of strings) a list of layer names
			lyr_group_name: (list of strings) a list of layer group names
	
	"""
	
	models,data,app,cookies = utility.getInput(request) # get the input and models
	
	# perform function logic
	try:
	
		# get the user profile
		userProfileObj,status = utility.getUserProfile(cookies)
		
		# get the layers objects
		authLayerGroups = eval('userProfileObj.'+app+'_layer_groups.values_list("name",flat=True)')
		layersObj = models.layers.objects.select_related('layer_group__name').filter(deleted=False,layer_group__name__in=authLayerGroups).order_by('pk').values_list('pk','name','layer_group__name')
		
		# unzip layers
		outLayersObj = zip(*layersObj)
	
		# return the output
		return utility.response(1,{'lyr_id':outLayersObj[0],'lyr_name':outLayersObj[1],'lyr_group_name':outLayersObj[2]},{})
		
	except:
		return utility.errorCheck(sys)

def getLayerPoints(request):
	""" Returns all layer points for the input parameters.
	
	Input:
		location: (string) the location name of the output points
		season: (string) the season name of the output points
		segment_id: (integer) the segment id of the output points
			OR
		segment: (string) the segment name of the output points
		
			OR
			
		point_path_id: (integer, list of integers) point path ids for output points
		
	Optional Inputs:
		lyr_name: (string or list of strings) the layer names of the output
			default: all layers that are not deleted and have a public group
		
		start_gps_time: (float) the first gps time to limit the output points
		stop_gps_time: (float) the last gps time to limit the output points
			default: entire gps time range of the given segment
		
		return_geom: (string) 'geog' or 'proj' to include either lat/lon/elev or x/y/elev in the output
			If return_geom = 'proj' variable location MUST be included
		
	Output:
		status: (integer) 0:error 1:success 2:warning
		data:
			point_path_id: (integer or list of integers) point path ids of the output points
			lyr_id: (integer or list of integers) layer ids of the output points
			gps_time: (float or list of floats) gps times of the output points
			twtt: (integer or list of integers) two-way travel time of the output points
			type: (integer or list of integers) pick type of the output points
			quality: (integer or list of integers) quality of the output points
		
	Optional Outputs:
		lat/y: (float or list of floats) 
		lon/x: (float or list of floats)
		elev: (float or list of floats)
	
	If point_path_id is given location, season, segment or segment_id and start/stop_gps_time will be ignored.
	
	"""
	models,data,app,cookies = utility.getInput(request) # get the input and models

	# parse the data input
	try:

		usePointPathIds = True
		inPointPathIds = data['properties']['point_path_id']

	except:

		usePointPathIds = False

		# parse optional inputs (dependent of point_path_id)
		try:

			inLocationName = data['properties']['location']
			inSeasonName = data['properties']['season']

			try:

				segName = False
				inSegment = data['properties']['segment_id']

			except:

				segName = True
				inSegment = data['properties']['segment']

			try:

				useAllGps = False
				inStartGpsTime = data['properties']['start_gps_time']
				inStopGpsTime = data['properties']['stop_gps_time']

			except:

				useAllGps = True

		except:
			return utility.errorCheck(sys)

	# parse additional optional inputs (not dependent on point_path_id)
	try:

		useAllLyr = False
		inLyrNames = utility.forceList(data['properties']['lyr_name'])

	except:

		useAllLyr = True

	try:

		returnGeom = True
		inGeomType = data['properties']['return_geom']
		if inGeomType == 'proj':
			inLocationName = data['properties']['location']

	except:

		returnGeom = False


	# perform function logic
	try:

		if not usePointPathIds:

			# get a segment object with a pk field
			if segName:
				segmentsObj = models.segments.objects.filter(name=inSegment)
				segmentId = segmentsObj.pk
			else:
				segmentId = inSegment

			# get the start/stop gps times
			if useAllGps:
				pointPathsObj = models.point_paths.objects.filter(segment_id=segmentId,location__name=inLocationName).aggregate(Max('gps_time'),Min('gps_time'))
				inStartGpsTime = inPointPathsObj['gps_time__max']
				inStopGpsTime = inPointPathsObj['gps_time__min']

			# get the point path ids
			inPointPathIds = models.point_paths.objects.filter(segment_id=segmentId,location__name=inLocationName,gps_time__range=(inStartGpsTime,inStopGpsTime)).values_list('pk',flat=True)

		# get a layers object
		if useAllLyr:
			layerIds = models.layers.objects.filter(deleted=False,layer_group__public=True).values_list('pk',flat=True)
		else:
			layerIds = models.layers.objects.filter(name__in=inLyrNames,deleted=False,layer_group__public=True).values_list('pk',flat=True)

		if not returnGeom:

			# get a layer points object (no geometry)
			layerPointsObj = models.layer_points.objects.select_related('point_path__gps_time').filter(point_path_id__in=inPointPathIds,layer_id__in=layerIds).values_list('point_path','layer_id','point_path__gps_time','twtt','type','quality')

			if len(layerPointsObj) == 0:
				return utility.response(2,'WARNING: NO LAYER POINTS FOUND FOR THE GIVEN PARAMETERS.')

			layerPoints = zip(*layerPointsObj) # unzip the layerPointsObj

			# return the output
			return utility.response(1,{'point_path_id':layerPoints[0],'lyr_id':layerPoints[1],'gps_time':layerPoints[2],'twtt':layerPoints[3],'type':layerPoints[4],'quality':layerPoints[5]},{})

		else:

			# get a layer points object (with geometry)
			layerPointsObj = models.layer_points.objects.select_related('point_path__gps_time','point_path__geom').filter(point_path_id__in=inPointPathIds,layer_id__in=layerIds).values_list('point_path','layer_id','point_path__gps_time','twtt','type','quality','point_path__geom')

			if len(layerPointsObj) == 0:
				return utility.response(2,'WARNING: NO LAYER POINTS FOUND FOR THE GIVEN PARAMETERS.')

			pointPathId,layerIds,gpsTimes,twtts,types,qualitys,pointPaths = zip(*layerPointsObj) # unzip the layerPointsObj

			outLon = []; outLat = []; outElev = [];
			for pointObj in pointPaths:
				ptGeom = GEOSGeometry(pointObj)
				if inGeomType == 'proj':
					epsg = utility.epsgFromLocation(inLocationName) # get the input epsg
					ptGeom.transform(epsg)
				outLon.append(ptGeom.x);
				outLat.append(ptGeom.y);
				outElev.append(ptGeom.z);

			# return the output
			return utility.response(1,{'point_path_id':pointPathId,'lyr_id':layerIds,'gps_time':gpsTimes,'twtt':twtts,'type':types,'quality':qualitys,'lon':outLon,'lat':outLat,'elev':outElev},{})

	except:
		return utility.errorCheck(sys)

def getLayerPointsCsv(request):
	""" Creates a CSV file from layer points and writes it to the server.
	
	Input:
		bound: (WKT) well-known text polygon geometry
		location: (string) name of the location to return points for
		
	Optional Inputs:
		allPoints: (boolean) if True all points (csv type) are used instead of the default only bed (csv-good type)
		startseg: (string) a segment name to limit the output
		stopseg: (string) a segment name to limit the output
		season: (string or list of string) a/ season name to limit the output
		
	Output:
		status: (integer) 0:error 1:success 2:warning
		data:  url to [L2CSV].csv on the server
		
	Output is limited to 2 million points
	
	"""
	models,data,app,cookies = utility.getInput(request) # get the input and models
	
	# parse the data input
	try:
	
		inLocationName = data['properties']['location']
		inBoundaryWkt = data['properties']['bound']
		
		# parse the optional data input
		try:
			inStartSeg = data['properties']['startseg']
			inStopSeg = data['properties']['stopseg']
		except:
			inStartSeg = '00000000_00'
			inStopSeg = '99999999_99'
		
		try:
			inSeasons = utility.forceList(data['properties']['season'])
		except:
			inSeasons = models.seasons.objects.filter(season_group__public=True).values_list('name',flat=True)
			
		try:
			getAllPoints = data['properties']['allPoints']
		except:
			getAllPoints = False
	
	except:
		utility.errorCheck(sys)

	# perform function logic
	try:
	
		inPoly = GEOSGeometry(inBoundaryWkt, srid=4326) # create a polygon geometry object
	
		# get the point paths that match the input filters
		pointPathsObj = models.point_paths.objects.select_related('season__name','frame__name').filter(location__name=inLocationName,season__name__in=inSeasons,segment__name__range=(inStartSeg,inStopSeg),geom__within=inPoly).order_by('frame__name','gps_time').values_list('pk','gps_time','roll','pitch','heading','geom','season__name','frame__name')[:2000000]
		
		# unzip the pointPathsObj into lists of values
		ppIds,ppGpsTimes,ppRolls,ppPitchs,ppHeadings,ppPaths,ppSeasonNames,ppFrameNames = zip(*pointPathsObj)
		del pointPathsObj
		
		# force the outputs to be lists (handles single element results)
		utility.forceList(ppIds)
		utility.forceList(ppGpsTimes)
		utility.forceList(ppRolls)
		utility.forceList(ppPitchs)
		utility.forceList(ppHeadings)
		utility.forceList(ppPaths)
		utility.forceList(ppSeasonNames)
		utility.forceList(ppFrameNames)

		# get layer points (surface and bottom) for the filtered point path ids
		layerPointsObj = models.layer_points.objects.filter(point_path_id__in=ppIds,layer_id__in=[1,2]).values_list('pk','layer_id','point_path_id','twtt','type','quality')
		
		# unzip the layerPointsObj into lists of values
		lpIds,lpLyrIds,lpPpIds,lpTwtts,lpTypes,lpQualitys = zip(*layerPointsObj)
		del layerPointsObj
		
		# force the outputs to be lists (handles single element results)
		utility.forceList(lpIds)
		utility.forceList(lpLyrIds)
		utility.forceList(lpPpIds)
		utility.forceList(lpTwtts)
		utility.forceList(lpTypes)
		utility.forceList(lpQualitys)
		
		badCount = 0 # create a counter for bad data
		
		# build output lists
		outLat = []; outLon = []; outElev = []; outRoll = []; outPitch = []; outHeading = []; outSeason = []; outFrame = [];
		outSurface = []; outBottom = []; outSurfaceType = []; outBottomType = []; outSurfaceQuality = []; outBottomQuality = [];
		outThickness = []; outUtcSod = []; outUtcDate = [];
		
		for ppIdx,ppId in enumerate(ppIds):
		
			# get the indexes in layerPointsData for ppId
			lpIdxs = [idx for idx in range(len(lpPpIds)) if lpPpIds[idx] == ppId]
			
			if not lpIdxs: # if there are no layer points for the point path, go to the next point path
				continue
				
			lyrIds = [lpLyrIds[idx] for idx in lpIdxs] # get the layer ids of the matched point path layer points
			
			if 1 in lyrIds and 2 in lyrIds: # write both surface and bottom values
				
				# get the surface and bottom idxs
				surfIdx = lpIdxs[lyrIds.index(1)]
				bottIdx = lpIdxs[lyrIds.index(2)]

				# write the values
				outLat.append(ppPaths[ppIdx].x)
				outLon.append(ppPaths[ppIdx].y)
				outElev.append(ppPaths[ppIdx].z)
				outRoll.append(ppRolls[ppIdx])
				outPitch.append(ppPitchs[ppIdx])
				outHeading.append(ppHeadings[ppIdx])
				outSeason.append(ppSeasonNames[ppIdx])
				outFrame.append(ppFrameNames[ppIdx])
				outSurface.append(lpTwtts[surfIdx])
				outSurfaceType.append(int(lpTypes[surfIdx]))
				outSurfaceQuality.append(int(lpQualitys[surfIdx]))
				outBottom.append(lpTwtts[bottIdx])
				outBottomType.append(int(lpTypes[bottIdx]))
				outBottomQuality.append(int(lpQualitys[bottIdx]))
				
				# calculate surface and bottom elevation from twtt
				try:
					surfElev,bottElev = utility.twttToElev(outSurface[-1],outBottom[-1])
					outSurface[-1] = surfElev
					outBottom[-1] = bottElev
				except:
					return utility.response(0,[outSurface[-1],outBottom[-1],ppId],{})
					
				
				# calculate ice thickness
				outThick = outBottom[-1]-outSurface[-1]
				if outThick < 0.0:
					outThick = 0.0
					outBottom[-1] = outSurface[-1]
				outThickness.append(outThick)
				
				# calculate utc date and seconds of day
				utcDateStruct = time.gmtime(ppGpsTimes[ppIdx])
				outUtcDate.append(time.strftime('%Y%m%d',utcDateStruct))
				outUtcSod.append(float(utcDateStruct.tm_hour*3600.0 + utcDateStruct.tm_min*60.0 + utcDateStruct.tm_sec))
				
				# calculate utc seconds of day
				#utcTime = datetime.datetime.utcfromtimestamp(ppGpsTimes[ppIdx]) - datetime.datetime.strptime(ppFrameNames[ppIdx][:-7],'%Y%m%d')
				#outUtcSod.append(utcTime.seconds + (utcTime.microseconds/1000000.0))
				
			elif 1 in lyrIds and getAllPoints: # write surface values and fill in nodata
				
				# get the surface idx
				surfIdx = lpIdxs[lyrIds.index(1)]

				# write the values
				outLat.append(ppPaths[ppIdx].x)
				outLon.append(ppPaths[ppIdx].y)
				outElev.append(ppPaths[ppIdx].z)
				outRoll.append(ppRolls[ppIdx])
				outPitch.append(ppPitchs[ppIdx])
				outHeading.append(ppHeadings[ppIdx])
				outSeason.append(ppSeasonNames[ppIdx])
				outFrame.append(ppFrameNames[ppIdx])
				outSurface.append(lpTwtts[surfIdx])
				outSurfaceType.append(lpTypes[surfIdx])
				outSurfaceQuality.append(lpQualitys[surfIdx])
				outBottom.append(np.nan)
				outBottomType.append(np.nan)
				outBottomQuality.append(np.nan)
				
				# calculate surface and bottom elevation from twtt
				surfElev,_ = utility.twttToElev(outSurface[-1],outSurface[-1])
				outSurface[-1] = surfElev
				
				# calculate ice thickness
				outThickness.append(np.nan)
				
				# calculate utc date and seconds of day
				utcDateStruct = time.gmtime(ppGpsTimes[ppIdx])
				outUtcDate.append(time.strftime('%Y%m%d',utcDateStruct))
				outUtcSod.append(float(utcDateStruct.tm_hour*3600.0 + utcDateStruct.tm_min*60.0 + utcDateStruct.tm_sec))
				
				# calculate utc seconds of day
				#utcTime = datetime.datetime.utcfromtimestamp(ppGpsTimes[ppIdx]) - datetime.datetime.strptime(ppFrameNames[ppIdx][:-7],'%Y%m%d')
				#outUtcSod.append(utcTime.seconds + (utcTime.microseconds/1000000.0))
				
			elif 2 in lyrIds:
				# bottom found with no surface
				return utility.response(0,'ERROR: BOTTOM WITH NO SURFACE AT POINT PATH ID %d. PLEASE REPORT THIS.'%ppId,{})
			else:
				badCount += 1 # no surface or bottom found for point path id

		# make sure there was some data
		if badCount == len(ppIds):
			return utility.response(0,'ERROR: NO DATA FOUND THAT MATCHES THE SEARCH PARAMETERS',{})
		
		# clear some memory
		del lpIds,lpLyrIds,lpPpIds,lpTwtts,lpTypes,lpQualitys,ppIds,ppGpsTimes,ppRolls,ppPitchs,ppHeadings,ppPaths,ppSeasonNames,ppFrameNames

		# generate the output csv information
		serverDir = '/cresis/snfs1/web/ops2/data/csv/'
		webDir = 'data/csv/'
		if getAllPoints:
			tmpFn = 'OPS_CReSIS_L2_CSV_' + utility.randId(10) + '.csv'
		else:
			tmpFn = 'OPS_CReSIS_L2_CSV_GOOD_' + utility.randId(10) + '.csv'
		webFn = webDir + tmpFn
		serverFn  = serverDir + tmpFn
		
		# create the csv header
		csvHeader = ['LAT','LON','ELEVATION','ROLL','PITCH','HEADING','UTCSOD','UTCDATE','SURFACE','BOTTOM','THICKNESS',\
		'SURFACE_TYPE','BOTTOM_TYPE','SURFACE_QUALITY','BOTTOM_QUALITY','SEASON','FRAME']
		
		# write the csv file
		with open(serverFn,'wb') as csvFile:
			csvWriter = csv.writer(csvFile,delimiter=',',quoting=csv.QUOTE_NONE)
			csvWriter.writerow(csvHeader)
			for outIdx in range(len(outUtcSod)):
				csvWriter.writerow([
					"%.8f" % outLat[outIdx],
					"%.8f" % outLon[outIdx],
					"%.5f" % outElev[outIdx],
					"%.5f" % outRoll[outIdx],
					"%.5f" % outPitch[outIdx],
					"%.5f" % outHeading[outIdx],
					"%.3f" % outUtcSod[outIdx],
					outUtcDate[outIdx],
					"%.3f" % outSurface[outIdx],
					"%.3f" % outBottom[outIdx],
					"%.3f" % outThickness[outIdx],
					outSurfaceType[outIdx],
					outBottomType[outIdx],
					outSurfaceQuality[outIdx],
					outBottomQuality[outIdx],
					outSeason[outIdx],
					outFrame[outIdx],
				])
		
		# return the output
		return utility.response(1,webFn,{})
		
	except:
		return utility.errorCheck(sys)

def getLayerPointsKml(request):
	""" Creates a KML file of point paths and writes it to the server.
	
	Input:
		bound: (WKT) well-known text polygon geometry
		location: (string) name of the location to return points for
		
	Optional Inputs:
		startseg: (string) a segment name to limit the output
		stopseg: (string) a segment name to limit the output
		season: (string or list of string) a/ season name to limit the output
		
	Output:
		status: (integer) 0:error 1:success 2:warning
		data:  url to [L2KML].kml on the server
		
	Output is limited to 5 million points
	
	"""
	models,data,app,cookies = utility.getInput(request) # get the input and models
	
	# parse the data input
	try:
	
		inLocationName = data['properties']['location']
		inBoundaryWkt = data['properties']['bound']
		
		# parse the optional data input
		try:
			inStartSeg = data['properties']['startseg']
			inStopSeg = data['properties']['stopseg']
		except:
			inStartSeg = '00000000_00'
			inStopSeg = '99999999_99'
		
		try:
			inSeasonNames = utility.forceList(data['properties']['season'])
			useAllSeasons = False
		except:
			useAllSeasons = True
	
	except:
		utility.errorCheck(sys)

	# perform function logic
	try:
	
		if useAllSeasons:
		
			inSeasonNames = models.seasons.objects.filter(location_id__name=inLocationName,season_group__public=True).values_list('name',flat=True) # get all the public seasons
	
		inPoly = GEOSGeometry(inBoundaryWkt, srid=4326) # create a polygon geometry object
	
		# get the segments object
		segmentsObj = models.segments.objects.filter(season_id__name__in=inSeasonNames,name__range=(inStartSeg,inStopSeg),geom__intersects=inPoly).values_list('name','geom')
		
		segmentNames,segmentPaths = zip(*segmentsObj) # unzip the segmentsObj
		del segmentsObj
		
		kmlObj = simplekml.Kml() # create a new kml object
		kmlDoc = kmlObj.newdocument(name='OPS CReSIS KML DATA') # create a new kml document
		
		# add the segments as linestrings to the kml document
		for segIdx in range(len(segmentNames)):
			newLineString = kmlDoc.newlinestring(name=segmentNames[segIdx])
			newLineString.coords = list(segmentPaths[segIdx].coords)
			newLineString.style.linestyle.color = simplekml.Color.blue
		
		# generate the output kml information
		serverDir = '/cresis/snfs1/web/ops2/data/kml/'
		webDir = 'data/kml/'
		tmpFn = 'OPS_CReSIS_L2_KML_' + utility.randId(10) + '.kml'
		webFn = webDir + tmpFn
		serverFn  = serverDir + tmpFn
		
		kmlObj.save(serverFn) # save the kml
		
		# return the output
		return utility.response(1,webFn,{})
	
	except:
		return utility.errorCheck(sys)

def getLayerPointsMat(request):
	""" Creates a MAT file of layer points and writes it to the server.
	
	Input:
		bound: (WKT) well-known text polygon geometry
		location: (string) name of the location to return points for
		
	Optional Inputs:
		layers: (string or list of string) layers to include in the output (default = surface,bottom)
		startseg: (string) a segment name to limit the output
		stopseg: (string) a segment name to limit the output
		season: (string or list of string) a/ season name to limit the output
		
	Output:
		status: (integer) 0:error 1:success 2:warning
		data:  url to [L2MAT].mat on the server
		
	Output is limited to 2 million points
	All points will be returned (csv type) and there may be NaN values for layers.
	
	"""
	models,data,app,cookies = utility.getInput(request) # get the input and models
	
	# parse the data input
	try:
		inLocationName = data['properties']['location']
		inBoundaryWkt = data['properties']['bound']
		
		# parse the optional data input
		try:
			inStartSeg = data['properties']['startseg']
			inStopSeg = data['properties']['stopseg']
		except:
			inStartSeg = '00000000_00'
			inStopSeg = '99999999_99'
		
		try:
			inLayers = utility.forceList(data['properties']['layers'])
		except:
			inLayers = models.layers.objects.filter(layer_group__public=True,name='surface').values_list('name',flat=True)

		try:
			inSeasons = utility.forceList(data['properties']['season'])
		except:
			inSeasons = models.seasons.objects.filter(season_group__public=True).values_list('name',flat=True)
		
	except:
		return utility.errorCheck(sys)
	
	# perform the function logic
	try:
	
		# make sure surface and bottom are in the layers list
		if 'surface' not in inLayers:
			inLayers.append('surface')
			
		inPoly = GEOSGeometry(inBoundaryWkt, srid=4326) # create a polygon geometry object
	
		# get the point paths that match the input filters
		pointPathsObj = models.point_paths.objects.select_related('season__name','frame__name').filter(location__name=inLocationName,season__name__in=inSeasons,segment__name__range=(inStartSeg,inStopSeg),geom__within=inPoly).order_by('frame__name','gps_time').values_list('pk','gps_time','roll','pitch','heading','geom','season__name','frame__name')[:2000000]
		
		# unzip the pointPathsObj into lists of values
		ppIds,ppGpsTimes,ppRolls,ppPitchs,ppHeadings,ppPaths,ppSeasonNames,ppFrameNames = zip(*pointPathsObj)
		del pointPathsObj
		
		# force the outputs to be lists (handles single element results)
		ppIds = utility.forceList(ppIds)
		ppGpsTimes = utility.forceList(ppGpsTimes)
		ppRolls = utility.forceList(ppRolls)
		ppPitchs = utility.forceList(ppPitchs)
		ppHeadings = utility.forceList(ppHeadings)
		ppPaths = utility.forceList(ppPaths)
		ppSeasonNames = utility.forceList(ppSeasonNames)
		ppFrameNames = utility.forceList(ppFrameNames)
		
		# get layer points (surface and bottom) for the filtered point path ids
		layerPointsObj = models.layer_points.objects.select_related('layer__name').filter(point_path_id__in=ppIds,layer_id__name__in=inLayers).values_list('pk','layer_id','point_path_id','twtt','type','quality','layer__name')
		
		# unzip the layerPointsObj into lists of values
		lpIds,lpLyrIds,lpPpIds,lpTwtts,lpTypes,lpQualitys,lpLyrNames = zip(*layerPointsObj)
		del layerPointsObj
		
		# force the outputs to be lists (handles single element results)
		lpIds = utility.forceList(lpIds)
		lpLyrIds = utility.forceList(lpLyrIds)
		lpPpIds = utility.forceList(lpPpIds)
		lpTwtts = utility.forceList(lpTwtts)
		lpTypes = utility.forceList(lpTypes)
		lpQualitys = utility.forceList(lpQualitys)
		lpLyrNames = utility.forceList(lpLyrNames)
		
		# create output data structure
		outLayers = OrderedDict()
		
		# write surface and bottom to output structure
		outLayers['surface'] = {'name':'surface','elev':np.empty(0,dtype='float64'),'type':np.empty(0,dtype='float16'),'quality':np.empty(0,dtype='float16')}
		
		# write the rest of the layers to the output structure
		for lyrName in list(set(lpLyrNames)):
			if lyrName not in ['surface']:
				outLayers[str(lyrName)] = {'name':str(lyrName),'elev':np.empty(0,dtype='float64'),'type':np.empty(0,dtype='float16'),'quality':np.empty(0,dtype='float16')}
		
		# create additional output arrays
		outLat = np.empty(0,dtype='float64'); outLon = np.empty(0,dtype='float64'); outElev = np.empty(0,dtype='float64'); outRoll = np.empty(0,dtype='float64'); outPitch = np.empty(0,dtype='float64'); outHeading = np.empty(0,dtype='float64'); outSeason = np.empty(0,dtype=object); outFrame = np.empty(0,dtype=object); outUtcSod = np.empty(0,dtype='float64'); outUtcDate = np.empty(0,dtype=object)
		
		# set up count for point paths with no surface
		noSurfaceCount = 0
		
		# process the data for each point path
		for ppIdx,ppId in enumerate(ppIds):
		
			# find the layer points for the current point path
			lpPpIdxs = [idx for idx in range(len(lpPpIds)) if lpPpIds[idx] == ppId]
			
			if not lpPpIdxs: # make sure there are layer points for the point path
				continue
				
			# get the layer names, and layer point indexes for each layer point found
			lpPpLyrNames,lpIdx = zip(*[[lpLyrNames[idx],idx] for idx in lpPpIdxs])
			
			# if there is a surface in the found layer names write the output
			if 'surface' in lpPpLyrNames:
			
				# append point path information to the output arrays
				outLat = np.append(outLat,float(ppPaths[ppIdx].x))
				outLon = np.append(outLon,float(ppPaths[ppIdx].y))
				outElev = np.append(outElev,float(ppPaths[ppIdx].z))
				outRoll = np.append(outRoll,float(ppRolls[ppIdx]))
				outPitch = np.append(outPitch,float(ppPitchs[ppIdx]))
				outHeading = np.append(outHeading,float(ppHeadings[ppIdx]))
				outSeason = np.append(outSeason,ppSeasonNames[ppIdx])
				outFrame = np.append(outFrame,ppFrameNames[ppIdx])
				
				# calculate utc date and seconds of day
				utcDateStruct = time.gmtime(ppGpsTimes[ppIdx])
				outUtcDate = np.append(outUtcDate,time.strftime('%Y%m%d',utcDateStruct))
				outUtcSod = np.append(outUtcSod,float(utcDateStruct.tm_hour*3600.0 + utcDateStruct.tm_min*60.0 + utcDateStruct.tm_sec))
				
				# write the surface record to the output layers structure
				surfTwtt = lpTwtts[lpIdx[lpPpLyrNames.index('surface')]]
				_,surfElev = utility.twttToElev(surfTwtt,surfTwtt)
				outLayers['surface']['elev'] = np.append(outLayers['surface']['elev'],float(surfElev))
				outLayers['surface']['type'] = np.append(outLayers['surface']['type'],lpTypes[lpPpLyrNames.index('surface')])
				outLayers['surface']['quality'] = np.append(outLayers['surface']['quality'],lpQualitys[lpPpLyrNames.index('surface')])
				
				# write each additional (non-surface) records to the output layers structure
				for lyrName in set(lpLyrNames):
					if lyrName not in ['surface']: # write the records (data or nans)
						if lyrName in lpPpLyrNames:
							lyrTwtt = lpTwtts[lpIdx[lpPpLyrNames.index(lyrName)]]
							_,lyrElev = utility.twttToElev(surfTwtt,lyrTwtt)
							outLayers[lyrName]['elev'] = np.append(outLayers[lyrName]['elev'],float(lyrElev))
							outLayers[lyrName]['type'] = np.append(outLayers[lyrName]['type'],lpTypes[lpPpLyrNames.index(lyrName)])
							outLayers[lyrName]['quality'] = np.append(outLayers[lyrName]['quality'],lpQualitys[lpPpLyrNames.index(lyrName)])
						else:
							outLayers[lyrName]['elev'] = np.append(outLayers[lyrName]['elev'],np.nan)
							outLayers[lyrName]['type'] = np.append(outLayers[lyrName]['type'],np.nan)
							outLayers[lyrName]['quality'] = np.append(outLayers[lyrName]['quality'],np.nan)
			else:
				noSurfaceCount += 1 # no surface exists
						
		# make sure there was some data
		if noSurfaceCount == len(ppIds):
			return utility.response(0,'ERROR: NO DATA FOUND THAT MATCHES THE SEARCH PARAMETERS',{})
		
		# clear some memory
		del lpIds,lpLyrIds,lpPpIds,lpTwtts,lpTypes,lpQualitys,ppIds,ppGpsTimes,ppRolls,ppPitchs,ppHeadings,ppPaths,ppSeasonNames,ppFrameNames,lpLyrNames,lpPpLyrNames
		
		# generate the output mat information
		serverDir = '/cresis/snfs1/web/ops2/data/mat/'
		webDir = 'data/mat/'
		tmpFn = 'OPS_CReSIS_L2_MAT_' + utility.randId(10) + '.mat'
		webFn = webDir + tmpFn
		serverFn  = serverDir + tmpFn
		
		# format outLayers
		outLayerList = []
		for key in outLayers:
			outLayerList.append(outLayers[key])
		
		# create the mat python dictionary
		outMatData = {'lat':outLat,'lon':outLon,'elev':outElev,'roll':outRoll,'pitch':outPitch,'heading':outHeading,'season':outSeason,'frame':outFrame,'utcsod':outUtcSod,'utcdate':outUtcDate,'layers':outLayerList}
		
		# write the mat file
		savemat(serverFn,outMatData,True,'5',False,True,'row')
		
		# return the output
		return utility.response(1,webFn,{})
	
	except:
		return utility.errorCheck(sys)

def getLayerPointsNetcdf(request):
	""" Creates a NetCDF file of layer points and writes it to the server.
	
	Input:
		bound: (WKT) well-known text polygon geometry
		location: (string) name of the location to return points for
		
	Optional Inputs:
		layers: (string or list of string) layers to include in the output (default = surface,bottom)
		startseg: (string) a segment name to limit the output
		stopseg: (string) a segment name to limit the output
		season: (string or list of string) a/ season name to limit the output
		
	Output:
		status: (integer) 0:error 1:success 2:warning
		data:  url to [L2NETCDF].nc on the server
		
	Output is limited to 2 million points
	All points will be returned (csv type) and there may be NaN values for layers.
	
	"""
	try:
	
		return utility.response(1,'NetCDF Output Is Not Implemented',{})

	except:
		return utility.errorCheck(sys)

def getSystemInfo(request): 
	"""Get basic information about data in the OPS.
	
	Input:
		app: (none)
		data:
			FROM GEOPORTAL: (none)
			FROM MATLAB:
				mat: (boolean) true
				userName: (string) username of an authenticated user (or anonymous)
				isAuthenticated (boolean) authentication status of a user
		
	Output:
		status: (integer) 0:error 1:success 2:warning
		data: list of dictionary objects of the form:
			{'system':[string],'season':[string],'location':[string]}

	"""
	
	models,data,app,cookies = utility.getInput(request) # get the input and models
	
	# perform the function logic
	try:
	
		# get the user profile
		userProfileObj,status = utility.getUserProfile(cookies)
		
		from ops.settings import INSTALLED_APPS as apps # get a list of all the apps

		outData = []
		
		for app in apps:
			if app.startswith(('rds','snow','accum','kuband')):

				models = utility.getAppModels(app) # get the models

				# get all of the seasons (and location)
				authSeasonGroups = eval('userProfileObj.'+app+'_season_groups.values_list("name",flat=True)')
				seasonsObj = models.seasons.objects.select_related('locations__name').filter(season_group__name__in=authSeasonGroups).values_list('name','location__name')

				# if there are seasons populate the outData list
				if not (len(seasonsObj) == 0):

					data = zip(*seasonsObj)
					
					for dataIdx in range(len(data[0])):

						outData.append({'system':app,'season':data[0][dataIdx],'location':data[1][dataIdx]})

		# return the output
		return utility.response(1,outData,{})
		
	except:
		return utility.errorCheck(sys)

def getSegmentInfo(request):
	""" Get information about a given segment from the OPS.
	
	Input:
		segment_id: segment id of a segment in the segments table
		
	Output:
		status: (integer) 0:error 1:success 2:warning
		data:
			season: (string) name of the season of the given segment
			segment: (string) name of the given segment
			frame: (list of strings) names of the frames of the given segment
			start_gps_time: (list of floats) start gps time of each frame
			stop_gps_time: (list of floats) stop gps time of each frame
	
	"""
	models,data,app,cookies = utility.getInput(request) # get the input and models
	
	# parse the input data
	try:
		inSegmentId = data['properties']['segment_id']
	except:
		utility.errorCheck(sys)
	
	# perform the function logic
	try:
	
		# get the segment name, season name, frame names, and frame ids
		pointPathsObj = models.point_paths.objects.select_related('seasons__name','segments__name','frames__name').filter(segment_id=inSegmentId).order_by('frame').distinct('frame').values_list('season__name','segment__name','frame__name','frame')
		
		seasonNames,segmentNames,frameNames,frameIds = zip(*pointPathsObj) # extract all the elements
		
		if len(frameNames) < 1:
			return utility.response(2,'WARNING: NO FRAMES FOUND FOR THE GIVEN SEGMENT ID',{}) # return if there are no frames
		
		# for each frame get max/min gps_time from point paths
		startGpsTimes = []
		stopGpsTimes = []
		for frmId in frameIds:
			pointPathGpsTimes = models.point_paths.objects.filter(frame_id=frmId).values_list('gps_time',flat=True)
			startGpsTimes.append(min(pointPathGpsTimes))
			stopGpsTimes.append(max(pointPathGpsTimes))
		
		# return the output
		return utility.response(1,{'season':seasonNames[0],'segment':segmentNames[0],'frame':frameNames,'start_gps_time':startGpsTimes,'stop_gps_time':stopGpsTimes},{})
			
	except:
		return utility.errorCheck(sys)

def getCrossovers(request): 
	""" Get crossover values from the OPS.
	
	Input:
		location: (string)
		lyr_name: (string or list of strings)
		
		point_path_id: (integer or list of integers)
			OR
		frame: (string or list of strings)
		
	Output:
		status: (integer) 0:error 1:success 2:warning
		data:
			source_point_path_id: (list of integer/s) point path ids of the source points
			cross_point_path_id: (list of integer/s) point path ids of the crossovers
			source_elev: (list of float/s) aircraft elevation of the source points
			cross_elev: (list of float/s) aircraft elevation of the crossovers
			layer_id: (list of integer/s) layer ids of the crossovers
			season_name: (list of string/s) season names of the crossovers
			frame_name: (list of string/s) frame names of the crossovers
			segment_id: (list of integer/s) segment ids of the crossovers
			twtt: (list of float/s) two-way travel time of the crossovers
			angle: (list of float/s) acute angle (degrees) of the crossovers path
			abs_error: (list of float/s) absolute difference (meters) between the source and crossover layer points
		
	"""
	models,data,app,cookies = utility.getInput(request) # get the input and models
	
	# parse the data input
	try:
		inLocationName = utility.forceList(data['properties']['location'])
		inLayerNames = utility.forceList(data['properties']['lyr_name'])
		try:
			getPointPathIds = False
			inPointPathIds = utility.forceTuple(data['properties']['point_path_id'])
		except:
			try:
				getPointPathIds = True
				inFrameNames = utility.forceList(data['properties']['frame'])
			except:
				return utility.response(0,'ERROR: EITHER POINT PATH IDS OR FRAME NAMES MUST BE GIVEN',{})
	except:
		return utility.errorCheck(sys)
	
	# perform the function logic
	try:
		#Get layer ids: 
		layerIds = utility.forceTuple(list(models.layers.objects.filter(name__in=inLayerNames).values_list('pk',flat=True)))
		
		if getPointPathIds:
		
			# get the point path ids based on the given frames
			inPointPathIds = utility.forceTuple(list(models.point_paths.objects.filter(frame_id__name__in=inFrameNames,location__name__in=inLocationName).values_list('pk',flat=True)))

		cursor = connection.cursor() # create a database cursor
		
		# get all of the data needed for crossovers
		try:
			sql_str = "SELECT point_path_1_id, point_path_2_id, ST_Z(point_path_1_geom), ST_Z(point_path_2_geom),layer_id, frame_1_name, frame_2_name, segment_1_id, segment_2_id, twtt_1, twtt_2, angle, ABS(layer_elev_1-layer_elev_2) AS error,season_1_name,season_2_name FROM {app}_crossover_errors WHERE (point_path_1_id IN %s OR point_path_2_id IN %s) AND (layer_id IN %s OR layer_id IS NULL) UNION SELECT cx.point_path_1_id, cx.point_path_2_id, ST_Z(pp1.geom),ST_Z(pp2.geom), NULL AS layer_id, frm1.name AS frame_1_name, frm2.name AS frame_2_name, pp1.segment_id AS segment_1_id, pp2.segment_id AS segment_2_id, NULL AS twtt_1, NULL AS twtt_2, cx.angle, NULL AS error, s1.name AS season_1_name, s2.name AS season_2_name FROM {app}_crossovers cx JOIN {app}_point_paths pp1 ON cx.point_path_1_id=pp1.id JOIN {app}_point_paths pp2 ON cx.point_path_2_id=pp2.id JOIN {app}_frames frm1 ON pp1.frame_id=frm1.id JOIN {app}_frames frm2 ON pp2.frame_id=frm1.id JOIN {app}_seasons s1 ON pp1.season_id=s1.id JOIN {app}_seasons s2 ON pp2.season_id=s2.id WHERE (cx.point_path_1_id IN %s OR cx.point_path_2_id IN %s) AND cx.id NOT IN (SELECT cross_id FROM {app}_crossover_errors WHERE layer_id IN %s OR layer_id IS NULL);".format(app=app)
			cursor.execute(sql_str,[inPointPathIds,inPointPathIds,layerIds,inPointPathIds,inPointPathIds,layerIds])
			crossoverRows = cursor.fetchall() # get all of the data from the query
			
		except DatabaseError as dberror:
			return utility.response(0,dberror[0],{})
		
		finally:
			cursor.close() # close the cursor in case of exception
		if len(crossoverRows) == 0:
			#No crossovers found. Return empty response. 
			return utility.response(1,{'source_point_path_id':[],'cross_point_path_id':[],'source_elev':[],'cross_elev':[],'layer_id':[],'season_name':[],'segment_id':[],'frame_name':[],'twtt':[],'angle':[],'abs_error':[]},{}) 
			
		# set up for the creation of outputs
		sourcePointPathIds = []; crossPointPathIds = []; sourceElev = []; crossElev = []; 
		crossTwtt = []; crossAngle = []; crossFrameName = []; layerId = []; absError = [];
		crossSeasonName = []; crossSegmentId = [];
		
		for crossoverData in crossoverRows: # parse each output row and sort it into either source or crossover outputs
		
			if crossoverData[0] in inPointPathIds:
			
				# point_path_1 is the source
				sourcePointPathIds.append(crossoverData[0])
				sourceElev.append(crossoverData[2])
				
				# point_path_2 is the crossover
				crossPointPathIds.append(crossoverData[1])
				crossElev.append(crossoverData[3])
				crossTwtt.append(crossoverData[10])
				crossAngle.append(crossoverData[11])
				crossSeasonName.append(crossoverData[14])
				crossFrameName.append(crossoverData[6])
				layerId.append(crossoverData[4])
				absError.append(crossoverData[12])
				crossSegmentId.append(crossoverData[8])
			
			else:
			
				# point_path_1 is the crossover
				crossPointPathIds.append(crossoverData[0])
				crossElev.append(crossoverData[2])
				crossTwtt.append(crossoverData[9])
				crossAngle.append(crossoverData[11])
				crossSeasonName.append(crossoverData[13])
				crossFrameName.append(crossoverData[5])
				layerId.append(crossoverData[4])
				absError.append(crossoverData[12])
				crossSegmentId.append(crossoverData[7])
				
				# point_path_2 is the source
				sourcePointPathIds.append(crossoverData[1])
				sourceElev.append(crossoverData[3])
		
		# return the output
		return utility.response(1,{'source_point_path_id':sourcePointPathIds,'cross_point_path_id':crossPointPathIds,'source_elev':sourceElev,'cross_elev':crossElev,'layer_id':layerId,'season_name':crossSeasonName,'segment_id':crossSegmentId,'frame_name':crossFrameName,'twtt':crossTwtt,'angle':crossAngle,'abs_error':absError},{})
		
	except:
		return utility.errorCheck(sys)

def getCrossoversReport(request):
	""" Get crossover error report from the OPS.
	
	Input:
		location: (string)
		lyr_name: (string or list of strings)
		
		seasons: (string or list of strings)
			OR
		point_path_id: (integer or list of integers)
			OR
		frame: (string or list of strings)
		
	Output:
		status: (integer) 0:error 1:success 2:warning
		data: url to crossover report .csv on the server
	"""
	models,data,app,cookies = utility.getInput(request) # get the input and models
	
	# parse the data input
	try:
	
		inLocationName = utility.forceList(data['properties']['location'])
		inLayerNames = utility.forceList(data['properties']['lyr_name'])
		try:
			getPointPathIds = False
			inSeasonNames = utility.forceTuple(data['properties']['seasons'])
		except:
			inSeasonNames = False
			try:
				getPointPathIds = False
				inPointPathIds = utility.forceTuple(data['properties']['point_path_id'])
		
			except:
			
				try:
				
					getPointPathIds = True
					inFrameNames = utility.forceList(data['properties']['frame'])
				
				except:
				
					return utility.response(0,'ERROR: POINT PATH IDS, FRAME NAMES, OR SEASON NAMES MUST BE GIVEN',{})
	
	except:
		return utility.errorCheck(sys)
	
	# perform the function logic
	try:
	#Get layer ids: 
		layerIds = utility.forceTuple(list(models.layers.objects.filter(name__in=inLayerNames).values_list('pk',flat=True)))
			
		if getPointPathIds:
		
			# get the point path ids based on the given frames
			inPointPathIds = utility.forceTuple(list(models.point_paths.objects.filter(frame_id__name__in=inFrameNames,location__name__in=inLocationName).values_list('pk',flat=True)))

		cursor = connection.cursor() # create a database cursor
		try:
			#Create, execute, and retrieve results from query to get crossover error information. 
			if inSeasonNames:
				sql_str = "SELECT ABS(layer_elev_1-layer_elev_2), layer_elev_1, layer_elev_2, twtt_1, twtt_2, angle, (SELECT name FROM {app}_layers WHERE id = layer_id), season_1_name, season_2_name,frame_1_name,frame_2_name, gps_time_1, gps_time_2, ST_X(point_path_1_geom), ST_X(point_path_2_geom), ST_Y(point_path_1_geom), ST_Y(point_path_2_geom), ST_Z(point_path_1_geom), ST_Z(point_path_2_geom), ST_X(geom), ST_Y(geom) FROM {app}_crossover_errors WHERE layer_elev_1 IS NOT NULL AND layer_elev_2 IS NOT NULL AND layer_id IN %s AND (season_1_name IN %s OR season_2_name IN %s);".format(app=app)
				cursor.execute(sql_str,[layerIds,inSeasonNames,inSeasonNames])
			else:
				sql_str = "SELECT ABS(layer_elev_1-layer_elev_2), layer_elev_1, layer_elev_2, twtt_1, twtt_2, angle, (SELECT name FROM {app}_layers WHERE id = layer_id), season_1_name,season_2_name,frame_1_name, frame_2_name, gps_time_1, gps_time_2, ST_X(point_path_1_geom), ST_X(point_path_2_geom), ST_Y(point_path_1_geom), ST_Y(point_path_2_geom), ST_Z(point_path_1_geom), ST_Z(point_path_2_geom), ST_X(geom), ST_Y(geom) FROM {app}_crossover_errors WHERE layer_elev_1 IS NOT NULL AND layer_elev_2 IS NOT NULL AND layer_id IN %s AND (point_path_1_id IN %s OR point_path_2_id IN %s);".format(app=app)
				cursor.execute(sql_str,[layerIds,inPointPathIds,inPointPathIds])
			crossoverRows = cursor.fetchall()
			
		except DatabaseError as dberror:
			return utility.response(0,dberror[0],{})
		finally:
			cursor.close()
		
		if len(crossoverRows) > 0:
		
			# generate the output report information
			serverDir = '/cresis/snfs1/web/ops2/data/reports/'
			webDir = 'data/reports/'
			tmpFn = 'OPS_CReSIS_Crossovers_Report_' + utility.randId(10) + '.csv'
			webFn = webDir + tmpFn
			serverFn  = serverDir + tmpFn
			
			#Construct the csv header
			csvHeader = ['ERROR','LAYER_ELEV1', 'LAYER_ELEV2','TWTT1','TWTT2', 'CROSS_ANGLE','LAYER_NAME', 'SEASON1',\
			'SEASON2','FRAME1','FRAME2','UTCSOD1','UTCSOD2','UTCDATE1','UTCDATE2', 'LON1','LON2','LAT1','LAT2','ELEV1','ELEV2','CROSS_LON','CROSS_LAT']
			
			# write the csv file
			with open(serverFn,'wb') as csvFile:
				csvWriter = csv.writer(csvFile,delimiter=',',quoting=csv.QUOTE_NONE)
				csvWriter.writerow(csvHeader)
				for row in crossoverRows:
					csvWriter.writerow([
						"%.5f" % row[0], 
						"%.5f" % row[1],
						"%.5f" % row[2],
						"%.8f" % row[3],
						"%.8f" % row[4],
						"%.3f" % row[5],
						row[6], 
						row[7],
						row[8],
						row[9],
						row[10],
						"%.3f" % (float(time.gmtime(row[11]).tm_hour*3600.0 + time.gmtime(row[11]).tm_min*60.0 + time.gmtime(row[11]).tm_sec)),
						"%.3f" % (float(time.gmtime(row[12]).tm_hour*3600.0 + time.gmtime(row[12]).tm_min*60.0 + time.gmtime(row[12]).tm_sec)),
						(time.strftime('%Y%m%d',time.gmtime(row[11]))),
						(time.strftime('%Y%m%d',time.gmtime(row[12]))),
						"%.8f" % row[13],
						"%.8f" % row[14],
						"%.5f" % row[15],
						"%.8f" % row[16],
						"%.8f" % row[17],
						"%.5f" % row[18],
						"%.8f" % row[19],
						"%.8f" % row[20]
					])
			
			# return the output
			return utility.response(1,webFn,{})
		else: 
			return utility.response(2, "No crossover errors found with specified parameters.",{})
	except:
		return utility.errorCheck(sys)

def getFrameSearch(request): 
	""" Get a frame based on input search parameters.
	
	Input:
		location: (string)
		searc_str: (string) a date string of minimum yyyy
			examples: (2011,201102,20110203,20110203_01,20110203_01_001)
		
	Optional Inputs:
		season: (string or list of strings) name of season/s to search on
		
	Output:
		status: (integer) 0:error 1:success 2:warning
		data:
			season: (string) name of the season of the matched frame
			segment_id: (integer) id of the segment of the matched frame
			frame: (string) name of the matched frame
			X: (list of floats) x coordinates of the matched frame
			Y: (list of floats) y coordinates of the matched frame
			gps_time: (list of floats) gps times of the matched frame
	
	Only the first frame that matches the search string is returned
	
	"""
	models,data,app,cookies = utility.getInput(request) # get the input and models
	
	# parse the data input
	try:
	
		inLocationName = data['properties']['location']
		inSearchStr = data['properties']['search_str']
	
		# parse the optional input
		try:
		
			useAllSeasons = False
			inSeasonNames = data['properties']['season']
		
		except:
		
			useAllSeasons = True
	
	except:
		return utility.errorCheck(sys)
	
	# perform the function logic
	try:
		
		if useAllSeasons:
		
			inSeasonNames = models.seasons.objects.filter(location__name=inLocationName,season_group__public=True).values_list('name',flat=True) # get all the public seasons
		
		# get any frame objects that match the search string
		framesObj = models.frames.objects.filter(name__istartswith=inSearchStr,segment__season__location__name=inLocationName).order_by('pk')
		
		# if there are search results get the first return
		if framesObj.exists():
			framesObj = framesObj[0]
		else:
			return utility.response(2,'WARNING: NO FRAMES FOUND THAT MATCH YOUR SEARCH',{})
		
		epsg = utility.epsgFromLocation(inLocationName) # get the input epsg
		
		# get the season name, segment id, X, Y, and gps time for the frame (transform the geometry)
		pointPathsObj = models.point_paths.objects.select_related('season__name').filter(frame_id=framesObj.pk).transform(epsg).values_list('season__name','segment_id','geom','gps_time').order_by('gps_time')
		
		pointPathsData = zip(*pointPathsObj) # extract all the elements
		del pointPathsObj
		
		lon = []; lat = []; # parse the geometry and extract longitude and latitude
		for ptIdx in range(len(pointPathsData[2])):
			lon.append(pointPathsData[2][ptIdx].x)
			lat.append(pointPathsData[2][ptIdx].y)
		
		# return the output
		return utility.response(1,{'season':pointPathsData[0][0],'segment_id':pointPathsData[1][0],'frame': framesObj.name,'X':lon,'Y':lat,'gps_time':pointPathsData[3]},{})
	
	except:
		return utility.errorCheck(sys)

def getInitialData(request): 
	""" Create data packs for initial data loading on the server.
	
	Input:
		seasons: (string or list of strings) seasons to create data packs for
		radars: (string or list of strings) radars to create data packs for
		segments: (string or list of strings) segments to create data packs for
		
	Optional Inputs:
		layers: (string or list of strings) layers to create data packs for
		
	Output:
		status: (integer) 0:error 1:success 2:warning
		data: url of [DATAPACK].tar.gz on the server
		
	Ignores data from tables that are loaded in the django fixtures (django default initial data)
	
	"""
	models,data,app,cookies = utility.getInput(request) # get the input
	
	# parse the data input
	try:
	
		inSeasons = utility.forceList(data['properties']['seasons'])
		inRadars = utility.forceList(data['properties']['radars'])
		inSegments = utility.forceList(data['properties']['segments'])
		
		# parse the optional inputs
		try:
		
			useAllLyr = False
			inLyrNames = utility.forceList(data['properties']['layers'])
		
		except:
		
			useAllLyr = True
	
	except:
		return utility.errorCheck(sys)
		
	# perform the function logic
	try:
		
		# get point path, frame, segment, location, season, and radar ids
		pointPathsObj = models.point_paths.objects.select_related('segment__radar_id').filter(segment__name__in=inSegments,season__name__in=inSeasons,segment__radar__name__in=inRadars).values_list('pk','location_id','season_id','segment_id','frame_id','segment__radar_id')
		
		pointPathIds,locationIds,seasonIds,segmentIds,frameIds,radarIds = zip(*pointPathsObj) # extract all the elements
		del pointPathsObj
		
		# force objects to be lists (only keep unique location and radar ids)
		pointPathIds = utility.forceList(pointPathIds)
		frameIds = utility.forceList(frameIds)
		segmentIds = utility.forceList(segmentIds)
		locationIds = utility.forceList(set(locationIds))
		seasonIds = utility.forceList(seasonIds)
		radarIds = utility.forceList(set(radarIds))
	
		# get a layers object
		if useAllLyr:
			layersObj = models.layers.objects.filter(deleted=False,layer_group__public=True).values_list('pk','layer_group_id')
		else:
			layersObj = models.layers.objects.filter(name__in=inLyrNames,deleted=False,layer_group__public=True).values_list('pk','layer_group_id')
			
		layerIds,layerGroupIds = zip(*layersObj) # extract all the elements
		del layersObj
		
		# force objects to be lists (only keep unique layer groups)
		layerIds = utility.forceList(layerIds)
		layerGroupIds = utility.forceList(set(layerGroupIds))
		
		# create a temporary directory to store the csv files for compression
		tmpDir = '/cresis/snfs1/web/ops2/datapacktmp/' + utility.randId(10)
		sysCmd = 'mkdir -p -m 777 ' + tmpDir + ' && chown -R postgres:postgres ' + tmpDir
		os.system(sysCmd)
		
		cursor = connection.cursor() # create a database cursor
		
		# copy all of the database tables (based on the input filters) to csv files (exclude data from django fixtures)
		try:
		
			sqlStrings = []; # build raw strings (parameters wont work because non-column fields are dynamic)
			sqlStrings.append("COPY (SELECT * FROM %s_layers WHERE id IN %s AND id NOT IN (1,2))\
			TO '%s/%s_layers' WITH CSV" % (app,layerIds,tmpDir,app))
			sqlStrings.append("COPY (SELECT * FROM %s_layer_links WHERE layer_1_id IN %s AND layer_2_id IN %s)\
			TO '%s/%s_layer_links' WITH CSV" % (app,layerIds,layerIds,tmpDir,app))
			sqlStrings.append("COPY (SELECT * FROM %s_layer_groups WHERE id IN %s AND id NOT IN (1,2))\
			TO '%s/%s_layer_groups' WITH CSV" % (app,layerGroupIds,tmpDir,app))
			sqlStrings.append("COPY (SELECT * FROM %s_crossovers WHERE point_path_1_id IN %s AND point_path_2_id IN %s)\
			TO '%s/%s_crossovers' WITH CSV" % (app,pointPathIds,pointPathIds,tmpDir,app))
			sqlStrings.append("COPY (SELECT * FROM %s_locations WHERE id IN %s AND id NOT IN (1,2))\
			TO '%s/%s_layer_groups' WITH CSV" % (app,locationIds,tmpDir,app))
			sqlStrings.append("COPY (SELECT * FROM %s_layer_points WHERE point_path_id IN %s)\
			TO '%s/%s_layer_points' WITH CSV" % (app,pointPathIds,tmpDir,app))
			sqlStrings.append("COPY (SELECT * FROM %s_point_paths WHERE id IN %s)\
			TO '%s/%s_point_paths' WITH CSV" % (app,pointPathIds,tmpDir,app))
			sqlStrings.append("COPY (SELECT * FROM %s_frames WHERE id IN %s)\
			TO '%s/%s_frames' WITH CSV" % (app,frameIds,tmpDir,app))
			sqlStrings.append("COPY (SELECT * FROM %s_landmarks WHERE point_path_1_id IN %s AND point_path_2_id IN %s)\
			TO '%s/%s_landmarks' WITH CSV" % (app,pointPathIds,pointPathIds,tmpDir,app))
			sqlStrings.append("COPY (SELECT * FROM %s_seasons WHERE id IN %s)\
			TO '%s/%s_seasons' WITH CSV" % (app,seasonIds,tmpDir,app))
			sqlStrings.append("COPY (SELECT * FROM %s_segments WHERE id IN %s)\
			TO '%s/%s_segments' WITH CSV" % (app,segmentIds,tmpDir,app))
			sqlStrings.append("COPY (SELECT * FROM %s_radars WHERE id IN %s)\
			TO '%s/%s_radars' WITH CSV" % (app,radarIds,tmpDir,app))
			
			for sqlStr in sqlStrings:
				cursor.execute(sqlStr.replace('[','(').replace(']',')')) # execute the raw sql, format list insertions as tuples

		except DatabaseError as dberror:
			return utility.response(0,dberror[0],{})
			
		finally:
			cursor.close() # close the cursor in case of exception
		
		# generate the output .tar.gz information
		serverDir = '/cresis/snfs1/web/ops2/data/datapacks/'
		webDir = 'data/datapacks/'
		tmpFn = 'OPS_CReSIS_%s_DATAPACK' % (app.upper()) + '_' + utility.randId(10) + '.tar.gz'
		webFn = webDir + tmpFn

		# compress, copy, and delete source csv files
		sysCmd = 'cd %s && tar -zcf %s * && cp %s %s && cd .. && rm -rf %s' % (tmpDir,tmpFn,tmpFn,serverDir,tmpDir)
		os.system(sysCmd)
		
		# return the output
		return utility.response(1,webFn,{})

	except:
		return utility.errorCheck(sys)

def getUserProfileData(request):
	""" Gets the user profile for a specified user is that user is authenticated.
	
	Input:
		FROM GEOPORTAL: (none)
		FROM MATLAB:
			mat: (boolean) true
			userName: (string) username of an authenticated user (or anonymous)
			isAuthenticated (boolean) authentication status of a user
		
	Output:
		status: (integer) 0:error 1:success 2:warning
		data: (string) status message
	
	"""
	_,data,_,cookies = utility.getInput(request) # get the input and models
	
	# perform function logic
	try:
	
		# get the user profile
		uPObj,status = utility.getUserProfile(cookies)
		if not status:
			return utility.response(0,uPObj,{})
		
		# build the outputs (get rid of unicode strings)
		rdsSg = [output.encode("utf8") for output in uPObj.rds_season_groups.values_list('name',flat=True)]
		rdsSgId = list(uPObj.rds_season_groups.values_list('pk',flat=True))
		rdsLg = [output.encode("utf8") for output in uPObj.rds_layer_groups.values_list('name',flat=True)]
		rdsLgId = list(uPObj.rds_layer_groups.values_list('pk',flat=True))
		
		accumSg = [output.encode("utf8") for output in uPObj.accum_season_groups.values_list('name',flat=True)]
		accumSgId = list(uPObj.accum_season_groups.values_list('pk',flat=True))
		accumLg = [output.encode("utf8") for output in uPObj.accum_layer_groups.values_list('name',flat=True)]
		accumLgId = list(uPObj.accum_layer_groups.values_list('pk',flat=True))
		
		snowSg = [output.encode("utf8") for output in uPObj.snow_season_groups.values_list('name',flat=True)]
		snowSgId = list(uPObj.snow_season_groups.values_list('pk',flat=True))
		snowLg = [output.encode("utf8") for output in uPObj.snow_layer_groups.values_list('name',flat=True)]
		snowLgId = list(uPObj.snow_layer_groups.values_list('pk',flat=True))
		
		kubandSg = [output.encode("utf8") for output in uPObj.kuband_season_groups.values_list('name',flat=True)]
		kubandSgId = list(uPObj.kuband_season_groups.values_list('pk',flat=True))
		kubandLg = [output.encode("utf8") for output in uPObj.kuband_layer_groups.values_list('name',flat=True)]
		kubandLgId = list(uPObj.kuband_layer_groups.values_list('pk',flat=True))
		
		# return the output
		return utility.response(1,{'rds_season_groups':rdsSg,'rds_season_group_ids':rdsSgId,'rds_layer_groups':rdsLg,'rds_layer_group_ids':rdsLgId,'accum_season_groups':accumSg,'accum_season_group_ids':accumSgId,'accum_layer_groups':accumLg,'accum_layer_group_ids':accumLgId,'snow_season_groups':snowSg,'snow_season_groupIds':snowSgId,'snow_layer_groups':snowLg,'snow_layer_group_ids':snowLgId,'kuband_season_groups':kubandSg,'kuband_season_group_ids':kubandSgId,'kuband_layer_groups':kubandLg,'kuband_layer_group_ids':kubandLgId,'layerGroupRelease':uPObj.layerGroupRelease,'seasonRelease':uPObj.seasonRelease,'createData':uPObj.createData,'bulkDeleteData':uPObj.bulkDeleteData},{})
		
	except:
		return utility.errorCheck(sys)

# =======================================
# UTILITY FUNCTIONS
# =======================================

def createUser(request):
	""" Creates a user in the OPS database
	
	Input:
		username: (string)
		email: (string)
		password: (string)
		
	Output:
		status: (integer) 0:error 1:success 2:warning
		data: (string) status message
	
	"""
	
	_,data,_,cookies = utility.getInput(request) # get the input and models
	
	try:
	
		inUsername = data['properties']['userName']
		inPassword = data['properties']['password']
		inEmail = data['properties']['email']
		
		try:
			userObj = User.objects.get(username__exact=inUsername)
			if userObj is not None:
				return utility.response(2,'WARNING: USERNAME ALREADY EXISTS',{})
		except:
			_ = User.objects.create_user(inUsername,inEmail,inPassword)
		
		return utility.response(1,'SUCCESS: NEW USER CREATED',{})
		
	except:
		return utility.errorCheck(sys)

def loginUser(request):
	""" Logs in a user to the browser session.
	
	Input:
		userName: (string)
		password: (string)
		
	Output:
		status: (integer) 0:error 1:success 2:warning
		data: (string) status message
	
	"""
	_,data,_,cookies = utility.getInput(request) # get the input and models
	
	try:
	
		# get inputs
		inUsername = data['properties']['userName']
		inPassword = data['properties']['password']
		
		if not cookies['isMat']:
			# check the status of the user (log them out if there logged in)
			curUserName = cookies['userName']
			if curUserName == inUsername:
				userAuthStatus = int(cookies['isAuthenticated'])
				if userAuthStatus == 1:
					logout(request) # log out active user
			
		# authenticate the user
		user = authenticate(username=inUsername, password=inPassword)
		
		# if the user authenticates log them in
		if user is not None:
			if user.is_active:
				login(request, user)
				return utility.response(1,'SUCCESS: USER NOW LOGGED IN.',{'userName':inUsername,'isAuthenticated':1})
			else:
				return utility.response(2,'WARNING: USER ACCOUNT IS DISABLED.',{'userName':'','isAuthenticated':0})
		else:
			return utility.response(0,'ERROR: USER AUTHENTICATION FAILED.',{'userName':'','isAuthenticated':0})
	
	except:
		return utility.errorCheck(sys)

def logoutUser(request):
	""" Logs out a user from the browser session.
	
	Input:
		FROM GEOPORTAL: (none)
		FROM MATLAB:
			mat: (boolean) true
			userName: (string) username of an authenticated user (or anonymous)
		
	Output:
		status: (integer) 0:error 1:success 2:warning
		data: (string) status message
	
	"""
	try:
		
		logout(request)
		
		return utility.response(1,'SUCESS: USER LOGGED OUT',{'userName':'','isAuthenticated':0})

	except:
		return utility.errorCheck(sys)

@ipAuth()
def query(request):
	""" Run an SQL query on the database.
	
	Input:
		query: (string) an SQL query
		
	Output:
		status: (integer) 0:error 1:success 2:warning
		data: (json) the raw response from the SQL query
		
	If no rows are returned from the query a warning is returned (status=2)
	
	"""
	queryStr,cookies = utility.getQuery(request) # get the input
	
	# perform the function logic
	try:
		
		cursor = connection.cursor() # create a database cursor
		cursor.execute(queryStr) # execute the query
		queryData = cursor.fetchall() # fetch the query results
		
		# return the output
		if not queryData:
			return utility.response(2,'NO DATA RETURNED FROM QUERY',{})
		else:
			return utility.response(1,queryData,{})
			
	except DatabaseError as dbError:
		return utility.response(0,dbError[0],{})

@ipAuth()
def analyze(request): 
	""" ANALYZE a list of tables in the OPS database.
	
	Input:
		tables: (list) names of tables in the OPS database
		
	Output:
		status: (integer) 0:error 1:success 2:warning
		data: string status message
	
	"""
	models,data,app,cookies = utility.getInput(request) # get the input and models
	
	# parse the input data
	try:
		
		tables = utility.forceList(data['properties']['tables'])
	
	except:
		return utility.errorCheck(sys)
		
	# perform the function logic
	try:
	
		cursor = connection.cursor() # create a database cursor
		try:
			
			for table in tables:
				cursor.execute("ANALYZE " +app+"_"+table) # execute the query
		
		except DatabaseError as dbError:
			return utility.response(0,dbError[0],{})
		
		finally:
			cursor.close() # close the connection if there is an error
		
		# return the output
		return utility.response(1, "SUCESS: DATABASE TABLES ANALYZED.",{})
	
	except:
		return utility.errorCheck(sys)

@ipAuth()
def profile(request): 
	""" Runs the profiler for the function called.
	
	Input:
		none: no additional input is needed, passes on called function input
		
	Output:
		status: (integer) 0:error 1:success 2:warning
		data: string status message
			
	"""
	try:
	
		view = request.POST.get('view') # get the function call
		
		evalStr = view + '(request)' # create the string to be evaluated
		 
		profiler = line_profiler.LineProfiler() # get a profiler object
		 
		profiler.enable() # enable the profiler
		 
		profiler.add_function(eval(view)) # add the function call to the profiler
		 
		viewResponse = eval(evalStr) # run the function
		 
		profiler.disable() # disable the profiler
		 
		 # build output information
		timeStr = datetime.datetime.now().strftime('-%d-%m-%y-%X')  
		fn = '/var/profile_logs/'+view+timeStr+'.lprof'
		fnTxt = '/var/profile_logs/txt/'+view+timeStr+'.txt'
		
		# write the output
		profiler.dump_stats(fn)
		os.system('python -m line_profiler '+fn+' > '+fnTxt)
		
		# return the output (from the function call)
		return viewResponse
	
	except:
		return utility.errorCheck(sys)