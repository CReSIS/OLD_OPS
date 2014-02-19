from django.contrib.gis.db import models

##################################################
# LOCATIONS TABLE
##################################################

class locations(models.Model):
    location_id = models.AutoField(primary_key=True)
    location_name = models.CharField(max_length=20)

    def __unicode__(self):
        return "%s"%(self.location_name)

##################################################
# SEASONS TABLE
##################################################

class seasons(models.Model):
    season_id = models.AutoField(primary_key=True)
    season_name = models.CharField(max_length=50)
    description = models.CharField(max_length=200,blank=True)
    status = models.CharField(max_length=20,default='private')
    location = models.ForeignKey('locations')

    def __unicode__(self):
        return "%s"%(self.season_name)

##################################################
# RADARS TABLE
##################################################

class radars(models.Model):
    radar_id = models.AutoField(primary_key=True)
    radar_name = models.CharField(max_length=20)

    def __unicode__(self):
        return "%s"%(self.radar_name)
    
##################################################
# LAYERS TABLE
##################################################

class layers(models.Model):
	layer_id = models.AutoField(primary_key=True)
	layer_group = models.ForeignKey('layer_groups') 
	layer_name = models.CharField(max_length=20)
	color = models.CharField(max_length=10)
	description = models.CharField(max_length=200,blank=True)
	status = models.CharField(max_length=20,default='normal')

	def __unicode__(self):
		return "%s"%(self.layer_name)

##################################################
# LAYER GROUPS TABLE
##################################################

class layer_groups(models.Model):
    layer_group_id = models.AutoField(primary_key=True)
    group_name = models.CharField(max_length=200)
    description = models.CharField(max_length=200,blank=True)

    def __unicode__(self):
        return "%s"%(self.layer_name)

##################################################
# LAYER_LINKS TABLE
##################################################

class layer_links(models.Model):
    layer_link_id = models.AutoField(primary_key=True)
    layer_1 = models.ForeignKey('layers',related_name='layer_link_fk_1')
    layer_2 = models.ForeignKey('layers',related_name='layer_link_fk_2')
    description = models.CharField(max_length=200,blank=True)

    def __unicode__(self):
        return "%d"%(self.layer_link_id)


##################################################
# POINT_PATHS TABLE
##################################################

class point_paths(models.Model):
    point_path_id = models.AutoField(primary_key=True)
    season = models.ForeignKey('seasons')
    segment = models.ForeignKey('segments')
    gps_time = models.DecimalField(max_digits=20,decimal_places=7,db_index=True)
    roll = models.DecimalField(max_digits=15,decimal_places=13)
    pitch = models.DecimalField(max_digits=15,decimal_places=13)
    heading = models.DecimalField(max_digits=15,decimal_places=10)
    point_path = models.PointField(dim=3)
    objects = models.GeoManager()
    location = models.ForeignKey('locations')

    def __unicode__(self):
        return "%d"%(self.point_path_id)

##################################################
# LAYER_POINTS TABLE
##################################################

class layer_points(models.Model):
    layer_points_id = models.AutoField(primary_key=True)
    layer = models.ForeignKey('layers')
    season = models.ForeignKey('seasons')
    segment = models.ForeignKey('segments')
    gps_time = models.DecimalField(max_digits=20,decimal_places=7,db_index=True)
    twtt = models.DecimalField(max_digits=15,decimal_places=10)
    pick_type = models.IntegerField()
    quality = models.IntegerField()
    username = models.CharField(max_length=20)
    last_updated = models.DateTimeField(auto_now=True)
    layer_point = models.PointField(dim=3)
    objects = models.GeoManager()
    location = models.ForeignKey('locations')

    def __unicode__(self):
        return "%d"%(self.layer_points_id)

##################################################
# SEGMENTS TABLE
##################################################

class segments(models.Model):
    segment_id = models.AutoField(primary_key=True)
    season = models.ForeignKey('seasons')
    radar = models.ForeignKey('radars')
    segment_name = models.CharField(max_length=20)
    start_gps_time = models.DecimalField(max_digits=20,decimal_places=7,db_index=True)
    stop_gps_time = models.DecimalField(max_digits=20,decimal_places=7,db_index=True)
    line_path = models.LineStringField(dim=3)
    objects = models.GeoManager()
    location = models.ForeignKey('locations')
    
    def __unicode__(self):
        return "%s"%(self.segment_name)

##################################################
# FRAMES TABLE
##################################################

class frames(models.Model):
    frame_id = models.AutoField(primary_key=True)
    segment = models.ForeignKey('segments')
    frame_name = models.CharField(max_length=20)
    start_gps_time = models.DecimalField(max_digits=20,decimal_places=7,db_index=True)
    stop_gps_time = models.DecimalField(max_digits=20,decimal_places=7,db_index=True)
    location = models.ForeignKey('locations')

    def __unicode__(self):
        return "%s"%(self.frame_name)

##################################################
# ECHOGRAMS TABLE
##################################################

class echograms(models.Model):
    echogram_id = models.AutoField(primary_key=True)
    frame = models.ForeignKey('frames')
    echogram_url = models.URLField(max_length=500)

    def __unicode__(self):
        return "%s"%(self.echogram_url)

##################################################
# LANDMARKS TABLE
##################################################

class landmarks(models.Model):
    landmark_id = models.AutoField(primary_key=True)
    radar = models.ForeignKey('radars')
    segment = models.ForeignKey('segments')
    start_gps_time = models.DecimalField(max_digits=20,decimal_places=7,db_index=True)
    stop_gps_time = models.DecimalField(max_digits=20,decimal_places=7,db_index=True)
    start_twtt = models.DecimalField(max_digits=15,decimal_places=10,db_index=True)
    stop_twtt = models.DecimalField(max_digits=15,decimal_places=10,db_index=True)
    description = models.CharField(max_length=200,blank=True)
    location = models.ForeignKey('locations')

    def __unicode__(self):
        return "%d"%(self.landmark_id)

##################################################
# CROSSOVERS TABLE
##################################################

class crossovers(models.Model):
    crossover_id = models.AutoField(primary_key=True)
    segment_1 = models.ForeignKey('segments',related_name='segment_link_fk_1')
    segment_2 = models.ForeignKey('segments',related_name='segment_link_fk_2')
    gps_time_1 = models.DecimalField(max_digits=20,decimal_places=7,db_index=True)
    gps_time_2 = models.DecimalField(max_digits=20,decimal_places=7,db_index=True)
    cross_angle = models.DecimalField(max_digits=10,decimal_places=5)
    cross_point = models.PointField()
    objects = models.GeoManager()
    location = models.ForeignKey('locations')

    def __unicode__(self):
        return "%d"%(self.crossover_id)