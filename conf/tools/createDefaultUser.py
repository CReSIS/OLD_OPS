from django.contrib.auth.models import User

# set new user properties
userName = "anonymous"
userEmail = "anonymous@ku.edu"
userPassword = "anonymous"

# create the new user
newUser = User.objects.create_user(userName, userEmail, userPassword)

# set the user profile options (example for cresis superuser)
newUser.profile.rds_layer_groups.set([1, 2])
newUser.profile.accum_layer_groups.set([1, 2])
newUser.profile.kuband_layer_groups.set([1, 2])
newUser.profile.snow_layer_groups.set([1, 2])
newUser.profile.rds_season_groups.set([1, 2])
newUser.profile.accum_season_groups.set([1, 2])
newUser.profile.kuband_season_groups.set([1, 2])
newUser.profile.snow_season_groups.set([1, 2])
newUser.profile.layerGroupRelease.set(True)
newUser.profile.bulkDeleteData.set(False)
newUser.profile.createData.set(True)
newUser.profile.seasonRelease.set(True)

# save the user profile
newUser.profile.save()
