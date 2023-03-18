# After editing the script (e.g. with gedit), run this script by following these steps:
# 	(1) Switch to root user: sudo -i
# 	(2) Activate VirtualEnv: source /usr/bin/venv/bin/activate
# 	(3) Open a Python shell with Django environment: python /var/django/ops/manage.py shell
#       (4) Run this script: exec(open("./createUserExample.py").read())
#       (5) Press ctrl-d or type quit() or exit()

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
newUser.profile.layerGroupRelease = True
newUser.profile.bulkDeleteData = False
newUser.profile.createData = True
newUser.profile.seasonRelease = True

# save the user profile
newUser.profile.save()
