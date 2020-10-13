from django.contrib.gis.db import models


class locations(models.Model):

    name = models.CharField(max_length=20)

    def __unicode__(self):
        return "%s" % (self.name)


class seasons(models.Model):

    location = models.ForeignKey("locations")
    season_group = models.ForeignKey("season_groups")
    name = models.CharField(max_length=50)

    def __unicode__(self):
        return "%s" % (self.name)


class season_groups(models.Model):

    name = models.CharField(max_length=200)
    description = models.CharField(max_length=200, blank=True)
    public = models.BooleanField(default=False)

    def __unicode__(self):
        return "%s" % (self.name)


class radars(models.Model):

    name = models.CharField(max_length=20)

    def __unicode__(self):
        return "%s" % (self.name)


class segments(models.Model):

    season = models.ForeignKey("seasons")
    radar = models.ForeignKey("radars")
    name = models.CharField(max_length=20)
    geom = models.LineStringField()
    objects = models.GeoManager()

    def __unicode__(self):
        return "%s" % (self.name)


class frames(models.Model):

    segment = models.ForeignKey("segments")
    name = models.CharField(max_length=20)

    def __unicode__(self):
        return "%s" % (self.name)


class point_paths(models.Model):

    location = models.ForeignKey("locations")
    season = models.ForeignKey("seasons")
    segment = models.ForeignKey("segments")
    frame = models.ForeignKey("frames")
    gps_time = models.DecimalField(max_digits=16, decimal_places=6, db_index=True)
    roll = models.DecimalField(max_digits=6, decimal_places=5)
    pitch = models.DecimalField(max_digits=6, decimal_places=5)
    heading = models.DecimalField(max_digits=6, decimal_places=5)
    geom = models.PointField(dim=3)
    objects = models.GeoManager()

    def __unicode__(self):
        return "%d" % (self.id)


class crossovers(models.Model):

    point_path_1 = models.ForeignKey(
        "point_paths", related_name="point_paths_link_fk_1"
    )
    point_path_2 = models.ForeignKey(
        "point_paths", related_name="point_paths_link_fk_2"
    )
    angle = models.DecimalField(max_digits=6, decimal_places=3)
    geom = models.PointField()
    objects = models.GeoManager()

    def __unicode__(self):
        return "%d" % (self.id)


class layer_groups(models.Model):

    name = models.CharField(max_length=200)
    description = models.CharField(max_length=200, blank=True)
    public = models.BooleanField(default=False)

    def __unicode__(self):
        return "%s" % (self.name)


class layers(models.Model):

    id = models.AutoField(primary_key=True)
    layer_group = models.ForeignKey("layer_groups")
    name = models.CharField(max_length=20)
    description = models.CharField(max_length=200, blank=True)
    deleted = models.BooleanField(default=False)

    def __unicode__(self):
        return "%s" % (self.name)


class layer_links(models.Model):

    layer_1 = models.ForeignKey("layers", related_name="layer_link_fk_1")
    layer_2 = models.ForeignKey("layers", related_name="layer_link_fk_2")

    def __unicode__(self):
        return "%d" % (self.id)


class layer_points(models.Model):

    # import User for 'user_id' column
    from django.contrib.auth.models import User

    layer = models.ForeignKey("layers")
    point_path = models.ForeignKey("point_paths")
    twtt = models.DecimalField(max_digits=12, decimal_places=11, blank=True, null=True)
    type = models.IntegerField(blank=True, null=True)  # 1:manual,2:auto
    quality = models.IntegerField(blank=True, null=True)  # 1:good,2:moderate,3:derived
    user = models.ForeignKey(User, related_name="snow_user_id_fk")
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("layer", "point_path")

    def __unicode__(self):
        return "%d" % (self.id)


class landmarks(models.Model):

    radar = models.ForeignKey("radars")
    segment = models.ForeignKey("segments")
    point_path_1 = models.ForeignKey(
        "point_paths", related_name="point_paths_link_fk2_1"
    )
    point_path_2 = models.ForeignKey(
        "point_paths", related_name="point_paths_link_fk2_2"
    )
    start_twtt = models.DecimalField(max_digits=12, decimal_places=11, db_index=True)
    stop_twtt = models.DecimalField(max_digits=12, decimal_places=11, db_index=True)
    description = models.CharField(max_length=200, blank=True, null=True)

    def __unicode__(self):
        return "%d" % (self.id)
