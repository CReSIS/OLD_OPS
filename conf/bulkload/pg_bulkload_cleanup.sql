--Set sequences for primary keys to begin at max value inserted from initial data + 1.
SELECT setval('rds_layer_points_layer_points_id_seq', (SELECT max(layer_points_id) FROM rds_layer_points)+1);
SELECT setval('rds_layer_links_layer_link_id_seq', (SELECT max(layer_link_id) FROM rds_layer_links)+1);
SELECT setval('rds_layer_groups_layer_group_id_seq', (SELECT max(layer_group_id) FROM rds_layer_groups)+1);
SELECT setval('rds_layers_layer_id_seq', (SELECT max(layer_id) FROM rds_layers)+1);
SELECT setval('rds_seasons_season_id_seq', (SELECT max(season_id) FROM rds_seasons)+1);
SELECT setval('rds_point_paths_point_path_id_seq', (SELECT max(point_path_id) FROM rds_point_paths)+1);
SELECT setval('rds_locations_location_id_seq', (SELECT max(location_id) FROM rds_locations)+1);
SELECT setval('rds_segments_segment_id_seq', (SELECT max(segment_id) FROM rds_segments)+1);
SELECT setval('rds_crossovers_crossover_id_seq', (SELECT max(crossover_id) FROM rds_crossovers)+1);
SELECT setval('rds_radars_radar_id_seq', (SELECT max(radar_id) FROM rds_radars)+1);
SELECT setval('rds_frames_frame_id_seq', (SELECT max(frame_id) FROM rds_frames)+1);
SELECT setval('rds_echograms_echogram_id_seq', (SELECT max(echogram_id) FROM rds_echograms)+1);
SELECT setval('rds_landmarks_landmark_id_seq', (SELECT max(landmark_id) FROM rds_landmarks)+1);
SELECT setval('accum_layer_points_layer_points_id_seq', (SELECT max(layer_points_id) FROM accum_layer_points)+1);
SELECT setval('accum_layer_links_layer_link_id_seq', (SELECT max(layer_link_id) FROM accum_layer_links)+1);
SELECT setval('accum_layer_groups_layer_group_id_seq', (SELECT max(layer_group_id) FROM accum_layer_groups)+1);
SELECT setval('accum_layers_layer_id_seq', (SELECT max(layer_id) FROM accum_layers)+1);
SELECT setval('accum_seasons_season_id_seq', (SELECT max(season_id) FROM accum_seasons)+1);
SELECT setval('accum_point_paths_point_path_id_seq', (SELECT max(point_path_id) FROM accum_point_paths)+1);
SELECT setval('accum_locations_location_id_seq', (SELECT max(location_id) FROM accum_locations)+1);
SELECT setval('accum_segments_segment_id_seq', (SELECT max(segment_id) FROM accum_segments)+1);
SELECT setval('accum_crossovers_crossover_id_seq', (SELECT max(crossover_id) FROM accum_crossovers)+1);
SELECT setval('accum_radars_radar_id_seq', (SELECT max(radar_id) FROM accum_radars)+1);
SELECT setval('accum_frames_frame_id_seq', (SELECT max(frame_id) FROM accum_frames)+1);
SELECT setval('accum_echograms_echogram_id_seq', (SELECT max(echogram_id) FROM accum_echograms)+1);
SELECT setval('accum_landmarks_landmark_id_seq', (SELECT max(landmark_id) FROM accum_landmarks)+1);
SELECT setval('snow_layer_points_layer_points_id_seq', (SELECT max(layer_points_id) FROM snow_layer_points)+1);
SELECT setval('snow_layer_links_layer_link_id_seq', (SELECT max(layer_link_id) FROM snow_layer_links)+1);
SELECT setval('snow_layer_groups_layer_group_id_seq', (SELECT max(layer_group_id) FROM snow_layer_groups)+1);
SELECT setval('snow_layers_layer_id_seq', (SELECT max(layer_id) FROM snow_layers)+1);
SELECT setval('snow_seasons_season_id_seq', (SELECT max(season_id) FROM snow_seasons)+1);
SELECT setval('snow_point_paths_point_path_id_seq', (SELECT max(point_path_id) FROM snow_point_paths)+1);
SELECT setval('snow_locations_location_id_seq', (SELECT max(location_id) FROM snow_locations)+1);
SELECT setval('snow_segments_segment_id_seq', (SELECT max(segment_id) FROM snow_segments)+1);
SELECT setval('snow_crossovers_crossover_id_seq', (SELECT max(crossover_id) FROM snow_crossovers)+1);
SELECT setval('snow_radars_radar_id_seq', (SELECT max(radar_id) FROM snow_radars)+1);
SELECT setval('snow_frames_frame_id_seq', (SELECT max(frame_id) FROM snow_frames)+1);
SELECT setval('snow_echograms_echogram_id_seq', (SELECT max(echogram_id) FROM snow_echograms)+1);
SELECT setval('snow_landmarks_landmark_id_seq', (SELECT max(landmark_id) FROM snow_landmarks)+1);
SELECT setval('kuband_layer_points_layer_points_id_seq', (SELECT max(layer_points_id) FROM kuband_layer_points)+1);
SELECT setval('kuband_layer_links_layer_link_id_seq', (SELECT max(layer_link_id) FROM kuband_layer_links)+1);
SELECT setval('kuband_layer_groups_layer_group_id_seq', (SELECT max(layer_group_id) FROM kuband_layer_groups)+1);
SELECT setval('kuband_layers_layer_id_seq', (SELECT max(layer_id) FROM kuband_layers)+1);
SELECT setval('kuband_seasons_season_id_seq', (SELECT max(season_id) FROM kuband_seasons)+1);
SELECT setval('kuband_point_paths_point_path_id_seq', (SELECT max(point_path_id) FROM kuband_point_paths)+1);
SELECT setval('kuband_locations_location_id_seq', (SELECT max(location_id) FROM kuband_locations)+1);
SELECT setval('kuband_segments_segment_id_seq', (SELECT max(segment_id) FROM kuband_segments)+1);
SELECT setval('kuband_crossovers_crossover_id_seq', (SELECT max(crossover_id) FROM kuband_crossovers)+1);
SELECT setval('kuband_radars_radar_id_seq', (SELECT max(radar_id) FROM kuband_radars)+1);
SELECT setval('kuband_frames_frame_id_seq', (SELECT max(frame_id) FROM kuband_frames)+1);
SELECT setval('kuband_echograms_echogram_id_seq', (SELECT max(echogram_id) FROM kuband_echograms)+1);
SELECT setval('kuband_landmarks_landmark_id_seq', (SELECT max(landmark_id) FROM kuband_landmarks)+1);


--Recreate all indexes 
CREATE INDEX rds_point_paths_gps_time ON rds_point_paths (gps_time); 
CREATE INDEX rds_point_paths_point_path_id ON rds_point_paths USING GIST (point_path);
CREATE INDEX rds_layer_points_gps_time ON rds_layer_points (gps_time);
CREATE INDEX rds_layer_points_layer_point_id ON rds_layer_points USING GIST (layer_point);
CREATE INDEX rds_segments_start_gps_time ON rds_segments (start_gps_time);
CREATE INDEX rds_segments_stop_gps_time ON rds_segments (stop_gps_time);
CREATE INDEX rds_segments_line_path_id ON rds_segments USING GIST (line_path);
CREATE INDEX rds_crossovers_gps_time_1 ON rds_crossovers (gps_time_1);
CREATE INDEX rds_crossovers_gps_time_2 ON rds_crossovers (gps_time_2);
CREATE INDEX rds_crossovers_cross_point_id ON rds_crossovers USING GIST (cross_point);
CREATE INDEX rds_frames_start_gps_time ON rds_frames (start_gps_time);
CREATE INDEX rds_frames_stop_gps_time ON rds_frames (stop_gps_time);
CREATE INDEX rds_landmarks_start_gps_time ON rds_landmarks (start_gps_time);
CREATE INDEX rds_landmarks_stop_gps_time ON rds_landmarks (stop_gps_time);
CREATE INDEX rds_landmarks_start_twtt ON rds_landmarks (start_twtt);
CREATE INDEX rds_landmarks_stop_twtt ON rds_landmarks (stop_twtt);
CREATE INDEX accum_point_paths_gps_time ON accum_point_paths (gps_time); 
CREATE INDEX accum_point_paths_point_path_id ON accum_point_paths USING GIST (point_path);
CREATE INDEX accum_layer_points_gps_time ON accum_layer_points (gps_time);
CREATE INDEX accum_layer_points_layer_point_id ON accum_layer_points USING GIST (layer_point);
CREATE INDEX accum_segments_start_gps_time ON accum_segments (start_gps_time);
CREATE INDEX accum_segments_stop_gps_time ON accum_segments (stop_gps_time);
CREATE INDEX accum_segments_line_path_id ON accum_segments USING GIST (line_path);
CREATE INDEX accum_crossovers_gps_time_1 ON accum_crossovers (gps_time_1);
CREATE INDEX accum_crossovers_gps_time_2 ON accum_crossovers (gps_time_2);
CREATE INDEX accum_crossovers_cross_point_id ON accum_crossovers USING GIST (cross_point);
CREATE INDEX accum_frames_start_gps_time ON accum_frames (start_gps_time);
CREATE INDEX accum_frames_stop_gps_time ON accum_frames (stop_gps_time);
CREATE INDEX accum_landmarks_start_gps_time ON accum_landmarks (start_gps_time);
CREATE INDEX accum_landmarks_stop_gps_time ON accum_landmarks (stop_gps_time);
CREATE INDEX accum_landmarks_start_twtt ON accum_landmarks (start_twtt);
CREATE INDEX accum_landmarks_stop_twtt ON accum_landmarks (stop_twtt);
CREATE INDEX snow_point_paths_gps_time ON snow_point_paths (gps_time); 
CREATE INDEX snow_point_paths_point_path_id ON snow_point_paths USING GIST (point_path);
CREATE INDEX snow_layer_points_gps_time ON snow_layer_points (gps_time);
CREATE INDEX snow_layer_points_layer_point_id ON snow_layer_points USING GIST (layer_point);
CREATE INDEX snow_segments_start_gps_time ON snow_segments (start_gps_time);
CREATE INDEX snow_segments_stop_gps_time ON snow_segments (stop_gps_time);
CREATE INDEX snow_segments_line_path_id ON snow_segments USING GIST (line_path);
CREATE INDEX snow_crossovers_gps_time_1 ON snow_crossovers (gps_time_1);
CREATE INDEX snow_crossovers_gps_time_2 ON snow_crossovers (gps_time_2);
CREATE INDEX snow_crossovers_cross_point_id ON snow_crossovers USING GIST (cross_point);
CREATE INDEX snow_frames_start_gps_time ON snow_frames (start_gps_time);
CREATE INDEX snow_frames_stop_gps_time ON snow_frames (stop_gps_time);
CREATE INDEX snow_landmarks_start_gps_time ON snow_landmarks (start_gps_time);
CREATE INDEX snow_landmarks_stop_gps_time ON snow_landmarks (stop_gps_time);
CREATE INDEX snow_landmarks_start_twtt ON snow_landmarks (start_twtt);
CREATE INDEX snow_landmarks_stop_twtt ON snow_landmarks (stop_twtt);
CREATE INDEX kuband_point_paths_gps_time ON kuband_point_paths (gps_time); 
CREATE INDEX kuband_point_paths_point_path_id ON kuband_point_paths USING GIST (point_path);
CREATE INDEX kuband_layer_points_gps_time ON kuband_layer_points (gps_time);
CREATE INDEX kuband_layer_points_layer_point_id ON kuband_layer_points USING GIST (layer_point);
CREATE INDEX kuband_segments_start_gps_time ON kuband_segments (start_gps_time);
CREATE INDEX kuband_segments_stop_gps_time ON kuband_segments (stop_gps_time);
CREATE INDEX kuband_segments_line_path_id ON kuband_segments USING GIST (line_path);
CREATE INDEX kuband_crossovers_gps_time_1 ON kuband_crossovers (gps_time_1);
CREATE INDEX kuband_crossovers_gps_time_2 ON kuband_crossovers (gps_time_2);
CREATE INDEX kuband_crossovers_cross_point_id ON kuband_crossovers USING GIST (cross_point);
CREATE INDEX kuband_frames_start_gps_time ON kuband_frames (start_gps_time);
CREATE INDEX kuband_frames_stop_gps_time ON kuband_frames (stop_gps_time);
CREATE INDEX kuband_landmarks_start_gps_time ON kuband_landmarks (start_gps_time);
CREATE INDEX kuband_landmarks_stop_gps_time ON kuband_landmarks (stop_gps_time);
CREATE INDEX kuband_landmarks_start_twtt ON kuband_landmarks (start_twtt);
CREATE INDEX kuband_landmarks_stop_twtt ON kuband_landmarks (stop_twtt);

--Recreate table constraints (foreign keys)
DO $body$
DECLARE r record;
BEGIN
	FOR r IN SELECT constraint_name, table_name, column_name, foreign_table_name, foreign_column_name FROM constraint_tab
	LOOP 
		EXECUTE 'ALTER TABLE ' || quote_ident(r.table_name) || ' ADD CONSTRAINT ' || quote_ident(r.constraint_name) || ' FOREIGN KEY (' || quote_ident(r.column_name) || ') REFERENCES ' || quote_ident(r.foreign_table_name) || ' (' || quote_ident(r.foreign_column_name) || ');';
	END LOOP;
	
	DROP TABLE constraint_tab;
END
$body$;

--Vacuum Analyze database to update statistics and cleanup bad rows. 
VACUUM ANALYZE;

--Reset default DB parameters.
SET maintenance_work_mem TO '16MB';


