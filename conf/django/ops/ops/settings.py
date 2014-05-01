"""
Django settings for ops project.

For more information on this file, see
https://docs.djangoproject.com/en/1.6/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.6/ref/settings/
"""

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
import os
BASE_DIR = os.path.dirname(os.path.dirname(__file__))

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.6/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
with open('/etc/secret_key.txt') as f:
    SECRET_KEY = f.read().strip()

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

TEMPLATE_DEBUG = DEBUG

ADMINS = (
	('Kyle Purdon','kylepurdon@gmail.com'),
	('Trey Stafford','treystaff@gmail.com'),
)

ALLOWED_HOSTS = ['ops.cresis.ku.edu','ops2.cresis.ku.edu','192.168.111.222']

# Application definition
INSTALLED_APPS = (
	#'django.contrib.admin',
	'django.contrib.auth',
	'django.contrib.contenttypes',
	#'django.contrib.sessions',
	'django.contrib.messages',
	'django.contrib.staticfiles',
	'django.contrib.gis',
	'django_extensions',
	'rds',
	'accum',
	'snow',
	'kuband',
	'opsuser',
)

AUTH_PROFILE_MODULE = 'opsuser.UserProfile'

# Sessions
# https://docs.djangoproject.com/en/dev/ref/settings/#sessions

SESSION_ENGINE = 'django.contrib.sessions.backends.signed_cookies'
SESSION_COOKIE_NAME = 'opssession'
SESSION_COOKIE_PATH = '/ops'
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SESSION_COOKIE_HTTPONLY = True

MIDDLEWARE_CLASSES = (
	'django.contrib.sessions.middleware.SessionMiddleware',
	'django.middleware.common.CommonMiddleware',
	#'django.middleware.csrf.CsrfViewMiddleware',
	'django.contrib.auth.middleware.AuthenticationMiddleware',
	'django.contrib.messages.middleware.MessageMiddleware',
	'django.middleware.clickjacking.XFrameOptionsMiddleware',
)

ROOT_URLCONF = 'ops.urls'

WSGI_APPLICATION = 'ops.wsgi.application'

# Database
# https://docs.djangoproject.com/en/1.6/ref/settings/#databases

with open('/etc/db_pswd.txt') as f:
    DB_PSWD = f.read().strip()

DATABASES = {
	'default': {
		'ENGINE': 'django.contrib.gis.db.backends.postgis',
		'NAME': 'ops',
		'USER': 'admin',
		'PASSWORD': DB_PSWD,
		'HOST': '',
		'PORT': '',
	}
}

# Internationalization
# https://docs.djangoproject.com/en/1.6/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = False

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.6/howto/static-files/

STATIC_URL = '/static/'
