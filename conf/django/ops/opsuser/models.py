from django.contrib.gis.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save


class UserProfile(models.Model):
    user = models.OneToOneField(User, related_name="profile", unique=True, on_delete=models.CASCADE)
    rds_season_groups = models.ManyToManyField("rds.season_groups")
    rds_layer_groups = models.ManyToManyField("rds.layer_groups")
    accum_season_groups = models.ManyToManyField("accum.season_groups")
    accum_layer_groups = models.ManyToManyField("accum.layer_groups")
    snow_season_groups = models.ManyToManyField("snow.season_groups")
    snow_layer_groups = models.ManyToManyField("snow.layer_groups")
    kuband_season_groups = models.ManyToManyField("kuband.season_groups")
    kuband_layer_groups = models.ManyToManyField("kuband.layer_groups")
    layerGroupRelease = models.BooleanField(default=False)
    seasonRelease = models.BooleanField(default=False)
    createData = models.BooleanField(default=False)
    bulkDeleteData = models.BooleanField(default=False)
    isRoot = models.BooleanField(default=False)

    def create_profile(sender, instance, created, **kwargs):
        if created:
            profile, created = UserProfile.objects.get_or_create(user=instance)
            profile.rds_season_groups.set([1])
            profile.accum_season_groups.set([1])
            profile.snow_season_groups.set([1])
            profile.kuband_season_groups.set([1])
            profile.rds_layer_groups.set([1, 2])
            profile.accum_layer_groups.set([1, 2])
            profile.snow_layer_groups.set([1, 2])
            profile.kuband_layer_groups.set([1, 2])

    post_save.connect(create_profile, sender=User)
