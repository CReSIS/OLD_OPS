--Set sequences for primary keys to begin at max value inserted from initial data + 1.
SELECT setval('rds_layer_points_id_seq', (SELECT max(id) FROM rds_layer_points)+1);
SELECT setval('rds_layer_links_id_seq', (SELECT max(id) FROM rds_layer_links)+1);
SELECT setval('rds_layer_groups_id_seq', (SELECT max(id) FROM rds_layer_groups)+1);
SELECT setval('rds_layers_id_seq', (SELECT max(id) FROM rds_layers)+1);
SELECT setval('rds_seasons_id_seq', (SELECT max(id) FROM rds_seasons)+1);
SELECT setval('rds_point_paths_id_seq', (SELECT max(id) FROM rds_point_paths)+1);
SELECT setval('rds_locations_id_seq', (SELECT max(id) FROM rds_locations)+1);
SELECT setval('rds_segments_id_seq', (SELECT max(id) FROM rds_segments)+1);
SELECT setval('rds_crossovers_id_seq', (SELECT max(id) FROM rds_crossovers)+1);
SELECT setval('rds_radars_id_seq', (SELECT max(id) FROM rds_radars)+1);
SELECT setval('rds_frames_id_seq', (SELECT max(id) FROM rds_frames)+1);
SELECT setval('rds_landmarks_id_seq', (SELECT max(id) FROM rds_landmarks)+1);
SELECT setval('accum_layer_points_id_seq', (SELECT max(id) FROM accum_layer_points)+1);
SELECT setval('accum_layer_links_id_seq', (SELECT max(id) FROM accum_layer_links)+1);
SELECT setval('accum_layer_groups_id_seq', (SELECT max(id) FROM accum_layer_groups)+1);
SELECT setval('accum_layers_id_seq', (SELECT max(id) FROM accum_layers)+1);
SELECT setval('accum_seasons_id_seq', (SELECT max(id) FROM accum_seasons)+1);
SELECT setval('accum_point_paths_id_seq', (SELECT max(id) FROM accum_point_paths)+1);
SELECT setval('accum_locations_id_seq', (SELECT max(id) FROM accum_locations)+1);
SELECT setval('accum_segments_id_seq', (SELECT max(id) FROM accum_segments)+1);
SELECT setval('accum_crossovers_id_seq', (SELECT max(id) FROM accum_crossovers)+1);
SELECT setval('accum_radars_id_seq', (SELECT max(id) FROM accum_radars)+1);
SELECT setval('accum_frames_id_seq', (SELECT max(id) FROM accum_frames)+1);
SELECT setval('accum_landmarks_id_seq', (SELECT max(id) FROM accum_landmarks)+1);
SELECT setval('snow_layer_points_id_seq', (SELECT max(id) FROM snow_layer_points)+1);
SELECT setval('snow_layer_links_id_seq', (SELECT max(id) FROM snow_layer_links)+1);
SELECT setval('snow_layer_groups_id_seq', (SELECT max(id) FROM snow_layer_groups)+1);
SELECT setval('snow_layers_id_seq', (SELECT max(id) FROM snow_layers)+1);
SELECT setval('snow_seasons_id_seq', (SELECT max(id) FROM snow_seasons)+1);
SELECT setval('snow_point_paths_id_seq', (SELECT max(id) FROM snow_point_paths)+1);
SELECT setval('snow_locations_id_seq', (SELECT max(id) FROM snow_locations)+1);
SELECT setval('snow_segments_id_seq', (SELECT max(id) FROM snow_segments)+1);
SELECT setval('snow_crossovers_id_seq', (SELECT max(id) FROM snow_crossovers)+1);
SELECT setval('snow_radars_id_seq', (SELECT max(id) FROM snow_radars)+1);
SELECT setval('snow_frames_id_seq', (SELECT max(id) FROM snow_frames)+1);
SELECT setval('snow_landmarks_id_seq', (SELECT max(id) FROM snow_landmarks)+1);
SELECT setval('kuband_layer_points_id_seq', (SELECT max(id) FROM kuband_layer_points)+1);
SELECT setval('kuband_layer_links_id_seq', (SELECT max(id) FROM kuband_layer_links)+1);
SELECT setval('kuband_layer_groups_id_seq', (SELECT max(id) FROM kuband_layer_groups)+1);
SELECT setval('kuband_layers_id_seq', (SELECT max(id) FROM kuband_layers)+1);
SELECT setval('kuband_seasons_id_seq', (SELECT max(id) FROM kuband_seasons)+1);
SELECT setval('kuband_point_paths_id_seq', (SELECT max(id) FROM kuband_point_paths)+1);
SELECT setval('kuband_locations_id_seq', (SELECT max(id) FROM kuband_locations)+1);
SELECT setval('kuband_segments_id_seq', (SELECT max(id) FROM kuband_segments)+1);
SELECT setval('kuband_crossovers_id_seq', (SELECT max(id) FROM kuband_crossovers)+1);
SELECT setval('kuband_radars_id_seq', (SELECT max(id) FROM kuband_radars)+1);
SELECT setval('kuband_landmarks_id_seq', (SELECT max(id) FROM kuband_landmarks)+1);

--Vacuum Analyze database to update statistics and cleanup bad rows. 
VACUUM ANALYZE;

--Reset default DB parameters.
SET maintenance_work_mem TO '16MB';


