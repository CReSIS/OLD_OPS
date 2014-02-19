--Set DB parameters to facilitate load. 
SET maintenance_work_mem TO '1024MB';
--Drop all indexes to facilitate load. 
DROP INDEX rds_point_paths_gps_time; 
DROP INDEX rds_point_paths_point_path_id;
DROP INDEX rds_layer_points_gps_time;
DROP INDEX rds_layer_points_layer_point_id;
DROP INDEX rds_segments_start_gps_time;
DROP INDEX rds_segments_stop_gps_time;
DROP INDEX rds_segments_line_path_id;
DROP INDEX rds_crossovers_gps_time_1;
DROP INDEX rds_crossovers_gps_time_2;
DROP INDEX rds_crossovers_cross_point_id;
DROP INDEX rds_frames_start_gps_time;
DROP INDEX rds_frames_stop_gps_time;
DROP INDEX rds_landmarks_start_gps_time;
DROP INDEX rds_landmarks_stop_gps_time;
DROP INDEX rds_landmarks_start_twtt;
DROP INDEX rds_landmarks_stop_twtt;
DROP INDEX snow_point_paths_gps_time; 
DROP INDEX snow_point_paths_point_path_id;
DROP INDEX snow_layer_points_gps_time;
DROP INDEX snow_layer_points_layer_point_id;
DROP INDEX snow_segments_start_gps_time;
DROP INDEX snow_segments_stop_gps_time;
DROP INDEX snow_segments_line_path_id;
DROP INDEX snow_crossovers_gps_time_1;
DROP INDEX snow_crossovers_gps_time_2;
DROP INDEX snow_crossovers_cross_point_id;
DROP INDEX snow_frames_start_gps_time;
DROP INDEX snow_frames_stop_gps_time;
DROP INDEX snow_landmarks_start_gps_time;
DROP INDEX snow_landmarks_stop_gps_time;
DROP INDEX snow_landmarks_start_twtt;
DROP INDEX snow_landmarks_stop_twtt;
DROP INDEX accum_point_paths_gps_time; 
DROP INDEX accum_point_paths_point_path_id;
DROP INDEX accum_layer_points_gps_time;
DROP INDEX accum_layer_points_layer_point_id;
DROP INDEX accum_segments_start_gps_time;
DROP INDEX accum_segments_stop_gps_time;
DROP INDEX accum_segments_line_path_id;
DROP INDEX accum_crossovers_gps_time_1;
DROP INDEX accum_crossovers_gps_time_2;
DROP INDEX accum_crossovers_cross_point_id;
DROP INDEX accum_frames_start_gps_time;
DROP INDEX accum_frames_stop_gps_time;
DROP INDEX accum_landmarks_start_gps_time;
DROP INDEX accum_landmarks_stop_gps_time;
DROP INDEX accum_landmarks_start_twtt;
DROP INDEX accum_landmarks_stop_twtt;
DROP INDEX kuband_point_paths_gps_time; 
DROP INDEX kuband_point_paths_point_path_id;
DROP INDEX kuband_layer_points_gps_time;
DROP INDEX kuband_layer_points_layer_point_id;
DROP INDEX kuband_segments_start_gps_time;
DROP INDEX kuband_segments_stop_gps_time;
DROP INDEX kuband_segments_line_path_id;
DROP INDEX kuband_crossovers_gps_time_1;
DROP INDEX kuband_crossovers_gps_time_2;
DROP INDEX kuband_crossovers_cross_point_id;
DROP INDEX kuband_frames_start_gps_time;
DROP INDEX kuband_frames_stop_gps_time;
DROP INDEX kuband_landmarks_start_gps_time;
DROP INDEX kuband_landmarks_stop_gps_time;
DROP INDEX kuband_landmarks_start_twtt;
DROP INDEX kuband_landmarks_stop_twtt;

--Remove all foreign-key constraints. 
DO $body$
DECLARE r record;
BEGIN
	CREATE TABLE constraint_tab (constraint_name varchar(50), table_name varchar(20), column_name varchar(20), foreign_table_name varchar(20), foreign_column_name varchar(20));
    
	FOR r IN SELECT
    tc.constraint_name, tc.table_name,
	kcu.column_name,ccu.table_name AS foreign_table_name,
    ccu.column_name AS foreign_column_name 
FROM 
    information_schema.table_constraints AS tc 
    JOIN information_schema.key_column_usage AS kcu ON tc.constraint_name = kcu.constraint_name
    JOIN information_schema.constraint_column_usage AS ccu ON ccu.constraint_name = tc.constraint_name
WHERE constraint_type = 'FOREIGN KEY' AND tc.table_name LIKE '%rds_%'
    
	LOOP
       EXECUTE 'ALTER TABLE ' || quote_ident(r.table_name)|| ' DROP CONSTRAINT '|| quote_ident(r.constraint_name) || ';';
	   EXECUTE 'INSERT INTO constraint_tab (constraint_name, table_name, column_name, foreign_table_name, foreign_column_name) VALUES (''' || quote_ident(r.constraint_name) || ''', ''' || quote_ident(r.table_name) || ''', ''' || quote_ident(r.column_name) || ''', ''' || quote_ident(r.foreign_table_name) || ''', ''' || quote_ident(r.foreign_column_name) || ''');';
    END LOOP;
END
$body$;
