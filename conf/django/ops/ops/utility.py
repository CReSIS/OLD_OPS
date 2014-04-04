from django.http import HttpResponse
from django.db.models import get_model
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
