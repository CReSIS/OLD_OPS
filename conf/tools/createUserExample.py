# run this with the following completed:
#	(1) As root user (sudo -i)
#	(2) VirtualEnv activated: (source /usr/bin/venv/bin/activate
#	(3) Inside the Django shell (python /var/django/ops/mange.py shell)

from django.contrib.auth.models import User

# set new user properties
userName=''
userEmail=''
userPassword=''

# create the new user
newUser = User.objects.create_user(userName, userEmail, userPassword)

# get the new users profile
userProfile = newUser.get_profile()

# set the user profile options (example for cresis superuser)
userProfile.rds_layer_groups = [1,2,4] #4=atm(OPS2)
userProfile.accum_layer_groups = [1,2]
userProfile.kuband_layer_groups = [1,2]
userProfile.snow_layer_groups = [1,2]
userProfile.rds_season_groups = [1,2]
userProfile.accum_season_groups = [1,2]
userProfile.kuband_season_groups = [1,2]
userProfile.snow_season_groups = [1,2]
userProfile.layerGroupRelease = True
userProfile.bulkDeleteData = True
userProfile.createData = True
userProfile.seasonRelease = True

# save the user profile
userProfile.save()