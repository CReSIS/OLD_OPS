"""
WSGI config for ops project.

This module contains the WSGI application used by Django's development server
and any production WSGI deployments. It should expose a module-level variable
named ``application``. Django's ``runserver`` and ``runfcgi`` commands discover
this application via the ``WSGI_APPLICATION`` setting.

Usually you will have the standard Django WSGI application here, but it also
might make sense to replace the whole Django WSGI application with a custom one
that later delegates to the Django one. For example, you could introduce WSGI
middleware here, or combine a Django application with an application of another
framework.

"""
import os
import sys
import site
import ops.monitor

#Use the monitor to restart the Daemon WSGI process on changes
ops.monitor.start(interval=1.0)

#Add the site-packages of the OPS virtualenv
site.addsitedir('/usr/bin/venv/lib/python2.7/site-packages')

#Add ops directory to the PYTHONPATH
sys.path.append('/var/django/ops/')
sys.path.append('/var/django/ops/ops/')

# We defer to a DJANGO_SETTINGS_MODULE already in the environment. This breaks
# if running multiple sites in the same mod_wsgi process. To fix this, use
# mod_wsgi daemon mode with each site in its own daemon process, or use
# os.environ["DJANGO_SETTINGS_MODULE"] = "ops.settings"
os.environ["DJANGO_SETTINGS_MODULE"] = "ops.settings"

#Activate VIRTUALENV (OPS)
activate_env=os.path.expanduser('/usr/bin/venv/bin/activate_this.py')
exec(compile(open(activate_env, "rb").read(), activate_env, 'exec'),dict(__file__=activate_env))

# This application object is used by any WSGI server configured to use this
# file. This includes Django's development server, if the WSGI_APPLICATION
# setting points here.
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()

# Apply WSGI middleware here.
# from helloworld.wsgi import HelloWorldApplication
# application = HelloWorldApplication(application)
