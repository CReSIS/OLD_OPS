from django.db import connection, DatabaseError, transaction, IntegrityError
from django.db.models import Max, Min
from django.contrib.gis.geos import GEOSGeometry, Point, LineString, WKBReader
from django.contrib.gis.gdal import SpatialReference, CoordTransform
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.http import HttpResponse
from django.conf import settings
from .utility import ipAuth
from decimal import Decimal
import ops.utility as utility
import sys
import os
import datetime
import simplekml
import ujson
import csv
import time
import math
import tempfile
import logging
from scipy.io import savemat
import numpy as np
from collections import OrderedDict
from django.db.models.base import ModelState
import ops.settings as opsSettings

# =======================================
# DATA INPUT/DELETE FUNCTIONS
# =======================================

if settings.DEBUG:
    import debugpy


@ipAuth()
@transaction.atomic()
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

    try:
        models, data, app, cookies = utility.getInput(
            request)  # get the input and models

        userProfileObj, status = utility.getUserProfile(cookies)
        if status:
            if not userProfileObj.isRoot and not userProfileObj.createData:
                return utility.response(
                    0, 'ERROR: USER NOT AUTHORIZED TO CREATE DATA.', {})
        else:
            return utility.response(0, userProfileObj, {})

        # parse the data input
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
        inFrameStartGpsTimes = utility.forceList(
            data['properties']['frame_start_gps_time'])

        # Set up the basic logging configuration for createPath:
        logging.basicConfig(
            filename=opsSettings.OPS_DATA_PATH +
            'django_logs/createPath.log',
            format='%(levelname)s :: %(asctime)s :: %(message)s',
            datefmt='%c',
            level=logging.DEBUG)
        logging.info('Segment %s of season %s is now loading', inSegment, inSeason)

        locationsObj, _ = models.locations.objects.get_or_create(
            name=inLocationName.lower())  # get or create the location
        seasonGroupsObj, _ = models.season_groups.objects.get_or_create(
            name=inSeasonGroup)  # get or create the season
        seasonsObj, _ = models.seasons.objects.get_or_create(
            name=inSeason, season_group_id=seasonGroupsObj.pk, location_id=locationsObj.pk)  # get or create the season
        radarsObj, _ = models.radars.objects.get_or_create(
            name=inRadar.lower())  # get or create the radar

        linePathGeom = GEOSGeometry(ujson.dumps(inLinePath))  # create a geometry object

        # Check of the segment exists already:
        segmentsObj = models.segments.objects.filter(
            season_id=seasonsObj.pk,
            radar_id=radarsObj.pk,
            name=inSegment).values_list(
            'pk',
            flat=True)

        if segmentsObj:
            errorStr = 'SEGMENT %s HAS ALREADY BEEN CREATED' % inSegment
            logging.warning(
                'SEGMENT %s of SEASON %s WAS ALREADY CREATED.',
                inSegment,
                inSeason)
            return utility.response(0, errorStr, {})

        # Create the segment if it does not exist.
        segmentsObj, _ = models.segments.objects.get_or_create(
            season_id=seasonsObj.pk, radar_id=radarsObj.pk, name=inSegment, geom=linePathGeom, crossover_calc=False)

        logging.info('Segment %s of season %s has been created.', inSegment, inSeason)

        frmPks = []
        for frmId in range(int(inFrameCount)):
            frameName = inSegment + ("_%03d" % (frmId + 1))
            frmObj, _ = models.frames.objects.get_or_create(
                name=frameName, segment_id=segmentsObj.pk)  # get or create the frame object
            frmPks.append(frmObj.pk)  # store the pk for use in point paths

        # Open a temporary file to hold point path records
        # Centos 7 places tmp files into service-level subdirs which do not reflect the path returned in Python
        # Instead, create a dir in /db/
        temppath = opsSettings.OPS_DATA_PATH + "datapacktmp/createPath"
        os.makedirs(temppath, mode=0o777, exist_ok=True)

        with tempfile.NamedTemporaryFile(mode='w', prefix='tmp_', dir=temppath, suffix='_pointPaths.csv', delete=False) as f:

            # Create a csv writer object
            fwrite = csv.writer(f, delimiter=',')

            for ptIdx, ptGeom in enumerate(linePathGeom):
                # get the frame pk (based on start gps time list)
                frmId = frmPks[max([gpsIdx for gpsIdx in range(
                    len(inFrameStartGpsTimes)) if inFrameStartGpsTimes[gpsIdx] <= inGpsTime[ptIdx]])]
                # Create a GEOSGeometry of the point path
                pointPathGeom = GEOSGeometry('POINT Z (' +
                                             repr(ptGeom[0]) +
                                             ' ' +
                                             repr(ptGeom[1]) +
                                             ' ' +
                                             str(inElevation[ptIdx]) +
                                             ')', srid=4326)  # create a point geometry object
                # Write the row to the temp csv file
                fwrite.writerow([locationsObj.pk,
                                 seasonsObj.pk,
                                 segmentsObj.pk,
                                 frmId,
                                 inGpsTime[ptIdx],
                                 inRoll[ptIdx],
                                 inPitch[ptIdx],
                                 inHeading[ptIdx],
                                 str(pointPathGeom.hexewkb.decode()), 
                                 True])

        logging.info(
            'Point paths CSV for segment %s of season %s has now been created (%s).',
            inSegment,
            inSeason,
            f.name)
        # Create a cursor to interact with the database
        cursor = connection.cursor()
        try:
            # Change permissions on temp file to allow postgres read permission
            os.chmod(f.name, 100)
            # Copy the point paths from the temp csv to the databse.
            copySql = """COPY {app}_point_paths (location_id, season_id, segment_id, frame_id, gps_time, roll, pitch, heading, geom, key_point)
                         FROM %s
                         DELIMITER ',';""".format(app=app)
            cursor.execute(copySql, [f.name])
            logging.info(
                'Point paths CSV for segment %s of season %s has been copied to the database.',
                inSegment,
                inSeason)
            # Remove the temporary file.
            os.remove(f.name)

        except Exception as e:
            return utility.errorCheck(e, sys)
        finally:
            cursor.close()

        logging.info(
            'Segment %s of season %s was successfully inserted.',
            inSegment,
            inSeason)
        return utility.response(1, 'SUCCESS: PATH INSERTION COMPLETED.', {})

    except Exception as e:
        return utility.errorCheck(e, sys)


@ipAuth()
def crossoverCalculation(request):
    """ Creates/Updates entries in the crossovers tables.

    Input:
            geometry: (geojson) {'type':'LineString','coordinates',[longitude latitude]}
            season: (string) name of the season
            season_group: (string) name of the season group
            location: (string) name of the location
            radar: (string) name of the radar
            segment: (string) name of the segment

    Output:
            status: (integer) 0:error 1:success 2:warning
            data: string status message

    """

    try:
        logging.basicConfig(
            filename=opsSettings.OPS_DATA_PATH +
            'django_logs/createPath.log',
            format='%(levelname)s :: %(asctime)s :: %(message)s',
            datefmt='%c',
            level=logging.DEBUG)
        models, data, app, cookies = utility.getInput(
            request)  # get the input and models

        segments = data["segments"]
        if type(segments) == int:
            # Matlab arrays of one element are not JSONified into a list of one element
            segments = [segments]
        for segment_id in segments:

            cursor = connection.cursor()

            try:
                cursor.execute(f"SELECT name, season_id, radar_id from {app}_segments where id={segment_id};")
                inSegment, season_id, radar_id = cursor.fetchone()

                cursor.execute(f"SELECT name, location_id, season_group_id from {app}_seasons where id={season_id};")
                inSeason, location_id, season_group_id = cursor.fetchone()

                cursor.execute(f"SELECT name from {app}_locations where id={location_id};")
                inLocationName = cursor.fetchone()[0]

                cursor.execute(f"SELECT name from {app}_radars where id={radar_id};")
            except Exception as e:
                return utility.errorCheck(e, sys)
            finally:
                cursor.close()

            segmentsObj = models.segments.objects.get(id=segment_id)

            ### calculate and insert crossovers	###
            logging.info(
                'Non self-intersecting crossovers for segment %s of season %s are now being found.',
                inSegment,
                inSeason)
            # Get the correct srid for the locaiton
            proj = utility.epsgFromLocation(inLocationName)
            # Create a GEOS Well Known Binary reader and initialize vars
            cross_pts = []
            cross_angles = []
            point_path_1_id = []
            point_path_2_id = []

            # FIND ALL NON SELF-INTERSECTING CROSSOVERS
            # Get the points of intersection, the closest point_path_id, and the angle
            # in degrees for the current segment.
            sql_str = """SET LOCAL work_mem = '15MB';
                        WITH pts AS
                            (select row_number() over (order by gps_time) AS rn, pp.id, pp.geom from {app}_point_paths pp where segment_id={seg} and key_point=true order by rn),
                        LINE AS
                            (SELECT ST_MakeLine(ST_GeomFromText('POINTZ('||ST_X(pts.geom)||' '||ST_Y(pts.geom)||' '||pts.rn||')', 4326)) AS ln
                                FROM pts),
                        i_pts AS
                            (SELECT (ST_Dump(ST_Intersection(ST_Transform(line.ln,{proj}), ST_Transform(o.geom,{proj})))).geom AS i_pt
                                FROM LINE, {app}_segments AS o
                                    WHERE o.id != {seg} AND o.crossover_calc=true)

                        SELECT ST_Transform(ST_Force2D(i_pt), 4326) AS i,
                        pts1.id,
                            CASE
                                WHEN ST_Equals(i_pt, ST_Transform(pts1.geom,{proj})) THEN degrees(ST_Azimuth(i_pt, ST_Transform(pts2.geom,{proj})))
                                ELSE degrees(ST_Azimuth(i_pt, ST_Transform(pts1.geom,{proj})))
                            END
                            FROM i_pts,
                            pts AS pts1,
                            pts AS pts2
                        WHERE pts1.rn = ST_Z(i_pt)::int
                        AND pts2.rn =
                            (SELECT rn
                            FROM pts
                            WHERE rn != ST_Z(i_pts.i_pt)::int
                            ORDER BY ABS(ST_Z(i_pts.i_pt)::int - rn) ASC
                            LIMIT 1)
                        ORDER BY i;""".format(app=app, proj=proj, seg=segmentsObj.pk)
            cursor = connection.cursor()
            try:
                cursor.execute(sql_str)
                cross_info1 = cursor.fetchall()

                # Only perform second query and processing if the above had results.
                if cross_info1:
                    # Get the closest point_path_id and the angle in degrees for the other
                    # segments
                    logging.info(
                        'Closest points on intersecting segments for segment %s of season %s are now being found.',
                        inSegment,
                        inSeason)

                    sql_str = """SET LOCAL work_mem = '15MB';
                                with segment_ids as (SELECT s2.id as ids
                                        FROM {app}_segments AS s1, {app}_segments AS s2
                                        WHERE s1.id = {seg}
                                        AND s2.id != {seg} and s2.crossover_calc=true
                                        AND ST_Intersects(s1.geom, s2.geom)),
                                pts AS
                                    (select row_number() over (order by gps_time) AS rn, pp.geom, pp.id, pp.segment_id from {app}_point_paths pp where segment_id in (select ids from segment_ids) and key_point=true order by segment_id, rn),
                                LINE AS
                                    (SELECT ST_MakeLine(ST_GeomFromText('POINTZ('||ST_X(pts.geom)||' '||ST_Y(pts.geom)||' '||pts.rn||')', 4326)) AS ln
                                    FROM pts
                                    GROUP BY pts.segment_id), 
                                i_pts AS
                                    (SELECT (ST_Dump(ST_Intersection(ST_Transform(line.ln,{proj}), ST_Transform(o.geom,{proj})))).geom AS i_pt
                                    FROM LINE, {app}_segments AS o
                                    WHERE o.id = {seg})
                                SELECT pts1.id,
                                    CASE
                                        WHEN ST_Equals(i_pt, ST_Transform(pts1.geom,{proj})) THEN degrees(ST_Azimuth(i_pt, ST_Transform(pts2.geom,{proj})))
                                        ELSE degrees(ST_Azimuth(i_pt, ST_Transform(pts1.geom,{proj})))
                                    END
                                FROM i_pts,
                                    pts AS pts1,
                                    pts AS pts2
                                WHERE pts1.rn = ST_Z(i_pt)::int
                                AND pts2.rn =
                                    (SELECT rn
                                    FROM pts
                                    WHERE rn != ST_Z(i_pts.i_pt)::int
                                    ORDER BY ABS(ST_Z(i_pts.i_pt)::int - rn) ASC
                                    LIMIT 1)
                                ORDER BY ST_Transform(ST_Force2D(i_pt), 4326);""".format(app=app, proj=proj, seg=segmentsObj.pk)
                    cursor.execute(sql_str)
                    cross_info2 = cursor.fetchall()

                    if cross_info2:
                        # Extract all crossovers from above results.
                        for idx in range(len(cross_info1)):
                            cross_pts.append(cross_info1[idx][0])
                            point_path_1_id.append(cross_info1[idx][1])
                            point_path_2_id.append(cross_info2[idx][0])
                            # Determine the angle of intersection
                            angle1 = cross_info1[idx][2]
                            angle2 = cross_info2[idx][1]
                            angle = math.fabs(angle1 - angle2)
                            # Only record the acute angle.
                            if angle > 90:
                                angle = math.fabs(180 - angle)
                                if angle > 90:
                                    angle = math.fabs(180 - angle)
                            cross_angles.append(angle)

                    else:
                        # This should not occur.
                        # Only reached if no crossover information is returned from second query
                        # But second query is only executed if first query finds crossovers
                        # If this occurs while editing the queries, likely one no longer matches the other in
                        logging.error("ERROR FINDING MATCHING CROSSOVER POINT PATHS ON INTERSECTING LINES")
                        return utility.response(
                            0, "ERROR FINDING MATCHING CROSSOVER POINT PATHS ON INTERSECTING LINES", {})

                # FIND ALL SELF-INTERSECTING CROSSOVERS:
                # Fetch the given line path from the db as a multilinestring.
                # 'ST_UnaryUnion' results in a multilinestring with the last point of
                # every linestring except the last linestring as a crossover and the
                # first point of every linestring except the first linestring as a
                # crossover.
                logging.info(
                    'Self-intersecting crossovers for segment %s of season %s are now being found.',
                    inSegment,
                    inSeason)
                sql_str = """WITH pts AS
                                (select row_number() over (order by gps_time) AS rn, pp.id, pp.geom from {app}_point_paths pp where segment_id={seg} and key_point=true order by rn)
                            SELECT ST_UnaryUnion(ST_Transform(ST_MakeLine(ST_GeomFromText('POINTZ('||ST_X(pts.geom)||' '||ST_Y(pts.geom)||' '||pts.id||')', 4326)),{proj}))
                            FROM pts;""".format(app=app, proj=proj, seg=segmentsObj.pk)
                cursor.execute(sql_str)
                line = cursor.fetchone()
                # Create a GEOS geometry from the result fetched above.
                lines = GEOSGeometry(line[0])
                # Check if resulting object is a multilinestring, indicating crossovers.
                if lines.geom_type == 'MultiLineString':
                    # Get the point_path_ids for all points for the given segment:
                    pt_ids = models.point_paths.objects.filter(
                        segment_id=segmentsObj.pk).values_list(
                        'id', flat=True)
                    # Create a dictionary to keep track of crossovers and point ids.
                    self_crosses = {}
                    # Create a dictionary for managing next points (the point after the
                    # crossover along the flight path)
                    nxt_pts = {}
                    # Loop through all linestrings created by ST_UnaryUnion
                    for idx in range(len(lines) - 1):
                        # Set the value of idx2:
                        idx2 = idx + 1

                        # Keep track of intersection point w/ dictionary:
                        i_point = lines[idx][-1]
                        if i_point not in list(self_crosses.keys()):
                            self_crosses[i_point] = []
                            nxt_pts[i_point] = []

                        # Fall back/forward to point w/ z in pt_ids.
                        # For the point before the crossover:
                        # Include the crossover pt in the search (could be on top of
                        # point_path geom)
                        coord_idx = -1
                        while lines[idx][coord_idx][2] not in pt_ids:
                            coord_idx -= 1
                            if math.fabs(coord_idx) > len(lines[idx].coords):
                                coord_idx = -1
                                idx -= 1
                        pt_1 = lines[idx][coord_idx]
                        # For the point after the crossover:
                        coord_idx = 1  # Start after the crossover point.
                        while lines[idx2][coord_idx][2] not in pt_ids:
                            coord_idx += 1
                            if coord_idx >= len(lines[idx2].coords):
                                coord_idx = 0
                                idx2 += 1
                        pt_2 = lines[idx2][coord_idx]

                        # select pt closest to current intersection point
                        if LineString(
                                pt_1, i_point).length <= LineString(
                                i_point, pt_2).length:
                            self_crosses[i_point].append(pt_1[2])

                        else:
                            self_crosses[i_point].append(pt_2[2])
                        nxt_pts[i_point].append(pt_2)

                    # Extract information from self-intersecting crossovers dict and
                    # determine the angle of intersection
                    for i_pt in self_crosses:
                        cross_pts.append(
                            Point(
                                i_pt[0],
                                i_pt[1],
                                srid=proj).transform(
                                CoordTransform(
                                    SpatialReference(proj),
                                    SpatialReference(4326)),
                                True))
                        point_path_1_id.append(self_crosses[i_pt][0])
                        point_path_2_id.append(self_crosses[i_pt][1])

                        # Find the angle of self-intersection
                        change_x1 = i_pt[0] - nxt_pts[i_pt][0][0]
                        change_y1 = i_pt[1] - nxt_pts[i_pt][0][1]
                        change_x2 = i_pt[0] - nxt_pts[i_pt][1][0]
                        change_y2 = i_pt[1] - nxt_pts[i_pt][1][1]
                        angle1 = math.degrees(math.atan2(change_y1, change_x1))
                        angle2 = math.degrees(math.atan2(change_y2, change_x2))
                        angle = math.fabs(angle1 - angle2)
                        # Get the acute angle:
                        if angle > 90:
                            angle = math.fabs(180 - angle)
                            if angle > 90:
                                angle = math.fabs(180 - angle)
                        cross_angles.append(angle)

                # Check if any crossovers were found.
                if len(point_path_1_id) > 0:
                    logging.info(
                        'Crossovers for segment %s of season %s are being inserted.',
                        inSegment,
                        inSeason)
                    crossovers = []
                    # If so, package for bulk insert.
                    for i in range(len(point_path_1_id)):
                        crossovers.append(
                            models.crossovers(
                                point_path_1_id=point_path_1_id[i],
                                point_path_2_id=point_path_2_id[i],
                                angle=cross_angles[i],
                                geom=cross_pts[i]))
                    # Bulk insert found crossovers into the database.
                    _ = models.crossovers.objects.bulk_create(crossovers)
                else:
                    logging.info(
                        'No crossovers for segment %s of season %s were found.',
                        inSegment,
                        inSeason)
                
                logging.info(
                    'Segment %s of season %s has finished crossover calculation.',
                    inSegment,
                    inSeason)
                segmentsObj.crossover_calc = True
                segmentsObj.save()

            except Exception as e:
                import traceback
                tb = traceback.format_exc()
                logging.error(tb)
                return utility.errorCheck(e, sys)
            finally:
                cursor.close()

        logging.info("SUCCESS: CROSSOVER CALCULATION COMPLETED")
        return utility.response(1, 'SUCCESS: CROSSOVER CALCULATION COMPLETED.', {})

    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        try:
            logging.error(tb)
        except Exception:
            pass
        return utility.errorCheck(e, sys)


def _findKeyPoints(app, segment_id_list, segment_name_list):
    """
    Utility function to update the {app}_point_paths table in the database to mark key points.
    Key points are the points that comprise the {app}_segments geom linestring. Whenever this
    linestring is changed, this function should be called to update the point paths to match.

    Input:
        app: (str) the system who's table should be updated (e.g. "rds").
        segment_id_list: (list) a list of ID of the segments to update.
        segment_name_list: (list) a list of segment names corresponding to each segment ID for logging purposes

    """
    logging.basicConfig(
            filename=opsSettings.OPS_DATA_PATH +
            'django_logs/createPath.log',
            format='%(levelname)s :: %(asctime)s :: %(message)s',
            datefmt='%c',
            level=logging.DEBUG)
    # Set all key_points for segments to false
    sqlStr = """update {app}_point_paths set key_point=false where segment_id in %s;""".format(app=app)
    with connection.cursor() as cursor:
        cursor.execute(sqlStr, [segment_id_list])
        logging.info('Key points set to false')

    # Find key points and set to true for each segment
    for segment_id, segment_name in zip(segment_id_list, segment_name_list):
        logging.info(f'Finding key points for segment {segment_name}')
        sqlStr = """update {app}_point_paths set key_point=true
                    where id in
                    (select pp.id from {app}_point_paths pp join
                    (select st_dumppoints(geom) as seg_points from {app}_segments dseg where dseg.id=%s) seg
                    on ST_SnapToGrid(st_force2d(pp.geom), 0.000001)=ST_SnapToGrid((seg_points).geom, 0.000001)
                    where pp.segment_id=%s);""".format(app=app)
        with connection.cursor() as cursor:
            cursor.execute(sqlStr, [segment_id, segment_id])
            logging.info(f'Key points found for segment {segment_name}')

        # Recreate the segment linestring from the marked key points since finding the key points is not a perfect process
        # Sometimes, due to a precision difference in the DB (I believe), key_points do not exactly match points in the linestring
        logging.info(f'Updating segment to match key_points for segment {segment_name}')
        sqlStr = """WITH pts AS
                    (select pp.id, pp.geom
                    from {app}_point_paths pp where segment_id=%s and key_point=true order by gps_time),
                    line as (select ST_MakeLine(st_force2d(pts.geom)) as geom from pts)
                    update {app}_segments seg set geom=line.geom from line where seg.id=%s;""".format(app=app)
        with connection.cursor() as cursor:
            cursor.execute(sqlStr, [segment_id, segment_id])
            logging.info(f'Segment geom updated for segment {segment_name}')


@ipAuth()
def alterPathResolution(request):
    """ Alters a segment's resolution (vertex point spacing along line).

    Prefer simplifySegmentsResolution for a more sophisticated approach to reducing the 
    number of points. alterPathResolution is not crossover safe (see note at bottom of function).

    Input:
            segment: (string(s)) OR segment_id (integer(s))
            season: (string) name of the season for the segment(s) being altered.
            resolution: (double) number of meters between each point

    Output:
            status: (integer) 0:error 1:success 2:warning
            data: string status message
    """
    try:
        models, data, app, cookies = utility.getInput(
            request)  # get the input and models

        # Authenticate the user. Must be able to create data.
        userProfileObj, status = utility.getUserProfile(cookies)
        if status:
            if not userProfileObj.isRoot and not userProfileObj.createData:
                return utility.response(
                    0, 'ERROR: USER NOT AUTHORIZED TO CREATE DATA.', {})
        else:
            return utility.response(0, userProfileObj, {})

        # Get the input
        inSeason = data['properties']['season']

        try:
            inSegmentName = utility.forceList(data['properties']['segment'])
            segmentObjs = models.segments.objects.filter(
                name__in=inSegmentName, season__name=inSeason)
            if len(segmentObjs) == 0:
                return utility.response(
                    0, 'No segment(s) with the specified name(s) exist for the given season.', {})

        except KeyError:
            inSegmentId = utility.forceList(data['properties']['segment_id'])
            segmentObjs = models.segments.objects.filter(
                id__in=inSegmentId, season__name=inSeason)
            if len(segmentObjs) == 0:
                return utility.response(
                    0, 'No segment(s) with the specified id(s) exist for the given season.', {})

        resolution = data['properties']['resolution']

        # Perform the function logic

        messageStr = 'Resolution has successfully been altered for the following segments: '
        try:
            for segmentObj in segmentObjs:

                # Create a linepath constructed from the point paths.
                sqlStr = """WITH pts AS
                            (SELECT loc.name,
                                    ST_Force2D(pp.geom) AS geom
                            FROM {app}_point_paths pp
                            JOIN {app}_locations loc ON pp.location_id = loc.id
                            WHERE pp.segment_id = %s
                            ORDER BY gps_time)
                            SELECT DISTINCT(name),
                                ST_MakeLine(ST_Force2D(geom))
                            FROM pts
                            GROUP BY name;""".format(app=app)
                with connection.cursor() as cursor:
                    cursor.execute(sqlStr, [segmentObj.pk])
                    pointLine = cursor.fetchone()

                # determine the projection
                proj = utility.epsgFromLocation(pointLine[0])

                # Get the line object and transform to correct projection
                line = GEOSGeometry(pointLine[1])
                line.transform(proj)

                # Interpolate new points at the desired resolution
                newLine = []
                dist = 0
                while dist < line.length:
                    newLine.append(line.interpolate(dist))
                    dist = dist + resolution
                if dist < line.length:
                    newLine.append(line[-1])

                # Construct the new linestring
                newLine = LineString(newLine, srid=proj)

                # Transform the line back for storage in DB
                newLine.transform(4326)

                # Alter the segment's geometry
                segmentObj.geom = newLine
                segmentObj.save()
                messageStr += segmentObj.name + '; '

            # NOTE[Reece]: Point Paths do not exactly map to geom linestring points now due to the use of interpolation above.
            #              Attempting to find key points will only yield a few points and then the geom will be overwritten to match.
            #              Either Use a different method to find the closest points to mark as key points or don't mark key points after this method.
            #              Not marking key points means that once this function has been ran, calculating crossovers will be unreliable
            #              as a mix of geoms comprised of points in the point paths table and geoms from the segments table
            #              will be compared and these geoms will differ.
            # segment_id_list = tuple(seg["id"] for seg in segmentObjs.values())
            # segment_name_list = tuple(seg["name"] for seg in segmentObjs.values())
            # _findKeyPoints(app, segment_id_list, segment_name_list)

        except DatabaseError as dberror:
            return utility.response(0, dberror.args[0], {})

        # return the response.

        return utility.response(1, messageStr, {})

    except Exception as e:
        return utility.errorCheck(e, sys)


@ipAuth()
def simplifySegmentsResolution(request):
    """ Simplifies a segment's resolution using ST_SimplifyPreserveTopology.

    Input:
            segment: (string(s)) OR segment_id (integer(s))
            resolution: (double) number of meters of deviation from original line allowed. -1 for full resolution.

    Output:
            status: (integer) 0:error 1:success 2:warning
            data: string status message

    """
    try:
        models, data, app, cookies = utility.getInput(
            request)  # get the input and models

        # Authenticate the user. Must be able to create data.
        userProfileObj, status = utility.getUserProfile(cookies)
        if status:
            if not userProfileObj.isRoot and not userProfileObj.createData:
                return utility.response(
                    0, 'ERROR: USER NOT AUTHORIZED TO CREATE DATA.', {})
        else:
            return utility.response(0, userProfileObj, {})

        try:
            inSegmentName = utility.forceList(data['properties']['segment'])
            segmentObjs = models.segments.objects.filter(
                name__in=inSegmentName)
            if len(segmentObjs) == 0:
                return utility.response(
                    0, 'No segment(s) with the specified name(s) exist.', {})

        except KeyError:
            inSegmentId = utility.forceList(data['properties']['segment_id'])
            segmentObjs = models.segments.objects.filter(
                id__in=inSegmentId)
            if len(segmentObjs) == 0:
                return utility.response(
                    0, 'No segment(s) with the specified id(s) exist.', {})

        resolution = data['properties']['resolution']

        # Perform the function logic

        segmentsStr = ", ".join(str(seg) for seg in segmentObjs)

        logging.basicConfig(
            filename=opsSettings.OPS_DATA_PATH +
            'django_logs/createPath.log',
            format='%(levelname)s :: %(asctime)s :: %(message)s',
            datefmt='%c',
            level=logging.DEBUG)
        logging.info('Performing simplification to resolution of %s on segments %s', resolution, segmentsStr)

        messageStr = f'Resolution has successfully been altered for the following segments: {segmentsStr}'
        segment_id_list = tuple(seg["id"] for seg in segmentObjs.values())
        segment_name_list = tuple(seg["name"] for seg in segmentObjs.values())

        if resolution == -1:
            # Use all points for segment geom
            try:
                sqlStr = """with pts as (select pp.segment_id, pp.geom from {app}_point_paths pp order by gps_time),
                            line as (select pts.segment_id as seg_id, st_makeline(st_force2d(pts.geom)) as geom 
                                    from pts group by pts.segment_id having pts.segment_id in %s)
                            update {app}_segments set geom=line.geom from line   
                                where id=line.seg_id and id in %s;""".format(app=app)
                with connection.cursor() as cursor:
                    cursor.execute(sqlStr, [segment_id_list, segment_id_list])
                    logging.info('Segment geom simplification complete')

                sqlStr = """update {app}_point_paths set key_point=true where segment_id in %s;""".format(app=app)
                with connection.cursor() as cursor:
                    cursor.execute(sqlStr, [segment_id_list])
                    logging.info('Key points set to true')

            except DatabaseError as dberror:
                logging.info('Error occured during simplification: %s', repr(dberror))
                return utility.response(0, dberror.args[0], {})
        else:
            # Resolution is not -1, perform a simplification
            try:
                # perform the simplification
                sqlStr = """update {app}_segments seg set geom=simplified.geom from 
                            (select points.id as id, st_transform(st_simplifypreservetopology(st_transform(
                             st_makeline(points.geom), case -- determine epsg to project to before simplification to ensure correct units are used for resolution
                                                        when loc.name='arctic' then 3413
                                                        when loc.name='antarctic' then 3031
                                                        end
                                                                                                          ), 
                                                                  {resolution}), 4326) as geom
                             from (select st_force2d(pp.geom) as geom, seg.id as id, seg.season_id 
                                 from {app}_point_paths pp join {app}_segments seg on pp.segment_id=seg.id where seg.id in %s order by gps_time) points
                             join {app}_seasons ss on points.season_id=ss.id join {app}_locations loc on ss.location_id=loc.id
                             group by points.id, loc.name
                            ) simplified
                            where seg.id=simplified.id;""".format(app=app, resolution=resolution)
                with connection.cursor() as cursor:
                    cursor.execute(sqlStr, [segment_id_list])
                    logging.info('Segment geom simplification done. Updating key_points...')

                _findKeyPoints(app, segment_id_list, segment_name_list)

            except DatabaseError as dberror:
                logging.info('Error occured during simplification: %s', repr(dberror))
                return utility.response(0, dberror.args[0], {})

        logging.info('Simplification process complete')
        # return the response.

        return utility.response(1, messageStr, {})

    except Exception as e:
        return utility.errorCheck(e, sys)


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
    try:
        models, data, app, cookies = utility.getInput(
            request)  # get the input and models

        userProfileObj, status = utility.getUserProfile(cookies)
        if status:
            if not userProfileObj.isRoot and not userProfileObj.createData:
                return utility.response(
                    0, 'ERROR: USER NOT AUTHORIZED TO CREATE DATA.', {})
        else:
            return utility.response(0, userProfileObj, {})

        # parse the data input

        inLyrName = data['properties']['lyr_name']

        # parse the optional data input
        try:
            inLyrGroupName = data['properties']['lyr_group_name']
        except BaseException:
            inLyrGroupName = 'ungrouped'

        try:
            inLyrDescription = data['properties']['lyr_description']
        except BaseException:
            inLyrDescription = None

        try:
            inGroupStatus = data['properties']['public']
        except BaseException:
            inGroupStatus = False

        # perform the function logic

        # make sure layer name is unique (ignoring groups)
        lyrObjCount = models.layers.objects.filter(
            name=inLyrName, deleted=False).count()
        if lyrObjCount > 0:
            return utility.response(
                0,
                'ERROR: LAYER WITH THE SAME NAME EXISTS. (LAYER NAMES MUST BE UNIQUE, EVEN ACROSS GROUPS)',
                {})  # throw error, trying to create a duplicate layer

        lyrGroupsObj, isNew = models.layer_groups.objects.get_or_create(
            name=inLyrGroupName)  # get or create the layer group
        if isNew:
            lyrGroupsObj.public = inGroupStatus
            lyrGroupsObj.save(update_fields=['public'])
            # add one new entry in opsuser_userprofile_sys_layer_groups
            eval('userProfileObj.' + app + '_layer_groups.add(lyrGroupsObj.pk)')
            userProfileObj.save()

        lyrObj, isNew = models.layers.objects.get_or_create(
            name=inLyrName, layer_group_id=lyrGroupsObj.pk)  # get or create the layer

        if not isNew:  # if layer is not new and deleted, set deleted = False
            if lyrObj.deleted:
                lyrObj.deleted = False
                lyrObj.save(update_fields=['deleted'])

            else:
                return utility.response(
                    0,
                    'ERROR: LAYER WITH THE SAME NAME EXISTS (WITHIN THE GROUP) AND IS NOT DELETED',
                    {})  # throw error, trying to create a duplicate layer

        else:
            lyrObj.description = inLyrDescription
            lyrObj.save(update_fields=['description'])

        # return the output
        return utility.response(
            1, {'lyr_id': lyrObj.pk, 'lyr_group_id': lyrGroupsObj.pk}, {})

    except Exception as e:
        return utility.errorCheck(e, sys)


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
    try:
        models, data, app, cookies = utility.getInput(
            request)  # get the input and models

        # parse the data input
        inLyrName = data['properties']['lyr_name']

        # perform the function logic

        lyrObjs = models.layers.objects.get(name=inLyrName)  # get the layers object
        lyrObjs.deleted = True
        lyrObjs.save(update_fields=['deleted'])  # update the deleted field

        # return the output
        return utility.response(1, {'lyr_id': lyrObjs.pk}, {})

    except Exception as e:
        return utility.errorCheck(e, sys)


@ipAuth()
@transaction.atomic()
def createLayerPoints(request):
    """ Creates entries in layer points.

    Input:
            point_path_id: (integer or list of integers) point path ids to update or create layer points on
            lyr_name OR lyr_id: (string) name of the layer  OR (integer) id of the layer for the points
            twtt: (float or list of floats) two-way travel time of the points
            type: (integer or list of integers) pick type of the points (1:manual 2:auto)
            quality: (integer or list of integers) quality value of the points (1:good 2:moderate 3:derived)

    Output:
            status: (integer) 0:error 1:success 2:warning
            data: string status message

    """
    try:
        models, data, app, cookies = utility.getInput(
            request)  # get the input and models

        userProfileObj, status = utility.getUserProfile(cookies)
        if status:
            if not userProfileObj.isRoot and not userProfileObj.createData:
                return utility.response(
                    0, 'ERROR: USER NOT AUTHORIZED TO CREATE DATA.', {})
        else:
            return utility.response(0, userProfileObj, {})

        # parse the data input
        inPointPathIds = utility.forceList(data['properties']['point_path_id'])

        # Get the layer name or ID:
        try:
            inLyrName = data['properties']['lyr_name']
            # get the layer id
            layerId = models.layers.objects.filter(
                name=inLyrName, deleted=False).values_list(
                'pk', flat=True)[0]  # get the layer object
            if not layerId:
                return utility.response(0, 'NO LAYER BY THE GIVEN NAME FOUND', {})
        except KeyError:
            layerId = data['properties']['lyr_id']

        inTwtt = utility.forceList(data['properties']['twtt'])
        inType = utility.forceList(data['properties']['type'])
        inQuality = utility.forceList(data['properties']['quality'])
        inUserName = cookies['userName']

        # perform the function logic

        # Get the user's id:
        userObj = User.objects.get(username__exact=inUserName)

        # delete all layer points passed in
        layerPointsObj = models.layer_points.objects.filter(
            point_path_id__in=inPointPathIds, layer_id=layerId)
        if layerPointsObj.exists():
            layerPointsObj.delete()

        # build an object for bulk create
        layerPointsObjs = []
        donePointPaths = []
        for ptIdx in range(len(inPointPathIds)):
            if inTwtt[ptIdx] is None:  # prevent nan-none twtt from being inserted
                continue
            # prevent duplicate points from being inserted
            if inPointPathIds[ptIdx] in donePointPaths:
                continue
            donePointPaths.append(inPointPathIds[ptIdx])
            layerPointsObjs.append(
                models.layer_points(
                    layer_id=layerId,
                    point_path_id=inPointPathIds[ptIdx],
                    twtt=inTwtt[ptIdx],
                    type=inType[ptIdx],
                    quality=inQuality[ptIdx],
                    user_id=userObj.id))
            # Don't insert more than 500 points in a single bulk_create.
            if len(layerPointsObjs) > 500:
                try:
                    _ = models.layer_points.objects.bulk_create(layerPointsObjs)
                except IntegrityError:
                    return utility.response(0, 'ERROR: DUPLICATE LAYER POINTS.', {})
                layerPointsObjs = []

        # bulk create any remaining layer points
        if len(layerPointsObjs) > 0:
            try:
                _ = models.layer_points.objects.bulk_create(layerPointsObjs)
            except IntegrityError:
                return utility.response(0, 'ERROR: DUPLICATE LAYER POINTS.', {})

        return utility.response(1, 'SUCCESS: LAYER POINTS INSERTION COMPLETED.', {})

    except Exception as e:
        return utility.errorCheck(e, sys)


@ipAuth()
def deleteLayerPoints(request):
    """ Deletes entries from layer points.

    Input:
            start_point_path_id: (integer) the start point path id of the points for deletion
            stop_point_path_id: (integer) the stop point path id of the points for deletion
            min_twtt: (float) the minimum two-way travel time of the points for deletion
            max_twtt: (float) the maximum two-way travel time of the points for deletion
            lyr_name OR lyr_id: (string) name of the layer  OR (integer) id of the layer for the points to delete
                    OR
            start_gps_time: (float) the start gps time of the points for deletion
            stop_gps_time: (float) the stop gps time of the points for deletion
            min_twtt: (float) the minimum two-way travel time of the points for deletion
            max_twtt: (float) the maximum two-way travel time of the points for deletion
            lyr_name OR lyr_id: (string) name of the layer  OR (integer) id of the layer for the points to delete
            segment: (string) the name of the segment of the points for deletion
            season: (string) the name of the season of the points for deletion
            location: (string) the name of the location of the points for deletion

    Output:
            status: (integer) 0:error 1:success 2:warning
            data: string status message

    """
    try:
        models, data, app, cookies = utility.getInput(
            request)  # get the input and models

        # parse the data input

        inMinTwtt = data['properties']['min_twtt']
        inMaxTwtt = data['properties']['max_twtt']

        # Get the layer name or ID:
        try:
            inLyrName = data['properties']['lyr_name']
            # get the layer id
            layerId = models.layers.objects.filter(
                name=inLyrName, deleted=False).values_list(
                'pk', flat=True)[0]  # get the layer object
            if not layerId:
                return utility.response(0, 'NO LAYER BY THE GIVEN NAME FOUND', {})
        except BaseException:
            layerId = data['properties']['lyr_id']

        # parse the optional inputs
        try:
            useGpsTimes = True
            inStartGpsTime = data['properties']['start_gps_time']
            inStopGpsTime = data['properties']['stop_gps_time']
            inSegmentName = data['properties']['segment']
            inSeasonName = data['properties']['season']
            inLocationName = data['properties']['location']

        except KeyError:
            useGpsTimes = False
            inStartPointPathId = data['properties']['start_point_path_id']
            inStopPointPathId = data['properties']['stop_point_path_id']

        # perform the function logic

        if useGpsTimes:

            # To handle double precision rounding error
            inStartGpsTimeN = inStartGpsTime - Decimal(0.00001)
            inStopGpsTimeN = inStopGpsTime + Decimal(0.00001)

            # get the min/max point_path_id
            PointPathObj = models.point_paths.objects.filter(
                segment__name=inSegmentName,
                season_id__name=inSeasonName,
                location__name=inLocationName,
                gps_time__range=(
                    inStartGpsTimeN,
                    inStopGpsTimeN)).aggregate(
                Max('pk'),
                Min('pk'))
            inStartPointPathId = PointPathObj['pk__min']
            inStopPointPathId = PointPathObj['pk__max']

        # get the next possible value after properly quantizing twtt (ensures
        # boundary points are deleted)
        minTwttN = 1e-11 * math.floor(float(inMinTwtt) * 1e11 - 1)
        maxTwttN = 1e-11 * math.ceil(float(inMaxTwtt) * 1e11 + 1)

        # get the layer points objects for deletion
        layerPointsObj = models.layer_points.objects.filter(
            point_path_id__range=(
                inStartPointPathId, inStopPointPathId), twtt__range=(
                minTwttN, maxTwttN), layer_id=layerId)

        if len(layerPointsObj) == 0:

            return utility.response(
                2, 'NO LAYER POINTS WERE REMOVED. (NO POINTS MATCHED THE REQUEST)', {})

        else:

            layerPointsObj.delete()  # delete the layer points

            # return the output
            return utility.response(1, 'SUCCESS: LAYER POINTS DELETION COMPLETED.', {})

    except Exception as e:
        return utility.errorCheck(e, sys)


@ipAuth()
def deleteBulk(request):
    """ Delete data in large chunks at either the segment or season level.

    Input:
            season: (string or list of strings) name of season to delete data from
            segment: (string or list of strings) names of segments to delete. An empty string deletes all segments.
            only_layer_points: (boolean) if true only layer points are deleted
            FROM MATLAB:
                    mat: (boolean) true
                    userName: (string) username of an authenticated user (or anonymous)
                    isAuthenticated (boolean) authentication status of a user

    Output:
            status: (integer) 0:error 1:success 2:warning
            data: string status message

    If no segment is given all segments for the given season are deleted.
    If full is not given only layer points are deleted

    """
    try:
        models, data, app, cookies = utility.getInput(
            request)  # get the input and models

        # Get user profile
        userProfileObj, status = utility.getUserProfile(cookies)
        if status:
            if not userProfileObj.isRoot and not userProfileObj.bulkDeleteData:
                return utility.response(
                    0, 'ERROR: USER NOT AUTHORIZED TO BULK DELETE DATA.', {})
        else:
            return utility.response(0, userProfileObj, {})

        # parse the data input

        inSeasonNames = utility.forceList(data['properties']['season'])

        inSegmentNames = utility.forceList(data['properties']['segment'])

        deleteOnlyLayerPoints = utility.forceBool(
            data['properties']['only_layer_points'])

        # Get all the segments if no segments passed in
        if len(inSegmentNames) == 1 and not inSegmentNames[0]:
            inSegmentNames = models.segments.objects.filter(
                season__name__in=inSeasonNames).values_list(
                'name', flat=True)  # get all the segments for the given seasons

        # Delete layer points
        _ = models.layer_points.objects.filter(
            point_path__season__name__in=inSeasonNames,
            point_path__segment__name__in=inSegmentNames).delete()

        # Delete segments as well if user requested
        if not deleteOnlyLayerPoints:

            _ = models.segments.objects.filter(
                name__in=inSegmentNames,
                season__name__in=inSeasonNames).delete()  # delete segments

            if not models.segments.objects.filter(season__name__in=inSeasonNames):

                # delete seasons (if there are no segments left for the specified
                # seasons)
                _ = models.seasons.objects.filter(name__in=inSeasonNames).delete()

        # return the output
        return utility.response(1, 'SUCCESS: BULK DELETION COMPLETED', {})

    except Exception as e:
        return utility.errorCheck(e, sys)


@ipAuth()
def releaseLayerGroup(request):
    """ Sets the status of a layer group to public.

    Input:
            lyr_group_name: (string) name of the layer group

    Output:
            status: (integer) 0:error 1:success 2:warning
            data: string status message

    """
    try:
        models, data, app, cookies = utility.getInput(
            request)  # get the input and models

        # parse the data input

        inLyrGroupName = data['properties']['lyr_group_name']

        # perform the function logic

        # update the groups public status
        lyrGroupsObj = models.layer_groups.objects.filter(
            name=inLyrGroupName).update(public=True)

        # return the output
        return utility.response(1, 'SUCCESS: LAYER GROUP IS NOW PUBLIC', {})

    except Exception as e:
        return utility.errorCheck(e, sys)

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
                    OR
            point_path_id: (integer, list of integers) point path ids for output points

    Output:
            status: (integer) 0:error 1:success 2:warning
            data:
                    id: (integer) id of point path/s
                    gps_time: (float) gps time of point path/s
                    elev: (float) elev of point path/s
                    X: (float) x value of point path/s
                    Y: (float) y value of point path/s

    """
    try:
        models, data, app, cookies = utility.getInput(
            request)  # get the input and models

        # parse the data input
        try:
            # parse the data input
            usePointPathIds = True
            inPointPathIds = data['properties']['point_path_id']
        except KeyError:
            usePointPathIds = False

        inLocationName = data['properties']['location']

        if not usePointPathIds:
            inSeasonName = data['properties']['season']
            # To handle double precision rounding error
            inStartGpsTime = data['properties']['start_gps_time'] - Decimal(0.00001)
            inStopGpsTime = data['properties']['stop_gps_time'] + Decimal(0.00001)

        # parse optional inputs
        try:
            nativeGeom = utility.forceBool(data['properties']['nativeGeom'])
        except KeyError:
            nativeGeom = False

        # Perform the function logic
        # get epsg for the input location
        epsg = utility.epsgFromLocation(inLocationName)

        if not usePointPathIds:
            # get point paths based on input
            if nativeGeom:
                pointPathsObj = models.point_paths.objects.filter(
                    season_id__name=inSeasonName,
                    location_id__name=inLocationName,
                    gps_time__gte=inStartGpsTime,
                    gps_time__lte=inStopGpsTime).order_by('gps_time').values_list(
                    'pk',
                    'gps_time',
                    'geom')
            else:
                pointPathsObj = models.point_paths.objects.filter(
                    season_id__name=inSeasonName,
                    location_id__name=inLocationName,
                    gps_time__gte=inStartGpsTime,
                    gps_time__lte=inStopGpsTime).order_by('gps_time').values_list(
                    'pk',
                    'gps_time',
                    'geom')
                for pnt in pointPathsObj:  # Transform the geom value to the correct epsg
                    pnt[2].transform(epsg)
        else:
            if nativeGeom:
                pointPathsObj = models.point_paths.objects.filter(
                    id__in=inPointPathIds,
                    location_id__name=inLocationName).order_by('gps_time').values_list(
                    'pk',
                    'gps_time',
                    'geom')
            else:
                pointPathsObj = models.point_paths.objects.filter(
                    id__in=inPointPathIds,
                    location_id__name=inLocationName).order_by('gps_time').values_list(
                    'pk',
                    'gps_time',
                    'geom')
                for pnt in pointPathsObj:  # Transform the geom value to the correct epsg
                    pnt[2].transform(epsg)

        # unzip the data for output
        pks, gpsTimes, pointPaths = list(zip(*pointPathsObj))
        xCoords, yCoords, elev = list(zip(*pointPaths))

        # return the output
        return utility.response(1,
                                {'id': pks,
                                 'gps_time': gpsTimes,
                                 'elev': elev,
                                 'X': xCoords,
                                 'Y': yCoords},
                                {})

    except Exception as e:
        return utility.errorCheck(e, sys)


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
    try:
        models, data, app, cookies = utility.getInput(
            request)  # get the input and models

        # parse the data input
        inLocationName = data['properties']['location']
        inPointX = data['properties']['x']
        inPointY = data['properties']['y']

        # parse the optional data input
        try:
            inSeasonNames = utility.forceTuple(data['properties']['season'])
            useAllSeasons = False
        except KeyError:
            useAllSeasons = True

        try:
            inStartSeg = data['properties']['startseg']
            inStopSeg = data['properties']['stopseg']
        except KeyError:
            inStartSeg = '00000000_00'
            inStopSeg = '99999999_99'

        # Perform the function logic

        # Get all of the season names if useAllSeasons=True
        if useAllSeasons:
            inSeasonNames = utility.forceTuple(
                list(
                    models.seasons.objects.filter(
                        location_id__name=inLocationName,
                        season_group__public=True).values_list(
                        'name',
                        flat=True)))  # get all the public seasons

        epsg = utility.epsgFromLocation(inLocationName)  # get the input epsg

        # Get the location id
        location_id = models.locations.objects.filter(
            name=inLocationName).values_list(
            'pk', flat=True)[0]

        # Prepare the input point as text for ST_GeomFromText
        pointTxt = 'POINT(%s %s)' % (inPointX, inPointY)

        try:
            # Get the closest frame to the input point as a linestring.
            queryStr = """
            WITH pt AS
            (
                    SELECT   pp.frame_id
                    FROM     {app}_point_paths pp
                    JOIN     {app}_seasons ss
                    ON       pp.season_id=ss.id
                    WHERE    ss.NAME IN %s
                    AND      pp.location_id = %s
                    ORDER BY st_transform(pp.geom,%s) <-> st_geomfromtext(%s,%s) limit 1)
            SELECT   ss.NAME,
                    pp.segment_id,
                    min(pp.gps_time),
                    max(pp.gps_time),
                    frm.NAME,
                    st_makeline(st_transform(st_geomfromtext('POINTZ('
                            || st_x(pp.geom)
                            || ' '
                            || st_y(pp.geom)
                            || ' '
                            || pp.gps_time
                            ||')',4326),%s))
            FROM     pt,
                    {app}_point_paths pp
            JOIN     {app}_seasons ss
            ON       pp.season_id=ss.id
            JOIN     {app}_frames frm
            ON       pp.frame_id=frm.id
            WHERE    pt.frame_id = pp.frame_id
            GROUP BY ss.NAME,
                    pp.segment_id,
                    frm.NAME;
            """.format(app=app)
            with connection.cursor() as cursor:
                cursor.execute(
                    queryStr, [
                    inSeasonNames, location_id, epsg, pointTxt, epsg, epsg])
                closestFrame = cursor.fetchone()
        except DatabaseError as dberror:
            return utility.response(0, dberror.args[0], {})

        # Extract x,y, and gps_time from linestring
        xCoords, yCoords, gpsTimes = list(zip(*GEOSGeometry(closestFrame[-1])))

        # Sort the results.
        xCoords = [x for (gps, x) in sorted(zip(gpsTimes, xCoords))]
        yCoords = [y for (gps, y) in sorted(zip(gpsTimes, yCoords))]
        gpsTimes = sorted(gpsTimes)

        # build the echogram image urls list
        outEchograms = utility.buildEchogramList(app, closestFrame[0], closestFrame[4])

        # returns the output
        return utility.response(1,
                                {'season': closestFrame[0],
                                 'segment_id': closestFrame[1],
                                    'start_gps_time': closestFrame[2],
                                    'stop_gps_time': closestFrame[3],
                                    'frame': closestFrame[4],
                                    'echograms': outEchograms,
                                    'X': xCoords,
                                    'Y': yCoords,
                                    'gps_time': gpsTimes},
                                {})

    except Exception as e:
        return utility.errorCheck(e, sys)


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
    try:
        models, data, app, cookies = utility.getInput(
            request)  # get the input and models

        # perform function logic

        # get the user profile
        userProfileObj, status = utility.getUserProfile(cookies)

        # get the layers objects
        if userProfileObj.isRoot:
            layersObj = models.layers.objects.select_related('layer_group__name').filter(
                deleted=False).order_by('pk').values_list('pk', 'name', 'layer_group__name')
        else:
            authLayerGroups = eval(
                'userProfileObj.' +
                app +
                '_layer_groups.values_list("name",flat=True)')
            layersObj = models.layers.objects.select_related('layer_group__name').filter(
                deleted=False, layer_group__name__in=authLayerGroups).order_by('pk').values_list(
                'pk', 'name', 'layer_group__name')

        # unzip layers
        outLayersObj = list(zip(*layersObj))

        # return the output
        return utility.response(1,
                                {'lyr_id': outLayersObj[0],
                                 'lyr_name': outLayersObj[1],
                                    'lyr_group_name': outLayersObj[2]},
                                {})

    except Exception as e:
        return utility.errorCheck(e, sys)


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
    try:
        models, data, app, cookies = utility.getInput(
            request)  # get the input and models

        try:
            # parse the data input
            usePointPathIds = True
            inPointPathIds = data['properties']['point_path_id']
        except KeyError:
            usePointPathIds = False

        inLocationName = data['properties']['location']
        inSeasonName = data['properties']['season']

        # parse optional inputs (dependent of point_path_id)

        try:
            segName = False
            inSegment = data['properties']['segment_id']
        except KeyError:
            segName = True
            inSegment = data['properties']['segment']

        try:
            useAllGps = False
            # To handle double precision rounding error
            inStartGpsTime = data['properties']['start_gps_time'] - Decimal(0.00001)
            inStopGpsTime = data['properties']['stop_gps_time'] + Decimal(0.00001)
        except KeyError:
            useAllGps = True

        # parse additional optional inputs (not dependent on point_path_id)
        try:
            useAllLyr = False
            inLyrNames = utility.forceList(data['properties']['lyr_name'])
        except KeyError:
            useAllLyr = True

        try:
            returnGeom = True
            inGeomType = data['properties']['return_geom']
            if inGeomType == 'proj':
                inLocationName = data['properties']['location']
        except KeyError:
            returnGeom = False

        # perform function logic

        if not usePointPathIds:
            # get a segment object with a pk field
            if segName:
                segmentId = models.segments.objects.filter(
                    name=inSegment, season__name=inSeasonName).values_list(
                    'pk', flat=True)
                if segmentId.exists():
                    segmentId = segmentId[0]
                else:
                    return utility.response(0, 'ERROR: SEGMENT DOES NOT EXIST.', {})
            else:
                segmentId = inSegment

            # get the point path ids
            if useAllGps:
                inPointPathIds = models.point_paths.objects.filter(
                    segment_id=segmentId, location__name=inLocationName).values_list(
                    'pk', flat=True)
            else:

                inPointPathIds = models.point_paths.objects.filter(
                    segment_id=segmentId,
                    location__name=inLocationName,
                    gps_time__range=(
                        inStartGpsTime,
                        inStopGpsTime)).values_list(
                    'pk',
                    flat=True)

        # get the user profile
        userProfileObj, status = utility.getUserProfile(cookies)
        authLayerGroups = eval(
            'userProfileObj.' +
            app +
            '_layer_groups.values_list("pk",flat=True)')

        # get a layers object
        if useAllLyr:
            if userProfileObj.isRoot:
                layerIds = models.layers.objects.filter(
                    deleted=False).values_list('pk', flat=True)
            else:
                layerIds = models.layers.objects.filter(
                    deleted=False, layer_group__in=authLayerGroups).values_list(
                    'pk', flat=True)
        else:
            if userProfileObj.isRoot:
                layerIds = models.layers.objects.filter(
                    name__in=inLyrNames, deleted=False).values_list(
                    'pk', flat=True)
            else:
                layerIds = models.layers.objects.filter(
                    name__in=inLyrNames,
                    deleted=False,
                    layer_group__in=authLayerGroups).values_list(
                    'pk',
                    flat=True)

        if not returnGeom:
            # get a layer points object (no geometry)
            layerPointsObj = models.layer_points.objects.select_related('point_path__gps_time').filter(
                point_path_id__in=inPointPathIds, layer_id__in=layerIds).values_list(
                'point_path', 'layer_id', 'point_path__gps_time', 'twtt', 'type', 'quality')

            if len(layerPointsObj) == 0:
                return utility.response(
                    2, 'WARNING: NO LAYER POINTS FOUND FOR THE GIVEN PARAMETERS.', {})

            layerPoints = list(zip(*layerPointsObj))  # unzip the layerPointsObj
            # return the output
            return utility.response(1,
                                    {'point_path_id': layerPoints[0],
                                     'lyr_id': layerPoints[1],
                                        'gps_time': layerPoints[2],
                                        'twtt': layerPoints[3],
                                        'type': layerPoints[4],
                                        'quality': layerPoints[5]},
                                    {})

        else:
            # get a layer points object (with geometry)
            layerPointsObj = models.layer_points.objects.select_related(
                'point_path__gps_time',
                'point_path__geom').filter(
                point_path_id__in=inPointPathIds,
                layer_id__in=layerIds).values_list(
                'point_path',
                'layer_id',
                'point_path__gps_time',
                'twtt',
                'type',
                'quality',
                'point_path__geom')

            if len(layerPointsObj) == 0:
                return utility.response(
                    2, 'WARNING: NO LAYER POINTS FOUND FOR THE GIVEN PARAMETERS.', {})

            pointPathId, layerIds, gpsTimes, twtts, types, qualitys, pointPaths = list(
                zip(*layerPointsObj))  # unzip the layerPointsObj

            outLon = []
            outLat = []
            outElev = []
            if inGeomType == 'proj':
                epsg = utility.epsgFromLocation(inLocationName)  # get the input epsg
            for pointObj in pointPaths:
                ptGeom = GEOSGeometry(pointObj)
                if inGeomType == 'proj':
                    ptGeom.transform(epsg)
                outLon.append(ptGeom.x)
                outLat.append(ptGeom.y)
                outElev.append(ptGeom.z)

            # return the output
            return utility.response(1,
                                    {'point_path_id': pointPathId,
                                     'lyr_id': layerIds,
                                     'gps_time': gpsTimes,
                                     'twtt': twtts,
                                     'type': types,
                                     'quality': qualitys,
                                     'lon': outLon,
                                     'lat': outLat,
                                     'elev': outElev},
                                    {})

    except Exception as e:
        return utility.errorCheck(e, sys)


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

    KNOWN ISSUE: inSeasons is not actually used to restrict query

    """
    try:
        models, data, app, cookies = utility.getInput(
            request)  # get the input and models

        # parse the data input

        inLocationName = data['properties']['location']
        inBoundaryWkt = data['properties']['bound']

        # parse the optional data input
        try:
            inStartSeg = data['properties']['startseg']
            inStopSeg = data['properties']['stopseg']
        except BaseException:
            inStartSeg = '00000000_00'
            inStopSeg = '99999999_99'

        inStartDateStr = inStartSeg.split("_")[0]
        inStopDateStr = inStopSeg.split("_")[0]
        inStartDate = datetime.datetime.strptime(inStartDateStr, '%Y%m%d')
        inStopDate = datetime.datetime.strptime(inStopDateStr, '%Y%m%d')

        try:
            inSeasons = utility.forceList(data['properties']['season'])
        except BaseException:
            inSeasons = models.seasons.objects.filter(
                season_group__public=True).values_list(
                'name', flat=True)

        try:
            getAllPoints = data['properties']['allPoints']
        except BaseException:
            getAllPoints = False

        # perform function logic
        # Get location id
        locationId = models.locations.objects.filter(
            name=inLocationName).values_list(
            'pk', flat=True)[0]

        try:
            # Construct query string
            sqlStr = """WITH surflp
                        AS
                        (
                                SELECT lp.twtt,
                                        lp.type,
                                        lp.quality,
                                        lp.point_path_id
                                FROM   {app}_layer_points lp
                                WHERE  lp.layer_id = 1), botlp
                        AS
                        (
                                SELECT lp.twtt,
                                        lp.type,
                                        lp.quality,
                                        lp.point_path_id
                                FROM   {app}_layer_points lp
                                WHERE  lp.layer_id = 2)
                        SELECT st_y(pp.geom) lat,
                                st_x(pp.geom) lon,
                                st_z(pp.geom) elevation,
                                pp.roll,
                                pp.pitch,
                                pp.heading,
                                pp.gps_time,
                                surflp.twtt*({half_c})                                                                                        surface,
                                surflp.twtt*({half_c}) + ((botlp.twtt-surflp.twtt)*({half_c}/sqrt(3.15)))                                      bottom,
                                abs((surflp.twtt*({half_c})) - (surflp.twtt*({half_c}) + ((botlp.twtt-surflp.twtt)*({half_c}/sqrt(3.15))))) thickness,
                                surflp.type,
                                botlp.type,
                                surflp.quality,
                                botlp.quality,
                                s.name   season,
                                frm.name frame
                        FROM   {app}_point_paths pp
                        JOIN   surflp
                        ON     pp.id=surflp.point_path_id
                        {LEFT} JOIN   botlp
                        ON     pp.id=botlp.point_path_id
                        JOIN
                                (
                                        SELECT id,
                                            name,
                                            season_group_id
                                        FROM   {app}_seasons
                                        WHERE  season_group_id=1) AS s
                        ON     s.id=pp.season_id
                        JOIN   {app}_frames frm
                        ON     frm.id=pp.frame_id
                        WHERE  pp.location_id = %s
                        AND    st_within(pp.geom,st_geomfromtext(%s,4326));""".format(app=app, LEFT="LEFT" if getAllPoints else "", half_c="299792458.0/2")

            # Query the database and fetch results
            with connection.cursor() as cursor:
                cursor.execute(sqlStr, [locationId, inBoundaryWkt])
                data = cursor.fetchall()

        except DatabaseError as dberror:
            return utility.response(0, dberror.args[0], {})

        # generate the output csv information
        serverDir = opsSettings.OPS_DATA_PATH + 'data/csv/'
        webDir = 'data/csv/'
        if getAllPoints:
            tmpFn = 'OPS_CReSIS_L2_CSV_' + utility.randId(10) + '.csv'
        else:
            tmpFn = 'OPS_CReSIS_L2_CSV_GOOD_' + utility.randId(10) + '.csv'
        webFn = webDir + tmpFn
        serverFn = serverDir + tmpFn

        # create the csv header
        csvHeader = [
            'LAT',
            'LON',
            'ELEVATION',
            'ROLL',
            'PITCH',
            'HEADING',
            'UTCSOD',
            'UTCDATE',
            'SURFACE',
            'BOTTOM',
            'THICKNESS',
            'SURFACE_TYPE',
            'BOTTOM_TYPE',
            'SURFACE_QUALITY',
            'BOTTOM_QUALITY',
            'SEASON',
            'FRAME']

        # write the csv file
        with open(serverFn, 'w') as csvFile:
            csvWriter = csv.writer(csvFile, delimiter=',', quoting=csv.QUOTE_NONE)
            csvWriter.writerow(csvHeader)
            for row in data:

                # calculate utc date and seconds of day
                utcDateStruct = time.gmtime(row[6])
                rowDateTime = datetime.datetime.fromtimestamp(row[6])
                outUtcDate = time.strftime('%Y%m%d', utcDateStruct)
                outUtcSod = float(
                    utcDateStruct.tm_hour *
                    3600.0 +
                    utcDateStruct.tm_min *
                    60.0 +
                    utcDateStruct.tm_sec)

                if not (inStartDate <= rowDateTime <= inStopDate):
                    continue  # Filter between start and stop dates provided

                # Account for surfaces without bottom values
                if row[8] is None:
                    bottom = np.nan
                    thick = np.nan
                    bott_type = np.nan
                    bott_quality = np.nan
                else:
                    bottom = row[8]
                    thick = row[9]
                    bott_type = row[11]
                    bott_quality = row[13]

                # Write the row to file.
                csvWriter.writerow([
                    "%.8f" % row[0],
                    "%.8f" % row[1],
                    "%.5f" % row[2],
                    "%.5f" % row[3],
                    "%.5f" % row[4],
                    "%.5f" % row[5],
                    "%.3f" % outUtcSod,
                    outUtcDate,
                    "%.3f" % row[7],
                    "%.3f" % bottom,
                    "%.3f" % thick,
                    row[10],
                    bott_type,
                    row[12],
                    bott_quality,
                    row[14],
                    row[15],
                ])

        # return the output
        return utility.response(1, webFn, {})

    except Exception as e:
        return utility.errorCheck(e, sys)


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
    try:
        models, data, app, cookies = utility.getInput(
            request)  # get the input and models

        # parse the data input

        inLocationName = data['properties']['location']
        inBoundaryWkt = data['properties']['bound']

        # parse the optional data input
        try:
            inStartSeg = data['properties']['startseg']
            inStopSeg = data['properties']['stopseg']
        except BaseException:
            inStartSeg = '00000000_00'
            inStopSeg = '99999999_99'

        try:
            inSeasonNames = utility.forceList(data['properties']['season'])
            useAllSeasons = False
        except BaseException:
            useAllSeasons = True

        # perform function logic

        if useAllSeasons:

            inSeasonNames = models.seasons.objects.filter(
                location_id__name=inLocationName, season_group__public=True).values_list(
                'name', flat=True)  # get all the public seasons

        # create a polygon geometry object
        inPoly = GEOSGeometry(inBoundaryWkt, srid=4326)

        # get the segments object
        segmentsObj = models.segments.objects.filter(
            season_id__name__in=inSeasonNames, name__range=(
                inStartSeg, inStopSeg), geom__intersects=inPoly).values_list(
            'name', 'geom')

        segmentNames, segmentPaths = list(zip(*segmentsObj))  # unzip the segmentsObj
        del segmentsObj

        kmlObj = simplekml.Kml()  # create a new kml object
        kmlDoc = kmlObj.newdocument(
            name='OPS CReSIS KML DATA')  # create a new kml document

        # add the segments as linestrings to the kml document
        for segIdx in range(len(segmentNames)):
            newLineString = kmlDoc.newlinestring(name=segmentNames[segIdx])
            newLineString.coords = list(segmentPaths[segIdx].coords)
            newLineString.style.linestyle.color = simplekml.Color.blue

        # generate the output kml information
        serverDir = opsSettings.OPS_DATA_PATH + 'data/kml/'
        webDir = 'data/kml/'
        tmpFn = 'OPS_CReSIS_L2_KML_' + utility.randId(10) + '.kml'
        webFn = webDir + tmpFn
        serverFn = serverDir + tmpFn

        kmlObj.save(serverFn)  # save the kml

        # return the output
        return utility.response(1, webFn, {})

    except Exception as e:
        return utility.errorCheck(e, sys)


def getFramesWithinPolygon(request):
    """ Return the list of frames located inside a WKT polygon boundary.

    Input:
            bound: (WKT) well-known text polygon geometry (WGS84)
            location: (string) name of the location

    Optional Inputs:
            season: (string or list of string) a/ season name to limit the output

    Output:
            status: (integer) 0:error 1:success 2:warning
            data:  List of frames, ordered by segments

    """

    try:
        models, data, app, cookies = utility.getInput(
            request)  # get the input and models

        # parse the data input
        inLocationName = data['properties']['location']
        inBoundaryWkt = data['properties']['bound']

        # parse the optional data input
        try:
            inSeasonNames = utility.forceList(data['properties']['season'])
            useAllSeasons = False
        except BaseException:
            useAllSeasons = True

        # perform function logic

        if useAllSeasons:
            inSeasonNames = models.seasons.objects.filter(
                location_id__name=inLocationName,
                season_group__public=True).values_list(
                'name',
                flat=True)

        inPoly = GEOSGeometry(inBoundaryWkt, srid=4326)

        # get the segments/frames object
        frameNames = models.point_paths.objects.select_related('frames__name').filter(
            season_id__name__in=inSeasonNames,
            geom__within=inPoly).order_by('frame').distinct('frame').values_list(
            'frame__name',
            flat=True)

        frameNames = list(frameNames)

        if len(frameNames) == 0:
            return utility.response(
                2, "WARNING: THERE ARE NO FRAMES IN THIS POLYGON.", {})
        else:
            return utility.response(1, {'frame': list(frameNames)}, {})

    except Exception as e:
        return utility.errorCheck(e, sys)


def getPointsWithinPolygon(request):
    """ Return the list of points located inside a WKT polygon boundary.

    Input:
            bound: (WKT) well-known text polygon geometry (WGS84)
            location: (string) name of the location

    Optional Inputs:
            season: (string or list of string) a/ season name to limit the output

    Output:
            status: (integer) 0:error 1:success 2:warning
            data:  List of points, ordered by segments

    KNOWN ISSUE: inSeasonsNames is not actually used to restrict query

    """

    try:
        models, data, app, cookies = utility.getInput(
            request)  # get the input and models

        # parse the data input
        inLocationName = data['properties']['location']
        inBoundaryWkt = data['properties']['bound']

        # parse the optional data input
        try:
            inSeasonNames = utility.forceList(data['properties']['season'])
            useAllSeasons = False
        except BaseException:
            useAllSeasons = True

        # perform function logic
        # Get location id
        locationId = models.locations.objects.filter(
            name=inLocationName).values_list(
            'pk', flat=True)[0]

        try:
            sqlStr = """WITH surflp AS
                        (SELECT lp.twtt,
                                lp.type,
                                lp.quality,
                                lp.point_path_id
                        FROM {app}_layer_points lp
                        WHERE lp.layer_id = 1),
                            botlp AS
                        (SELECT lp.twtt,
                                lp.type,
                                lp.quality,
                                lp.point_path_id
                        FROM {app}_layer_points lp
                        WHERE lp.layer_id = 2)
                        SELECT ST_Y(pp.geom) LAT,
                            ST_X(pp.geom) LON,
                            ST_Z(pp.geom) ELEVATION,
                            pp.gps_time,
                            surflp.twtt*({half_c}) surface,
                            surflp.twtt*({half_c}) + ((botlp.twtt-surflp.twtt)*({half_c}/sqrt(3.15))) bottom,
                            ABS((surflp.twtt*({half_c})) - (surflp.twtt*({half_c}) + ((botlp.twtt-surflp.twtt)*({half_c}/sqrt(3.15))))) thickness,
                            surflp.quality,
                            botlp.quality,
                            s.name SEASON,
                            frm.name FRAME
                        FROM {app}_point_paths pp
                        JOIN surflp ON pp.id=surflp.point_path_id
                        LEFT JOIN botlp ON pp.id=botlp.point_path_id
                        JOIN {app}_seasons s ON s.id=pp.season_id
                        JOIN {app}_frames frm ON frm.id=pp.frame_id
                        WHERE pp.location_id = %s
                        AND ST_Within(pp.geom, ST_GeomFromText(%s, 4326));""".format(app=app, half_c="299792458.0/2")

            # Query the database and fetch results
            with connection.cursor() as cursor:
                cursor.execute(sqlStr, [locationId, inBoundaryWkt])
                data = cursor.fetchall()

        except DatabaseError as dberror:
            return utility.response(0, dberror.args[0], {})

        if len(data) == 0:
            return utility.response(
                2, "WARNING: THERE ARE NO POINTS IN THIS POLYGON.", {})
        else:
            layerPoints = list(zip(*data))  # unzip the layerPointsObj
            # return the output
            return utility.response(1,
                                    {'Lat': layerPoints[0],
                                     'Lon': layerPoints[1],
                                        'Elevation': layerPoints[2],
                                        'Gps_Time': layerPoints[3],
                                        'Surface': layerPoints[4],
                                        'Bottom': layerPoints[5],
                                        'Thickness': layerPoints[6],
                                        'Surface_Quality': layerPoints[7],
                                        'Bottom_Quality': layerPoints[8],
                                        'Season': layerPoints[9],
                                        'Frame': layerPoints[10]},
                                    {})

    except Exception as e:
        return utility.errorCheck(e, sys)


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
    try:
        models, data, app, cookies = utility.getInput(
            request)  # get the input and models

        # parse the data input

        inLocationName = data['properties']['location']
        inBoundaryWkt = data['properties']['bound']

        # parse the optional data input
        try:
            inStartSeg = data['properties']['startseg']
            inStopSeg = data['properties']['stopseg']
        except BaseException:
            inStartSeg = '00000000_00'
            inStopSeg = '99999999_99'

        try:
            inLayers = utility.forceList(data['properties']['layers'])
        except BaseException:
            inLayers = models.layers.objects.filter(
                layer_group__public=True, name='surface').values_list(
                'name', flat=True)

        try:
            inSeasons = utility.forceList(data['properties']['season'])
        except BaseException:
            inSeasons = models.seasons.objects.filter(
                season_group__public=True).values_list(
                'name', flat=True)

        # perform the function logic

        # make sure surface and bottom are in the layers list
        if 'surface' not in inLayers:
            inLayers.append('surface')

        # create a polygon geometry object
        inPoly = GEOSGeometry(inBoundaryWkt, srid=4326)

        # get the point paths that match the input filters
        pointPathsObj = models.point_paths.objects.select_related(
            'season__name',
            'frame__name').filter(
            location__name=inLocationName,
            season__name__in=inSeasons,
            segment__name__range=(
                inStartSeg,
                inStopSeg),
            geom__within=inPoly).order_by(
                'frame__name',
                'gps_time').values_list(
                    'pk',
                    'gps_time',
                    'roll',
                    'pitch',
                    'heading',
                    'geom',
                    'season__name',
                    'frame__name')[
                        :2000000]

        # unzip the pointPathsObj into lists of values
        ppIds, ppGpsTimes, ppRolls, ppPitchs, ppHeadings, ppPaths, ppSeasonNames, ppFrameNames = list(
            zip(*pointPathsObj))
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
        layerPointsObj = models.layer_points.objects.select_related('layer__name').filter(
            point_path_id__in=ppIds, layer_id__name__in=inLayers).values_list(
            'pk', 'layer_id', 'point_path_id', 'twtt', 'type', 'quality', 'layer__name')

        # unzip the layerPointsObj into lists of values
        lpIds, lpLyrIds, lpPpIds, lpTwtts, lpTypes, lpQualitys, lpLyrNames = list(
            zip(*layerPointsObj))
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
        outLayers['surface'] = {
            'name': 'surface', 'elev': np.empty(
                0, dtype='float64'), 'type': np.empty(
                0, dtype='float16'), 'quality': np.empty(
                0, dtype='float16')}

        # write the rest of the layers to the output structure
        for lyrName in list(set(lpLyrNames)):
            if lyrName not in ['surface']:
                outLayers[str(lyrName)] = {'name': str(lyrName), 'elev': np.empty(
                    0, dtype='float64'), 'type': np.empty(0, dtype='float16'), 'quality': np.empty(0, dtype='float16')}

        # create additional output arrays
        outLat = np.empty(0, dtype='float64')
        outLon = np.empty(0, dtype='float64')
        outElev = np.empty(0, dtype='float64')
        outRoll = np.empty(0, dtype='float64')
        outPitch = np.empty(0, dtype='float64')
        outHeading = np.empty(0, dtype='float64')
        outSeason = np.empty(0, dtype=object)
        outFrame = np.empty(0, dtype=object)
        outUtcSod = np.empty(0, dtype='float64')
        outUtcDate = np.empty(0, dtype=object)

        # set up count for point paths with no surface
        noSurfaceCount = 0

        # process the data for each point path
        for ppIdx, ppId in enumerate(ppIds):

            # find the layer points for the current point path
            lpPpIdxs = [idx for idx in range(len(lpPpIds)) if lpPpIds[idx] == ppId]

            if not lpPpIdxs:  # make sure there are layer points for the point path
                continue

            # get the layer names, and layer point indexes for each layer point found
            lpPpLyrNames, lpIdx = list(
                zip(*[[lpLyrNames[idx], idx] for idx in lpPpIdxs]))

            # if there is a surface in the found layer names write the output
            if 'surface' in lpPpLyrNames:

                # append point path information to the output arrays
                outLat = np.append(outLat, float(ppPaths[ppIdx].x))
                outLon = np.append(outLon, float(ppPaths[ppIdx].y))
                outElev = np.append(outElev, float(ppPaths[ppIdx].z))
                outRoll = np.append(outRoll, float(ppRolls[ppIdx]))
                outPitch = np.append(outPitch, float(ppPitchs[ppIdx]))
                outHeading = np.append(outHeading, float(ppHeadings[ppIdx]))
                outSeason = np.append(outSeason, ppSeasonNames[ppIdx])
                outFrame = np.append(outFrame, ppFrameNames[ppIdx])

                # calculate utc date and seconds of day
                utcDateStruct = time.gmtime(ppGpsTimes[ppIdx])
                outUtcDate = np.append(
                    outUtcDate, time.strftime(
                        '%Y%m%d', utcDateStruct))
                outUtcSod = np.append(
                    outUtcSod,
                    float(
                        utcDateStruct.tm_hour *
                        3600.0 +
                        utcDateStruct.tm_min *
                        60.0 +
                        utcDateStruct.tm_sec))

                # write the surface record to the output layers structure
                surfTwtt = lpTwtts[lpIdx[lpPpLyrNames.index('surface')]]
                surfRange, _ = utility.twttToRange(surfTwtt, surfTwtt)
                outLayers['surface']['elev'] = np.append(
                    outLayers['surface']['elev'], float(surfRange))
                outLayers['surface']['type'] = np.append(
                    outLayers['surface']['type'], lpTypes[lpPpLyrNames.index('surface')])
                outLayers['surface']['quality'] = np.append(
                    outLayers['surface']['quality'], lpQualitys[lpPpLyrNames.index('surface')])

                # write each additional (non-surface) records to the output layers
                # structure
                for lyrName in set(lpLyrNames):
                    if lyrName not in ['surface']:  # write the records (data or nans)
                        if lyrName in lpPpLyrNames:
                            lyrTwtt = lpTwtts[lpIdx[lpPpLyrNames.index(lyrName)]]
                            _, lyrRange = utility.twttToRange(surfTwtt, lyrTwtt)
                            outLayers[lyrName]['elev'] = np.append(
                                outLayers[lyrName]['elev'], float(lyrRange))
                            outLayers[lyrName]['type'] = np.append(
                                outLayers[lyrName]['type'], lpTypes[lpPpLyrNames.index(lyrName)])
                            outLayers[lyrName]['quality'] = np.append(
                                outLayers[lyrName]['quality'], lpQualitys[lpPpLyrNames.index(lyrName)])
                        else:
                            outLayers[lyrName]['elev'] = np.append(
                                outLayers[lyrName]['elev'], np.nan)
                            outLayers[lyrName]['type'] = np.append(
                                outLayers[lyrName]['type'], np.nan)
                            outLayers[lyrName]['quality'] = np.append(
                                outLayers[lyrName]['quality'], np.nan)
            else:
                noSurfaceCount += 1  # no surface exists

        # make sure there was some data
        if noSurfaceCount == len(ppIds):
            return utility.response(
                0, 'ERROR: NO DATA FOUND THAT MATCHES THE SEARCH PARAMETERS', {})

        # clear some memory
        del lpIds, lpLyrIds, lpPpIds, lpTwtts, lpTypes, lpQualitys, ppIds, ppGpsTimes, ppRolls, ppPitchs, ppHeadings, ppPaths, ppSeasonNames, ppFrameNames, lpLyrNames, lpPpLyrNames

        # generate the output mat information
        serverDir = opsSettings.OPS_DATA_PATH + 'data/mat/'
        webDir = 'data/mat/'
        tmpFn = 'OPS_CReSIS_L2_MAT_' + utility.randId(10) + '.mat'
        webFn = webDir + tmpFn
        serverFn = serverDir + tmpFn

        # format outLayers
        outLayerList = []
        for key in outLayers:
            outLayerList.append(outLayers[key])

        # create the mat python dictionary
        outMatData = {
            'lat': outLat,
            'lon': outLon,
            'elev': outElev,
            'roll': outRoll,
            'pitch': outPitch,
            'heading': outHeading,
            'season': outSeason,
            'frame': outFrame,
            'utcsod': outUtcSod,
            'utcdate': outUtcDate,
            'layers': outLayerList}

        # write the mat file
        savemat(serverFn, outMatData, True, '5', False, True, 'row')

        # return the output
        return utility.response(1, webFn, {})

    except Exception as e:
        return utility.errorCheck(e, sys)


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

        return utility.response(1, 'NetCDF Output Is Not Implemented', {})

    except Exception as e:
        return utility.errorCheck(e, sys)


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
    try:
        models, data, app, cookies = utility.getInput(
            request)  # get the input and models

        # perform the function logic

        # get the user profile
        userProfileObj, status = utility.getUserProfile(cookies)

        apps = opsSettings.INSTALLED_APPS  # get a list of all the apps

        outData = []

        for app in apps:
            if app.startswith(('rds', 'snow', 'accum', 'kuband')):

                models = utility.getAppModels(app)  # get the models

                if userProfileObj.isRoot:
                    seasonsObj = models.seasons.objects.select_related(
                        'locations__name').filter().values_list('name', 'location__name')
                else:
                    # get all of the seasons (and location)
                    authSeasonGroups = eval(
                        'userProfileObj.' + app + '_season_groups.values_list("name",flat=True)')
                    seasonsObj = models.seasons.objects.select_related('locations__name').filter(
                        season_group__name__in=authSeasonGroups).values_list('name', 'location__name')

                # if there are seasons populate the outData list
                if not (len(seasonsObj) == 0):

                    data = list(zip(*seasonsObj))

                    for dataIdx in range(len(data[0])):

                        outData.append({'system': app,
                                        'season': data[0][dataIdx],
                                        'location': data[1][dataIdx]})

        # return the output
        return utility.response(1, outData, {})

    except Exception as e:
        return utility.errorCheck(e, sys)


def getSegmentInfo(request):
    """ Get information about a given segment from the OPS.

    Input:
            segment_id: (integer) segment id of a segment in the segments table
                    or
            segment: (string) name of the segment
            season: (string) name of the season

    Output:
            status: (integer) 0:error 1:success 2:warning
            data:
                    season: (string) name of the season of the given segment
                    segment: (string) name of the given segment
                    frame: (list of strings) names of the frames of the given segment
                    start_gps_time: (list of floats) start gps time of each frame
                    stop_gps_time: (list of floats) stop gps time of each frame

    """
    try:
        models, data, app, cookies = utility.getInput(
            request)  # get the input and models

        # parse the input data
        try:
            inSegmentId = data['properties']['segment_id']
        except BaseException:
            inSegment = data['properties']['segment']
            inSeason = data['properties']['season']
            inSegmentId = models.segments.objects.filter(
                name=inSegment, season_id__name=inSeason).values_list(
                'pk', flat=True)
            if inSegmentId.exists():
                inSegmentId = inSegmentId[0]
            else:
                return utility.response(0, 'ERROR: SEGMENT DOES NOT EXIST.', {})

        # perform the function logic

        # get the segment name, season name, frame names, and frame ids
        pointPathsObj = models.point_paths.objects.select_related(
            'seasons__name', 'segments__name', 'frames__name').filter(
            segment_id=inSegmentId).order_by('frame').distinct('frame').values_list(
            'season__name', 'segment__name', 'frame__name', 'frame')

        seasonNames, segmentNames, frameNames, frameIds = list(
            zip(*pointPathsObj))  # extract all the elements

        if len(frameNames) < 1:
            return utility.response(2,
                                    'WARNING: NO FRAMES FOUND FOR THE GIVEN SEGMENT ID',
                                    {})  # return if there are no frames

        # for each frame get max/min gps_time from point paths
        startGpsTimes = []
        stopGpsTimes = []
        for frmId in frameIds:
            pointPathGpsTimes = models.point_paths.objects.filter(
                frame_id=frmId).values_list('gps_time', flat=True)
            startGpsTimes.append(min(pointPathGpsTimes))
            stopGpsTimes.append(max(pointPathGpsTimes))

        # return the output
        return utility.response(1,
                                {'season': seasonNames[0],
                                 'segment': segmentNames[0],
                                    'frame': frameNames,
                                    'start_gps_time': startGpsTimes,
                                    'stop_gps_time': stopGpsTimes},
                                {})

    except Exception as e:
        return utility.errorCheck(e, sys)


def getCrossovers(request):
    """ Get crossover values from the OPS.

    Input:
            location: (string)
            lyr_name: (string or list of strings)

            point_path_id: (integer or list of integers)
                    OR
            frame: (string or list of strings)
            segment_id: (integer or list of integers)

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
    try:
        models, data, app, cookies = utility.getInput(
            request)  # get the input and models

        # parse the data input

        inLocationName = utility.forceList(data['properties']['location'])
        inLayerNames = utility.forceList(data['properties']['lyr_name'])
        try:
            inFrameNames = utility.forceTuple(data['properties']['frame'])
            inSegmentIDs = utility.forceTuple(data['properties']['segment_id'])
            inPointPathIds = []

        except BaseException:
            try:
                inPointPathIds = utility.forceTuple(data['properties']['point_path_id'])
                inFrameNames = []
            except BaseException:
                return utility.response(
                    0, 'ERROR: EITHER POINT PATH IDS OR FRAME NAMES/SEGMENT_IDS MUST BE GIVEN', {})

        # perform the function logic

        # Set up variables for the creation of outputs
        sourcePointPathIds = []
        crossPointPathIds = []
        sourceElev = []
        crossElev = []
        crossTwtt = []
        crossAngle = []
        crossFrameName = []
        layerId = []
        absError = []
        crossSeasonName = []
        crossSegmentId = []
        crossQuality = []
        # Get layer ids:
        layerIds = utility.forceTuple(
            list(
                models.layers.objects.filter(
                    name__in=inLayerNames).values_list(
                    'pk', flat=True)))
        if not layerIds:
            return utility.response(2, 'SELECTED LAYERS NOT FOUND.', {})

        cursor = connection.cursor()  # create a database cursor

        # get all of the data needed for crossovers
        try:
            # Get frame ids
            if not inPointPathIds:
                frameIds = utility.forceTuple(
                    list(
                        models.frames.objects.filter(
                            name__in=inFrameNames,
                            segment__in=inSegmentIDs).values_list(
                            'pk',
                            flat=True)))
            # Get crossover errors for each layer.
            for lyrId in layerIds:
                if inPointPathIds:
                    if lyrId == 1:
                        sql_str = """SET LOCAL work_mem = '15MB';
                                     WITH cx1 AS
                                     (SELECT cx.id,
                                             cx.angle,
                                             cx.geom,
                                             cx.point_path_1_id,
                                             pp1.geom AS pp1_geom,
                                             pp1.frame_id,
                                             pp1.segment_id,
                                             pp1.season_id,
                                             lp.layer_id,
                                             lp.twtt,
                                             lp.quality
                                     FROM {app}_crossovers cx
                                     JOIN {app}_point_paths pp1 ON cx.point_path_1_id=pp1.id
                                     JOIN {app}_point_paths pp2 ON cx.point_path_2_id=pp2.id
                                     LEFT JOIN {app}_layer_points lp ON cx.point_path_1_id=lp.point_path_id
                                     AND lp.layer_id=1
                                     WHERE pp1.id IN %s
                                         OR pp2.id IN %s),
                                         cx2 AS
                                     (SELECT cx.id,
                                             cx.point_path_2_id,
                                             pp2.geom AS pp2_geom,
                                             pp2.frame_id,
                                             pp2.segment_id,
                                             pp2.season_id,
                                             lp.layer_id,
                                             lp.twtt,
                                             lp.quality
                                     FROM {app}_crossovers cx
                                     JOIN {app}_point_paths pp2 ON cx.point_path_2_id=pp2.id
                                     JOIN {app}_point_paths pp1 ON cx.point_path_1_id=pp1.id
                                     LEFT JOIN {app}_layer_points lp ON cx.point_path_2_id=lp.point_path_id
                                     AND lp.layer_id=1
                                     WHERE pp2.id IN %s
                                         OR pp1.id IN %s)
                                     SELECT point_path_1_id,
                                         point_path_2_id,
                                         ST_Z(pp1_geom),
                                         ST_Z(pp2_geom),
                                         COALESCE(cx1.layer_id, cx2.layer_id),
                                         frm1.name,
                                         frm2.name,
                                         cx1.segment_id,
                                         cx2.segment_id,
                                         cx1.twtt,
                                         cx2.twtt,
                                         cx1.angle,
                                         ABS((ST_Z(pp1_geom)-(cx1.twtt*299792458.0003452/2)) - (ST_Z(pp2_geom)-(cx2.twtt*299792458.0003452/2))),
                                         s1.name,
                                         s2.name,
                                         cx1.quality,
                                         cx2.quality
                                     FROM cx1
                                     FULL OUTER JOIN cx2 ON cx1.id=cx2.id
                                     JOIN {app}_frames frm1 ON cx1.frame_id=frm1.id
                                     JOIN {app}_frames frm2 ON cx2.frame_id=frm2.id
                                     JOIN {app}_seasons s1 ON cx1.season_id=s1.id
                                     JOIN {app}_seasons s2 ON cx2.season_id=s2.id;""".format(app=app)
                        cursor.execute(
                            sql_str, [
                                inPointPathIds, inPointPathIds, inPointPathIds, inPointPathIds])
                    else:
                        sql_str = """SET LOCAL work_mem = '15MB';
                                     WITH cx1 AS
                                     (SELECT cx.id,
                                             cx.angle,
                                             cx.geom,
                                             cx.point_path_1_id,
                                             pp1.geom AS pp1_geom,
                                             pp1.frame_id,
                                             pp1.segment_id,
                                             pp1.season_id,
                                             lp.layer_id,
                                             lp.twtt,
                                             lp.quality
                                     FROM {app}_crossovers cx
                                     JOIN {app}_point_paths pp1 ON cx.point_path_1_id=pp1.id
                                     JOIN {app}_point_paths pp2 ON cx.point_path_2_id=pp2.id
                                     LEFT JOIN {app}_layer_points lp ON cx.point_path_1_id=lp.point_path_id
                                     AND lp.layer_id=%s
                                     WHERE pp1.id IN %s
                                         OR pp2.id IN %s),
                                         cx2 AS
                                     (SELECT cx.id,
                                             cx.point_path_2_id,
                                             pp2.geom AS pp2_geom,
                                             pp2.frame_id,
                                             pp2.segment_id,
                                             pp2.season_id,
                                             lp.layer_id,
                                             lp.twtt,
                                             lp.quality
                                     FROM {app}_crossovers cx
                                     JOIN {app}_point_paths pp2 ON cx.point_path_2_id=pp2.id
                                     JOIN {app}_point_paths pp1 ON cx.point_path_1_id=pp1.id
                                     LEFT JOIN {app}_layer_points lp ON cx.point_path_2_id=lp.point_path_id
                                     AND lp.layer_id=%s
                                     WHERE pp2.id IN %s
                                         OR pp1.id IN %s)
                                     SELECT point_path_1_id,
                                         point_path_2_id,
                                         ST_Z(pp1_geom),
                                         ST_Z(pp2_geom),
                                         COALESCE(cx1.layer_id, cx2.layer_id),
                                         frm1.name,
                                         frm2.name,
                                         cx1.segment_id,
                                         cx2.segment_id,
                                         cx1.twtt,
                                         cx2.twtt,
                                         cx1.angle,
                                         ABS((((ST_Z(pp1_geom) -
                                                     (SELECT twtt
                                                     FROM {app}_layer_points
                                                     WHERE layer_id=1
                                                     AND point_path_id = cx1.point_path_1_id)*299792458.0003452/2) - ((cx1.twtt -
                                                        (SELECT twtt
                                                            FROM {app}_layer_points
                                                            WHERE layer_id = 1
                                                            AND point_path_id = cx1.point_path_1_id))*299792458.0003452/2/sqrt(3.15))) - (((ST_Z(pp2_geom) -
                                                                (SELECT twtt
                                                                FROM {app}_layer_points
                                                                WHERE layer_id=1
                                                                AND point_path_id = cx2.point_path_2_id)*299792458.0003452/2) - ((cx2.twtt -
                                                                    (SELECT twtt
                                                                        FROM {app}_layer_points
                                                                        WHERE layer_id = 1
                                                                        AND point_path_id = cx2.point_path_2_id))*299792458.0003452/2/sqrt(3.15)))))),
                                         s1.name,
                                         s2.name,
                                         cx1.quality,
                                         cx2.quality
                                     FROM cx1
                                     FULL OUTER JOIN cx2 ON cx1.id=cx2.id
                                     JOIN {app}_frames frm1 ON cx1.frame_id=frm1.id
                                     JOIN {app}_frames frm2 ON cx2.frame_id=frm2.id
                                     JOIN {app}_seasons s1 ON cx1.season_id=s1.id
                                     JOIN {app}_seasons s2 ON cx2.season_id=s2.id;""".format(app=app)
                        cursor.execute(
                            sql_str, [
                                lyrId, inPointPathIds, inPointPathIds, lyrId, inPointPathIds, inPointPathIds, ])
                else:
                    if lyrId == 1:
                        sql_str = """SET LOCAL work_mem = '15MB';
                                     WITH cx1 AS
                                     (SELECT cx.id,
                                             cx.angle,
                                             cx.geom,
                                             cx.point_path_1_id,
                                             pp1.geom AS pp1_geom,
                                             pp1.frame_id,
                                             pp1.segment_id,
                                             pp1.season_id,
                                             lp.layer_id,
                                             lp.twtt,
                                             lp.quality
                                     FROM {app}_crossovers cx
                                     JOIN {app}_point_paths pp1 ON cx.point_path_1_id=pp1.id
                                     JOIN {app}_point_paths pp2 ON cx.point_path_2_id=pp2.id
                                     LEFT JOIN {app}_layer_points lp ON cx.point_path_1_id=lp.point_path_id
                                     AND lp.layer_id=1
                                     WHERE pp1.frame_id IN %s
                                         OR pp2.frame_id IN %s),
                                         cx2 AS
                                     (SELECT cx.id,
                                             cx.point_path_2_id,
                                             pp2.geom AS pp2_geom,
                                             pp2.frame_id,
                                             pp2.segment_id,
                                             pp2.season_id,
                                             lp.layer_id,
                                             lp.twtt,
                                             lp.quality
                                     FROM {app}_crossovers cx
                                     JOIN {app}_point_paths pp2 ON cx.point_path_2_id=pp2.id
                                     JOIN {app}_point_paths pp1 ON cx.point_path_1_id=pp1.id
                                     LEFT JOIN {app}_layer_points lp ON cx.point_path_2_id=lp.point_path_id
                                     AND lp.layer_id=1
                                     WHERE pp2.frame_id IN %s
                                         OR pp1.frame_id IN %s)
                                     SELECT point_path_1_id,
                                         point_path_2_id,
                                         ST_Z(pp1_geom),
                                         ST_Z(pp2_geom),
                                         COALESCE(cx1.layer_id, cx2.layer_id),
                                         frm1.name,
                                         frm2.name,
                                         cx1.segment_id,
                                         cx2.segment_id,
                                         cx1.twtt,
                                         cx2.twtt,
                                         cx1.angle,
                                         ABS((ST_Z(pp1_geom)-(cx1.twtt*299792458.0003452/2)) - (ST_Z(pp2_geom)-(cx2.twtt*299792458.0003452/2))),
                                         s1.name,
                                         s2.name,
                                         cx1.quality,
                                         cx2.quality
                                     FROM cx1
                                     FULL OUTER JOIN cx2 ON cx1.id=cx2.id
                                     JOIN {app}_frames frm1 ON cx1.frame_id=frm1.id
                                     JOIN {app}_frames frm2 ON cx2.frame_id=frm2.id
                                     JOIN {app}_seasons s1 ON cx1.season_id=s1.id
                                     JOIN {app}_seasons s2 ON cx2.season_id=s2.id;""".format(app=app)
                        cursor.execute(
                            sql_str, [
                                frameIds, frameIds, frameIds, frameIds])
                    else:
                        sql_str = """SET LOCAL work_mem = '15MB';
                                     WITH cx1 AS
                                     (SELECT cx.id,
                                             cx.angle,
                                             cx.geom,
                                             cx.point_path_1_id,
                                             pp1.geom AS pp1_geom,
                                             pp1.frame_id,
                                             pp1.segment_id,
                                             pp1.season_id,
                                             lp.layer_id,
                                             lp.twtt,
                                             lp.quality
                                     FROM {app}_crossovers cx
                                     JOIN {app}_point_paths pp1 ON cx.point_path_1_id=pp1.id
                                     JOIN {app}_point_paths pp2 ON cx.point_path_2_id=pp2.id
                                     LEFT JOIN {app}_layer_points lp ON cx.point_path_1_id=lp.point_path_id
                                     AND lp.layer_id=%s
                                     WHERE pp1.frame_id IN %s
                                         OR pp2.frame_id IN %s),
                                         cx2 AS
                                     (SELECT cx.id,
                                             cx.point_path_2_id,
                                             pp2.geom AS pp2_geom,
                                             pp2.frame_id,
                                             pp2.segment_id,
                                             pp2.season_id,
                                             lp.layer_id,
                                             lp.twtt,
                                             lp.quality
                                     FROM {app}_crossovers cx
                                     JOIN {app}_point_paths pp2 ON cx.point_path_2_id=pp2.id
                                     JOIN {app}_point_paths pp1 ON cx.point_path_1_id=pp1.id
                                     LEFT JOIN {app}_layer_points lp ON cx.point_path_2_id=lp.point_path_id
                                     AND lp.layer_id=%s
                                     WHERE pp2.frame_id IN %s
                                         OR pp1.frame_id IN %s)
                                     SELECT point_path_1_id,
                                         point_path_2_id,
                                         ST_Z(pp1_geom),
                                         ST_Z(pp2_geom),
                                         COALESCE(cx1.layer_id, cx2.layer_id),
                                         frm1.name,
                                         frm2.name,
                                         cx1.segment_id,
                                         cx2.segment_id,
                                         cx1.twtt,
                                         cx2.twtt,
                                         cx1.angle,
                                         ABS((((ST_Z(pp1_geom) -
                                            (SELECT twtt
                                            FROM {app}_layer_points
                                            WHERE layer_id=1
                                            AND point_path_id = cx1.point_path_1_id)*299792458.0003452/2) - ((cx1.twtt -
                                                (SELECT twtt
                                                    FROM {app}_layer_points
                                                    WHERE layer_id = 1
                                                    AND point_path_id = cx1.point_path_1_id))*299792458.0003452/2/sqrt(3.15))) - (((ST_Z(pp2_geom) -
                                                        (SELECT twtt
                                                        FROM {app}_layer_points
                                                        WHERE layer_id=1
                                                        AND point_path_id = cx2.point_path_2_id)*299792458.0003452/2) - ((cx2.twtt -
                                                            (SELECT twtt
                                                                FROM {app}_layer_points
                                                                WHERE layer_id = 1
                                                                AND point_path_id = cx2.point_path_2_id))*299792458.0003452/2/sqrt(3.15)))))),
                                         s1.name,
                                         s2.name,
                                         cx1.quality,
                                         cx2.quality
                                     FROM cx1
                                     FULL OUTER JOIN cx2 ON cx1.id=cx2.id
                                     JOIN {app}_frames frm1 ON cx1.frame_id=frm1.id
                                     JOIN {app}_frames frm2 ON cx2.frame_id=frm2.id
                                     JOIN {app}_seasons s1 ON cx1.season_id=s1.id
                                     JOIN {app}_seasons s2 ON cx2.season_id=s2.id;""".format(app=app)
                        cursor.execute(
                            sql_str, [
                                lyrId, frameIds, frameIds, lyrId, frameIds, frameIds, ])
                crossoverRows = cursor.fetchall()  # get all of the data from the query

                for crossoverData in crossoverRows:  # parse each output row and sort it into either source or crossover outputs

                    if crossoverData[5] in inFrameNames or crossoverData[0] in inPointPathIds:

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
                        layerId.append(lyrId)
                        absError.append(crossoverData[12])
                        crossSegmentId.append(crossoverData[8])
                        crossQuality.append(crossoverData[16])

                    else:

                        # point_path_1 is the crossover
                        crossPointPathIds.append(crossoverData[0])
                        crossElev.append(crossoverData[2])
                        crossTwtt.append(crossoverData[9])
                        crossAngle.append(crossoverData[11])
                        crossSeasonName.append(crossoverData[13])
                        crossFrameName.append(crossoverData[5])
                        layerId.append(lyrId)
                        absError.append(crossoverData[12])
                        crossSegmentId.append(crossoverData[7])
                        crossQuality.append(crossoverData[15])

                        # point_path_2 is the source
                        sourcePointPathIds.append(crossoverData[1])
                        sourceElev.append(crossoverData[3])

        except DatabaseError as dberror:
            return utility.response(0, dberror.args[0], {})

        finally:
            cursor.close()  # close the cursor in case of exception

        if crossPointPathIds:
            # return the output
            return utility.response(1,
                                    {'source_point_path_id': sourcePointPathIds,
                                     'cross_point_path_id': crossPointPathIds,
                                     'source_elev': sourceElev,
                                     'cross_elev': crossElev,
                                     'layer_id': layerId,
                                     'season_name': crossSeasonName,
                                     'segment_id': crossSegmentId,
                                     'frame_name': crossFrameName,
                                     'twtt': crossTwtt,
                                     'angle': crossAngle,
                                     'abs_error': absError,
                                     'cross_quality': crossQuality},
                                    {})
        else:
            # No crossovers found. Return empty response.
            return utility.response(1,
                                    {'source_point_path_id': [],
                                     'cross_point_path_id': [],
                                        'source_elev': [],
                                        'cross_elev': [],
                                        'layer_id': [],
                                        'season_name': [],
                                        'segment_id': [],
                                        'frame_name': [],
                                        'twtt': [],
                                        'angle': [],
                                        'abs_error': [],
                                        'cross_quality': []},
                                    {})
    except Exception as e:
        return utility.errorCheck(e, sys)


def getCrossoversReport(request):
    """ Get crossover error report from the OPS.

    Input:
            location: (string)
            lyr_name: (string or list of strings)
                    'all' will fetch crossovers for all layers

            seasons: (string or list of strings)
                    OR
            frame: (string or list of strings)

    Output:
            status: (integer) 0:error 1:success 2:warning
            data: url to crossover report .csv on the server
    """
    try:
        models, data, app, cookies = utility.getInput(
            request)  # get the input and models

        # parse the data input

        inLocationName = utility.forceList(data['properties']['location'])
        inLayerNames = utility.forceList(data['properties']['lyr_name'])
        try:
            inSeasonNames = utility.forceTuple(data['properties']['seasons'])
        except BaseException:
            inSeasonNames = False
            try:
                inFrameNames = utility.forceTuple(data['properties']['frame'])

            except BaseException:

                return utility.response(
                    0, 'ERROR: FRAME NAMES OR SEASON NAMES MUST BE GIVEN', {})

        # perform the function logic
        # Get layer ids:
        if len(inLayerNames) == 1 and inLayerNames[0].lower() == 'all':
            layerIds = utility.forceTuple(
                list(
                    models.layers.objects.values_list(
                        'pk', flat=True)))
        else:
            layerIds = utility.forceTuple(
                list(
                    models.layers.objects.filter(
                        name__in=inLayerNames).values_list(
                        'pk', flat=True)))

        try:
            # Create, execute, and retrieve results from query to get crossover error
            # information.
            with connection.cursor() as cursor:
                if inSeasonNames:
                    sql_str = """SET LOCAL work_mem = '15MB';
                                 WITH cx1 AS
                                 (SELECT cx.id,
                                         cx.angle,
                                         cx.geom,
                                         cx.point_path_1_id,
                                         pp1.geom AS pp1_geom,
                                         pp1.frame_id,
                                         pp1.segment_id,
                                         pp1.season_id,
                                         lp.layer_id,
                                         lp.twtt,
                                         lp.quality
                                 FROM {app}_crossovers cx
                                 JOIN {app}_point_paths pp1 ON cx.point_path_1_id=pp1.id
                                 JOIN {app}_point_paths pp2 ON cx.point_path_2_id=pp2.id
                                 LEFT JOIN {app}_layer_points lp ON cx.point_path_1_id=lp.point_path_id
                                 AND lp.layer_id=1
                                 WHERE pp1.id IN %s
                                     OR pp2.id IN %s),
                                     cx2 AS
                                 (SELECT cx.id,
                                         cx.point_path_2_id,
                                         pp2.geom AS pp2_geom,
                                         pp2.frame_id,
                                         pp2.segment_id,
                                         pp2.season_id,
                                         lp.layer_id,
                                         lp.twtt,
                                         lp.quality
                                 FROM {app}_crossovers cx
                                 JOIN {app}_point_paths pp2 ON cx.point_path_2_id=pp2.id
                                 JOIN {app}_point_paths pp1 ON cx.point_path_1_id=pp1.id
                                 LEFT JOIN {app}_layer_points lp ON cx.point_path_2_id=lp.point_path_id
                                 AND lp.layer_id=1
                                 WHERE pp2.id IN %s
                                     OR pp1.id IN %s)
                                 SELECT point_path_1_id,
                                     point_path_2_id,
                                     ST_Z(pp1_geom),
                                     ST_Z(pp2_geom),
                                     COALESCE(cx1.layer_id, cx2.layer_id),
                                     frm1.name,
                                     frm2.name,
                                     cx1.segment_id,
                                     cx2.segment_id,
                                     cx1.twtt,
                                     cx2.twtt,
                                     cx1.angle,
                                     ABS((ST_Z(pp1_geom)-(cx1.twtt*299792458.0003452/2)) - (ST_Z(pp2_geom)-(cx2.twtt*299792458.0003452/2))),
                                     s1.name,
                                     s2.name,
                                     cx1.quality,
                                     cx2.quality
                                 FROM cx1
                                 FULL OUTER JOIN cx2 ON cx1.id=cx2.id
                                 JOIN {app}_frames frm1 ON cx1.frame_id=frm1.id
                                 JOIN {app}_frames frm2 ON cx2.frame_id=frm2.id
                                 JOIN {app}_seasons s1 ON cx1.season_id=s1.id
                                 JOIN {app}_seasons s2 ON cx2.season_id=s2.id;""".format(app=app)
                    cursor.execute(
                        sql_str, [
                            layerIds, inSeasonNames, layerIds, inSeasonNames])
                else:
                    sql_str = """WITH cx1 AS
                                (SELECT cx.point_path_1_id,
                                        cx.id,
                                        cx.angle,
                                        cx.geom,
                                        pp1.geom AS pp1_geom,
                                        pp1.gps_time,
                                        frm1.name AS frm1Name,
                                        ss1.name AS ss1Name,
                                        lp.layer_id,
                                        lp.twtt
                                FROM {app}_crossovers cx
                                JOIN {app}_point_paths pp1 ON cx.point_path_1_id=pp1.id
                                JOIN {app}_frames frm1 ON pp1.frame_id=frm1.id
                                JOIN {app}_seasons ss1 ON pp1.season_id=ss1.id
                                JOIN {app}_layer_points lp ON cx.point_path_1_id=lp.point_path_id
                                AND lp.layer_id IN %s
                                WHERE frm1.name IN %s),
                                    cx2 AS
                                (SELECT cx.point_path_2_id,
                                        cx.id,
                                        pp2.geom AS pp2_geom,
                                        pp2.gps_time,
                                        frm2.name AS frm2Name,
                                        ss2.name AS ss2Name,
                                        lp.layer_id,
                                        lp.twtt
                                FROM {app}_crossovers cx
                                JOIN {app}_point_paths pp2 ON cx.point_path_2_id=pp2.id
                                JOIN {app}_frames frm2 ON pp2.frame_id=frm2.id
                                JOIN {app}_seasons ss2 ON pp2.season_id=ss2.id
                                JOIN {app}_layer_points lp ON cx.point_path_2_id=lp.point_path_id
                                AND lp.layer_id IN %s
                                WHERE frm2.name IN %s)
                                SELECT CASE
                                        WHEN COALESCE(cx1.layer_id, cx2.layer_id) = 1 THEN (ST_Z(cx1.pp1_geom) - cx1.twtt*299792458.0003452/2)
                                        ELSE (ST_Z(cx1.pp1_geom) -
                                            (SELECT twtt
                                                FROM {app}_layer_points
                                                WHERE layer_id=1
                                                AND point_path_id = cx1.point_path_1_id)*299792458.0003452/2 - (cx1.twtt -
                                                    (SELECT twtt
                                                    FROM {app}_layer_points
                                                    WHERE layer_id = 1
                                                    AND point_path_id = cx1.point_path_1_id))*299792458.0003452/2/sqrt(3.15))
                                    END AS layer_elev_1,
                                    CASE
                                        WHEN COALESCE(cx1.layer_id, cx2.layer_id) = 1 THEN (ST_Z(cx2.pp2_geom) - cx2.twtt*299792458.0003452/2)
                                        ELSE (ST_Z(cx2.pp2_geom) -
                                            (SELECT twtt
                                                FROM {app}_layer_points
                                                WHERE layer_id=1
                                                AND point_path_id = cx2.point_path_2_id)*299792458.0003452/2 - (cx2.twtt -
                                                    (SELECT twtt
                                                    FROM {app}_layer_points
                                                    WHERE layer_id = 1
                                                    AND point_path_id = cx2.point_path_2_id))*299792458.0003452/2/sqrt(3.15))
                                    END AS layer_elev_2,
                                    cx1.twtt,
                                    cx2.twtt,
                                    cx1.angle,
                                    lyr.name,
                                    cx1.ss1Name,
                                    cx2.ss2Name,
                                    frm1Name,
                                    frm2Name,
                                    cx1.gps_time,
                                    cx2.gps_time,
                                    cx1.pp1_geom,
                                    cx2.pp2_geom,
                                    cx1.geom
                                FROM cx1
                                JOIN cx2 ON cx1.id=cx2.id
                                AND cx1.layer_id=cx2.layer_id
                                JOIN {app}_layers lyr ON lyr.id=cx1.layer_id;""".format(app=app)
                    cursor.execute(
                        sql_str, [
                            layerIds, inFrameNames, layerIds, inFrameNames])
                crossoverRows = cursor.fetchall()

        except DatabaseError as dberror:
            return utility.response(0, dberror.args[0], {})

        if len(crossoverRows) > 0:

            # generate the output report information
            serverDir = opsSettings.OPS_DATA_PATH + 'data/reports/'
            webDir = 'data/reports/'
            tmpFn = 'OPS_CReSIS_Crossovers_Report_' + utility.randId(10) + '.csv'
            webFn = webDir + tmpFn
            serverFn = serverDir + tmpFn

            # Construct the csv header
            csvHeader = [
                'ERROR',
                'LAYER_ELEV1',
                'LAYER_ELEV2',
                'TWTT1',
                'TWTT2',
                'CROSS_ANGLE',
                'LAYER_NAME',
                'SEASON1',
                'SEASON2',
                'FRAME1',
                'FRAME2',
                'UTCSOD1',
                'UTCSOD2',
                'UTCDATE1',
                'UTCDATE2',
                'LON1',
                'LON2',
                'LAT1',
                'LAT2',
                'ELEV1',
                'ELEV2',
                'CROSS_LON',
                'CROSS_LAT']

            # write the csv file
            with open(serverFn, 'w') as csvFile:

                # Create a GEOS Well Known Binary reader
                wkb_r = WKBReader()

                # Create a python csv writer
                csvWriter = csv.writer(csvFile, delimiter=',', quoting=csv.QUOTE_NONE)

                # Write the header to the csv file
                csvWriter.writerow(csvHeader)

                # Write each crossover result to the csv file
                for row in crossoverRows:

                    if row[0] is not None:
                        layerElev1 = "%.5f" % row[0]
                    else:
                        layerElev1 = None
                    if row[1] is not None:
                        layerElev2 = "%.5f" % row[1]
                    else:
                        layerElev2 = None

                    # Only write the result if an error can be reported.
                    if layerElev1 is not None and layerElev2 is not None:
                        # Extract variables from each row for writing to csv
                        ppGeom1 = wkb_r.read(row[12])
                        ppGeom2 = wkb_r.read(row[13])
                        crossGeom = wkb_r.read(row[14])
                        error = "%.5f" % math.fabs(row[0] - row[1])
                        twtt1 = str(row[2].quantize(Decimal('0.00000001')))
                        twtt2 = str(row[3].quantize(Decimal('0.00000001')))
                        # Write each row as a record to a csv file
                        csvWriter.writerow(
                            [
                                error,
                                layerElev1,
                                layerElev2,
                                twtt1,
                                twtt2,
                                "%.3f" %
                                row[4],
                                row[5],
                                row[6],
                                row[7],
                                row[8],
                                row[9],
                                "%.3f" %
                                (float(
                                    time.gmtime(
                                        row[10]).tm_hour *
                                    3600.0 +
                                    time.gmtime(
                                        row[10]).tm_min *
                                    60.0 +
                                    time.gmtime(
                                        row[10]).tm_sec)),
                                "%.3f" %
                                (float(
                                    time.gmtime(
                                        row[11]).tm_hour *
                                    3600.0 +
                                    time.gmtime(
                                        row[11]).tm_min *
                                    60.0 +
                                    time.gmtime(
                                        row[11]).tm_sec)),
                                (time.strftime(
                                    '%Y%m%d',
                                    time.gmtime(
                                        row[10]))),
                                (time.strftime(
                                    '%Y%m%d',
                                    time.gmtime(
                                        row[11]))),
                                "%.8f" %
                                ppGeom1.x,
                                "%.8f" %
                                ppGeom2.x,
                                "%.5f" %
                                ppGeom1.y,
                                "%.8f" %
                                ppGeom2.y,
                                "%.8f" %
                                ppGeom1.z,
                                "%.5f" %
                                ppGeom2.z,
                                "%.8f" %
                                crossGeom.x,
                                "%.8f" %
                                crossGeom.y])

            # return the output
            return utility.response(1, webFn, {})
        else:
            return utility.response(
                2, "No crossover errors found with specified parameters.", {})
    except Exception as e:
        return utility.errorCheck(e, sys)


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
    try:
        models, data, app, cookies = utility.getInput(
            request)  # get the input and models

        # parse the data input

        inLocationName = data['properties']['location']
        inSearchStr = data['properties']['search_str']

        # parse the optional input
        try:
            useAllSeasons = False
            inSeasonNames = utility.forceList(data['properties']['season'])

        except KeyError:
            useAllSeasons = True

        # perform the function logic

        # get the first matching frame object
        if useAllSeasons:
            framesObj = models.frames.objects.filter(
                name__istartswith=inSearchStr,
                segment__season__location__name=inLocationName).order_by('pk')
        else:
            framesObj = models.frames.objects.filter(
                name__istartswith=inSearchStr,
                segment__season__location__name=inLocationName,
                segment__season__name__in=inSeasonNames).order_by('pk')

        if framesObj.exists():
            framesObj = framesObj[0]
        else:
            return utility.response(
                2, 'WARNING: NO FRAMES FOUND FOR THE GIVEN SEARCH STRING.', {})

        epsg = utility.epsgFromLocation(inLocationName)  # get the input epsg

        try:
            # Query for the rquired information (get the points as a linestring w/ z
            # value of gps_time)
            queryStr = """
            SELECT  ss.name,
                    pp.segment_id,
                    st_transform(St_makeline(St_geomfromtext('POINTZ('
                            ||St_x(geom)
                            ||' '
                            || St_y(geom)
                            ||' '
                            || pp.gps_time
                            ||')',4326)),%s)
            FROM     {app}_point_paths pp
            JOIN     {app}_seasons ss
            ON       pp.season_id=ss.id
            WHERE    pp.frame_id=%s
            GROUP BY ss.name,
                    pp.segment_id;
            """.format(app=app)
            with connection.cursor() as cursor:
                cursor.execute(queryStr, [epsg, framesObj.pk])
                pointPathsObj = cursor.fetchone()
        except DatabaseError as dberror:
            return utility.response(0, dberror.args[0], {})

        # extract all the elements
        seasonName = pointPathsObj[0]
        segmentId = pointPathsObj[1]
        # break apart the linestring.
        lon, lat, gps_time = list(zip(*GEOSGeometry(pointPathsObj[2])))
        del pointPathsObj

        # Sort the results.
        lon = [x for (gps, x) in sorted(zip(gps_time, lon))]
        lat = [y for (gps, y) in sorted(zip(gps_time, lat))]
        gps_time = sorted(gps_time)

        # return the output
        return utility.response(1,
                                {'season': seasonName,
                                 'segment_id': segmentId,
                                 'frame': framesObj.name,
                                 'X': lon,
                                 'Y': lat,
                                 'gps_time': gps_time},
                                {})

    except Exception as e:
        return utility.errorCheck(e, sys)


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
    try:
        models, data, app, cookies = utility.getInput(request)  # get the input

        # parse the data input

        inSeasons = utility.forceList(data['properties']['seasons'])
        inRadars = utility.forceList(data['properties']['radars'])
        inSegments = utility.forceList(data['properties']['segments'])

        # parse the optional inputs
        try:
            useAllLyr = False
            inLyrNames = utility.forceList(data['properties']['layers'])

        except BaseException:
            useAllLyr = True

        # perform the function logic

        # get point path, frame, segment, location, season, and radar ids
        pointPathsObj = models.point_paths.objects.select_related('segment__radar_id').filter(
            segment__name__in=inSegments,
            season__name__in=inSeasons,
            segment__radar__name__in=inRadars).values_list(
            'pk',
            'location_id',
            'season_id',
            'segment_id',
            'frame_id',
            'segment__radar_id')

        pointPathIds, locationIds, seasonIds, segmentIds, frameIds, radarIds = list(
            zip(*pointPathsObj))  # extract all the elements
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
            layersObj = models.layers.objects.filter(
                deleted=False, layer_group__public=True).values_list(
                'pk', 'layer_group_id')
        else:
            layersObj = models.layers.objects.filter(
                name__in=inLyrNames,
                deleted=False,
                layer_group__public=True).values_list(
                'pk',
                'layer_group_id')

        layerIds, layerGroupIds = list(zip(*layersObj))  # extract all the elements
        del layersObj

        # force objects to be lists (only keep unique layer groups)
        layerIds = utility.forceList(layerIds)
        layerGroupIds = utility.forceList(set(layerGroupIds))

        # create a temporary directory to store the csv files for compression
        tmpDir = opsSettings.OPS_DATA_PATH + 'datapacktmp/' + utility.randId(10)
        sysCmd = 'mkdir -p -m 777 ' + tmpDir + ' && chown -R postgres:postgres ' + tmpDir
        os.system(sysCmd)

        # copy all of the database tables (based on the input filters) to csv
        # files (exclude data from django fixtures)
        try:

            # build raw strings (parameters wont work because non-column fields are
            # dynamic)
            sqlStrings = []
            sqlStrings.append(
                "COPY (SELECT * FROM %s_layers WHERE id IN %s AND id NOT IN (1,2))\
			TO '%s/%s_layers' WITH CSV" %
                (app, layerIds, tmpDir, app))
            sqlStrings.append(
                "COPY (SELECT * FROM %s_layer_links WHERE layer_1_id IN %s AND layer_2_id IN %s)\
			TO '%s/%s_layer_links' WITH CSV" %
                (app, layerIds, layerIds, tmpDir, app))
            sqlStrings.append(
                "COPY (SELECT * FROM %s_layer_groups WHERE id IN %s AND id NOT IN (1,2))\
			TO '%s/%s_layer_groups' WITH CSV" %
                (app, layerGroupIds, tmpDir, app))
            sqlStrings.append(
                "COPY (SELECT * FROM %s_crossovers WHERE point_path_1_id IN %s AND point_path_2_id IN %s)\
			TO '%s/%s_crossovers' WITH CSV" %
                (app, pointPathIds, pointPathIds, tmpDir, app))
            sqlStrings.append(
                "COPY (SELECT * FROM %s_locations WHERE id IN %s AND id NOT IN (1,2))\
			TO '%s/%s_layer_groups' WITH CSV" %
                (app, locationIds, tmpDir, app))
            sqlStrings.append(
                "COPY (SELECT * FROM %s_layer_points WHERE point_path_id IN %s)\
			TO '%s/%s_layer_points' WITH CSV" %
                (app, pointPathIds, tmpDir, app))
            sqlStrings.append("COPY (SELECT * FROM %s_point_paths WHERE id IN %s)\
			TO '%s/%s_point_paths' WITH CSV" % (app, pointPathIds, tmpDir, app))
            sqlStrings.append("COPY (SELECT * FROM %s_frames WHERE id IN %s)\
			TO '%s/%s_frames' WITH CSV" % (app, frameIds, tmpDir, app))
            sqlStrings.append(
                "COPY (SELECT * FROM %s_landmarks WHERE point_path_1_id IN %s AND point_path_2_id IN %s)\
			TO '%s/%s_landmarks' WITH CSV" %
                (app, pointPathIds, pointPathIds, tmpDir, app))
            sqlStrings.append("COPY (SELECT * FROM %s_seasons WHERE id IN %s)\
			TO '%s/%s_seasons' WITH CSV" % (app, seasonIds, tmpDir, app))
            sqlStrings.append("COPY (SELECT * FROM %s_segments WHERE id IN %s)\
			TO '%s/%s_segments' WITH CSV" % (app, segmentIds, tmpDir, app))
            sqlStrings.append("COPY (SELECT * FROM %s_radars WHERE id IN %s)\
			TO '%s/%s_radars' WITH CSV" % (app, radarIds, tmpDir, app))

            with connection.cursor() as cursor:
                for sqlStr in sqlStrings:
                    # execute the raw sql, format list insertions as tuples
                    cursor.execute(sqlStr.replace('[', '(').replace(']', ')'))

        except DatabaseError as dberror:
            return utility.response(0, dberror.args[0], {})

        # generate the output .tar.gz information
        serverDir = opsSettings.OPS_DATA_PATH + 'data/datapacks/'
        webDir = 'data/datapacks/'
        tmpFn = 'OPS_CReSIS_%s_DATAPACK' % (
            app.upper()) + '_' + utility.randId(10) + '.tar.gz'
        webFn = webDir + tmpFn

        # compress, copy, and delete source csv files
        sysCmd = 'cd %s && tar -zcf %s * && cp %s %s && cd .. && rm -rf %s' % (
            tmpDir, tmpFn, tmpFn, serverDir, tmpDir)
        os.system(sysCmd)

        # return the output
        return utility.response(1, webFn, {})

    except Exception as e:
        return utility.errorCheck(e, sys)


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
    try:
        _, data, _, cookies = utility.getInput(request)  # get the input and models

        # perform function logic

        # get the user profile
        uPObj, status = utility.getUserProfile(cookies)
        if not status:
            return utility.response(0, uPObj, {})

        # build the outputs (get rid of unicode strings)
        rdsSg = [
            output.encode("utf8") for output in uPObj.rds_season_groups.values_list(
                'name', flat=True)]
        rdsSgId = list(uPObj.rds_season_groups.values_list('pk', flat=True))
        rdsLg = [
            output.encode("utf8") for output in uPObj.rds_layer_groups.values_list(
                'name', flat=True)]
        rdsLgId = list(uPObj.rds_layer_groups.values_list('pk', flat=True))

        accumSg = [
            output.encode("utf8") for output in uPObj.accum_season_groups.values_list(
                'name', flat=True)]
        accumSgId = list(uPObj.accum_season_groups.values_list('pk', flat=True))
        accumLg = [
            output.encode("utf8") for output in uPObj.accum_layer_groups.values_list(
                'name', flat=True)]
        accumLgId = list(uPObj.accum_layer_groups.values_list('pk', flat=True))

        snowSg = [
            output.encode("utf8") for output in uPObj.snow_season_groups.values_list(
                'name', flat=True)]
        snowSgId = list(uPObj.snow_season_groups.values_list('pk', flat=True))
        snowLg = [
            output.encode("utf8") for output in uPObj.snow_layer_groups.values_list(
                'name', flat=True)]
        snowLgId = list(uPObj.snow_layer_groups.values_list('pk', flat=True))

        kubandSg = [
            output.encode("utf8") for output in uPObj.kuband_season_groups.values_list(
                'name', flat=True)]
        kubandSgId = list(uPObj.kuband_season_groups.values_list('pk', flat=True))
        kubandLg = [
            output.encode("utf8") for output in uPObj.kuband_layer_groups.values_list(
                'name', flat=True)]
        kubandLgId = list(uPObj.kuband_layer_groups.values_list('pk', flat=True))

        # return the output
        return utility.response(1,
                                {'rds_season_groups': rdsSg,
                                 'rds_season_group_ids': rdsSgId,
                                 'rds_layer_groups': rdsLg,
                                 'rds_layer_group_ids': rdsLgId,
                                 'accum_season_groups': accumSg,
                                 'accum_season_group_ids': accumSgId,
                                 'accum_layer_groups': accumLg,
                                 'accum_layer_group_ids': accumLgId,
                                 'snow_season_groups': snowSg,
                                 'snow_season_group_ids': snowSgId,
                                 'snow_layer_groups': snowLg,
                                 'snow_layer_group_ids': snowLgId,
                                 'kuband_season_groups': kubandSg,
                                 'kuband_season_group_ids': kubandSgId,
                                 'kuband_layer_groups': kubandLg,
                                 'kuband_layer_group_ids': kubandLgId,
                                 'layerGroupRelease': uPObj.layerGroupRelease,
                                 'seasonRelease': uPObj.seasonRelease,
                                 'createData': uPObj.createData,
                                 'bulkDeleteData': uPObj.bulkDeleteData,
                                 'isRoot': uPObj.isRoot},
                                {})

    except Exception as e:
        return utility.errorCheck(e, sys)

# =======================================
# UTILITY FUNCTIONS
# =======================================


def createUser(request):
    """ Creates a user in the OPS database

    Input:
            userName: (string)
            email: (string)
            password: (string)

    Output:
            status: (integer) 0:error 1:success 2:warning
            data: (string) status message

    """
    try:
        _, data, _, cookies = utility.getInput(request)  # get the input and models

        inUserName = data['properties']['userName']
        inPassword = data['properties']['password']
        inEmail = data['properties']['email']

        try:
            userObj = User.objects.get(username__exact=inUserName)
            if userObj is not None:
                return utility.response(2, 'WARNING: USERNAME ALREADY EXISTS', {})
        except BaseException:
            _ = User.objects.create_user(inUserName, inEmail, inPassword)

        return utility.response(1, 'SUCCESS: NEW USER CREATED', {})

    except Exception as e:
        return utility.errorCheck(e, sys)


@ipAuth()
@transaction.atomic()
def alterUserPermissions(request):
    """ Alters a user's permissions in the database.
            MUST BE A ROOT USER TO CHANGE ANOTHER USER'S PERMISSIONS.

    Input:
            user_name: (string; the username of the user for which permissions will be changed)
            Optional permissions to change:
                    sys_layer_groups
                    sys_season_groups
                    layerGroupRelease
                    bulkDeleteData
                    createData
                    seasonRelease
                    isRoot

            FROM MATLAB:
                    mat: (boolean) true
                    userName: (string) username of an authenticated user (or anonymous)
                    isAuthenticated (boolean) authentication status of a user

    Output:
            status: (integer) 0:error 1:success 2:warning
            data: (string) status message

    """
    try:
        _, data, app, cookies = utility.getInput(request)  # get the input
        inUserName = data['properties']['user_name']

        # Get the user profile from the user initiating the changes
        userProfileObj, status = utility.getUserProfile(cookies)
        if status:
            if userProfileObj.isRoot:
                # Get user from database
                try:
                    userObj = User.objects.get(username__exact=inUserName)
                    if userObj is None:
                        return utility.response(
                            2, 'USER ' + inUserName + ' DOES NOT EXIST', {})
                except BaseException:
                    return utility.response(
                        2, 'USER ' + inUserName + ' DOES NOT EXIST', {})

                alteredPermissions = []
                # Extract optional parameters
                # Layer groups
                try:
                    sysLayerGroups = utility.forceList(
                        data['properties']['sys_layer_groups'])
                except KeyError:
                    pass
                else:
                    if '+' in sysLayerGroups:
                        sysLayerGroups.remove('+')
                        sysLayerGroups.extend(
                            eval(
                                "userObj.profile." +
                                app +
                                "_layer_groups.values_list('pk',flat=True)"))

                    exec(
                        'userObj.profile.' +
                        app +
                        '_layer_groups = list(set(sysLayerGroups))')
                    alteredPermissions.append(app + '_layer_groups')

                # Season groups
                try:
                    sysSeasonGroups = utility.forceList(
                        data['properties']['sys_season_groups'])
                except KeyError:
                    pass
                else:
                    if '+' in sysSeasonGroups:
                        sysSeasonGroups.extend(
                            eval(
                                "userObj.profile." +
                                app +
                                "_season_groups.values_list('pk',flat=True)"))

                    exec(
                        'userObj.profile.' +
                        app +
                        '_season_groups = list(set(sysSeasonGroups))')
                    alteredPermissions.append(app + '_season_groups')

                # Layer group release
                try:
                    layerGroupRelease = utility.forceList(
                        data['properties']['layerGroupRelease'])
                except KeyError:
                    pass
                else:
                    userObj.profile.layerGroupRelease = layerGroupRelease
                    alteredPermissions.append('layerGroupRelease')

                # Bulk Delete
                try:
                    bulkDeleteData = utility.forceBool(
                        data['properties']['bulkDeleteData'])
                except KeyError:
                    pass
                else:
                    userObj.profile.bulkDeleteData = bulkDeleteData
                    alteredPermissions.append('bulkDeleteData')

                # Create data
                try:
                    createData = utility.forceBool(data['properties']['createData'])
                except KeyError:
                    pass
                else:
                    userObj.profile.createData = createData
                    alteredPermissions.append('createData')

                # Season release
                try:
                    seasonRelease = utility.forceBool(
                        data['properties']['seasonRelease'])
                except KeyError:
                    pass
                else:
                    userObj.profile.seasonRelease = seasonRelease
                    alteredPermissions.append('seasonRelease')

                # Root user
                try:
                    isRoot = utility.forceBool(data['properties']['isRoot'])
                except KeyError:
                    pass
                else:
                    userObj.profile.isRoot = isRoot
                    alteredPermissions.append('isRoot')

                if len(alteredPermissions) > 0:
                    userObj.profile.save()
                    returnStr = 'The following permissions were altered: '
                    for permission in alteredPermissions:
                        returnStr = returnStr + permission + '; '
                    return utility.response(1, returnStr, {})
                else:
                    return utility.response(
                        1, 'No permissions for ' + inUserName + ' were changed', {})
            else:
                return utility.response(
                    0, 'ERROR: YOU ARE NOT AUTHORIZED TO CHANGE PERMISSIONS.', {})
        else:
            return utility.response(0, userProfileObj, {})

    except Exception as e:
        return utility.errorCheck(e, sys)


def loginUser(request):
    """ Logs in a user to the browser session.

    Input:
            userName: (string)
            password: (string)

    Output:
            status: (integer) 0:error 1:success 2:warning
            data: (string) status message

    """
    try:
        _, data, _, cookies = utility.getInput(request)  # get the input and models

        # get inputs
        inUserName = data['properties']['userName']
        inPassword = data['properties']['password']

        if not cookies['isMat']:
            # check the status of the user (log them out if there logged in)
            curUserName = cookies['userName']
            if curUserName == inUserName:
                userAuthStatus = int(cookies['isAuthenticated'])
                if userAuthStatus == 1:
                    logout(request)  # log out active user

        # authenticate the user
        user = authenticate(username=inUserName, password=inPassword)

        # if the user authenticates log them in
        if user is not None:
            if user.is_active:
                login(request, user)
                return utility.response(
                    1, 'SUCCESS: USER NOW LOGGED IN.', {
                        'userName': inUserName, 'isAuthenticated': 1})
            else:
                return utility.response(
                    2, 'WARNING: USER ACCOUNT IS DISABLED.', {
                        'userName': '', 'isAuthenticated': 0})
        else:
            return utility.response(
                0, 'ERROR: USER AUTHENTICATION FAILED.', {
                    'userName': '', 'isAuthenticated': 0})

    except Exception as e:
        return utility.errorCheck(e, sys)


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

        return utility.response(
            1, 'SUCCESS: USER LOGGED OUT', {
                'userName': '', 'isAuthenticated': 0})

    except Exception as e:
        return utility.errorCheck(e, sys)


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
    try:
        queryStr, cookies = utility.getQuery(request)  # get the input

        # perform the function logic

        cursor = connection.cursor()  # create a database cursor
        cursor.execute(queryStr)  # execute the query
        queryData = cursor.fetchall()  # fetch the query results

        # return the output
        if not queryData:
            return utility.response(2, 'NO DATA RETURNED FROM QUERY', {})
        else:
            return utility.response(1, queryData, {})

    except DatabaseError as dberror:
        return utility.response(0, dberror.args[0], {})


@ipAuth()
def updateMaterializedView(request):
    """ REFRESH MATERIALIZED VIEW xxx; on the database.

    Input:
            query: (string) an SQL clause 'REFRESH MATERIALIZED VIEW xxx'

    Output:
            status: (integer) 0:error 1:success


    """
    try:
        queryStr, cookies = utility.getQuery(request)  # get the input

        # perform the function logic
        with connection.cursor() as cursor:
            cursor.execute(queryStr)  # execute the query
            connection.commit()

        return utility.response(
            1, "SUCCESS: The materialized view has been updated.", {})

    except DatabaseError as dberror:
        return utility.response(0, dberror.args[0], {})

@ipAuth()
def analyze(request):
    """ ANALYZE a list of tables in the OPS database.

    Input:
            tables: (list) names of tables in the OPS database

    Output:
            status: (integer) 0:error 1:success 2:warning
            data: string status message

    """
    try:
        models, data, app, cookies = utility.getInput(
            request)  # get the input and models

        # parse the input data
        tables = utility.forceList(data['properties']['tables'])

        if len(tables) == 0:
            return utility.response(2, "WARNING: NO TABLES ARE ANALYZED.", {})
        # perform the function logic

        try:
            with connection.cursor() as cursor:
                for table in tables:
                    cursor.execute("ANALYZE " + app + "_" + table)  # execute the query

        except DatabaseError as dberror:
            return utility.response(0, dberror.args[0], {})

        # return the output
        return utility.response(1, "SUCCESS: DATABASE TABLES ANALYZED.", {})

    except Exception as e:
        return utility.errorCheck(e, sys)


@ipAuth()
def profile(request):
    """ Runs the profiler for the function called.

    Input:
            none: no additional input is needed, passes on called function input

    Output:
            status: (integer) 0:error 1:success 2:warning
            data: string status message

    """
    import line_profiler
    
    try:

        view = request.POST.get('view')  # get the function call

        evalStr = view + '(request)'  # create the string to be evaluated

        profiler = line_profiler.LineProfiler()  # get a profiler object

        profiler.enable()  # enable the profiler

        profiler.add_function(eval(view))  # add the function call to the profiler

        viewResponse = eval(evalStr)  # run the function

        profiler.disable()  # disable the profiler

        # build output information
        timeStr = datetime.datetime.now().strftime('-%d-%m-%y-%X')
        fn = '/var/profile_logs/' + view + timeStr + '.lprof'
        fnTxt = '/var/profile_logs/txt/' + view + timeStr + '.txt'

        # write the output
        profiler.dump_stats(fn)
        os.system('python -m line_profiler ' + fn + ' > ' + fnTxt)

        # return the output (from the function call)
        return viewResponse

    except Exception as e:
        return utility.errorCheck(e, sys)
