from django.http import HttpResponse
from auth_ips import *
from functools import wraps
from django.db.models import get_model
from django.contrib.gis.geos import Point,LineString,WKBReader
from scipy.constants import c
from math import fabs,atan,degrees,sqrt
import collections,string,random,time,traceback,sys,ujson,pdb

def response(status,data):
    return HttpResponse(ujson.dumps({'status':status,'data':data}),content_type='application/json')
    
def ip_authorization():
    def decorator(view):
        @wraps(view)
        def wrapper(request, *args, **kwargs):
            request_ip = request.META['REMOTE_ADDR']
            if request_ip in AUTHORIZED_IPS:
                return view(request, *args, **kwargs)
            else:
                return HttpResponse(status=403,content='403: Forbidden')
        return wrapper
    return decorator

def error_check(sys):
    try:
        error = sys.exc_info()
        err_str = error[1][0]
        err_line = traceback.extract_tb(error[2])[0][1]
        err_type = error[0]
        err_file = traceback.extract_tb(error[2])[0][0]
        err_mod = traceback.extract_tb(error[2])[0][2]
        error_return = str(err_type)+' ERROR IN '+err_file+'/'+ err_mod+' AT LINE '+str(err_line)+':: ERROR: '+err_str
        return response(0, ujson.dumps(error_return))
    except:
        return response(0, 'UNKOWN ERROR (ERROR CHECK FAILED.)')

def proj_from_region(region):
    if region == 'arctic':
        return 3413
    elif region == 'antarctic':
        return 3031
    else:
        return response(0,'ERROR. ONLY MAPPED FOR (antarctic or arctic).')

def twtt2distm(surface_twtt,layer_twtt):
    surface_m = surface_twtt*(c/2.0)
    layer_m = surface_m + ((layer_twtt-surface_twtt)*(c/(sqrt(3.15)*2.0)))
    return surface_m,layer_m

def randid(size):
    return ''.join(random.choice(string.ascii_letters+string.digits) for _ in range(size))

def get_query(request):
    if request.method == 'POST':
        try:
            query = request.POST.get('query')
            
            if query is not None:
                return True,query
            else:
                return False,response(0,'query is empty in POST')
        except:
            return error_check(sys)
    else:
        return False,response(0,'method must be POST')

def get_data(request):
    if request.method == 'POST':
        try:
            app = request.POST.get('app')
            data = request.POST.get('data')
            if data is not None and app is not None:
				#return False,response(1,{"app":app,"data":json.loads(data)}),''
                return True,app,data
            else:
                return False,response(0,'data or app is empty in POST'),''
        except:
            return False,response(0,'could not get POST'),''
    else:
        return False,response(0,'method must be POST'),''

'''def get_data(request):
	if request.method == 'POST':
		try:
			app = request.POST.get('app')
			data = request.POST.get('data')
			if data is not None or app is not None:
				return True,app,data
		except:
			try:
				return False,response(1,request.body),''
				#bodyData = json.loads(request.body)
				#app = bodyData['app']
				#data = bodyData['data']
				if data is not None or app is not None:
					return True,app,data
				else:
					return False,response(0,'NO DATA IN POST OR BODY'),''
			except:
				return False,response(0,'ERROR RETRIEVING POST'),''
	else:
		return False,response(0,'METHOD MUST BE POST'),''


def get_data(request):
	if request.method == 'POST':
	
		try:
			app = request.POST.get('app')
			data = request.POST.get('data')
			if data is not None and app is not None:
				return False,response(1,[app,data]),''
			else:
				bodyData = json.loads(request.body)
				return False,response(1,str(type(bodyData))),''
		except:
			return False,response(1,'somethin failed'),''
	else:
		return False,response(0,'METHOD MUST BE POST'),''
'''
def get_app_models(app):
    
    models = collections.namedtuple('model',['locations','seasons','radars','point_paths','segments','frames','layers','layer_groups','layer_points','echograms','crossovers','landmarks', 'layer_links'])
    
    locations = get_model(app,'locations')
    seasons = get_model(app,'seasons')
    radars = get_model(app,'radars')
    point_paths = get_model(app,'point_paths')
    segments = get_model(app,'segments')
    frames = get_model(app,'frames')
    layers = get_model(app,'layers')
    layer_groups = get_model(app,'layer_groups')
    layer_points = get_model(app,'layer_points')
    echograms = get_model(app,'echograms')
    crossovers = get_model(app, 'crossovers')
    landmarks = get_model(app,'landmarks')
    layer_links = get_model(app,'layer_links')
    
    return models(locations,seasons,radars,point_paths,segments,frames,layers,layer_groups,layer_points,echograms,crossovers,landmarks,layer_links)

def crossovers(models,path_id,loc_id):
    
    # SET THE SEARCH OFFSET
    search_offset = 50
    
    # FIND CROSSOVERS (NON SELF-INSERSECTING)
    try:
        
        # GET LINE PATH
        line_pathz = models.segments.objects.filter(segment_id=path_id).values_list('line_path', flat=True)
        
        #line path w/out z values
        line_path = line_pathz.extra(select={'line_path':'ST_Force_2D(line_path)'}).values_list('line_path',flat=True)
        
        #Get all other line paths with z values.
        other_linesz = models.segments.objects.exclude(segment_id=path_id).filter(line_path__intersects=line_path[0])
        
        #Get all other line paths w/out z values
        other_lines = other_linesz.extra(select={'line_path':'ST_Force_2D(line_path)'}).values_list('line_path','segment_id')
      
        #Create a GEOS Well Known Binary reader and set up variables                            
        wkb_r = WKBReader()
        points1 = []
        line_ids = []
      
        #Find points of intersection w/ interpolated z values for given line
        # path
        for line in other_lines:
            l = wkb_r.read(line[0])
            crosses = l.intersection(line_pathz[0])
            if crosses.geom_type == 'MultiPoint':
                for pt in crosses:
                    points1.append(pt)
                    line_ids.append(line[1])
            else:
                points1.append(crosses)
                line_ids.append(line[1])
   
        #Find points of intersection w/ interpolated z values for other line
        #  paths
        points2 = other_linesz.intersection(line_path[0]).values_list('intersection',flat=True)
      
        #EXTRACT x/y coordinates of intersections and gps_time1/2
        x=[]
        y=[]
        gps_time1 = []
        gps_time2 = []
        #Check all point objects for multiple crossovers and extract x/y coords
        # and gps times
        for po in points1:
            if po.geom_type == 'MultiPoint':
                for p in po:
                    x.append(p[0])
                    y.append(p[1])
                    gps_time1.append(p[2])
            else:
                x.append(po[0])
                y.append(po[1])
                gps_time1.append(po[2])
        for po in points2:
            if po.geom_type == 'MultiPoint':
                for p in po:
                    gps_time2.append(p[2])
            else:
                gps_time2.append(po[2])
      
        #Create point objects for all crossover points
        cross_pts = [Point(point) for point in zip(x,y)]
      
    except:
        return error_check(sys)
   
    #Find all non-self-intersecting Crossover angles:
    try:
        #Get the lines associated w/ crossover points
        lines = models.segments.objects.filter(segment_id__in=list(set(line_ids))).values_list('line_path','segment_id')
        line_dict = {}
        for line in lines:
            line_dict[line[1]] = line[0]
   
        #Enumerate over line_ids in order to query for the nearest point paths to each cross point.
        angles = []
        for idx,pt_id in enumerate(line_ids):
            try:
                #Get the nearest point paths for the other line to the crossover
                # point and sort them by point_path_id
                line_pts = models.point_paths.objects.filter(segment_id=pt_id, gps_time__range=(repr(gps_time2[idx]-search_offset),repr(gps_time2[idx]+search_offset))).distance(cross_pts[idx]).order_by('distance','gps_time').values_list('point_path','point_path_id','gps_time', 'distance')
                line_pts = sorted(line_pts,key=lambda l_id: l_id[1])
                #Find the two points adjacent to the cross point. Use time_diff to ensure they are
                # the closest two points.

                time_diff = None
                for pt_idx in range(len(line_pts) - 1):
                    if float(line_pts[pt_idx][2]) <  gps_time2[idx] and float(line_pts[pt_idx+1][2]) > gps_time2[idx]:
                        if time_diff is None:
                            time_diff = float(line_pts[pt_idx+1][2])-float(line_pts[pt_idx][2])
                            change_x1 = line_pts[pt_idx][0].coords[0]-line_pts[pt_idx+1][0].coords[0]
                            change_y1 = line_pts[pt_idx][0].coords[1]-line_pts[pt_idx+1][0].coords[1]
                        elif float(line_pts[pt_idx+1][2])-float(line_pts[pt_idx][2]) < time_diff:
                            time_diff = float(line_pts[pt_idx+1][2])-float(line_pts[pt_idx][2])
                            change_x1 = line_pts[pt_idx][0].coords[0]-line_pts[pt_idx+1][0].coords[0]
                            change_y1 = line_pts[pt_idx][0].coords[1]-line_pts[pt_idx+1][0].coords[1]

                #Get the nearest point paths for the given line to the crossover
                # point and sort them by point_path_id.
                line_pts = models.point_paths.objects.filter(segment_id=path_id, gps_time__range=(repr(gps_time1[idx]-search_offset),repr(gps_time1[idx]+search_offset))).distance(cross_pts[idx]).order_by('distance','gps_time').values_list('point_path','point_path_id','gps_time','distance')
                line_pts = sorted(line_pts,key=lambda l_id: l_id[1])
                time_diff = None
                for pt_idx in range(len(line_pts) - 1):
                    if float(line_pts[pt_idx][2]) <  gps_time1[idx] and float(line_pts[pt_idx+1][2]) > gps_time1[idx]:
                        if time_diff is None:
                            time_diff = float(line_pts[pt_idx+1][2])-float(line_pts[pt_idx][2])
                            change_x2 = line_pts[pt_idx][0].coords[0]-line_pts[pt_idx+1][0].coords[0]
                            change_y2 = line_pts[pt_idx][0].coords[1]-line_pts[pt_idx+1][0].coords[1]
                        elif float(line_pts[pt_idx+1][2])-float(line_pts[pt_idx][2]) < time_diff:
                            time_diff = float(line_pts[pt_idx+1][2])-float(line_pts[pt_idx][2])
                            change_x2 = line_pts[pt_idx][0].coords[0]-line_pts[pt_idx+1][0].coords[0]
                            change_y2 = line_pts[pt_idx][0].coords[1]-line_pts[pt_idx+1][0].coords[1]  
             
            except:
                return error_check(sys)  
          
            #Check if either of the lines is parallel to the y-axis and find
            # the angle of intersection.
            if change_x1 == 0 and change_x2 == 0:
                angle = 180
            elif change_x1 == 0:
                angle = degrees(atan(fabs(1/(change_y2/change_x2))))
            elif change_x2 == 0:
                angle = degrees(atan(fabs(1/(change_y1/change_x1))))
            else:
                slope1 = change_y1/change_x1
                slope2 = change_y2/change_x2
                if slope1*slope2 == -1:
                    angle = 90
                else:
                    angle = degrees(atan(fabs((slope1 - slope2)/(1 + slope1 * slope2))))
          
            #Save all the angles for later
            angles.append(angle)
    except:
        return error_check(sys)
   
    #FIND all self-intersecting crossovers
    try:
        #Fetch the given line path from the db as a multilinestring.
        # 'ST_UnaryUnion' results in a multilinestring with the last point of
        # every linestring except the last linestring is a crossover and the
        # first point of every linestring except the first linestring is a
        # crossover.
        line = models.segments.objects.filter(segment_id=path_id).extra(select={'multi_line_path':'ST_UnaryUnion(line_path)'}
                                                ).values_list('multi_line_path', flat=True)
      
        #Create a GEOS MultiLineString from the multilinestring fetched above.
        lines = wkb_r.read(line[0])
        #Check if resulting object is a multilinestring, indicating crossovers.
        if lines.geom_type.encode('ascii', 'ignore') == 'MultiLineString':
            self_cross = True
            #Loop through all linestrings created by ST_UnaryUnion to get crossover
            # points and interpolate GPS times.
            crossover_gps = {}
            crossover_slopes = {}
            for idx in range(len(lines) - 1):  
                #Check if current linestring is composed only of crossovers.
                if len(lines[idx].coords) ==2 and idx != 0:
                    #Fall back on the next linestring not made exclusively of
                    # crossovers in order to get a good GPS time.
                    idx1 = idx-1
                    while idx1 >= 0:
                        if idx1 == 0 or len(lines[idx1].coords) > 2:
                        
                            #Check if next linestring is made only of crossovers
                            # in order to obtain the next linestring w/ good GPS
                            # time.
                            if len(lines[idx+1].coords) == 2 and idx+1 != len(lines)-1:
                                idx2 = idx+2
                                while idx2 < len(lines):
                                    if idx2 == len(lines)-1 or len(lines[idx2].coords) > 2:
                                        point1 = Point(lines[idx1].coords[-2])
                                        point2 = Point(lines[idx2].coords[1])
                                        #Break while loop
                                        break
                                    else:
                                        idx2 += 1
                            else:
                                point1 = Point(lines[idx1].coords[-2])
                                point2 = Point(lines[idx+1].coords[1])
                            #Break while loop
                            break        
                        else:
                            idx1 = idx1 - 1
                #If current linestring is not made exclusively of crossovers, check
                # if next one is.
                elif len(lines[idx+1].coords) == 2 and idx+1 != len(lines)-1:
                    idx2 = idx+2
                    while idx2 < len(lines):
                        if idx2 == len(lines)-1 or len(lines[idx2].coords) > 2:
                            point1 = Point(lines[idx].coords[-2])
                            point2 = Point(lines[idx2].coords[1])
                            #break loop
                            break
                        else:
                            idx2 += 1
                else:
                    point1 = Point(lines[idx].coords[-2])
                    point2 = Point(lines[idx+1].coords[1])
               
                #Find the change in x/y in order to determine slope
                change_x = point1[0] - point2[0]
                change_y = point1[1] - point2[1]
              
                #Check if the change in x is zero
                if change_x == 0:
                    slope = None
                else:
                    slope = change_y/change_x
              
                #Create a new line object from the two points adjacent to the
                # crossover.
                newline = LineString(point1,point2)
                #Find the crossover point/interpolate the gps time.
                crossover = Point(lines[idx].coords[-1])
                cross_pt = newline.interpolate(newline.project(crossover))
              
                #Use crossover coordinates as keys for a dictionary storing gps
                # times
                if (crossover[0],crossover[1]) not in crossover_gps.keys():
                    crossover_gps[crossover[0],crossover[1]] = [cross_pt[2]]
                else:
                    crossover_gps[crossover[0],crossover[1]].append(cross_pt[2])
              
                #Use crossover coordinates as keys for a dictionary storing slopes
                if (crossover[0],crossover[1]) not in crossover_slopes.keys():
                    crossover_slopes[crossover[0], crossover[1]] = [slope]
                else:
                    crossover_slopes[crossover[0], crossover[1]].append(slope)
              
            #Create a dictionary holding both gps times and slopes.
            crossovers = crossover_gps
            for key in crossover_slopes:
                crossovers[key].append(crossover_slopes[key][0])
                crossovers[key].append(crossover_slopes[key][1])
            del crossover_gps, crossover_slopes
          
            #Extract self-intersecting crossovers information from above.
            self_cross_pts = []
            self_gps1 = []
            self_gps2 = []
            self_angles = []
            for x,y in crossovers:
                self_cross_pts.append(Point(x,y))
                self_gps1.append(crossovers[x,y][0])
                self_gps2.append(crossovers[x,y][1])
                #Determine angle of intersection
                slope1 = crossovers[x,y][2]
                slope2 = crossovers[x,y][3]
                if slope1 == None and slope2 == None:
                    angle = 180
                elif slope1 == None:
                    angle = degrees(atan(fabs(1/slope2)))
                elif slope2 == None:
                    angle = degrees(atan(fabs(1/slope1)))
                else:
                    if slope1*slope2 == -1:
                        angle = 90
                    else:
                        angle = degrees(atan(fabs((slope1 - slope2)/
                                                      (1 + slope1 * slope2))))
                self_angles.append(angle)
        else:
            self_cross = False
    except:
        return error_check(sys)
   
    
    #Format and return crossovers for writing to CSV file:
    try:
        rows = []
        #Non-self-intersecting crossovers
        for idx, pt in enumerate(cross_pts):
            rows.append([path_id,line_ids[idx],repr(gps_time1[idx]), repr(gps_time2[idx]), repr(angles[idx]), repr(pt[0]), repr(pt[1]), loc_id])
        
        if self_cross:
            #Self-intersecting crossovers
            for idx, pt in enumerate(self_cross_pts):
                rows.append([path_id,path_id,repr(self_gps1[idx]),repr(self_gps2[idx]),repr(self_angles[idx]),repr(pt[0]),repr(pt[1]),loc_id])
       
        return rows

    except:
        return error_check(sys)
