from django.db import connection,transaction,DatabaseError
from django.db.models import Q
from django.contrib.gis.geos import GEOSGeometry,Point,fromstr
from django.views.decorators.csrf import csrf_exempt
from utility import ip_authorization
import os,datetime,sys,line_profiler,utility,json,ujson,numpy,csv,simplekml
from math import fabs
from decimal import Decimal
from scipy import interpolate
from collections import defaultdict
# =============================================================
# INSERT FUNCTIONS (PATH,LAYER,LAYER_POINTS)
# ==============================================================

@ip_authorization()
@csrf_exempt
def create_path(request):

    # GET THE JSON FROM THE SERVER REQUEST
    status,response1,response2 = utility.get_data(request)
    if not status: return response1

    # LOAD THE MODELS FOR THE SPECIFIED APP
    models = utility.get_app_models(response1)

    # DECODE THE ujson OBJECT
    try:
        data = ujson.loads(response2)
    except:
        return utility.error_check(sys)    

    # PARSE THE ujson STRUCTURE
    try:
        path = data['geometry']
        season = data['properties']['season']
        region = data['properties']['location']
        radar = data['properties']['radar']
        c_segment_name = data['properties']['segment']
        segment_start_gps = repr(data['properties']['segment_start_gps_time'])
        segment_stop_gps = repr(data['properties']['segment_stop_gps_time'])
        c_roll = data['properties']['roll']
        c_pitch = data['properties']['pitch']
        c_heading = data['properties']['heading']
        echogram_urls = data['properties']['echo_img_url']
        frame_count = data['properties']['frame_count']
        frame_start_gps = data['properties']['frame_start_gps_time']
        frame_stop_gps = data['properties']['frame_stop_gps_time']
        elev = data['properties']['elev']

        # MAKE SURE SINGLE ELEMENTS ARE LISTS AND FLOATS ARE STRINGS
        if not isinstance(echogram_urls,list):
            echogram_urls = [echogram_urls]
        if not isinstance(frame_start_gps,list):
            frame_start_gps = [repr(frame_start_gps)]
        else:
            frame_start_gps = [repr(i) for i in frame_start_gps]
        if not isinstance(frame_stop_gps,list):
            frame_stop_gps = [repr(frame_stop_gps)]
        else:
            frame_stop_gps = [repr(i) for i in frame_stop_gps]
        if not isinstance(elev, list):
            elev = [elev]

    except:
        return utility.error_check(sys)

    # CREATE THE SEGMENT LINE PATH
    try:

        # GET/CREATE LOCATION
        c_location,_ = models.locations.objects.get_or_create(location_name=region.lower())              

        # GET/CREATE SEASON
        c_season,_ = models.seasons.objects.get_or_create(season_name=season,location_id=c_location.pk,status='private')        

        # GET/CREATE RADAR
        c_radar,_ = models.radars.objects.get_or_create(radar_name=radar.lower())

        # CREATE A GEOS GEOMETRY FROM THE ujson PATH
        geom = GEOSGeometry(ujson.dumps(path))  

        # GET/CREATE SEGMENT
        c_segment,_ = models.segments.objects.get_or_create(season_id=c_season.pk,radar_id=c_radar.pk,segment_name=c_segment_name,start_gps_time=segment_start_gps,stop_gps_time=segment_stop_gps,line_path=geom,location_id=c_location.pk)

        # ITERATE THROUGH FRAMES
        for frm_id in range(int(frame_count)):

            # CREATE THE FRAME STRING
            frm_name = c_segment_name+("_%03d"%(frm_id+1))

            # GET/CREATE FRAMES
            c_frame,_ = models.frames.objects.get_or_create(segment_id=c_segment.pk,frame_name=frm_name,start_gps_time=frame_start_gps[frm_id],stop_gps_time=frame_stop_gps[frm_id],location_id=c_location.pk)

            # GET/CREATE ECHOGRAMS
            _,_ = models.echograms.objects.get_or_create(frame_id=c_frame.pk,echogram_url=echogram_urls[frm_id])

        # CREATE THE SEGMENT POINT PATH
        if not models.point_paths.objects.filter(segment_id=c_segment.pk,location_id=c_location.pk):

            # BREAK DOWN THE GEOS GEOM FOR WRITING TO A TMP FILE
            rows = []
            for idx, pts in enumerate(geom):
                rows.append([c_segment.pk, c_season.pk, repr(pts[2]), repr(c_heading[idx]), repr(c_roll[idx]), repr(c_pitch[idx]), repr(pts[0]), repr(pts[1]), c_location.pk, repr(elev[idx])])

            # CREATE TMP FILENAME STRING
            fn = os.tmpnam() + 'pointpaths.csv'

            # CREATE A TMP CSV AND WRITE ALL THE GEOM ROWS
            numpy.savetxt(fn,rows,delimiter=',',fmt="%s")

            # INSERT THE TMP CSV DATA INTO THE POINT PATHS TABLE (VIA A TMP TABLE)
            cursor = connection.cursor()
            try:
                cursor.execute('CREATE TEMP TABLE pt_paths(segment_id integer,season_id integer,gps_time numeric,heading numeric,roll numeric,pitch numeric,lon numeric,lat numeric,location_id integer,elev numeric);')
                cursor.execute("COPY pt_paths (segment_id,season_id,gps_time,heading,roll,pitch,lon,lat,location_id,elev) FROM '" + fn + "' DELIMITER ',';")
                cursor.execute("INSERT INTO "+response1+"_point_paths (segment_id, season_id, gps_time, heading, roll, pitch, point_path, location_id) SELECT segment_id, season_id, gps_time, heading, roll, pitch, ST_GeomFromText('POINTZ('||lon||' '||lat||' '||elev||')',4326), location_id FROM pt_paths;")
            finally:
                cursor.close()
            # DELETE THE TMP CSV
            try:
                os.remove(fn)
            except:
                return utility.response(0, 'ERROR REMOVING TMP POINT PATHS CSV')

            # FIND ALL CROSSOVER POINTS
            crossovers = utility.crossovers(models,c_segment.pk,c_location.pk)

            # CHECK CROSSOVERS FOR SUCESS > INSERT CROSSOVERS
            if type(crossovers) is not list:
                return crossovers
            else:

                # CREATE TMP FILENAME STRING
                fn = os.tmpnam() + 'crossovers.csv'

                # CREATE A TMP CSV AND WRITE ALL THE CROSSOVERS ROWS
                numpy.savetxt(fn, crossovers, delimiter = ',',fmt="%s")

                # INSERT THE TMP CSV DATA INTO THE CROSSOVERS TABLE (VIA A TMP TABLE)
                cursor = connection.cursor()
                try:
                    cursor.execute('CREATE TEMP TABLE cross_pts (segment_1_id integer,segment_2_id integer, gps_time_1 numeric, gps_time_2 numeric, cross_angle numeric, lon numeric, lat numeric, location_id integer);')
                    cursor.execute("COPY cross_pts (segment_1_id,segment_2_id, gps_time_1,gps_time_2, cross_angle,lon,lat, location_id) FROM '" + fn + "' DELIMITER ',';")
                    cursor.execute("INSERT INTO "+response1+"_crossovers (segment_1_id,segment_2_id, gps_time_1,gps_time_2,cross_angle,cross_point,location_id) SELECT segment_1_id,segment_2_id, gps_time_1,gps_time_2,cross_angle,ST_GeomFromText('POINT('||lon||' '||lat||')',4326),location_id FROM cross_pts;")
                finally: 
                    cursor.close()
               
                # DELETE THE TMP CSV
                try:
                    os.remove(fn)
                except:
                    return utility.response(0, "ERROR REMOVING TMP CROSSOVERS CSV")

        # RETURN success utility.response   
        return utility.response(1,'SUCCESS: SEGMENT PATH INSERTION COMPLETED.')

    except:
        # RETURN failure utility.response
        return utility.error_check(sys)

@ip_authorization()
@csrf_exempt    
def create_layer(request):

    # GET THE JSON FROM THE SERVER REQUEST
    status,response1,response2 = utility.get_data(request)
    if not status: return response1

    # LOAD THE MODELS FOR THE SPECIFIED APP
    models = utility.get_app_models(response1)

    # DECODE THE JSON OBJECT
    try:
        data = ujson.loads(response2)
    except:
        return utility.error_check(sys)

    # PARSE THE ujson STRUCTURE
    try:
        c_layer_name = data['properties']['lyr_name']
        c_group_name = data['properties']['lyr_group_name']
        c_description = data['properties']['lyr_description']
    except:
        return utility.error_check(sys)

    try: 
        
        # GET/CREATE THE LAYER GROUP
        c_group,_ = models.layer_groups.objects.get_or_create(group_name=c_group_name)
        
        # GET/CREATE THE LAYER
        c_layer,created = models.layers.objects.get_or_create(layer_name=c_layer_name,layer_group_id=c_group.pk)
        
        # IF THE LAYER WAS NOT CREATED UPDATE IT'S STATUS AND RETURN
        if not created:
            c_layer.status ='normal'
            c_layer.save()
            
            # RETURN A RESPONSE TO THE CLIENT
            return utility.response(1,ujson.dumps({'lyr_id':c_layer.pk,'lyr_group_id':c_group.pk}))
        else:
            
            # UPDATE THE STATUS AND DESCRIPTION
            update_count = models.layers.objects.filter(layer_name=c_layer_name,layer_group_id=c_group.pk).update(description=c_description,status='normal')
            c_layer = models.layers.objects.filter(layer_name=c_layer_name,layer_group_id=c_group.pk).values_list('pk',flat=True)
            
            # RETURN A RESPONSE TO THE CLIENT
            return utility.response(1,ujson.dumps({'lyr_id':c_layer[0],'lyr_group_id':c_group.pk}))
    
    except:
        return utility.error_check(sys)     

@ip_authorization()
@csrf_exempt
def delete_layer(request):

    # GET THE JSON FROM THE SERVER REQUEST
    status,response1,response2 = utility.get_data(request)
    if not status: return response1

    # LOAD THE MODELS FOR THE SPECIFIED APP
    models = utility.get_app_models(response1)

    # DECODE THE JSON OBJECT
    try:
        data = ujson.loads(response2)
    except:
        return utility.error_check(sys)

    # PARSE THE JSON STRUCTURE
    try:
        c_layer_name = data['properties']['lyr_name']
    except:
        return utility.error_check(sys)

    # SET THE LAYER STATUS TO DELETED (DONT ACTUALLY DELETE LAYER)
    try: 

        c_layer = models.layers.objects.get(layer_name=c_layer_name)
        c_layer.status = 'deleted'
        c_layer.save(update_fields=['status'])

        # RETURN A RESPONSE TO THE CLIENT
        return utility.response(1,ujson.dumps({'lyr_id':c_layer.pk}))

    except:
        return utility.error_check(sys)     

@ip_authorization()
@csrf_exempt
def create_layer_points(request):

    # GET THE ujson FROM THE SERVER REQUEST
    status,response1,response2 = utility.get_data(request)
    if not status: return response1

    # LOAD THE MODELS FOR THE SPECIFIED APP
    models = utility.get_app_models(response1)

    # DECODE THE json OBJECT
    try:
        data = json.loads(response2,parse_float=Decimal)
    except:
        return utility.error_check(sys)

    # PARSE THE ujson STRUCTURE
    try:
        path = data['geometry']
        user = data['properties']['username']
        region = data['properties']['location']
        c_segment_name = data['properties']['segment']
        all_gps_time = data['properties']['gps_time']
        all_twtt = data['properties']['twtt']
        all_pick_type = data['properties']['type']
        all_pick_quality = data['properties']['quality']
        lyr_type = data['properties']['lyr_name']
        c_layer_group_name = data['properties']['lyr_group_name']

    except:
        return utility.error_check(sys)

    try:

        # GET/CREATE LOCATION, LAYER, AND LAYER GROUP
        c_location,_ = models.locations.objects.get_or_create(location_name=region)
        c_group,_ = models.layer_groups.objects.get_or_create(group_name=c_layer_group_name)
        c_layer,_ = models.layers.objects.get_or_create(layer_name=lyr_type,layer_group_id=c_group.pk) 

        # GET SEGMENT
        c_segment = models.segments.objects.filter(segment_name=c_segment_name,location_id=c_location.pk).values_list('segment_id','season_id')[0]

        # CREATE GEOS GEOMETRY
        geom = GEOSGeometry(ujson.dumps(path))

        if geom.geom_type.encode('ascii','ignore') == 'Point':

            # TREAT GEOMETRY AS A POINT
            pt = geom.wkb
            
            # CREATE THE VALUES STRING FOR INSERT
            values_str = "VALUES(%s,%s,%s,%s,%s,%s,%s,ST_SetSRID(ST_GeomFromWKB(%s),4326),%s,%s,%s);" 

        else:

            # TREAT GEOMETRY AS A LINESTRING (POINT ARRAY)
            pt = []
            for pts in geom:
                pt.append(Point(pts).wkb)

            # CREATE THE VALUES STRING FOR INSERT
            values_str = "VALUES (%s,%s,%s,unnest(%s),unnest(%s),unnest(%s),unnest(%s),ST_SetSRID(ST_GeomFromWKB(unnest(%s)),4326),%s,%s,%s);" 


        # CONSTRUCT QUERY
        insert_query = "INSERT INTO " + response1 + "_layer_points (layer_id,season_id,segment_id,gps_time,twtt,pick_type,quality,layer_point,username,location_id,last_updated) " + values_str

        # EXECUTE QUERY
        cursor = connection.cursor()
        cursor.execute(insert_query, (c_layer.pk,c_segment[1],c_segment[0],all_gps_time,all_twtt,all_pick_type,all_pick_quality,pt,user,c_location.pk,datetime.datetime.now()))

        # RETURN A RESPONSE TO THE SERVER  
        return utility.response(1,'SUCCESS: LAYER_POINTS INSERTION COMPLETED.')

    except:
        return utility.error_check(sys)

@ip_authorization()
@csrf_exempt
def delete_layer_points(request):

    # GET THE JSON FROM THE SERVER REQUEST
    status,response1,response2 = utility.get_data(request)
    if not status: 
        return response1

    # LOAD THE MODELS FOR THE SPECIFIED APP
    models = utility.get_app_models(response1)

    # DECODE THE JSON OBJECT
    try:
        data = json.loads(response2,parse_float=Decimal)
    except:
        return utility.error_check(sys)    

    # PARSE THE JSON STRUCTURE
    try:

        region = data['properties']['location']
        start_gps = data['properties']['start_gps_time']
        stop_gps = data['properties']['stop_gps_time']
        max_twtt = data['properties']['max_twtt']
        min_twtt = data['properties']['min_twtt']
        lyr_type = data['properties']['lyr_name']
        c_segment_name = data['properties']['segment']

    except:
        return utility.error_check(sys)

    try:
        # MAKE SURE THE LIMITS ARE INCLUDED IN THE DELETION
        start_gps = start_gps.next_minus()
        stop_gps = stop_gps.next_plus()
        max_twtt = max_twtt.quantize(Decimal(10) ** -10).next_plus() 
        min_twtt = min_twtt.quantize(Decimal(10) ** -10).next_minus()
        
        # GET LAYER AND SEGMENT
        c_layer = models.layers.objects.filter(layer_name=lyr_type).only('layer_id')[0]
        c_segment = models.segments.objects.filter(segment_name=c_segment_name,location_id__location_name=region).values_list('segment_id','season_id')[0]

        # GET LAYER POINTS
        c_layer_points = models.layer_points.objects.filter(location_id__location_name=region,season_id=c_segment[1],segment_id=c_segment[0],
                                                            layer_id=c_layer.pk,gps_time__gte=start_gps,gps_time__lte=stop_gps,twtt__gte=min_twtt,twtt__lte=max_twtt)

        # MAKE SURE THERE ARE POINTS IN THE QUERY
        if len(c_layer_points)==0:
            return utility.response(2,'NO LAYER POINTS WERE REMOVED. (NO POINTS MATCHED THE REQUEST)')

        # DELETE LAYER POINTS
        c_layer_points.delete()
        
        # RETURN A RESPONSE TO THE SERVER
        return utility.response(1,'SUCCESS: LAYER_POINTS REMOVAL COMPLETED.')

    except:
        return utility.error_check(sys)

@ip_authorization()
@csrf_exempt
def bulk_delete(request):
    
    # RETRIEVE JSON from POST
    status,response1,response2 = utility.get_data(request)
    if not status: return response1

    # GET the models
    models = utility.get_app_models(response1)

    # LOAD JSON object
    try:
        data = ujson.loads(response2)
    except:
        return utility.error_check(sys)

    # COLLECT JSON elements
    try:
        type = data['properties']['type']
        
        season = data['properties']['season']

        #If there are specific segments, get them
        try: 
            segments = data['properties']['segments']
            if not isinstance(segments,list):
                segments = [segments]
        except:
            segments = []
        
    except:
        return utility.error_check(sys)
        
    #BEGIN DELETION PROCESS
    try:
        if type == 'full':
            #Delete everything w/ relationships to the segments table. 
            models.segments.objects.filter(season_id__season_name=season,segment_name__in=segments).delete()
            
            #If there are no segments remaining in the given season, remove it from the database. 
            segment_ids = models.segments.objects.filter(season_id__season_name=season).values_list('segment_id',flat=True)
            if not segment_ids:
                models.seasons.objects.filter(season_name=season).delete()
        elif type == 'layer':
            #Delete only from the layer_points table.
            models.layer_points.objects.filter(season_id__season_name=season,segment_id__segment_name__in=segments).delete()
        else: 
            return utility.response(0,'Unsupported Type! Choices are ''full'' or ''layer.''')
        
        return utility.response(1,'Deletion Complete.')
        
    except:
        return utility.error_check(sys)
    
# ==============================================================
# OUTPUT FUNCTIONS (PATH,LAYER,LAYER_POINTS,FRAMES,SYSTEMS,ETC)
# ==============================================================

@csrf_exempt  
def get_path(request):

    # GET THE JSON FROM THE SERVER REQUEST
    status,response1,response2 = utility.get_data(request)
    if not status: return response1

    # LOAD THE MODELS FOR THE SPECIFIED APP
    models = utility.get_app_models(response1)

    # DECODE THE JSON OBJECT
    try:
        data = json.loads(response2,parse_float=Decimal)
    except:
        return utility.error_check(sys)

    # PARSE THE JSON STRUCTURE
    try:
        region = data['properties']['location']
        season = data['properties']['season']
        start_gps = data['properties']['start_gps_time']
        stop_gps = data['properties']['stop_gps_time']

    except:
        return utility.error_check(sys)

    try: 

        # GET EPSG CODE
        proj = utility.proj_from_region(region)

        # GET POINTS
        c_points = models.point_paths.objects.filter(season_id__season_name=season, location_id__location_name=region, gps_time__gte=start_gps, gps_time__lte=stop_gps).transform(proj).order_by('gps_time').values_list('gps_time','point_path')

        # UNZIP POINT DATA
        gps_time,point_paths = zip(*c_points)
        x_coord,y_coord,_ = zip(*point_paths)

        # RETURN RESPONSE TO THE CLIENT
        return utility.response(1,ujson.dumps({'gps_time':gps_time,'X':x_coord,'Y':y_coord}))

    except:
        return utility.error_check(sys)   

@csrf_exempt
def get_closest_point(request):

    # GET THE JSON FROM THE SERVER REQUEST
    status,response1,response2 = utility.get_data(request)
    if not status: return response1

    # LOAD THE MODELS FOR THE SPECIFIED APP
    models = utility.get_app_models(response1)

    # DECODE THE JSON OBJECT
    try:
        data = json.loads(response2,parse_float=Decimal)
    except:
        return utility.error_check(sys)

    # PARSE THE JSON STRUCTURE
    try:
        region = data['properties']['location']
        start_gps = data['properties']['start_gps_time']
        stop_gps = data['properties']['stop_gps_time']
        x = data['properties']['x']
        y = data['properties']['y']

        # MAKE SURE SINGLE ELEMENTS ARE LISTS AND FLOATS ARE STRINGS
        if not isinstance(start_gps,list):
            start_gps = [start_gps]
        if not isinstance(stop_gps,list):
            stop_gps = [stop_gps]

    except:
        return utility.error_check(sys)

    try: 

        # GET EPSG CODE
        proj = utility.proj_from_region(region)

        # CREATE GEOS GEOMETRY
        point = GEOSGeometry('POINT('+repr(x)+' '+repr(y)+')',srid=proj)

        point_ids = [];

        for start,stop in zip(start_gps, stop_gps):
            
            # GET POINT PATH ID
            c_point_paths = models.point_paths.objects.filter(gps_time__range=(start,stop),location_id__location_name=region).values_list('pk',flat=True)
            [point_ids.append(pt_id) for pt_id in c_point_paths]

        # GET THE CLOSEST POINT PATH ID
        c_point = models.point_paths.objects.filter(pk__in=point_ids,location_id__location_name=region).transform(proj).distance(point).order_by('distance').values_list('point_path', 'gps_time','distance')[0]

        # RETURN RESPONSE TO CLIENT
        return utility.response(1,ujson.dumps({'X':c_point[0].coords[0],'Y': c_point[0].coords[1],'gps_time':c_point[1]}))

    except:
        return utility.error_check(sys)

@csrf_exempt
def get_closest_frame(request):

    # GET THE JSON FROM THE SERVER REQUEST
    status,response1,response2 = utility.get_data(request)
    if not status: return response1

    # LOAD THE MODELS FOR THE SPECIFIED APP
    models = utility.get_app_models(response1)

    # DECODE THE JSON OBJECT
    try:
        data = ujson.loads(response2)
    except:
        return utility.error_check(sys)

    # PARSE THE JSON STRUCTURE
    try:
        region = data['properties']['location']
        c_seasons = data['properties']['season']
        x = data['properties']['x']
        y = data['properties']['y']

        # GET THE START AND STOP SEGMENT IF THEY EXIST
        try:
            startseg = data['properties']['startseg']
            stopseg = data['properties']['stopseg']
        except:
            startseg = '00000000_00'
            stopseg = '99999999_99'
            
        try:
            c_status = data['properties']['status']
        except:
            c_status = ['public']
        
        # MAKE SURE SINGLE ELEMENTS ARE LISTS AND FLOATS ARE STRINGS
        if not isinstance(c_seasons,list):
            c_seasons = [c_seasons]

    except:
        return utility.error_check(sys)

    try: 

        # CREATE THE GEOS GEOMETRY
        proj = utility.proj_from_region(region)
        point = GEOSGeometry('POINT('+repr(x)+' '+repr(y)+')', srid=proj)

        try:
            if not c_seasons[0]:
                
                # GET SEGMENT (ALL SEASONS)
                c_segment = models.segments.objects.filter(location_id__location_name=region,segment_name__range=(startseg,stopseg)).transform(proj).distance(point).order_by('distance').values_list('segment_id','season_id','distance')[0]
            
            else:
    
                # GET SEGMENT (SPECIFIED SEASONS)
                c_segment = models.segments.objects.filter(location_id__location_name=region,season_id__season_name__in=c_seasons,segment_name__range=(startseg,stopseg)).transform(proj).distance(point).order_by('distance').values_list('segment_id','season_id','distance')[0]
        except:
            return utility.response(0,'NO FRAME MATCHES YOUR SELECTION.')
        
        # GET THE SEASON
        c_season = models.seasons.objects.filter(season_id=c_segment[1],status__in=c_status).values_list('season_name',flat=True)[0]

        # GET THE CLOSEST POINT
        c_point = models.point_paths.objects.filter(segment_id=c_segment[0]).transform(proj).distance(point).order_by('distance').values_list('gps_time','distance')[0]

		# GET THE FRAME (BASED ON THE CLOSEST POINT)
        c_frame = models.frames.objects.filter(segment_id=c_segment[0],start_gps_time__lte=c_point[0],stop_gps_time__gte=c_point[0]).values_list('frame_name','start_gps_time','stop_gps_time','frame_id')[0]
        
        # GET THE ECHOGRAM (BASED ON THE FRAME)
        c_echogram = models.echograms.objects.filter(frame_id=c_frame[3]).values_list('echogram_url',flat=True)[0]

        # GET THE FRAME POINTS
        c_points = models.point_paths.objects.filter(segment_id=c_segment[0],gps_time__range=(c_frame[1],c_frame[2])).transform(proj).values_list('point_path','gps_time')

        # UNZIP THE FRAME POINTS AND GPS_TIME
        c_points = [(i[0].x,i[0].y,float(i[1])) for i in c_points]
        x_coord,y_coord,gps_time = zip(*c_points)
		
        # RETURN RESPONSE TO THE CLIENT
        return utility.response(1, ujson.dumps({'season':c_season,'segment_id':c_segment[0],'start_gps_time':c_frame[1],'stop_gps_time':c_frame[2],'frame': c_frame[0],'echogram_url': c_echogram,'X':x_coord,'Y':y_coord,'gps_time':gps_time}))

    except:
        return utility.error_check(sys)

@csrf_exempt
def get_layers(request):

    # GET THE JSON FROM THE SERVER REQUEST
    status,response1,_ = utility.get_data(request)
    if not status: return response1

    # LOAD THE MODELS FOR THE SPECIFIED APP
    models = utility.get_app_models(response1)

    try: 

        # GET LAYERS
        c_layers = models.layers.objects.filter(status='normal').order_by('layer_id').values_list('layer_id','layer_name')

        # UNZIP LAYERS
        layers = zip(*c_layers)

        # RETURN RESPONSE TO CLIENT
        return utility.response(1,ujson.dumps(dict(lyr_id=list(layers[0]),lyr_name=list(layers[1]))))

    except:
        return utility.error_check(sys)  

@csrf_exempt    
def get_layer_points(request):
    
    # GET THE JSON FROM THE SERVER REQUEST
    status,response1,response2 = utility.get_data(request)
    if not status: return response1
    
    # LOAD THE MODELS FOR THE SPECIFIED APP
    models = utility.get_app_models(response1)
    
    # DECODE THE JSON OBJECT
    try:
        data = json.loads(response2,parse_float=Decimal)
    except:
        return utility.error_check(sys)
    
    # PARSE THE JSON STRUCTURE
    try:
        region = data['properties']['location']
        season = data['properties']['season']
        geom_type = data['properties']['return_geom']
    
        try:
            name_seg = False
            seg_id = data['properties']['segment_id']
        except:
            name_seg = True
            seg_name = data['properties']['segment']
        
        try:
            full_gps = False
            start_gps = data['properties']['start_gps_time']
            stop_gps = data['properties']['stop_gps_time']
        except:
            full_gps = True
        
        lyr_type = data['properties']['lyr_name']
        if not isinstance(lyr_type,list):
            lyr_type = [lyr_type]
    
    except:
        return utility.error_check(sys)
    
    try:
    
        # GET SEASON AND LOCATION
        c_season = models.seasons.objects.filter(season_name=season).only('season_id')[0]
        c_location = models.locations.objects.filter(location_name=region).only('location_id')[0]
        
        # CONSTUCT QUERY
        if geom_type == 'geog':
            query = "SELECT gps_time,twtt,pick_type,quality,layer_id,ST_X(layer_point),ST_Y(layer_point),ST_Z(layer_point) FROM %s_layer_points " % (response1)
        else:
            query = "SELECT gps_time,twtt,pick_type,quality,layer_id FROM %s_layer_points " % (response1)
        
        query += "WHERE "
        
        if 'all' not in lyr_type:
            c_layer_pks = tuple(models.layers.objects.filter(layer_name__in=lyr_type).values_list('layer_id',flat=True))
            if len(c_layer_pks) == 1:
                query += "layer_id IN (%s) AND " % (c_layer_pks)                
            else:
                query += "layer_id IN %s AND " % (c_layer_pks)
        
        query += "location_id=%s AND season_id=%s " % (c_location.pk,c_season.pk)
        
        if name_seg:
            query += "AND segment_id=(select segment_id from %s_segments where segment_name='%s' and season_id=%s) " % (response1,seg_name,c_season.pk)
        else:
            query += "AND segment_id=%s " % (seg_id)
        
        if not full_gps:
            query += "AND gps_time between %s AND %s " % (start_gps,stop_gps)
        
        query += "ORDER BY gps_time"
        
        # OPEN A DATABASE CURSOR
        cursor = connection.cursor()
        try:
            # EXECUTE THE QUERY
            cursor.execute(query)
        
            # FETCH ALL THE ROWS
            rows = cursor.fetchall()
        finally:
            cursor.close()
        # MAKE SURE THERE IS A RETURN
        if len(rows)==0:
            return utility.response(2,'WARNING: NO LAYER POINTS EXIST FOR THE GIVEN PARAMS.')
        
        # UNZIP LAYER POINTS
        lp = zip(*rows)
        
        # RETURN RESPONSE TO CLIENT
        if geom_type == 'geog':
            return utility.response(1,ujson.dumps({'gps_time':lp[0],'twtt':lp[1],'type':lp[2],'quality':lp[3],'lyr_id':lp[4],'lon':lp[5],'lat':lp[6],'elev':lp[7]}))
        else:
            return utility.response(1,ujson.dumps({'gps_time':lp[0],'twtt':lp[1],'type':lp[2],'quality':lp[3],'lyr_id':lp[4]}))
        
    except:
        return utility.error_check(sys)

@csrf_exempt 
def get_layer_points_csv(request):
    
    # GET THE JSON FROM THE SERVER REQUEST
    status,response1,response2 = utility.get_data(request)
    if not status: return response1

    # LOAD THE MODELS FOR THE SPECIFIED APP
    models = utility.get_app_models(response1)

    # DECODE THE JSON OBJECT
    try:
        data = ujson.loads(response2)
    except:
        return utility.error_check(sys)

    # PARSE THE JSON STRUCTURE
    try:
        bound = data['bound']
        region = data['location']
        
        # GET THE START AND STOP SEGMENT IF THEY EXIST
        try:
            startseg = data['properties']['startseg']
            stopseg = data['properties']['stopseg']
        except:
            startseg = '00000000_00'
            stopseg = '99999999_99'
            
    except:
        return utility.error_check(sys)

    try:
        
        # GET THE LOCATION
        c_location = models.locations.objects.filter(location_name=region).values_list('location_id',flat=True)[0]
        
        # CREATE THE QUERY
        c_layer_pks = tuple(models.layers.objects.filter(layer_name__in=['surface','bottom'],status='normal').values_list('pk',flat=True))
        query = "SELECT DISTINCT ON (lp.gps_time) s.season_name,sg.segment_name,lp.segment_id,lp.layer_id,lp.gps_time,lp.twtt,lp.quality,lp.pick_type,ST_X(lp.layer_point),ST_Y(lp.layer_point),ST_Z(lp.layer_point) FROM %s_layer_points lp INNER JOIN %s_seasons s ON lp.season_id = s.season_id INNER JOIN %s_segments sg ON lp.segment_id = sg.segment_id WHERE s.status = 'public' AND lp.layer_id IN %s AND lp.location_id=%s AND sg.segment_name BETWEEN '%s' AND '%s' AND ST_Within(lp.layer_point,ST_GeomFromText('%s',4326)) ORDER BY lp.gps_time,lp.segment_id" % (response1,response1,response1,c_layer_pks,c_location,startseg,stopseg,bound)

        # OPEN A CURSOR
        cursor = connection.cursor()
        try:
            # EXECUTE THE QUERY
            cursor.execute(query)

            # FETCH THE ROWS
            rows = cursor.fetchall()
        finally: 
            cursor.close()    
        # CONFIRM THERE IS DATA
        if not rows:
            return utility.response(0,'NO DATA FOUND. (NO DATA IN YOUR SEARCH REGION)')
        
        # UNZIP THE DATA 
        data = zip(*rows)
        
        # CONVERT DATA TO A DEFAULTDICT ORDERED BY SEGMENT_ID
        seg_ids = list(data[2])
        
        datapack = defaultdict(list)
        data_list = [data[0],data[1],data[3],data[4],data[5],data[6],data[7],data[8],data[9],data[10]]
        
        for ki, kl in zip(seg_ids, zip(*data_list)):
            datapack[ki] += [kl]
        
        for k, v in datapack.items():
            datapack[k] = map(list, zip(*v))
        
        # FREE UP SOME MEMORY
        del rows,data,data_list
        
        # CREATE LISTS FOR INTERPOLATION OUTPUT (s=surface, b=bottom, t=thickness)
        s_out_twtt = []; s_out_quality = []; s_out_pick_type = []; s_out_m = [];
        b_out_gps = []; b_out_utc = []; b_out_twtt = []; b_out_quality = []; b_out_pick_type = []; b_out_gps = []; b_out_season = []; b_out_segment = []; b_out_lat = []; b_out_lon = []; b_out_elev= []; b_out_m = [];  b_out_utcsod = [];
        t_out_m = [];
        
        # COUNTERS!
        all_count = 0
        bad_count = 0
        
        # FOR EACH SEGMENT IN THE DATAPACK EXTRACT THE VALUES
        for season_name,segment_name,layer_id,gps_time,twtt,quality,pick_type,lon,lat,elev in datapack.itervalues():
        
            all_count +=1
        
            # CREATE EMPTY LISTS
            s_gps = []; s_twtt = []; s_quality = []; s_pick_type = [];
            b_gps = []; b_twtt = []; b_quality = []; b_pick_type = []; b_season =[]; b_segment = []; b_lat = []; b_lon = []; b_elev = [];
        
            # PORTION THE DATA OUT INTO SURFACE AND BOTTOM LISTS
            for pt_idx in range(len(gps_time)):
            
                # EXTRACT SURFACE DATA
                if layer_id[pt_idx] == 1:
            
                    s_gps.append(float(gps_time[pt_idx]))
                    s_twtt.append(float(twtt[pt_idx]))
                    s_quality.append(int(quality[pt_idx]))
                    s_pick_type.append(int(pick_type[pt_idx]))
                    
                # EXTRACT BED DATA
                if layer_id[pt_idx] == 2:
                
                    b_segment.append(segment_name[pt_idx])
                    b_season.append(season_name[pt_idx])
                    b_lat.append(lat[pt_idx])
                    b_lon.append(lon[pt_idx])
                    b_elev.append(elev[pt_idx])
                    b_gps.append(float(gps_time[pt_idx]))
                    b_twtt.append(float(twtt[pt_idx]))
                    b_quality.append(int(quality[pt_idx]))
                    b_pick_type.append(int(pick_type[pt_idx]))
            
            # CHECK FOR NO BED, ADD 1 TO THE BAD COUNT
            if not b_gps:
                bad_count += 1
                break;
            
            # IF THERE IS NO SURFACE THROW AN ERROR (THIS SHOULD NEVER HAPPEN)
            if not s_gps:
                return utility.response(0,'NO SURFACE DATA WAS FOUND. PLEASE REPORT THIS ERROR TO CReSIS')
            
            # INTERPOLATE THE SURFACE TWTT AT THE BOTTOM TIMES
            s_interp_f = interpolate.splrep(s_gps,s_twtt,k=1,s=0)
            s_twtt_new = interpolate.splev(b_gps,s_interp_f,der=0)
            
            # INTERPOLATE THE SURFACE QUALITY AT THE BOTTOM TIMES
            s_interp_f = interpolate.interp1d(s_gps,s_quality,kind='nearest',bounds_error=False,fill_value=0)
            s_quality_new = list(s_interp_f(b_gps))
            
            # INTERPOLATE THE SURFACE PICK TYPE AT THE BOTTOM TIMES
            s_interp_f = interpolate.interp1d(s_gps,s_pick_type,kind='nearest',bounds_error=False,fill_value=2)
            s_pick_type_new = list(s_interp_f(b_gps))
            
            # SAVE TO THE OUTPUT LIST
            s_out_twtt.extend(s_twtt_new); s_out_quality.extend(s_quality_new); s_out_pick_type.extend(s_pick_type_new);
            b_out_quality.extend(b_quality); b_out_pick_type.extend(b_pick_type); 
            b_out_gps.extend(b_gps); b_out_twtt.extend(b_twtt); b_out_season.extend(b_season); b_out_segment.extend(b_segment); b_out_lat.extend(b_lat); b_out_lon.extend(b_lon); b_out_elev.extend(b_elev);
        
        # IF ALL OF THE SEGMENTS ARE BAD (NO BED DATA) RETURN ERROR RESPONSE.
        if bad_count == all_count:
            return utility.response(0,'NO DATA FOUND. (NO DATA IN YOUR SEARCH REGION)')
        
        # DO DATA CONVERSIONS (TWTT>M) & (GPS>UTCSOD
        for pt_idx in range(len(b_out_gps)):
        
            # CONVERT TWTT TO DISTANCE (M) AND CALCULATE THICKNESS
            s_m,b_m = utility.twtt2distm(s_out_twtt[pt_idx],b_out_twtt[pt_idx])
            
            # CORRECT FOR NEGATIVE THICKNESS
            if (b_m-s_m < 0):
                b_m = s_m
            
            # SAVE SURFACE/BED/THICKNESS
            s_out_m.append(s_m)
            b_out_m.append(b_m)
            t_out_m.append(b_m-s_m)
            
            # CONVERT GPS TIME TO UTCSOD
            utc_time = datetime.datetime.utcfromtimestamp(b_out_gps[pt_idx]) - datetime.datetime.strptime(b_out_segment[pt_idx][0:8],'%Y%m%d')
            utc_sod = utc_time.seconds + (utc_time.microseconds/1000000.0)
            b_out_utc.append(utc_sod)
        
        # CLEAR SOME MEMORY
        del season_name,segment_name,layer_id,gps_time,twtt,quality,pick_type,lon,lat,elev,datapack
        del s_twtt,b_twtt,b_gps,s_quality_new,b_quality,b_pick_type,b_season,b_segment,b_lat,b_lon,b_elev,b_out_gps
        
        # CONSTRUCT THE OUTPUT CSV INFORMATION
        server_dir = '/cresis/snfs1/web/ops/data/csv/'
        web_dir = 'data/csv/'
        tmp_fn = 'CReSIS_L2_CSV_GOOD_' + utility.randid(10) + '.csv'
        web_fn = web_dir + tmp_fn
        server_fn  = server_dir + tmp_fn
        
        # WRITE CSV FILE TO SERVER
        header = ['LAT','LON','ELEVATION','UTCSOD','SURFACE','BOTTOM','THICKNESS','SURFACE_TYPE','BOTTOM_TYPE','SURFACE_QUALITY','BOTTOM_QUALITY','SEASON','SEGMENT']
        
        with open(server_fn,'wb') as csvfile:
            csv_writer = csv.writer(csvfile,delimiter=',',quoting=csv.QUOTE_NONE)
            csv_writer.writerow(header)
            for point in range(len(b_out_lat)):
                csv_writer.writerow(["%.8f" % b_out_lat[point],"%.8f" % b_out_lon[point],"%.3f" % b_out_elev[point],"%.3f" % b_out_utc[point],"%.3f" % s_out_m[point],"%.3f" % b_out_m[point],"%.3f" % t_out_m[point],
                                     int(s_out_pick_type[point]),int(b_out_pick_type[point]),int(s_out_quality[point]),int(b_out_quality[point]),b_out_season[point],b_out_segment[point]])

        # RETURN THE CSV URL
        return utility.response(1,web_fn)
    
    except:        
        return utility.error_check(sys)

@csrf_exempt 
def get_layer_points_kml(request):
    
    # GET THE JSON FROM THE SERVER REQUEST
    status,response1,response2 = utility.get_data(request)
    if not status: return response1

    # LOAD THE MODELS FOR THE SPECIFIED APP
    models = utility.get_app_models(response1)

    # DECODE THE JSON OBJECT
    try:
        data = ujson.loads(response2)
    except:
        return utility.error_check(sys)

    # PARSE THE JSON STRUCTURE
    try:
        bound = data['bound']
        region = data['location']
        
        # GET THE START AND STOP SEGMENT IF THEY EXIST
        try:
            startseg = data['properties']['startseg']
            stopseg = data['properties']['stopseg']
        except:
            startseg = '00000000_00'
            stopseg = '99999999_99'
            
    except:
        return utility.error_check(sys)

    try:
        
        # GET LOCATION
        c_location = models.locations.objects.filter(location_name=region).values_list('location_id',flat=True)[0]
        
        # CREATE THE QUERY
        query = "SELECT DISTINCT ON (pp.gps_time) sg.segment_name,pp.segment_id,ST_X(pp.point_path),ST_Y(pp.point_path),ST_Z(pp.point_path),pp.gps_time FROM %s_segments sg INNER JOIN %s_point_paths pp ON sg.segment_id = pp.segment_id INNER JOIN %s_seasons s ON pp.season_id = s.season_id WHERE s.status = 'public' AND pp.location_id=%s AND sg.segment_name BETWEEN '%s' AND '%s' AND ST_Within(pp.point_path,ST_GeomFromText('%s',4326)) ORDER BY pp.gps_time,pp.segment_id" % (response1,response1,response1,c_location,startseg,stopseg,bound)
        
        # OPEN A CURSOR
        cursor = connection.cursor()
        try:
            # EXECUTE THE QUERY
            cursor.execute(query)

            # FETCH THE ROWS
            rows = cursor.fetchall()
        finally:
             cursor.close()   
        # IF ROWS IS EMPTY RETURN NO DATA ERROR
        if not rows:
            return utility.response(0,'NO DATA FOUND. (NO DATA IN YOUR SEARCH REGION)')
    
        # UNZIP THE DATA
        data = zip(*rows)
        
        # CONVERT DATA TO A DEFAULTDICT ORDERED BY SEGMENT_ID
        seg_ids = list(data[1])
        
        datapack = defaultdict(list)
        data_list = [data[0],data[2],data[3],data[4],data[5]] #segment_name,x,y,z(elev),z(gps_time)
        
        for ki, kl in zip(seg_ids, zip(*data_list)):
            datapack[ki] += [kl]
        
        for k, v in datapack.items():
            datapack[k] = map(list, zip(*v))
        
        # FREE UP SOME MEMORY
        del rows,data,data_list
        
        # CREATE A KML OBJECT
        kml = simplekml.Kml()
        
        # CREATE A MULTI-GEOMETRY OBJECTS
        linestrings = kml.newmultigeometry(name='')
        
        # FOR EACH SEGMENT IN THE DATAPACK ADD THE VALUES
        for segment_name,lon,lat,elev,gps_time in datapack.itervalues():
            
            seg_line = []
        
            for pt_idx in range(len(lon)):
                
                if pt_idx > 1 and (gps_time[pt_idx] - gps_time[pt_idx-1]) > 10:
                    
                    # WRITE CURRENT LINESTRING
                    linestrings.newlinestring(name=segment_name,coords=seg_line)
                    
                    # START NEW LINE SEGMENT AFTER GAP
                    seg_line = []
                    coord_string = (lon[pt_idx],lat[pt_idx],elev[pt_idx])
                    seg_line.append(coord_string)
                
                else:
                    coord_string = (lon[pt_idx],lat[pt_idx],elev[pt_idx])
                    seg_line.append(coord_string)
                    
            # ADD THE LINESTRING
            linestrings.newlinestring(name=segment_name,coords=seg_line)
            
        # SET THE LINESTRING COLOR
        linestrings.style.linestyle.color = simplekml.Color.hex('0000FF')
        linestrings.altitudemode = simplekml.AltitudeMode.relativetoground
        
        # CONSTRUCT THE OUTPUT CSV INFORMATION
        server_dir = '/cresis/snfs1/web/ops/data/kml/'
        web_dir = 'data/kml/'
        tmp_fn = 'CReSIS_L2_KML_' + utility.randid(10) + '.kml'
        web_fn = web_dir + tmp_fn
        server_fn  = server_dir + tmp_fn
                
        # WRITE KML FILE TO SERVER
        kml.save(server_fn)

        # RETURN THE KML URL
        return utility.response(1,web_fn)
    
    except:        
        return utility.error_check(sys)

@csrf_exempt
def get_system_info(request): 

    try:

        # GET ALL OF THE INSTALLED APPLICATIONS
        import ops.settings as settings
        apps = settings.INSTALLED_APPS

        systems = []
        seasons = []
        locations = []

        for app in apps:
            if app.startswith(('rds','snow','accum','kuband')):

    # LOAD THE MODELS FOR THE SPECIFIED APP
                models = utility.get_app_models(app)

                # GET SEASON AND LOCATION
                c_seasons = models.seasons.objects.select_related('locations__location_name').values_list('season_name','location__location_name')        

                if not len(c_seasons) == 0:

                    # UNZIP THE DATA
                    data = zip(*c_seasons)

                    # STORE THE DATA
                    seasons.extend(data[0])
                    locations.extend(data[1])
                    systems.extend([app]*len(data[0]))

        # RETURN A RESPONSE TO THE CLIENT
        return utility.response(1,ujson.dumps({'systems':systems,'seasons':seasons,'locations':locations}))

    except:
        return utility.error_check(sys)

@csrf_exempt
def get_segment_info(request):

    # GET THE JSON FROM THE SERVER REQUEST
    status,response1,response2 = utility.get_data(request)
    if not status: return response1

    # LOAD THE MODELS FOR THE SPECIFIED APP
    models = utility.get_app_models(response1)

    # DECODE THE JSON OBJECT
    try:
        data = ujson.loads(response2)
    except:
        return utility.error_check(sys)

    # PARSE THE JSON STRUCTURE
    try:
        c_segment_id = data['properties']['segment_id']
    except:
        return utility.error_check(sys)

    try:

        # GET SEGMENT SEASON AND FRAMES
        c_segment = models.segments.objects.filter(segment_id=c_segment_id).values_list('segment_id','segment_name','season_id')[0]        
        c_season = models.seasons.objects.filter(season_id=c_segment[2]).values_list('season_name',flat=True)[0]
        c_frames = models.frames.objects.filter(segment_id=c_segment[0]).values_list('frame_name','start_gps_time','stop_gps_time')

        # UNZIP FRAMES
        frames = zip(*c_frames)

        # RETURN RESPONSE TO CLIENT
        return utility.response(1,ujson.dumps({'season':c_season,'segment':c_segment[1],'frame':frames[0],'start_gps_time':frames[1],'stop_gps_time':frames[2]}))

    except:
        return utility.error_check(sys)

@csrf_exempt
def get_crossover_error(request):
    
    # GET THE JSON FROM THE SERVER REQUEST
    status,response1,response2 = utility.get_data(request)
    if not status: return response1
        
    # LOAD THE MODELS FOR THE SPECIFIED APP
    models = utility.get_app_models(response1)
            
    # DECODE THE JSON OBJECT
    try:
        data = ujson.loads(response2)
    except:
        return utility.error_check(sys)    
    
    # PARSE THE JSON STRUCTURE
    try:
        region = data['properties']['location']
        lyr_names = data['properties']['lyr_name']
        
        #Get any seasons to exclude if provided
        try:
            excluded_seasons = data['properties']['excluded_seasons']
            if not isinstance(excluded_seasons,list):
                excluded_seasons = [excluded_seasons]
            #Determine which segments not to include in searching for crossovers
            not_segments = models.segments.objects.filter(season_id__season_name__in=excluded_seasons).values_list('segment_id',flat=True)
        except:
            not_segments = []
        
        #Defines GPS time range to search for layer points within (crossover gps +/- search_offset) - LET 5 BE THE DEFAULT
        search_offset = data['properties']['search_offset']
        
        # MAKE SURE SINGLE ELEMENTS ARE LISTS AND FLOATS ARE STRINGS
        if not isinstance(lyr_names, list):
            lyr_names = [lyr_names]
            
        try: # CHECK IF SEASON IS GIVEN
            
            seasons = data['properties']['season']
            type = 1
            # MAKE SURE SINGLE ELEMENTS ARE LISTS
            if not isinstance(seasons,list):
                seasons = [seasons]
        
        except:
            
            try: # CHECK IF SEGMENT IS GIVEN
                
                segments = data['properties']['segment']
                type = 2
                #MAKE SURE SINGLE ELEMENTS ARE LITSTS
                if not isinstance(segments, list):
                    segments = [segments]
            
            except:
                
                try: # CHECK IF FRAME IS GIVEN

                    frm_nms = data['properties']['frame']
                    type = 3
                    #MAKE SURE SINGLE ELEMENTS ARE LISTS:
                    if not isinstance(frm_nms,list):
                        frm_nms = [frm_nms]
                
                except:
                    return utility.response(0, "PROPERTY NOT FOUND (properties.season, properties.segment, or properties.frame).")
    except:
        return utility.error_check(sys)    
    
    try:   
        
        # GET THE EPSG CODE
        proj = utility.proj_from_region(region)
        
        # GET LAYER 
        layers = models.layers.objects.filter(layer_name__in=lyr_names).values_list('layer_id',flat=True)
        
        # SET VARIABLES
        layer_twtt1 = []; layer_twtt2 = []; cross_points = []; abs_error = []; gps_time1 = []; gps_time2 = []; frame_id1 = []; frame_id2 = []; layer_id = []; frame_1 = []; frame_2 = [];ELEV_1 = []; ELEV_2 = [];lp_id1 = []; lp_id2 = []; cross_angle = []; distance_1 = []; distance_2 = [];

        if type == 3: 
             
            #Get info on frames   
            frames = models.frames.objects.filter(frame_name__in=frm_nms).values_list('segment_id','start_gps_time','stop_gps_time', 'frame_id')
            if frames is None:
                return utility.response(0, "No Matching Frames Were Found")
            #Establish connection with DB
            cursor = connection.cursor()
            try:
                #Find crossovers for each frame. Loop through all crossovers and find two nearest layer points in time and space for each layer.
                for frm in frames:
                    crossovers = models.crossovers.objects.filter(Q(segment_1_id=frm[0]) | Q(segment_2_id=frm[0]), Q(gps_time_1__range=(frm[1],frm[2])) | Q(gps_time_2__range=(frm[1],frm[2]))).exclude(Q(segment_1_id__in=not_segments) | Q(segment_2_id__in=not_segments)).transform(proj).values_list('crossover_id','segment_1_id','segment_2_id','gps_time_1','gps_time_2','cross_point','cross_angle')
                    for layer in layers:
                        for cross in crossovers:
                            lp_sql = "WITH lp1 AS (SELECT lp.layer_points_id, lp.twtt, lp.gps_time,lp.layer_point, frm.frame_id,frm.frame_name, ST_Distance(ST_Transform(lp.layer_point,%s),ST_GeomFromText('%s',%s)) as Distance FROM %s_layer_points AS lp,%s_frames AS frm WHERE lp.segment_id = %s AND lp.layer_id = %s AND lp.gps_time BETWEEN %2.10f - %2.10f AND %2.10f + %2.10f AND lp.gps_time BETWEEN frm.start_gps_time AND frm.stop_gps_time ORDER BY ABS(%2.10f - gps_time) LIMIT 1), lp2 AS (SELECT lp.layer_points_id, lp.twtt, lp.gps_time,lp.layer_point, frm.frame_id, frm.frame_name, ST_Distance(ST_Transform(lp.layer_point,%s),ST_GeomFromText('%s',%s)) as Distance FROM %s_layer_points AS lp, %s_frames AS frm WHERE lp.segment_id = %s AND lp.layer_id = %s AND lp.gps_time BETWEEN %2.10f - %2.10f AND %2.10f + % 2.10f AND lp.gps_time BETWEEN frm.start_gps_time AND frm.stop_gps_time ORDER BY ABS(%2.10f - gps_time) LIMIT 1) SELECT lp1.twtt, lp2.twtt,lp1.gps_time, lp2.gps_time, lp1.frame_id, lp2.frame_id, lp1.frame_name, lp2.frame_name,ST_Z(lp1.layer_point),ST_Z(lp2.layer_point), lp1.Distance,lp2.Distance FROM lp1, lp2 WHERE lp1.layer_points_id != lp2.layer_points_id;" % (proj,cross[5],proj,response1,response1,cross[1],layer,cross[3],search_offset,cross[3],search_offset,cross[3],proj,cross[5],proj,response1,response1,cross[2],layer,cross[4],search_offset,cross[4],search_offset,cross[4])
                            # SELECT lp1.twtt, lp2.twtt, lp1.gps_time, lp2.gps_time, lp1.frame_id, lp2.frame_id, lp1.frame_name, lp2.frame_name,ST_Z(lp1.layer_point),ST_Z(lp2.layer_point),lp1.Distance,lp2.Distance
                            cursor.execute(lp_sql)
                            lps = cursor.fetchone()
                            #If there are two unique layer points associated with the crossover, append results to lists. 
                            if lps:
                                #Ensure that the first values are from the requested frame.
                                if frm[3] == lps[4]:
                                    layer_twtt1.append(lps[0])
                                    layer_twtt2.append(lps[1])
                                    cross_points.append(cross[5])
                                    cross_angle.append(cross[6])
                                    abs_error.append(fabs(lps[0] - lps[1]))
                                    gps_time1.append(lps[2])
                                    gps_time2.append(lps[3])
                                    ELEV_1.append(lps[8])
                                    ELEV_2.append(lps[9])
                                    distance_1.append(lps[10])
                                    distance_2.append(lps[11])
                                    frame_id1.append(lps[4])
                                    frame_id2.append(lps[5])
                                    frame_1.append(lps[6])
                                    frame_2.append(lps[7])
                                    layer_id.append(layer)
                                else: 
                                    layer_twtt1.append(lps[1])
                                    layer_twtt2.append(lps[0])
                                    cross_points.append(cross[5])
                                    cross_angle.append(cross[6])
                                    abs_error.append(fabs(lps[0] - lps[1]))
                                    gps_time1.append(lps[3])
                                    gps_time2.append(lps[2])
                                    ELEV_1.append(lps[9])
                                    ELEV_2.append(lps[8])
                                    distance_1.append(lps[11])
                                    distance_2.append(lps[10])
                                    frame_id1.append(lps[5])
                                    frame_id2.append(lps[4])
                                    frame_1.append(lps[7])
                                    frame_2.append(lps[6])
                                    layer_id.append(layer)
            finally:
                cursor.close()
                                
        else:
                    
            if type == 1:
            
                # GET SEGMENT FOR GIVEN SEASON
                segments = models.segments.objects.filter(season_id__season_name__in=seasons).values_list('segment_id',flat=True)
                
                # FIND CROSSOVERS
                crossovers = models.crossovers.objects.filter(Q(segment_1_id__in=segments) | Q(segment_2_id__in=segments)).exclude(Q(segment_1_id__in=not_segments) | Q(segment_2_id__in=not_segments)).transform(proj).values_list('crossover_id','segment_1_id','segment_2_id','gps_time_1', 'gps_time_2','cross_point','cross_angle')
                
            elif type == 2:
            
                # FIND CROSSOVERS
                crossovers = models.crossovers.objects.filter(Q(segment_1_id__segment_name__in=segments) | Q(segment_2_id__segment_name__in=segments)).exclude(Q(segment_1_id__in=not_segments) | Q(segment_2_id__in=not_segments)).transform(proj).values_list('crossover_id','segment_1_id','segment_2_id','gps_time_1', 'gps_time_2','cross_point')
            
            # FIND TWO NEAREST LAYER POINTS TO EACH CROSSOVER
            cursor = connection.cursor()
            try:
                for layer in layers:
                    for cross in crossovers:
                        lp_sql = "WITH lp1 AS (SELECT lp.layer_points_id, lp.twtt, lp.gps_time,lp.layer_point, frm.frame_id,frm.frame_name, ST_Distance(ST_Transform(lp.layer_point,%s),ST_GeomFromText('%s',%s)) as Distance FROM %s_layer_points AS lp,%s_frames AS frm WHERE lp.segment_id = %s AND lp.layer_id = %s AND lp.gps_time BETWEEN %2.10f - %2.10f AND %2.10f + %2.10f AND lp.gps_time BETWEEN frm.start_gps_time AND frm.stop_gps_time ORDER BY ABS(%2.10f - gps_time) LIMIT 1), lp2 AS (SELECT lp.layer_points_id, lp.twtt, lp.gps_time,lp.layer_point, frm.frame_id, frm.frame_name, ST_Distance(ST_Transform(lp.layer_point,%s),ST_GeomFromText('%s',%s)) as Distance FROM %s_layer_points AS lp, %s_frames AS frm WHERE lp.segment_id = %s AND lp.layer_id = %s AND lp.gps_time BETWEEN %2.10f - %2.10f AND %2.10f + % 2.10f AND lp.gps_time BETWEEN frm.start_gps_time AND frm.stop_gps_time ORDER BY ABS(%2.10f - gps_time) LIMIT 1) SELECT lp1.twtt, lp2.twtt,lp1.gps_time, lp2.gps_time, lp1.frame_id, lp2.frame_id, lp1.frame_name, lp2.frame_name,ST_Z(lp1.layer_point),ST_Z(lp2.layer_point),lp1.Distance,lp2.Distance FROM lp1, lp2 WHERE lp1.layer_points_id != lp2.layer_points_id;" % (proj,cross[5],proj,response1,response1,cross[1],layer,cross[3],search_offset,cross[3],search_offset,cross[3],proj,cross[5],proj,response1,response1,cross[2],layer,cross[4],search_offset,cross[4],search_offset,cross[4])
                        cursor.execute(lp_sql)
                        lps = cursor.fetchone()
                        
                        # IF THERE ARE TWO UNIQUE POINTS APPEND THEM TO THE OUTPUT
                        if lps:
                            layer_twtt1.append(lps[0])
                            layer_twtt2.append(lps[1])
                            cross_points.append(cross[5])
                            cross_angle.append(cross[6])
                            abs_error.append(fabs(lps[0] - lps[1]))
                            gps_time1.append(lps[2])
                            gps_time2.append(lps[3])
                            ELEV_1.append(lps[8])
                            ELEV_2.append(lps[9])
                            distance_1.append(lps[10])
                            distance_2.append(lps[11])
                            frame_id1.append(lps[4])
                            frame_id2.append(lps[5])
                            frame_1.append(lps[6])
                            frame_2.append(lps[7])
                            layer_id.append(layer)
            finally:
                 cursor.close()               
        
        # RETURN A RESPONSE TO THE CLIENT
        if cross_points: 
            
            x,y = zip(*cross_points)
            return utility.response(1,ujson.dumps({'X': x, 'Y': y, 'twtt_1': layer_twtt1, 'twtt_2': layer_twtt2, 'abs_error': abs_error,'cross_angle':cross_angle ,'gps_time_1':gps_time1, 'gps_time_2':gps_time2,'ELEV_1':ELEV_1,'ELEV_2':ELEV_2,'distance_1':distance_1,'distance_2':distance_2,'frame_id_1':frame_id1,'frame_id_2':frame_id2,'frame_1':frame_1, 'frame_2':frame_2, 'lyr_id': layer_id}))
        
        else:
            return utility.response(2, 'NO CROSSOVERS FOUND.')
    
    except:
       return utility.error_check(sys)

@csrf_exempt
def search_frames(request):
    
    # GET THE JSON FROM THE SERVER REQUEST
    status,response1,response2 = utility.get_data(request)
    if not status: return response1

    # LOAD THE MODELS FOR THE SPECIFIED APP
    models = utility.get_app_models(response1)

    # DECODE THE JSON OBJECT
    try:
        data = ujson.loads(response2)
    except:
        return utility.error_check(sys)

    # PARSE THE JSON STRUCTURE
    try:
        region = data['properties']['location']
        search = data['properties']['search_str']
        try:
            season_check = True
            c_season_name = data['properties']['season']
        except:
            season_check = False
    except:
        return utility.error_check(sys)

    # SEARCH THE DATABASE GIVEN THE SEARCH STRING
    try:

        # SELECT FRAME (LIMIT 1)
        try:
            if season_check:
                c_season = models.seasons.objects.filter(season_name=c_season_name).values_list('season_id', flat=True)
                c_segment = models.segments.objects.filter(season_id=c_season[0],segment_name__istartswith=search[0:11]).values_list('segment_id', flat=True)
                c_frame = models.frames.objects.filter(frame_name__istartswith=search, location_id__location_name=region,segment_id=c_segment[0]).select_related('segment__season_name').values_list('segment__season__season_name','segment_id', 'start_gps_time', 'stop_gps_time', 'frame_name').order_by('start_gps_time')[0]     
            else:
                c_frame = models.frames.objects.filter(frame_name__istartswith=search, location_id__location_name=region).select_related('segment__season_name').values_list('segment__season__season_name','segment_id', 'start_gps_time', 'stop_gps_time', 'frame_name').order_by('start_gps_time')[0]     
        
        except IndexError:
            return utility.response(2, 'NO RESULT FOUND')

        # GET THE EPSG CODE
        proj = utility.proj_from_region(region)
        
        # GET THE POINT PATH
        c_points = models.point_paths.objects.filter(segment_id=c_frame[1], gps_time__range=(c_frame[2], c_frame[3])).transform(proj).values_list('point_path','gps_time')

        # UNZIP THE FRAME POINTS AND GPS_TIME
        c_points = [(i[0].x,i[0].y,float(i[1])) for i in c_points]
        x_coord,y_coord,gps_time = zip(*c_points)

        # RETURN A RESPONSE TO THE CLIENT
        return utility.response(1, ujson.dumps({'season':c_frame[0],'segment_id':c_frame[1],'start_gps_time':c_frame[2],'stop_gps_time':c_frame[3],'frame': c_frame[4],'X':x_coord,'Y':y_coord,'gps_time':gps_time}))

    except: 
        return utility.error_check(sys)

@csrf_exempt
def get_initial_data(request):
    
    # RETRIEVE JSON from POST
    status,response1,response2 = utility.get_data(request)
    if not status: return response1

    # GET the models
    models = utility.get_app_models(response1)

    # LOAD JSON object
    try:
        data = ujson.loads(response2)
    except:
        return utility.error_check(sys)

    # COLLECT JSON elements
    try:
        seasons = data['properties']['seasons']
        #Make sure seasons is a list
        if not isinstance(seasons,list):
            seasons = [seasons]
        
        radars = data['properties']['radars']
        #Make sure radars is a list
        if not isinstance(radars,list):
            radars = [radars]
        
        segments = data['properties']['segments']
        #Make sure segments is a list
        if not isinstance(segments,list):
            segments = [segments]

        #Check if any layers are specified
        try: 
            layers = data['properties']['layers']
            if not isinstance(layers, list): 
                layers = [layers]
        except:
            layers = []
        
    except:
        return utility.error_check(sys)
        
    #Get the properties necessary for creating CSVs of tables.
    try:

        #Get season ids and location ids
        c_seasons = models.seasons.objects.filter(season_name__in=seasons).values_list('season_id', 'location_id')
        season_ids, location_ids = zip(*c_seasons)
        season_ids = list(season_ids)
        location_ids = list(set(location_ids))
        del c_seasons
        
        #Get radar and segment ids
        segments = models.segments.objects.filter(segment_name__in=segments,radar_id__radar_name__in=radars).values_list('segment_id','radar_id')
        #Separate segment_ids and unique radar_ids
        segment_ids, radar_ids = zip(*segments)
        segment_ids = list(segment_ids)
        radar_ids = list(set(radar_ids))
        del segments
        
        #Get frame ids
        frame_ids = models.frames.objects.filter(segment_id__in=segment_ids).values_list('frame_id',flat=True)
        frame_ids = list(frame_ids)
        
        #Get layer ids (either the ones specified or just the ones associated with the desired data)
        if layers:
            layers = models.layers.objects.filter(layer_name__in=layers).values_list('layer_id','layer_group')
        else:
            layers = models.layers.objects.values_list('layer_id','layer_group')
        layers = list(layers)
        
        #Separate layer_ids and unique layer_group_ids
        layer_ids,layer_group_ids = zip(*layers)
        layer_ids = list(layer_ids)
        layer_group_ids = list(set(layer_group_ids))
        del layers 
        
        #Create a temporary folder for holding csv files prior to compression into datapack 
        random_id = utility.randid(10)
        tmp_dir = '/cresis/snfs1/web/ops/datapacktmp/' + random_id
        os.system('mkdir -m 777 -p ' + tmp_dir)
        
        #Setup sql to copy relevant data to CSV files
        layers_sql = "COPY (SELECT * FROM %s_layers WHERE layer_name != 'surface' AND layer_name != 'bottom' AND layer_id IN %s ) TO '%s/%s_layers' WITH CSV;" % (response1,list(layer_ids),tmp_dir,response1)
        layer_link_sql = "COPY (SELECT * FROM %s_layer_links WHERE layer_1_id IN %s AND layer_2_id IN %s) TO '%s/%s_layer_links' WITH CSV;" % (response1,layer_ids, layer_ids, tmp_dir,response1)
        layer_groups_sql = "COPY (SELECT * FROM %s_layer_groups WHERE group_name != 'uncatagorized' AND group_name != 'standard' AND layer_group_id IN %s) TO '%s/%s_layer_groups' WITH CSV;" % (response1,layer_group_ids,tmp_dir,response1)
        seasons_sql = "COPY (SELECT * FROM %s_seasons WHERE season_id IN %s) TO '%s/%s_seasons' WITH CSV;" % (response1,season_ids,tmp_dir,response1)
        point_paths_sql = "COPY (SELECT * FROM %s_point_paths WHERE segment_id IN %s) TO '%s/%s_point_paths' WITH CSV;" % (response1, segment_ids,tmp_dir, response1)
        layer_points_sql = "COPY (SELECT * FROM %s_layer_points WHERE segment_id IN %s AND layer_id IN %s) TO '%s/%s_layer_points' WITH CSV;" % (response1, segment_ids, layer_ids,tmp_dir,response1)
        segments_sql = "COPY (SELECT * FROM %s_segments WHERE segment_id IN %s) TO '%s/%s_segments' WITH CSV;" % (response1, segment_ids,tmp_dir, response1)
        crossovers_sql = "COPY (SELECT * FROM %s_crossovers WHERE segment_1_id IN %s AND segment_2_id IN %s) TO '%s/%s_crossovers' WITH CSV;" % (response1, segment_ids, segment_ids,tmp_dir, response1)
        radars_sql = "COPY (SELECT * FROM %s_radars WHERE radar_id IN %s) TO '%s/%s_radars' WITH CSV;" % (response1, radar_ids,tmp_dir,response1)
        frames_sql = "COPY (SELECT * FROM %s_frames WHERE segment_id IN %s) TO '%s/%s_frames' WITH CSV;" % (response1, segment_ids,tmp_dir, response1)
        echograms_sql = "COPY (SELECT * FROM %s_echograms WHERE frame_id IN %s) TO '%s/%s_echograms' WITH CSV;" % (response1, frame_ids,tmp_dir, response1)
        landmarks_sql = "COPY (SELECT * FROM %s_landmarks WHERE segment_id IN %s) TO '%s/%s_landmarks' WITH CSV;" % (response1, segment_ids,tmp_dir,response1)
        locations_sql = "COPY (SELECT * FROM %s_locations WHERE location_name != 'arctic' AND location_name != 'antarctic' AND location_id IN %s) TO '%s/%s_locations' WITH CSV;" % (response1, location_ids,tmp_dir,response1)
        
        #Establish a connection to the DB and execute COPY commands
        cursor = connection.cursor()
        try:
            cursor.execute(layers_sql.replace('[','(').replace(']',')'))
            cursor.execute(layer_link_sql.replace('[','(').replace(']',')'))
            cursor.execute(layer_groups_sql.replace('[','(').replace(']',')'))
            cursor.execute(seasons_sql.replace('[','(').replace(']',')'))
            cursor.execute(point_paths_sql.replace('[','(').replace(']',')'))  
            cursor.execute(layer_points_sql.replace('[','(').replace(']',')'))
            cursor.execute(segments_sql.replace('[','(').replace(']',')'))
            cursor.execute(crossovers_sql.replace('[','(').replace(']',')'))
            cursor.execute(radars_sql.replace('[','(').replace(']',')'))
            cursor.execute(frames_sql.replace('[','(').replace(']',')'))
            cursor.execute(echograms_sql.replace('[','(').replace(']',')'))
            cursor.execute(landmarks_sql.replace('[','(').replace(']',')'))
            cursor.execute(locations_sql.replace('[','(').replace(']',')'))
        finally:
            cursor.close()
        
        # CONSTRUCT THE OUTPUT DATAPACK INFORMATION
        server_dir = '/cresis/snfs1/web/ops/data/datapacks/'
        web_dir = 'data/datapacks/'
        tmp_fn = 'CReSIS_%s_Datapack_' % (response1) + random_id + '.tar.gz'
        web_fn = web_dir + tmp_fn
        
        #Compress files to initial data pack, copy to web data dir, and delete temp directory w/ csv files.
        syscmd = '(cd %s && tar -zcf %s * && cp %s %s && cd .. && rm -rf %s)' % (tmp_dir,tmp_fn,tmp_fn,server_dir,tmp_dir)
        os.system(syscmd)
        
        #Return response
        return utility.response(1, web_fn)
    except:
        return utility.error_check(sys)

# =============================================================
# OUTPUT FUNCTIONS FOR EXT
# =============================================================
@csrf_exempt
def get_system_info_ext(request):

	try:

		# GET ALL OF THE INSTALLED APPLICATIONS
		import ops.settings as settings
		apps = settings.INSTALLED_APPS

		outData = []

		for app in apps:
			if app.startswith(('rds','snow','accum','kuband')):

				# LOAD THE MODELS FOR THE SPECIFIED APP
				models = utility.get_app_models(app)

				# GET SEASON AND LOCATION
				c_seasons = models.seasons.objects.select_related('locations__location_name').values_list('season_name','location__location_name')        

				if not len(c_seasons) == 0:

					# UNZIP THE DATA
					data = zip(*c_seasons)
					
					for dataIdx in range(len(data[0])):

						# STORE THE DATA
						outData.append({'system':app,'season':data[0][dataIdx],'location':data[1][dataIdx]})

		# RETURN A RESPONSE TO THE CLIENT
		return utility.response(1,outData)

	except:
		return utility.error_check(sys)
		
# ==============================================================
# UTILITY FUNCTIONS (QUERY,ANALYZE,PROFILE)
# ==============================================================

@ip_authorization()
@csrf_exempt
def query(request):

    # GET THE QUERY TEXT FROM THE SERVER REQUEST
    status,query_str = utility.get_query(request)

    # IF GET_QUERY WAS SUCCESFULL EXECUTE THE QUERY
    if status:
        try:
            
            # CREATE A CURSOR AND COMMIT THE QUERY
            cursor = connection.cursor()
            cursor.execute(query_str)
            
            # FETCH ALL THE RESULTS
            row = cursor.fetchall()
            
            # RETURN THE ROWS AS THE RESPONSE
            if not row:
                return utility.response(2,'QUERY MIGHT HAVE WORKED. NO ROWS RETURNED.')
            else:
                return utility.response(1,row)
        
        except DatabaseError as dberror:
            return utility.response(0,dberror[0])
    else:
        return query_str

@ip_authorization()           
@csrf_exempt
def tables_analyze(request):

    # RETRIEVE ujson from POST
    status,response1,response2 = utility.get_data(request)
    if not status: return response1

    # GET the models
    models = utility.get_app_models(response1)

    # LOAD ujson object
    try:
        data = ujson.loads(response2)
    except:
        return utility.error_check(sys)

    # COLLECT ujson elements
    try:
        tables = data['properties']['tables']
        # MAKE SURE SINGLE ELEMENTS ARE LISTS
        if not isinstance(tables,list):
            tables = [tables]
    except:
        return utility.error_check(sys)

    #Analyze tables 
    try: 
        cursor = connection.cursor()
        try: 
            for table in tables:
                cursor.execute("ANALYZE " +response1+"_"+ table)
        finally:
            cursor.close()
            
        return utility.response(1, "Tables successfully analyzed")

    except:
        return utility.error_check(sys)

@ip_authorization()
@csrf_exempt
def profile(request):

    try:
        # GET the view and create an eval string
        view = request.POST.get('view')
        eval_string = view + '(request)'

        # GET a profiler object
        profiler = line_profiler.LineProfiler()

        # ENABLE the profiler
        profiler.enable()
        profiler.add_function(eval(view+'.func_closure[0].cell_contents'))

        # EVALUEATE the view
        view_response = eval(eval_string)

        # DISABLE profiler and SET UP from output
        profiler.disable()
        time_str = datetime.datetime.now().strftime('-%d-%m-%y-%X')  
        fn = '/var/profile_logs/'+view+time_str+'.lprof'
        fntxt = '/var/profile_logs/txt/'+view+time_str+'.txt'

        # WRITE output files    
        profiler.dump_stats(fn) 
        os.system('python -m line_profiler '+fn+' > '+fntxt)

        # RETURN the view resonse
        return view_response

    except:
        return utility.error_check(sys)
