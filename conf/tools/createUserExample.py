# run this with the following completed:
#	(1) As root user (sudo -i)
#	(2) VirtualEnv activated: (source /usr/bin/venv/bin/activate
#	(3) Inside the Django shell (python /var/django/ops/manage.py shell)

from django.contrib.auth.models import User

# set new user properties
userName='anonymous'
userEmail='anonymous@ku.edu'
userPassword='anonymous'

# create the new user
newUser = User.objects.create_user(userName, userEmail, userPassword)

# set the user profile options (example for cresis superuser)
newUser.profile.rds_layer_groups = [1,2]
newUser.profile.accum_layer_groups = [1,2]
newUser.profile.kuband_layer_groups = [1,2]
newUser.profile.snow_layer_groups = [1,2]
newUser.profile.rds_season_groups = [1,2]
newUser.profile.accum_season_groups = [1,2]
newUser.profile.kuband_season_groups = [1,2]
newUser.profile.snow_season_groups = [1,2]
newUser.profile.layerGroupRelease = True
newUser.profile.bulkDeleteData = False
newUser.profile.createData = True
newUser.profile.seasonRelease = True

# save the user profile
newUser.profile.save()
