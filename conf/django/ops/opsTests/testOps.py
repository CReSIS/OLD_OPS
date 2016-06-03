# =========================================================================================
# PYTHON FILE DEFINING DJANGO/PYTHON UNITTESTS FOR OPS.
#
# Used with manage.py to test OPS django views.
#
# =========================================================================================

####    Necessary imports    ####
from django.contrib.auth.models import User
from django.test import TestCase
from django.test.client import RequestFactory
import ops.views as views
import ujson
import ops.utility


####    DEFINE FUNCTIONS USED BY TESTS    ####
#Function for parsing data response
def getData(response):
	return ujson.loads(response.content)['data']

#Function retunring path to fixtures used in tests requiring 
# initial data.
def testFixtures(*args):
	if not args:
		#Return the default.
		return ['/var/django/ops/opsTests/testFixtures.json']
	else:
		#Return a list of specified paths.
		fixtures = []
		for arg in args:
			fixtures.extend(arg)
		return fixtures
		
#Define the checkStatus function (should probably be used in all tests)
def checkStatus(self,response):
	#Cehck server status code
	self.assertEqual(response.status_code,200, 'SERVER ERROR: %s' % str(response.status_code)) 

	#Check OPS status code
	self.assertEqual(ujson.loads(response.content)['status'],1,getData(response))

#Define a setup subclass
def setUp(self):	
	#Every test will need a request factory.
	self.factory = RequestFactory()
	self.user = User.objects.create_user(username='admin',email='admin@admin.admin',password='admin')
	#Have the user be a root user
	self.user.profile.isRoot=True
	self.user.profile.save()
	#Let every test have access to database models.
	self.models = ops.utility.getAppModels('rds')

	
######	TESTS FOLLOW	######	
#Test the createPath() view.
class createPathTests(TestCase):
	fixtures = testFixtures()
	#Test only the status of createPath
	def test_createPath_status(self):
		setUp(self)
		# Set the json string
		jsonStr = '{ "type": "Feature", "geometry": { "type": "LineString", "coordinates": [ [ 76.422813519870743, -68.994377212760924 ], [ 76.422813519870743, -68.994377212760924 ], [ 76.422813519870743, -68.994377212760924 ] ] }, "properties": { "location": "arctic", "season": "test", "radar": "test", "segment": "99999999_01", "gps_time": [ 1301569765.9649489, 1301569766.9649489, 1301569767.9649489, 1301569768.9649489 ], "elev": [ 1257.839261098396, 1258.839261098396, 1259.839261098396, 1260.839261098396 ], "roll": [ -0.249471361002334, -0.249471361002334, -0.249471361002334, -0.249471361002334 ], "pitch": [ 0.088953745496139006, 0.088953745496139006, 0.088953745496139006, 0.088953745496139006 ], "heading": [ 2.1470276181592851, 2.1470276181592851, 2.1470276181592851, 2.1470276181592851 ], "frame_count": 2, "frame_start_gps_time": [ 1301569765.9649489, 1301569767.9649489 ], "season_group": "cresis_private", "userName": "admin", "isAuthenticated": true, "mat": true } }'
		
		#Create the request from the above app & jsonStr
		request = self.factory.post('create/path',{'app':'rds', 'data':jsonStr})
		#Get the response
		response = views.createPath(request)
		
		#Check the status
		checkStatus(self,response)
	
	#Test non-self intersecting crossovers
	def test_createPath_non_self_crossovers(self):
		setUp(self)
		jsonStr = '{ "type": "Feature", "geometry": { "type": "LineString", "coordinates": [ [ 1.5, 2.5 ], [ 1.5, 3.5 ], [ 3.5, 3.5 ], [ 3.5, 6 ] ] }, "properties": { "location": "arctic", "season": "fixtureTest", "radar": "fixtureTest", "segment": "10101010_01", "gps_time": [ 1301669765.9649489, 1301669766.9649489, 1301669767.9649489, 1301669768.9649489 ], "elev": [ 1267.839261098396, 1268.839261098396, 1269.839261098396, 1360.839261098396 ], "roll": [ -0.248471361002334, -0.249471361002334, -0.249471361002334, -0.249471361002334 ], "pitch": [ 0.088953745496139006, 0.088953745496139006, 0.088953745496139006, 0.088953745496139006 ], "heading": [ 2.1470276181592851, 2.1470276181592851, 2.1470276181592851, 2.1470276181592851 ], "frame_count": 2, "frame_start_gps_time": [ 1301669765.9649489, 1301669767.9649489 ], "season_group": "cresis_private", "userName": "admin", "isAuthenticated": true, "mat": true } }'
		

		#Create the request from the above app & jsonStr
		request = self.factory.post('create/path',{'app':'rds', 'data':jsonStr})
		#Get the response
		response = views.createPath(request)
		
		#Check the status
		checkStatus(self,response)
		
		#Check that the correct number of crossovers exist
		crossovers = self.models.crossovers.objects.count()
		
		#Check that the total number of crossovers equals 6. 
		# (5 crossovers from fixture + 1 from this test = 6)
		self.assertEqual(crossovers,6)

	#Test self intersecting crossovers
	def test_createPath_self_crossovers(self):
		setUp(self)
		jsonStr = '{ "type": "Feature", "geometry": { "type": "LineString", "coordinates": [ [ 10, 10], [ 20, 20], [ 15, 20 ], [ 20, 10 ] ] }, "properties": { "location": "arctic", "season": "fixtureTest", "radar": "fixtureTest", "segment": "11011011_01", "gps_time": [ 1301569765.9649489, 1301569766.9649489, 1301569767.9649489, 1301569768.9649489 ], "elev": [ 1257.839261098396, 1258.839261098396, 1259.839261098396, 1260.839261098396 ], "roll": [ -0.249471361002334, -0.249471361002334, -0.249471361002334, -0.249471361002334 ], "pitch": [ 0.088953745496139006, 0.088953745496139006, 0.088953745496139006, 0.088953745496139006 ], "heading": [ 2.1470276181592851, 2.1470276181592851, 2.1470276181592851, 2.1470276181592851 ], "frame_count": 2, "frame_start_gps_time": [ 1301569765.9649489, 1301569767.9649489 ], "season_group": "cresis_private", "userName": "admin", "isAuthenticated": true, "mat": true } }'
		
		#Create the request from the above app & jsonStr
		request = self.factory.post('create/path',{'app':'rds', 'data':jsonStr})
		#Get the response
		response = views.createPath(request)
		
		#Check the status
		checkStatus(self,response)
		
		#Check that the correct number of crossovers exist
		crossovers = self.models.crossovers.objects.count()
		
		#Check that the total number of crossovers equals 6. 
		# (5 crossovers from fixture + 1 from this test = 6)
		self.assertEqual(crossovers,6)
		
#Test createLayer() view.
class createLayerTests(TestCase):
	def test_createLayer_status(self):
		setUp(self)
		# Set the json string
		jsonStr = '{ "properties": { "lyr_name": "test", "lyr_group_name": "test", "lyr_description": "this is a test layer", "userName": "admin", "isAuthenticated": true, "mat": true } }'
		
		#Create the request from the above app & jsonStr
		request = self.factory.post('create/Layer',{'app':'rds','data':jsonStr})
		#Get the response
		response = views.createLayer(request)
		
		#Check the status
		checkStatus(self,response)
		
		#Make sure the layer was actually inserted
		self.assertEqual(self.models.layers.objects.filter(name__exact='test').count(),1)

#Test deleteLayer() view.		
class deleteLayerTests(TestCase):
	fixtures = testFixtures()
	def test_deleteLayer(self):
		setUp(self)
		# Set the json string that will be sent to the view
		jsonStr = '{ "properties": { "lyr_name": "fixtureTest" } }'
		
		#Create the request from the above app & jsonStr
		request = self.factory.post('delete/layer',{'app':'rds','data':jsonStr})
		#Get the response
		response = views.deleteLayer(request)
		
		#Check the status
		checkStatus(self,response)
		
		#Make sure the layer now has a deleted status.
		self.assertEqual(self.models.layers.objects.filter(name__exact='fixtureTest',deleted=True).count(),1)

#Test createLayerPoints() view.
class createLayerPointsTests(TestCase):			
	def test_createLayerPoints(self):
		setUp(self)
		# Set the json string
		jsonStr = '{ "properties": { "point_path_id": [ 4, 5, 6 ], "twtt": [ 2.4170566340199198e-006, 2.5170566340199299e-006, 2.3170566340199398e-006 ], "type": [ 1, 2, 1 ], "quality": [ 1, 2, 3 ], "lyr_name": "surface", "lyr_group_name": "standard", "userName": "admin", "isAuthenticated": true, "mat": true } }'
		
		#Create the request from the above app & jsonStr
		request = self.factory.post('create/layer/points',{'app':'rds','data':jsonStr})
		#Get the response
		response = views.createLayerPoints(request)
		
		#Check the status
		checkStatus(self,response)
		
		#Make sure the points were inserted properly
		self.assertEqual(self.models.layer_points.objects.filter(point_path_id__in=[4,5,6],user_id__username='admin',layer_id=1).count(),3)
		
#Test deleteLayerPoints() view
class deleteLayerPointsTests(TestCase):
	fixtures = testFixtures()
	def test_deleteLayerPoints_start_stop_point_path_id(self):
		setUp(self)
		# Set the json string
		jsonStr = '{ "properties": { "start_point_path_id": 2, "stop_point_path_id": 2, "max_twtt": 2.5170715674515201e-006, "min_twtt": 2.3170513543513799e-006, "lyr_name": "fixtureTest" } }'
		
		#Create the request from the above app & jsonStr
		request = self.factory.post('delete/layer/points',{'app':'rds','data':jsonStr})
		#Get the response
		response = views.deleteLayerPoints(request)
		
		#Check the status
		checkStatus(self,response)
		
		#Make sure the layer points were actually removed (There are 3 layer points w/ layer_id=3 from testFixtures).
		self.assertEqual(self.models.layer_points.objects.filter(layer_id=3,point_path_id__in=[1,3]).count(),2)
		
	def test_deleteLayerPoints_start_stop_gps_time(self):
		setUp(self)
		# Set the json string
		jsonStr = '{ "properties": { "location": "arctic", "segment": "11111111_01", "start_gps_time": 1301569766.964949, "stop_gps_time": 1301569766.964949, "max_twtt": 2.5170715674515201e-006, "min_twtt": 2.3170513543513799e-006, "season":  "fixtureTest", "lyr_name": "fixtureTest" } }'
		
		#Create the request from the above app & jsonStr
		request = self.factory.post('delete/layer/points',{'app':'rds','data':jsonStr})
		#Get the response
		response = views.deleteLayerPoints(request)
		
		#Check the status
		checkStatus(self,response)
		
		#Make sure the layer points were actually removed (There are 3 layer points w/ layer_id=3 from testFixtures).
		self.assertEqual(self.models.layer_points.objects.filter(layer_id=3,point_path_id__in=[1,3]).count(),2)
		
#Test the deleteBulk() view
class deleteBulkTests(TestCase):
	fixtures = testFixtures()
	def test_deleteBulk_onlyLayerPoints(self):
		setUp(self)
		# Set the json string (deletes only layer points for one segment)
		jsonStr = '{ "properties": { "season": "fixtureTest", "only_layer_points": 1, "segment": [ "11111111_01" ], "userName": "admin", "isAuthenticated": true, "mat": true } }'
		
		#Create the request from the above app & jsonStr
		request = self.factory.post('delete/bulk',{'app':'rds','data':jsonStr})
		#Get the response
		response = views.deleteBulk(request)
		
		#Check the status
		checkStatus(self,response)
		
		#Make sure that the layer points were removed:
		self.assertEqual(self.models.layer_points.objects.filter(point_path_id__segment__name='11111111_01').count(),0)
		
		#The segment should still exist
		self.assertEqual(self.models.segments.objects.filter(name='11111111_01').count(),1)
		
	def test_deleteBulk_all(self):
		setUp(self)
		# Set the json string (deletes everything.)
		jsonStr = '{ "properties": { "season": "fixtureTest", "only_layer_points": 0, "segment": [ "" ], "userName": "admin", "isAuthenticated": true, "mat": true } }'
		
		#Create the request from the above app & jsonStr
		request = self.factory.post('delete/bulk',{'app':'rds','data':jsonStr})
		#Get the response
		response = views.deleteBulk(request)
		
		#Check the status
		checkStatus(self,response)
		
		#Make sure the season no longer exists
		self.assertEqual(self.models.seasons.objects.filter(name='fixtureTest').count(),0)

#Test the releaseLayerGroup() view
class releaseLayerGroupTests(TestCase):	
	fixtures = testFixtures()	
	def test_releaseLayerGroup(self):
		setUp(self)
		# Set the json string
		jsonStr = '{ "properties": { "lyr_group_name": "fixtureTest" } }'
		
		#Create the request from the above app & jsonStr
		request = self.factory.post('release/layer/group',{'app':'rds','data':jsonStr})
		#Get the response
		response = views.releaseLayerGroup(request)
		
		#Check the status
		checkStatus(self,response)
		
		#Make sure the group was released
		self.assertTrue(self.models.layer_groups.objects.filter(name='fixtureTest').values_list('public',flat=True)[0])

#Test the getPath() view
class getPathTests(TestCase):
	fixtures = testFixtures()
	def test_getPath(self):
		setUp(self)
		# Set the json string
		jsonStr = '{ "properties": { "location": "arctic", "season": "fixtureTest", "start_gps_time": 1301569764.9649489, "stop_gps_time": 1301569868.9649489, "nativeGeom": true } }'
		
		#Create the request from the above app & jsonStr
		request = self.factory.post('get/path',{'app':'rds','data':jsonStr})
		#Get the response
		response = views.getPath(request)
		
		#Check the status
		checkStatus(self,response)
		
		#Make sure all the point paths were returned
		data = getData(response)
		self.assertEqual(len(data['gps_time']),7)
		
#Test the getFrameClosest() view
class getFrameClosestTests(TestCase):
	fixtures = testFixtures()
	def test_getFrameClosest(self):
		setUp(self)
		# Set the json string
		jsonStr = '{ "properties": { "location": "arctic", "x": 8857530.81742116, "y": -8116431.61282304, "season": "fixtureTest", "startseg": "11111111_01", "stopseg": "22222222_02"} }'
		
		#Create the request from the above app & jsonStr
		request = self.factory.post('get/frame/closest',{'app':'rds','data':jsonStr})
		#Get the response
		response = views.getFrameClosest(request)
		
		#Check the status
		checkStatus(self,response)
		
		#Make sure the correct frame is returned
		data = getData(response)
		self.assertEqual(data['frame'],'22222222_02_001')

#Test the getLayers() view
class getLayersTests(TestCase):	
	fixtures = testFixtures()
	def test_getLayers(self):
		setUp(self)
		# Set the json string
		jsonStr = '{ "properties": { "mat": true, "userName": "admin", "isAuthenticated": true } }'
		
		#Create the request from the above app & jsonStr
		request = self.factory.post('get/layers',{'app':'rds','data':jsonStr})
		#Get the response
		response = views.getLayers(request)
		
		#Check the status
		checkStatus(self,response)
		
		#Make sure all of the layers were returned. 
		data = getData(response)
		self.assertEqual(len(data['lyr_id']),3)

#Test the getLayerPoints() view
class getLayerPointsTests(TestCase):	
	fixtures = testFixtures()
	def test_getLayerPoints(self):
		setUp(self)
		# Set the json string
		jsonStr = '{ "properties": { "location": "arctic", "season": "fixtureTest", "segment": "11111111_01", "return_geom": "geog", "lyr_name": [ "surface", "bottom", "fixtureTest" ], "start_gps_time": 1301569764.9649489, "stop_gps_time": 1301569868.9649489, "mat": true, "userName": "admin", "isAuthenticated": true } }'
		
		#Create the request from the above app & jsonStr
		request = self.factory.post('get/layer/points',{'app':'rds','data':jsonStr})
		#Get the response
		response = views.getLayerPoints(request)
		
		#Check the status
		checkStatus(self,response)
		
		#Make sure the layer points are returned.
		data = getData(response)
		self.assertEqual(len(data['gps_time']),3)

#Test the getLayerPointsCsv() view
class getLayerPointsCsvTests(TestCase):
	def test_getLayerPointsCsv(self):
		#Not implemented yet.
		pass

#Test the getSystemInfo() view
class getSystemInfoTests(TestCase):
	fixtures = testFixtures()
	def test_getSystemInfo(self):
		setUp(self)
		# Set the json string
		jsonStr = '{ "properties": { "userName": "admin", "isAuthenticated": true, "mat": true } }'
		
		#Create the request from the above app & jsonStr
		request = self.factory.post('get/system/info',{'app':'rds','data':jsonStr})
		#Get the response
		response = views.getSystemInfo(request)
		
		#Check the status
		checkStatus(self,response)
		
		#Make sure the response is correct
		data = getData(response)
		self.assertEqual(data[0]['season'],'fixtureTest')

#Test the getSegmentInfo() view
class getSegmentInfoTests(TestCase):
	fixtures = testFixtures()
	def test_getSegmentInfo(self):
		setUp(self)
		# Set the json string
		jsonStr = '{ "properties": { "segment": "11111111_01", "season": "fixtureTest" } }'
		
		#Create the request from the above app & jsonStr
		request = self.factory.post('get/segment/info',{'app':'rds','data':jsonStr})
		#Get the response
		response = views.getSegmentInfo(request)
		
		#Check the status
		checkStatus(self,response)
		
		#Make sure the response at least returns the correct season.
		data = getData(response)
		self.assertEqual(data['season'],'fixtureTest')

#Test the getCrossovers() view
class getCrossoversTests(TestCase):	
	fixtures = testFixtures()
	def test_getCrossovers(self):
		setUp(self)
		# Set the json string
		jsonStr = '{ "properties": { "location": "arctic", "lyr_name": "fixtureTest", "frame": [ "11111111_01_001", "11111111_01_002", "22222222_02_001", "22222222_02_002" ], "segment_id": [ 1, 1, 1 ,1 ] } }'
		
		#Create the request from the above app & jsonStr
		request = self.factory.post('get/crossovers',{'app':'rds','data':jsonStr})
		#Get the response
		response = views.getCrossovers(request)
		
		#Check the status
		checkStatus(self,response)

		#Make sure the correct number of crossovers is returned (should be 5)
		data = getData(response)
		self.assertEqual(len(data['angle']),5)

#Test the getCrossoversReport() view
class getCrossoversReportTests(TestCase):		
	def test_getCrossoversReport(self):
		#Not implemented yet
		pass
		
#Test the getFrameSearch() view
class getFrameSearchTests(TestCase):
	fixtures = testFixtures()
	def test_getFrameSearch(self):
		setUp(self)
		# Set the json string
		jsonStr = '{ "properties": { "search_str": "11111111", "location": "arctic", "season": "fixtureTest" } }'
		
		#Create the request from the above app & jsonStr
		request = self.factory.post('get/frame/search',{'app':'rds','data':jsonStr})
		#Get the response
		response = views.getFrameSearch(request)
		
		#Check the status
		checkStatus(self,response)
		
		#Make sure the correct frame is returned
		data = getData(response)
		self.assertEqual(data['frame'],'11111111_01_001')
		
#Test the getInitialData() view
class getInitialDataTests(TestCase):		
	def test_getInitialData(self):
		#Not implemented yet
		pass

#Test the getUserProfileData() view
class getUserProfileDataTests(TestCase):		
	def test_getUserProfileData(self):
		setUp(self)
		# Set the json string
		jsonStr = '{ "properties": { "mat": true, "userName": "admin", "isAuthenticated": true } }'
		
		#Create the request from the above app & jsonStr
		request = self.factory.post('get/user/profile/data',{'app':'rds','data':jsonStr})
		#Get the response
		response = views.getUserProfileData(request)
		
		#Check the status
		checkStatus(self,response)

		#Make sure the response is correct
		data = getData(response)
		self.assertTrue(data['isRoot'])
		
#Test the createUser() view
class createUserTests(TestCase):
	def test_createUser(self):
		setUp(self)
		# Set the json string
		jsonStr = '{ "properties": { "mat": true, "userName": "testUser", "password": "testUser", "email": "test.test@test.test" } }'
		
		#Create the request from the above app & jsonStr
		request = self.factory.post('create/user',{'app':'rds','data':jsonStr})
		#Get the response
		response = views.createUser(request)
		
		#Check the status
		checkStatus(self,response)
		
		#Make sure the user was created with isRoot=False.
		self.assertFalse(User.objects.get(username__exact='testUser').profile.isRoot)

#Test the alterUserPermissions() view
class alterUserPermissionsTests(TestCase):
	def test_alterUserPermissions(self):
		setUp(self)
		#Create a default user to change
		User.objects.create_user(username='testDefault',email='test@default.test',password='testDefault')
		
		# Set the json string
		jsonStr = '{ "properties": { "user_name": "testDefault", "isRoot": "true", "userName": "admin", "isAuthenticated": true, "mat": true } }'
		
		#Create the request from the above app & jsonStr
		request = self.factory.post('alter/user/permissions',{'app':'rds','data':jsonStr})
		#Get the response
		response = views.alterUserPermissions(request)
		
		#Check the status
		checkStatus(self,response)
		
		#Make sure the altered user now has isRoot=True
		self.assertTrue(User.objects.get(username__exact='testDefault').profile.isRoot)

#Test the loginUser() view
class loginUserTests(TestCase):		
	def test_loginUser(self):	
		#Not implemented yet
		pass	

#Test the logoutUser() view
class logoutUserTests(TestCase):		
	def test_logoutUser(self):
		#Not implemented yet
		pass

#Test the query() view
class queryTests(TestCase):
	fixtures = testFixtures()
	def test_query(self):	
		setUp(self)
		#Create the request from the above app & jsonStr
		request = self.factory.post('query',{'query':'SELECT id FROM rds_point_paths'})
		#Get the response
		response = views.query(request)
		
		#Check the status
		checkStatus(self,response)
		
		#Make sure all of the correct ids from rds_point_paths were returned
		data = getData(response)
		self.assertEqual(len(data),7)

#Test the analyze() view
class analyzeTests(TestCase):
	fixtures = testFixtures()
	def test_analyze(self):	
		setUp(self)
		# Set the json string
		jsonStr = '{ "properties": { "tables": [ "segments", "point_paths" ] } }'
		
		#Create the request from the above app & jsonStr
		request = self.factory.post('analyze',{'app':'rds','data':jsonStr})
		#Get the response
		response = views.analyze(request)

		#Check the status
		checkStatus(self,response)
