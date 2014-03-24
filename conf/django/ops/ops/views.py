from django.db import connection,DatabaseError
from django.contrib.gis.geos import GEOSGeometry
from utility import ipAuth
from decimal import Decimal
import utility,sys,os,datetime,line_profiler,simplekml,ujson,csv

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
		location: (string) name of the location
		radar: (string) name of the radar
		segment: (string) name of the segment
		frame_count: (integer) number of frames for the given segment
		frame_start_gps_time: (list of floats) start gps time for each frame for the given segment
		
	Output:
		status: (integer) 0:error 1:success 2:warning
		data: string status message
	
	"""
	models,data,app = utility.getInput(request) # get the input and models
	
	# parse the data input
	try:
	
		inLinePath = data['geometry']
		inGpsTime = data['properties']['gps_time']
		inElevation = data['properties']['elev']
		inRoll = data['properties']['roll']
		inPitch = data['properties']['pitch']
		inHeading = data['properties']['heading']
		inSeason = data['properties']['season']
		inLocationName = data['properties']['location']
		inRadar = data['properties']['radar']
		inSegment = data['properties']['segment']
		inFrameCount = data['properties']['frame_count']
		inFrameStartGpsTimes = utility.forceList(data['properties']['frame_start_gps_time'])
		
	except:
		return utility.errorCheck(sys)
	
	try:

		locationsObj,_ = models.locations.objects.get_or_create(name=inLocationName.lower()) # get or create the location       
		seasonsObj,_ = models.seasons.objects.get_or_create(name=inSeason,location_id=locationsObj.pk) # get or create the season   
		radarsObj,_ = models.radars.objects.get_or_create(name=inRadar.lower()) # get or create the radar

		linePathGeom = GEOSGeometry(ujson.dumps(inLinePath)) # create a geometry object
		
		# get or create the segments object
		segmentsObj,_ = models.segments.objects.get_or_create(season_id=seasonsObj.pk,radar_id=radarsObj.pk,name=inSegment,path=linePathGeom)

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
			

			pointPathGeom = GEOSGeometry('POINT Z ('+repr(ptGeom[0])+' '+repr(ptGeom[1])+' '+str(inElevation[ptIdx])+')',srid=4326) # create a point geometry object
			
			# query for current point path (checking if it already exists)
			pointPathObj = models.point_paths.objects.filter(location_id=locationsObj.pk,season_id=seasonsObj.pk,segment_id=segmentsObj.pk,frame_id=frmId,gps_time=inGpsTime[ptIdx].quantize(Decimal('.000001'))).values_list('pk',flat=True)
			
			if len(pointPathObj) < 1:
				
				# add a point path object to the output list
				pointPathObjs.append(models.point_paths(location_id=locationsObj.pk,season_id=seasonsObj.pk,segment_id=segmentsObj.pk,frame_id=frmId,gps_time=inGpsTime[ptIdx],roll=inRoll[ptIdx],pitch=inPitch[ptIdx],heading=inHeading[ptIdx],path=pointPathGeom))
		
		if len(pointPathObjs) > 0:
			_ = models.point_paths.objects.bulk_create(pointPathObjs) # bulk create the point paths objects
		
		return utility.response(1,'SUCCESS: PATH INSERTION COMPLETED.')
		
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
	models,data,app = utility.getInput(request) # get the input and models
	
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
			return utility.response(0,'ERROR: LAYER WITH THE SAME NAME EXISTS. (LAYER NAMES MUST BE UNIQUE, EVEN ACROSS GROUPS)') # throw error, trying to create a duplicate layer
		
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
				return utility.response(0,'ERROR: LAYER WITH THE SAME NAME EXISTS (WITHIN THE GROUP) AND IS NOT DELETED') # throw error, trying to create a duplicate layer
		
		else:
			lyrObj.description = inLyrDescription
			lyrObj.save(update_fields=['description'])
			
		# return the output
		return utility.response(1,{'lyr_id':lyrObj.pk,'lyr_group_id':lyrGroupsObj.pk})
	
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
	models,data,app = utility.getInput(request) # get the input and models
	
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
		return utility.response(1,{'lyr_id':lyrObjs.pk})
		
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
		user: (string) username of the person submitting the points
		
	Output:
		status: (integer) 0:error 1:success 2:warning
		data: string status message
	
	"""	
	models,data,app = utility.getInput(request) # get the input and models
	
	# parse the data input
	try:
	
		inPointPathIds = utility.forceList(data['properties']['point_path_id'])
		inLyrName = data['properties']['lyr_name']
		inTwtt = utility.forceList(data['properties']['twtt'])
		inType = utility.forceList(data['properties']['type'])
		inQuality = utility.forceList(data['properties']['quality'])
		inUserName = data['properties']['username']
	
	except:
		return utility.errorCheck(sys)
	
	# perform the function logic
	try:
	
		layerId = models.layers.objects.filter(name=inLyrName,deleted=False).values_list('pk',flat=True)[0] # get the layer object
		
		layerPointsObjs = []
		for ptIdx in range(len(inPointPathIds)):
			
			layerPointsObj = models.layer_points.objects.filter(layer_id=layerId,point_path_id=inPointPathIds[ptIdx]) # get any current entry from the database
			
			if len(layerPointsObj) > 0:
			
				layerPointsObj.update(twtt=inTwtt[ptIdx],type=inType[ptIdx],quality=inQuality[ptIdx],user=inUserName,last_updated=datetime.datetime.now()) # update the current entry
			
				if len(layerPointsObj) > 1:
					
					for idx in range(layerPointsObj)[1:]: # delete duplicate entries (likely will never occur)
						layerPointsObj[idx].delete()
						
			else: # there is no existing object to update, create it
			
				# build a list of objects for bulk create
				layerPointsObjs.append(models.layer_points(layer_id=layerId,point_path_id=inPointPathIds[ptIdx],twtt=inTwtt[ptIdx],type=inType[ptIdx],quality=inQuality[ptIdx],user=inUserName))
		
		if len(layerPointsObjs) > 0:
			_ = models.layer_points.objects.bulk_create(layerPointsObjs) # bulk create the layer points objects
			
		return utility.response(1,'SUCCESS: LAYER POINTS INSERTION COMPLETED.')
		
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
	models,data,app = utility.getInput(request) # get the input and models
	
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
		
			return utility.response(2,'NO LAYER POINTS WERE REMOVED. (NO POINTS MATCHED THE REQUEST)')
		
		else:
			
			layerPointsObj.delete() # delete the layer points
			
			# return the output
			return utility.response(1,'SUCCESS: LAYER POINTS DELETION COMPLETED.')
	
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
	models,data,app = utility.getInput(request) # get the input and models
	
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
		return utility.response(1,'SUCCESS: BULK DELETION COMPLETED')		
	
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
	models,data,app = utility.getInput(request) # get the input and models
	
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
		return utility.response(1,'SUCCESS: LAYER GROUP IS NOW PUBLIC');
	
	except:
		return utility.errorCheck(sys)

@ipAuth()
def releaseSeason(request):
	""" Sets the status of a season to public.
	
	Input:
		season_name: (string) name of the season

	Output:
		status: (integer) 0:error 1:success 2:warning
		data: string status message

	"""
	models,data,app = utility.getInput(request) # get the input and models
	
	# parse the data input
	try:
	
		inSeasonName = data['properties']['season_name']
	
	except:
		return utility.errorCheck(sys)
	
	# perform the function logic
	try:
		
		# update the seasons public status
		seasonsObj = models.seasons.objects.filter(name=inSeasonName).update(public=True)
		
		# return the output
		return utility.response(1,'SUCCESS: SEASON IS NOW PUBLIC');
	
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
	models,data,app = utility.getInput(request) # get the input and models
	
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
			pointPathsObj = models.point_paths.objects.filter(season_id__name=inSeasonName, location_id__name=inLocationName, gps_time__gte=inStartGpsTime, gps_time__lte=inStopGpsTime).order_by('gps_time').values_list('pk','gps_time','path')
		else:
			pointPathsObj = models.point_paths.objects.filter(season_id__name=inSeasonName, location_id__name=inLocationName, gps_time__gte=inStartGpsTime, gps_time__lte=inStopGpsTime).transform(epsg).order_by('gps_time').values_list('pk','gps_time','path')
		
		# unzip the data for output
		pks,gpsTimes,pointPaths = zip(*pointPathsObj)
		xCoords,yCoords,elev = zip(*pointPaths)
		
		# return the output
		return utility.response(1,{'id':pks,'gps_time':gpsTimes,'elev':elev,'X':xCoords,'Y':yCoords})
		
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
		status: (boolean) can be used to get frames for private seasons
		
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
	models,data,app = utility.getInput(request) # get the input and models
	
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
			
		try:
			inSeasonStatus = data['properties']['status']
		except:
			inSeasonStatus = [True]

	except:
		return utility.errorCheck(sys)
	
	try:
		
		if useAllSeasons:
		
			inSeasonNames = models.seasons.objects.filter(location_id__name=inLocationName,public=True).values_list('name',flat=True) # get all the public seasons
		
		epsg = utility.epsgFromLocation(inLocationName) # get the input epsg
		inPoint = GEOSGeometry('POINT ('+str(inPointX)+' '+str(inPointY)+')', srid=epsg) # create a point geometry object
		
		# get the frame id of the closest point path
		closestFrameId = models.point_paths.objects.filter(location_id__name=inLocationName,season_id__name__in=inSeasonNames,season_id__public__in=inSeasonStatus,segment_id__name__range=(inStartSeg,inStopSeg)).transform(epsg).distance(inPoint).order_by('distance').values_list('frame_id','distance')[0][0]
		
		# get the frame name,segment id, season name, path, and gps_time from point_paths for the frame id above
		pointPathsObj = models.point_paths.objects.select_related('frames__name','seasons_name').filter(frame_id=closestFrameId).transform(epsg).order_by('gps_time').values_list('frame__name','segment_id','season__name','path','gps_time')
		
		# get the (x,y,z) coords from pointPathsObj
		pointPathsGeoms = [(pointPath[3].x,pointPath[3].y,pointPath[4]) for pointPath in pointPathsObj]
		xCoords,yCoords,gpsTimes = zip(*pointPathsGeoms)
		
		# build the echogram image urls list
		outEchograms = utility.buildEchogramList(app,pointPathsObj[0][2],pointPathsObj[0][0])
		
		# returns the output
		return utility.response(1,{'season':pointPathsObj[0][2],'segment_id':pointPathsObj[0][1],'start_gps_time':min(gpsTimes),'stop_gps_time':max(gpsTimes),'frame':pointPathsObj[0][0],'echograms':outEchograms,'X':xCoords,'Y':yCoords,'gps_time':gpsTimes})
		
	except:
		return utility.errorCheck(sys)

def getLayers(request): 
	""" Returns all layers that are public and not deleted.
	
	Input:
		none
		
	Output:
		status: (integer) 0:error 1:success 2:warning
		data:
			lyr_id: (list of integers) a list of layer ids
			lyr_name: (list of strings) a list of layer names
			lyr_group_name: (list of strings) a list of layer group names
	
	"""
	models,data,app = utility.getInput(request) # get the input and models
	
	# perform function logic
	try:
		
		# get the layers objects
		layersObj = models.layers.objects.select_related('layer_group__name').filter(deleted=False,layer_group__public=True).order_by('pk').values_list('pk','name','layer_group__name')
		
		# unzip layers
		outLayersObj = zip(*layersObj)
	
		# return the output
		return utility.response(1,{'lyr_id':outLayersObj[0],'lyr_name':outLayersObj[1],'lyr_group_name':outLayersObj[2]})
		
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
	models,data,app = utility.getInput(request) # get the input and models
	
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
		
	except:
	
		returnGeom = False
			
	
	# perform function logic
	try:
	
		if not usePointPathIds:
	
			# get a segment object with a pk field
			if SegName:
				segmentsObj = models.segments.objects.filter(name=inSegment)
			else:
				segmentsObj.pk = inSegment
				
			# get the start/stop gps times
			if useAllGps:
				pointPathsObj = models.point_paths.objects.filter(segment_id=segmentsObj.pk,location__name=inLocationName).aggregate(Max('gps_time'),Min('gps_time'))
				inStartGpsTime = inPointPathsObj['gps_time__max']
				inStopGpsTime = inPointPathsObj['gps_time__min']
		
			# get the point path ids
			inPointPathIds = models.point_paths.objects.filter(segment_id=segmentsObj.pk,location__name=inLocationName,gps_time__range=(inStartGpsTime,inStopGpsTime)).values_list('pk',flat=True)

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
			return utility.response(1,{'point_path_id':layerPoints[0],'lyr_id':layerPoints[1],'gps_time':layerPoints[2],'twtt':layerPoints[3],'type':layerPoints[4],'quality':layerPoints[5]})

		else:

			if inGeomType == 'proj':
				epsg = utility.epsgFromLocation(inLocationName) # get the input epsg
				layerPointsObj = models.layer_points.objects.select_related('point_path__gps_time','point_path__path').filter(point_path_id__in=inPointPathIds,layer_id__in=layerIds).transform(epsg).values_list('point_path','layer_id','point_path__gps_time','twtt','type','quality','point_path__path')

			elif inGeomType == 'geog':
				layerPointsObj = models.layer_points.objects.select_related('point_path__gps_time','point_path__path').filter(point_path_id__in=inPointPathIds,layer_id__in=layerIds).values_list('point_path','layer_id','point_path__gps_time','twtt','type','quality','point_path__path')

			else:
				return utility.response(0,'ERROR GEOM TYPE [%s] NOT SUPPORTED.' % inGeomType)

			if len(layerPointsObj) == 0:
				return utility.response(2,'WARNING: NO LAYER POINTS FOUND FOR THE GIVEN PARAMETERS.')

			pointPathId,layerIds,gpsTimes,twtts,types,qualitys,pointPaths = zip(*layerPointsObj) # unzip the layerPointsObj
			
			outLon = []; outLat = []; outElev = [];
			for pointObj in pointPaths:
				ptGeom = GEOSGeometry(pointObj)
				outLon.append(ptGeom.x);
				outLat.append(ptGeom.y);
				outElev.append(ptGeom.z);
			
			# return the output
			return utility.response(1,{'point_path_id':pointPathId,'lyr_id':layerIds,'gps_time':gpsTimes,'twtt':twtts,'type':types,'quality':qualitys,'lon':outLon,'lat':outLat,'elev':outElev})

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
	models,data,app = utility.getInput(request) # get the input and models
	
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
			inSeasons = models.seasons.objects.filter(public=True).values_list('name',flat=True)
			
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
		pointPathsObj = models.point_paths.objects.select_related('season__name','frame__name').filter(location__name=inLocationName,season__name__in=inSeasons,segment__name__range=(inStartSeg,inStopSeg),path__within=inPoly).order_by('frame__name','gps_time').values_list('pk','gps_time','roll','pitch','heading','path','season__name','frame__name')[:2000000]
		
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
		outThickness = []; outUtcSod = [];
		
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
				outSurfaceType.append(lpTypes[surfIdx])
				outSurfaceQuality.append(lpQualitys[surfIdx])
				outBottom.append(lpTwtts[bottIdx])
				outBottomType.append(lpTypes[bottIdx])
				outBottomQuality.append(lpQualitys[bottIdx])
				
				# calculate surface and bottom elevation from twtt
				surfElev,bottElev = utility.twttToElev(outSurface[-1],outBottom[-1])
				outSurface[-1] = surfElev
				outBottom[-1] = bottElev
				
				# calculate ice thickness
				outThick = outBottom[-1]-outSurface[-1]
				if outThick < 0.0:
					outThick = 0.0
					outBottom[-1] = outSurface[-1]
				outThickness.append(outThick)
				
				# calculate utc seconds of day
				utcTime = datetime.datetime.utcfromtimestamp(ppGpsTimes[ppIdx]) - datetime.datetime.strptime(ppFrameNames[ppIdx][:-7],'%Y%m%d')
				outUtcSod.append(utcTime.seconds + (utcTime.microseconds/1000000.0))
				
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
				outBottom.append(-9999)
				outBottomType.append(-9999)
				outBottomQuality.append(-9999)
				
				# calculate surface and bottom elevation from twtt
				surfElev,_ = utility.twttToElev(outSurface[-1],outBottom[-1])
				outSurface[-1] = surfElev
				
				# calculate ice thickness
				outThickness.append(-9999)
				
				# calculate utc seconds of day
				utcTime = datetime.datetime.utcfromtimestamp(ppGpsTimes[ppIdx]) - datetime.datetime.strptime(ppFrameNames[ppIdx][:-7],'%Y%m%d')
				outUtcSod.append(utcTime.seconds + (utcTime.microseconds/1000000.0))
				
			elif 2 in lyrIds:
				# bottom found with no surface
				return utility.response(0,'ERROR: BOTTOM WITH NO SURFACE AT POINT PATH ID %d. PLEASE REPORT THIS.'%ppId)
			else:
				badCount += 1 # no surface or bottom found for point path id

		# make sure there was some data
		if badCount == len(ppIds):
			return utility.response(0,'ERROR: NO DATA FOUND THAT MATCHES THE SEARCH PARAMETERS')
		
		# clear some memory
		del lpIds,lpLyrIds,lpPpIds,lpTwtts,lpTypes,lpQualitys,ppIds,ppGpsTimes,ppRolls,ppPitchs,ppHeadings,ppPaths,ppSeasonNames,ppFrameNames

		# generate the output csv information
		serverDir = '/cresis/snfs1/web/ops/data/csv/'
		webDir = 'data/csv/'
		if getAllPoints:
			tmpFn = 'OPS_CReSIS_L2_CSV_' + utility.randId(10) + '.csv'
		else:
			tmpFn = 'OPS_CReSIS_L2_CSV_GOOD_' + utility.randId(10) + '.csv'
		webFn = webDir + tmpFn
		serverFn  = serverDir + tmpFn
		
		# create the csv header
		csvHeader = ['LAT','LON','ELEVATION','ROLL','PITCH','HEADING','UTCSOD','SURFACE','BOTTOM','THICKNESS',\
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
					"%.3f" % outSurface[outIdx],
					"%.3f" % outBottom[outIdx],
					"%.3f" % outThickness[outIdx],
					int(outSurfaceType[outIdx]),
					int(outBottomType[outIdx]),
					int(outSurfaceQuality[outIdx]),
					int(outBottomQuality[outIdx]),
					outSeason[outIdx],
					outFrame[outIdx],
				])
		
		# return the output
		return utility.response(1,webFn)
		
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
	models,data,app = utility.getInput(request) # get the input and models
	
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
		
			inSeasonNames = models.seasons.objects.filter(location_id__name=inLocationName,public=True).values_list('name',flat=True) # get all the public seasons
	
		inPoly = GEOSGeometry(inBoundaryWkt, srid=4326) # create a polygon geometry object
	
		# get the segments object
		segmentsObj = models.segments.objects.filter(season_id__name__in=inSeasonNames,name__range=(inStartSeg,inStopSeg),path__within=inPoly).values_list('name','path')
		
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
		serverDir = '/cresis/snfs1/web/ops/data/kml/'
		webDir = 'data/kml/'
		tmpFn = 'OPS_CReSIS_L2_KML_' + utility.randId(10) + '.kml'
		webFn = webDir + tmpFn
		serverFn  = serverDir + tmpFn
		
		kmlObj.save(serverFn) # save the kml
		
		# return the output
		return utility.response(1,webFn)
	
	except:
		return utility.errorCheck(sys)

def getSystemInfo(request): 
	"""Get basic information about data in the OPS.
	
	Input:
		none
		
	Output:
		status: (integer) 0:error 1:success 2:warning
		data: list of dictionary objects of the form:
			{'system':[string],'season':[string],'location':[string],'public':[boolean]}

	"""
	
	# perform the function logic
	try:
	
		from ops.settings import INSTALLED_APPS as apps # get a list of all the apps

		outData = []
		
		for app in apps:
			if app.startswith(('rds','snow','accum','kuband')):

				models = utility.getAppModels(app) # get the models

				# get all of the seasons (and location)
				seasonsObj = models.seasons.objects.select_related('locations__name').filter().values_list('name','location__name','public')

				# if there are seasons populate the outData list
				if not (len(seasonsObj) == 0):

					data = zip(*seasonsObj)
					
					for dataIdx in range(len(data[0])):

						outData.append({'system':app,'season':data[0][dataIdx],'location':data[1][dataIdx],'public':data[2][dataIdx]})

		# return the output
		return utility.response(1,outData)
		
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
	models,data,app = utility.getInput(request) # get the input and models
	
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
			return utility.response(2,'WARNING: NO FRAMES FOUND FOR THE GIVEN SEGMENT ID') # return if there are no frames
		
		# for each frame get max/min gps_time from point paths
		startGpsTimes = []
		stopGpsTimes = []
		for frmId in frameIds:
			pointPathGpsTimes = models.point_paths.objects.filter(frame_id=frmId).values_list('gps_time',flat=True)
			startGpsTimes.append(max(pointPathGpsTimes))
			stopGpsTimes.append(min(pointPathGpsTimes))
		
		# return the output
		return utility.response(1,{'season':seasonNames[0],'segment':segmentNames[0],'frame':frameNames,'start_gps_time':startGpsTimes,'stop_gps_time':stopGpsTimes})
			
	except:
		return utility.errorCheck(sys)

def getCrossovers(request): 
	""" Get crossover values from the OPS.
	
	Input:
		location: (string)
		lyr_id: (integer or list of integers)
		
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
			frame_id: (list of integer/s) frame ids of the crossovers
			twtt: (list of float/s) two-way travel time of the crossovers
			angle: (list of float/s) angle (degrees) of the crossovers path
			abs_error: (list of float/s) absolute difference (meters) between the source and crossover layer points
		
	"""
	models,data,app = utility.getInput(request) # get the input and models
	
	# parse the data input
	try:
	
		inLocationName = data['properties']['location']
		inLayerIds = utility.forceTuple(data['properties']['location'])
	
		try:
		
			getPointPathIds = False
			inPointPathIds = utility.forceTuple(data['properties']['point_path_id'])
		
		except:
		
			try:
			
				getPointPathIds = True
				inFrameIds = utility.forceList(data['properties']['layer_id'])
			
			except:
			
				return utility.response(0,'ERROR: EITHER POINT PATH OR FRAME IDS MUST BE GIVEN')
	
	except:
		return utility.errorCheck(sys)
	
	# perform the function logic
	try:
		
		if getPointPathIds:
		
			# get the point path ids based on the given frames
			inPointPathIds = utility.forceTuple(models.point_paths.objects.filter(frame_id__in=inFrameIds,location__name__in=inLocationName).values_list('pk',flat=True))
		
		cursor = connection.cursor() # create a database cursor
		
		# get all of the data needed for crossovers
		try:
		
			cursor.execute("WITH cx AS (SELECT point_path_1_id, point_path_2_id, angle FROM %s_crossovers WHERE point_path_1_id IN %s OR point_path_2_id IN %s) SELECT pp1.id, pp2.id, lp1.id, lp2.id, lp1.twtt, lp2.twtt, ABS(lp1.twtt - lp2.twtt), cx.angle, ST_Z(pp1.path), ST_Z(pp2.path), pp1.frame_id, pp2.frame_id FROM cx, %s_layer_points AS lp1, %s_layer_points AS lp2, %s_point_paths AS pp1, %s_point_paths AS pp2 WHERE cx.point_path_1_id = lp1.point_path_id AND cx.point_path_2_id = lp2.point_path_id AND lp1.layer_id IN %s AND lp2.layer_id IN %s AND pp1.id = lp1.point_path_id AND pp2.id = lp2.point_path_id;",[app,inPointPathIds,inPointPathIds,app,app,app,app,inLayerIds,inLayerIds])
			
			crossoverRows = cursor.fetchall() # get all of the data from the query
			
		except DatabaseError as dberror:
			return utility.response(0,dberror[0])
		
		finally:
			cursor.close() # close the cursor in case of exception
		
		if len(crossoverRows) == 0:
			return utility.response(2,'WARNING: NO CROSSOVERS FOUND FOR THE GIVEN PARAMETERS.') # warning if no data is found
			
		crossoverData = zip(*crossoverRows) # extract all the elements
		del crossoverRows
			
		# set up for the creation of outputs
		sourcePointPathIds = []; crossPointPathIds = []; sourceElev = []; crossElev = []; 
		crossTwtt = []; crossAngle = []; crossFrameId = []; crossLayerId = []; crossAbsError = [];
		
		for crossIdx in range(len(crossoverData[0])): # parse each output row and sort it into either source or crossover outputs
		
			if any(crossoverData[0][crossIdx] == inPid for inPid in inPointPathIds):
			
				# point_path_1 is the source
				sourcePointPathIds.append(crossoverData[0][crossIdx])
				sourceElev.append(crossoverData[8][crossIdx])
				
				# point_path_2 is the crossover
				crossPointPathIds.append(crossoverData[1][crossIdx])
				crossElev.append(crossoverData[9][crossIdx])
				crossTwtt.append(crossoverData[5][crossIdx])
				crossAngle.append(crossoverData[7][crossIdx])
				crossFrameId.append(crossoverData[11][crossIdx])
				crossLayerId.append(crossoverData[3][crossIdx])
				crossAbsError.append(crossoverData[6][crossIdx])
			
			else:
			
				# point_path_1 is the crossover
				crossPointPathIds.append(crossoverData[0][crossIdx])
				crossElev.append(crossoverData[8][crossIdx])
				crossElev.append(crossoverData[9][crossIdx])
				crossTwtt.append(crossoverData[4][crossIdx])
				crossAngle.append(crossoverData[7][crossIdx])
				crossFrameId.append(crossoverData[10][crossIdx])
				crossLayerId.append(crossoverData[2][crossIdx])
				crossAbsError.append(crossoverData[6][crossIdx])
				
				# point_path_2 is the source
				sourcePointPathIds.append(crossoverData[1][crossIdx])
				sourceElev.append(crossoverData[9][crossIdx])
		
		# return the output
		return utility.response(1,{'source_point_path_id':sourcePointPathIds,'cross_point_path_id':crossPointPathIds,'source_elev':sourceElev,'cross_elev':crossElev,'layer_id':crossLayerId,'frame_id':crossFrameId,'twtt':crossTwtt,'angle':crossAngle,'abs_error':crossAbsError})
		
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
	models,data,app = utility.getInput(request) # get the input and models
	
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
		
			inSeasonNames = models.seasons.objects.filter(location__name=inLocationName,public=True).values_list('name',flat=True) # get all the public seasons
		
		# get the first matching frame object
		framesObj = models.frames.objects.filter(name__istartswith=inSearchStr,segment__season__location__name=inLocationName).order_by('pk')[0]
		
		epsg = utility.epsgFromLocation(inLocationName) # get the input epsg
		
		# get the season name, segment id, X, Y, and gps time for the frame (transform the geometry)
		pointPathsObj = models.point_paths.objects.select_related('season__name').filter(frame_id=framesObj.pk).transform(epsg).values_list('season__name','segment_id','path','gps_time').order_by('gps_time')
		
		pointPathsData = zip(*pointPathsObj) # extract all the elements
		del pointPathsObj
		
		lon = []; lat = []; # parse the geometry and extract longitude and latitude
		for ptIdx in range(len(pointPathsData[2])):
			lon.append(pointPathsData[2][ptIdx].x)
			lat.append(pointPathsData[2][ptIdx].y)
		
		# return the output
		return utility.response(1,{'season':pointPathsData[0][0],'segment_id':pointPathsData[1][0],'frame': framesObj.name,'X':lon,'Y':lat,'gps_time':pointPathsData[3]})
	
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
	models,data,app = utility.getInput(request) # get the input
	
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
	
		# get a layers object (exclude surface and bottom layers)
		if useAllLyr:
			layersObj = models.layers.objects.exclude(name__in=['surface','bottom']).filter(deleted=False,layer_group__public=True).values_list('pk','layer_group_id')
		else:
			layersObj = models.layers.objects.exclude(name__in=['surface','bottom']).filter(name__in=inLyrNames,deleted=False,layer_group__public=True).values_list('pk','layer_group_id')
			
		layerIds,layerGroupIds = zip(*layersObj) # extract all the elements
		del layersObj
		
		# force objects to be lists (only keep unique layer groups)
		layerIds = utility.forceList(layerIds)
		layerGroupIds = utility.forceList(set(layerGroupIds))
		
		# create a temporary directory to store the csv files for compression
		tmpDir = '/cresis/snfs1/web/ops/datapacktmp/' + utility.randId(10)
		sysCmd = 'mkdir -p -m 777 ' + tmpDir + ' && chown -R postgres:postgres ' + tmpDir
		os.system(sysCmd)
		
		cursor = connection.cursor() # create a database cursor
		
		# copy all of the database tables (based on the input filters) to csv files (exclude data from django fixtures)
		try:
		
			sqlStrings = []; # build raw strings (parameters wont work because non-column fields are dynamic)
			sqlStrings.append("COPY (SELECT * FROM %s_layers WHERE id IN %s)\
			TO '%s/%s_layers' WITH CSV" % (app,layerIds,tmpDir,app))
			sqlStrings.append("COPY (SELECT * FROM %s_layer_links WHERE layer_1_id IN %s AND layer_2_id IN %s)\
			TO '%s/%s_layer_links' WITH CSV" % (app,layerIds,layerIds,tmpDir,app))
			sqlStrings.append("COPY (SELECT * FROM %s_layer_groups WHERE id IN %s AND id NOT IN (1,2))\
			TO '%s/%s_layer_groups' WITH CSV" % (app,layerGroupIds,tmpDir,app))
			sqlStrings.append("COPY (SELECT * FROM %s_crossovers WHERE point_path_1_id IN %s AND point_path_2_id IN %s)\
			TO '%s/%s_crosovers' WITH CSV" % (app,pointPathIds,pointPathIds,tmpDir,app))
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
			return utility.response(0,dberror[0])
			
		finally:
			cursor.close() # close the cursor in case of exception
		
		# generate the output .tar.gz information
		serverDir = '/cresis/snfs1/web/ops/data/datapacks/'
		webDir = 'data/datapacks/'
		tmpFn = 'OPS_CReSIS_%s_DATAPACK' % (app) + utility.randId(10) + '.tar.gz'
		webFn = webDir + tmpFn

		# compress, copy, and delete source csv files
		sysCmd = 'cd %s && tar -zcf %s * && cp %s %s && cd .. && rm -rf %s' % (tmpDir,tmpFn,tmpFn,serverDir,tmpDir)
		os.system(sysCmd)
		
		# return the output
		return utility.response(1,webFn)

	except:
		return utility.errorCheck(sys)

# =======================================
# UTILITY FUNCTIONS
# =======================================

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
	queryStr = utility.getQuery(request) # get the input
	
	# perform the function logic
	try:
		
		cursor = connection.cursor() # create a database cursor
		cursor.execute(queryStr) # execute the query
		queryData = cursor.fetchall() # fetch the query results
		
		# return the output
		if not queryData:
			return utility.response(2,'NO DATA RETURNED FROM QUERY')
		else:
			return utility.response(1,queryData)
			
	except DatabaseError as dbError:
		return utility.response(0,dbError[0])

@ipAuth()
def analyze(request): 
	""" ANALYZE a list of tables in the OPS database.
	
	Input:
		tables: (list) names of tables in the OPS database
		
	Output:
		status: (integer) 0:error 1:success 2:warning
		data: string status message
	
	"""
	models,data,app = utility.getInput(request) # get the input and models
	
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
			return utility.response(0,dbError[0])
		
		finally:
			cursor.close() # close the connection if there is an error
		
		# return the output
		return utility.response(1, "SUCESS: DATABASE TABLES ANALYZED.")
	
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