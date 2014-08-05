from django.http import HttpResponse
from django.db.models import get_model
from authip import *
from django.contrib.auth.models import User
from functools import wraps
from decimal import Decimal
import math,collections,string,random,traceback,sys,ujson,json

def response(status,data,cookies):
	""" Creates an HttpResponse with OPS formatted JSON data.
	
	Input:
		status: (integer) 0:failure 1:success 2:warning
		data: (dictionary) a dictionary of key value pairs
		cookies: (dictionary) a dictionary of key value pairs of cookies
		
	Output:
		HttpResponse: http response object returned to web server
	
	"""
	outResponse = HttpResponse(ujson.dumps({'status':status,'data':data}),content_type='application/json')
	for key,value in cookies.iteritems():
		outResponse.set_cookie(key,value,max_age=3600)
	return outResponse

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

def errorCheck(exception,sys):
	""" Creates a human readable error string from a system error object.
	
	Input:
		exception: an exception instance
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
		try:
			trace = traceback.extract_tb(error[2])[1]
			errorOut = str(errorType)+' ERROR IN '+errorFile+'/'+ errorMod+' AT LINE '+str(errorLine)+':: ERROR: '+errorStr + '  | TRACEBACK: ' + trace[0] + ' LINE ' + str(trace[1])
		except:
			errorOut = str(errorType)+' ERROR IN '+errorFile+'/'+ errorMod+' AT LINE '+str(errorLine)+':: ERROR: '+errorStr
		
		return response(0, ujson.dumps(errorOut),{})
	except:
		try: 
			#If error check fails, try to return some useful info. 
			return response(0, str(exception),{})
		except:
			return response(0, 'ERROR: ERROR CHECK FAILED ON EXCEPTION.',{})

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
		raise Exception('ONLY (antarctic and arctic) MAPPED FOR epsgFromLocation().')

def twttToRange(surfTwtt,layerTwtt):
	""" Convert a layer's two-way travel time to range from aircraft in wgs1984 meters.
	
	Input:
		surfTwtt: (float) the two-way travel time of the surface for the given value
		layerTwtt: (float) the two-way travel time of the layer for the given value
		
	Output:
		surfRange: (float) the range in wgs1984 meters of the input surfaceTwtt from the aircraft
		layerRange: (float) the range in wgs1984 meters of the input layerTwtt from the aircraft
	
	"""
	myC = Decimal(299792458.0)
	surfRange = surfTwtt*(myC/Decimal(2.0))
	layerRange = surfRange + ((layerTwtt-surfTwtt)*(myC/Decimal(2.0)/Decimal(math.sqrt(3.15))))
	return surfRange,layerRange

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

		query = request.POST.get('query')
		cookies = request.COOKIES

		if query is not None:
			return query,cookies
		else:
			raise Exception('VALUE ''query'' IS NOT VALID OR EMPTY')

	else:
		raise Exception('method must be POST')

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
			jsonData = request.POST.get('data')
			
			if jsonData is not None:
				data = json.loads(jsonData,parse_float=Decimal)

			# parse for MATLAB specific input (build "cookies")
			try:
				outCookies = {}
				isMat = data['properties']['mat']
				outCookies['userName'] = data['properties']['userName']
				outCookies['isAuthenticated'] = data['properties']['isAuthenticated']
				outCookies['isMat'] = True
			except:
				outCookies = {}
				cookies = request.COOKIES
				outCookies['userName'] = cookies.get('userName')
				outCookies['isAuthenticated'] = cookies.get('isAuthenticated')
				outCookies['isMat'] = False
			
			if data is not None and app is not None:
				return app,data,outCookies
			else:
				raise Exception('INPUT VARIABLE ''data'' OR ''app'' IS EMPTY')
		except:
			raise Exception('COULD NOT GET POST')
	else:
		raise Exception('METHOD MUST BE POST')

def getAppModels(app):
	""" Gets the Django models for a specified application.
	
	Input:
		app: (string) application name
		
	Output:
		models: (named tuple) django model objects for the given application

	"""
	models = collections.namedtuple('model',['locations','seasons','season_groups','radars','segments','frames','point_paths','crossovers','layer_groups','layers','layer_links','layer_points','landmarks'])
	
	locations = get_model(app,'locations')
	seasons = get_model(app,'seasons')
	season_groups = get_model(app,'season_groups')
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

	return models(locations,seasons,season_groups,radars,segments,frames,point_paths,crossovers,layer_groups,layers,layer_links,layer_points,landmarks)

def getInput(request):
	""" Wrapper for getData that gets the application models and decodes the JSON
	
	Input:
		request: HTTPRequest object
		
	Output:
		models: (named tuple) django model objects for the given application
		data: (dictionary) decoded JSON data
		app: (string) application name
		cookies
	
	"""
	app,data,cookies = getData(request)

	models = getAppModels(app)
	
	return models,data,app,cookies

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
		if isinstance(var,str):
			return (var,)
		try:
			return tuple(var)
		except TypeError:
			return (var,)
	else:
		return var

def forceBool(var):
	if str(var).lower() in ['true','t','1','y','yes']:
		return True
	elif str(var).lower() in ['false','f','0','n','no']:
		return False
	else:
		raise Exception('forceBool() CANNOT CONVERT ' + str(var) + ' TO BOOLEAN')
	
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
	return [baseEchoURl+'_1echo.jpg',baseEchoURl+'_2echo_picks.jpg']

def getUserProfile(cookies):
	""" Get a user profile based on input user and authentication
	
	Input:
		cookies: (dict) cookies output from getInput()
		
	Output:
		userProfileObj: (dict) Django user profile object
	
	"""
	
	# get user information from cookies
	userName = cookies['userName']
	isAuthenticated = cookies['isAuthenticated']

	if not isAuthenticated:
		message = 'USER %s IS NOT AUTHENTICATED' % userName
		return message,False

	# get the user profile
	userObj = User.objects.get(username__exact=userName)
	userProfileObj = userObj.profile
		
	return userProfileObj,True