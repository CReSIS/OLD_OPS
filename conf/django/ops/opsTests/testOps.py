from django.contrib.auth.models import User
from django.test import TestCase
from django.test.client import RequestFactory

class simpleTest(TestCase):

	#Fixtures in the testFixtures.json file will be re-loaded into a fresh test databse for each test.
	fixtures = ['/var/django/ops/opsTests/testFixtures.json']
	
	def checkStatus(self,response):
		#Cehck server status code
		self.assertEqual(response.status_code,200, 'SERVER ERROR: %s' % str(response.status_code)) 

		#Check OPS status code
		self.assertEqual(self.ujson.loads(response.content)['status'],1,self.ujson.loads(response.content)['data'])
		
	#Define the setup subclass
	def setUp(self):
		#global imports
		import ops.views
		self.views = ops.views
		import ujson 
		self.ujson = ujson
		
		#Every test will need a request factory.
		self.factory = RequestFactory()
		self.user = User.objects.create_user(username='admin',email='admin@admin.admin',password='admin')
		#Have the user be a root user
		self.user.profile.isRoot=True
		self.user.profile.save()
		
		
	# TESTS FOLLOW:	
	# CHANGE test_createPath TO ALSO TEST FINDING CROSSOVERS
	def test_createPath(self):
		# Set the json string
		jsonStr = '{ "type": "Feature", "geometry": { "type": "LineString", "coordinates": [ [ 76.422813519870743, -68.994377212760924 ], [ 76.422813519870743, -68.994377212760924 ], [ 76.422813519870743, -68.994377212760924 ] ] }, "properties": { "location": "arctic", "season": "test", "radar": "test", "segment": "99999999_01", "gps_time": [ 1301569765.9649489, 1301569766.9649489, 1301569767.9649489, 1301569768.9649489 ], "elev": [ 1257.839261098396, 1258.839261098396, 1259.839261098396, 1260.839261098396 ], "roll": [ -0.249471361002334, -0.249471361002334, -0.249471361002334, -0.249471361002334 ], "pitch": [ 0.088953745496139006, 0.088953745496139006, 0.088953745496139006, 0.088953745496139006 ], "heading": [ 2.1470276181592851, 2.1470276181592851, 2.1470276181592851, 2.1470276181592851 ], "frame_count": 2, "frame_start_gps_time": [ 1301569765.9649489, 1301569767.9649489 ], "season_group": "cresis_private", "userName": "admin", "isAuthenticated": true, "mat": true } }'
		
		#Create the request from the above app & jsonStr
		request = self.factory.post('create/path',{'app':'rds', 'data':jsonStr})
		#Get the response
		response = self.views.createPath(request)
		
		#Check the status
		self.checkStatus(response)
		
	def test_createLayer(self):
		# Set the json string
		jsonStr = '{ "properties": { "lyr_name": "test", "lyr_group_name": "test", "lyr_description": "this is a test layer", "userName": "admin", "isAuthenticated": true, "mat": true } }'
		
		#Create the request from the above app & jsonStr
		request = self.factory.post('create/Layer',{'app':'rds','data':jsonStr})
		#Get the response
		response = self.views.createLayer(request)
		
		#Check the status
		self.checkStatus(response)
		
	def test_deleteLayer(self):
		# Set the json string that will be sent to the view
		jsonStr = '{ "properties": { "lyr_name": "fixtureTest" } }'
		
		#Create the request from the above app & jsonStr
		request = self.factory.post('delete/Llyer',{'app':'rds','data':jsonStr})
		#Get the response
		response = self.views.deleteLayer(request)
		
		#Check the status
		self.checkStatus(response)
		
	def test_createLayerPoints(self):
		# Set the json string
		jsonStr = '{ "properties": { "point_path_id": [ 4, 5, 6 ], "username": "fixtureAdmin", "twtt": [ 2.4170566340199198e-006, 2.5170566340199299e-006, 2.3170566340199398e-006 ], "type": [ 1, 2, 1 ], "quality": [ 1, 2, 3 ], "lyr_name": "surface", "lyr_group_name": "standard", "userName": "admin", "isAuthenticated": true, "mat": true } }'
		
		#Create the request from the above app & jsonStr
		request = self.factory.post('create/layer/points',{'app':'rds','data':jsonStr})
		#Get the response
		response = self.views.createLayerPoints(request)
		
		#Check the status
		self.checkStatus(response)
		
	def test_deleteLayerPoints(self):
		# Set the json string
		jsonStr = '{ "properties": { "start_point_path_id": 2, "stop_point_path_id": 2, "max_twtt": 2.5170715674515201e-006, "min_twtt": 2.3170513543513799e-006, "lyr_name": "fixtureTest" } }'
		
		#Create the request from the above app & jsonStr
		request = self.factory.post('delete/layer/points',{'app':'rds','data':jsonStr})
		#Get the response
		response = self.views.deleteLayerPoints(request)
		
		#Check the status
		self.checkStatus(response)
		
	def test_deleteBulk_onlyLayerPoints(self):
		# Set the json string (deletes only layer points for one segment)
		jsonStr = '{ "properties": { "season": "fixtureTest", "only_layer_points": 1, "segment": [ "11111111_01" ], "userName": "admin", "isAuthenticated": true, "mat": true } }'
		
		#Create the request from the above app & jsonStr
		request = self.factory.post('delete/bulk',{'app':'rds','data':jsonStr})
		#Get the response
		response = self.views.deleteBulk(request)
		
		#Check the status
		self.checkStatus(response)
		
	def test_deleteBulk_all(self):
		# Set the json string (deletes everything.)
		jsonStr = '{ "properties": { "season": "fixtureTest", "only_layer_points": 0, "segment": [ "" ], "userName": "admin", "isAuthenticated": true, "mat": true } }'
		
		#Create the request from the above app & jsonStr
		request = self.factory.post('delete/bulk',{'app':'rds','data':jsonStr})
		#Get the response
		response = self.views.deleteBulk(request)
		
		#Check the status
		self.checkStatus(response)
		
	def test_releaseLayerGroup(self):
		# Set the json string
		jsonStr = '{ "properties": { "lyr_group_name": "fixtureTest" } }'
		
		#Create the request from the above app & jsonStr
		request = self.factory.post('release/layer/group',{'app':'rds','data':jsonStr})
		#Get the response
		response = self.views.releaseLayerGroup(request)
		
		#Check the status
		self.checkStatus(response)
		
	def test_getPath(self):
		# Set the json string
		jsonStr = '{ "properties": { "location": "arctic", "season": "fixtureTest", "start_gps_time": 1301569764.9649489, "stop_gps_time": 1301569868.9649489, "nativeGeom": true } }'
		
		#Create the request from the above app & jsonStr
		request = self.factory.post('get/path',{'app':'rds','data':jsonStr})
		#Get the response
		response = self.views.getPath(request)
		
		#Check the status
		self.checkStatus(response)

	def test_getFrameClosest(self):
		# Set the json string
		jsonStr = '{ "properties": { "location": "arctic", "x": 1, "y": 1, "season": "fixtureTest", "startseg": "11111111_01", "stopseg": "22222222_02", "status": [ true, false ] } }'
		
		#Create the request from the above app & jsonStr
		request = self.factory.post('get/frame/closest',{'app':'rds','data':jsonStr})
		#Get the response
		response = self.views.getFrameClosest(request)
		
		#Check the status
		self.checkStatus(response)
		
	def test_getLayers(self):
		# Set the json string
		jsonStr = '{ "properties": { "mat": true, "userName": "admin", "isAuthenticated": true } }'
		
		#Create the request from the above app & jsonStr
		request = self.factory.post('get/layers',{'app':'rds','data':jsonStr})
		#Get the response
		response = self.views.getLayers(request)
		
		#Check the status
		self.checkStatus(response)
		
	def test_getLayerPoints(self):
		# Set the json string
		jsonStr = '{ "properties": { "location": "arctic", "season": "fixtureTest", "segment": "11111111_01", "return_geom": "geog", "lyr_name": [ "surface", "bottom", "fixtureTest" ], "start_gps_time": 1301569764.9649489, "stop_gps_time": 1301569868.9649489, "mat": true, "userName": "admin", "isAuthenticated": true } }'
		
		#Create the request from the above app & jsonStr
		request = self.factory.post('get/layer/points',{'app':'rds','data':jsonStr})
		#Get the response
		response = self.views.getLayerPoints(request)
		
		#Check the status
		self.checkStatus(response)

	def test_getLayerPointsCsv(self):
		#Not implemented yet.
		pass
		
	def test_getSystemInfo(self):
		# Set the json string
		jsonStr = '{ "properties": { "userName": "admin", "isAuthenticated": true, "mat": true } }'
		
		#Create the request from the above app & jsonStr
		request = self.factory.post('get/system/info',{'app':'rds','data':jsonStr})
		#Get the response
		response = self.views.getSystemInfo(request)
		
		#Check the status
		self.checkStatus(response)
		
	def test_getSegmentInfo(self):
		# Set the json string
		jsonStr = '{ "properties": { "segment": "11111111_01", "season": "fixtureTest" } }'
		
		#Create the request from the above app & jsonStr
		request = self.factory.post('get/segment/info',{'app':'rds','data':jsonStr})
		#Get the response
		response = self.views.getSegmentInfo(request)
		
		#Check the status
		self.checkStatus(response)
		
	def test_getCrossovers(self):
		# Set the json string
		jsonStr = '{ "properties": { "location": "arctic", "lyr_name": "fixtureTest", "frame": [ "11111111_01_001", "11111111_01_002", "22222222_02_001", "22222222_02_002" ] } }'
		
		#Create the request from the above app & jsonStr
		request = self.factory.post('get/crossovers',{'app':'rds','data':jsonStr})
		#Get the response
		response = self.views.getCrossovers(request)
		
		#Check the status
		self.checkStatus(response)	
		
	def test_getCrossoversReport(self):
		#Not implemented yet
		pass
		
	def test_getFrameSearch(self):
		# Set the json string
		jsonStr = '{ "properties": { "search_str": "11111111", "location": "arctic", "season": "fixtureTest" } }'
		
		#Create the request from the above app & jsonStr
		request = self.factory.post('get/frame/search',{'app':'rds','data':jsonStr})
		#Get the response
		response = self.views.getFrameSearch(request)
		
		#Check the status
		self.checkStatus(response)
		
	def test_getInitialData(self):
		#Not implemented yet
		pass
		
	def test_getUserProfileData(self):
		# Set the json string
		jsonStr = '{ "properties": { "mat": true, "userName": "admin", "isAuthenticated": true } }'
		
		#Create the request from the above app & jsonStr
		request = self.factory.post('get/user/profile/data',{'app':'rds','data':jsonStr})
		#Get the response
		response = self.views.getUserProfileData(request)
		
		#Check the status
		self.checkStatus(response)
		
	def test_createUser(self):
		# Set the json string
		jsonStr = '{ "properties": { "mat": true, "userName": "testUser", "password": "testUser", "email": "test.test@test.test" } }'
		
		#Create the request from the above app & jsonStr
		request = self.factory.post('create/user',{'app':'rds','data':jsonStr})
		#Get the response
		response = self.views.createUser(request)
		
		#Check the status
		self.checkStatus(response)

	def test_alterUserPermissions(self):
		#Create a default user to change
		User.objects.create_user(username='testDefault',email='test@default.test',password='testDefault')
		
		# Set the json string
		jsonStr = '{ "properties": { "user_name": "testDefault", "isRoot": "true", "userName": "admin", "isAuthenticated": true, "mat": true } }'
		
		#Create the request from the above app & jsonStr
		request = self.factory.post('alter/user/permissions',{'app':'rds','data':jsonStr})
		#Get the response
		response = self.views.alterUserPermissions(request)
		
		#Check the status
		self.checkStatus(response)
		
	def test_loginUser(self):	
		#Not implemented yet
		pass	
		
	def test_logoutUser(self):
		#Not implemented yet
		pass
		
	def test_query(self):	
		#Create the request from the above app & jsonStr
		request = self.factory.post('query',{'query':'SELECT id FROM rds_point_paths'})
		#Get the response
		response = self.views.query(request)
		
		#Check the status
		self.checkStatus(response)

	def test_analyze(self):	
		# Set the json string
		jsonStr = '{ "properties": { "tables": [ "segments", "point_paths" ] } }'
		
		#Create the request from the above app & jsonStr
		request = self.factory.post('analyze',{'app':'rds','data':jsonStr})
		#Get the response
		response = self.views.analyze(request)
		
		#Check the status
		self.checkStatus(response)