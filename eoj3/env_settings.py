# configurable settings

import os

# host & ip

if 'ALLOWED_HOSTS' in os.environ:
  ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS').split(';')

if 'PRIVATE_IP' in os.environ:
  IPWARE_PRIVATE_IP_PREFIX = tuple(os.getenv('PRIVATE_IP').split(';'))

if 'WHITE_LIST' in os.environ:
  WHITE_LIST_HOST = os.getenv('WHITE_LIST').split(';')

# path

if 'REPO_DIR' in os.environ:
  REPO_DIR = os.getenv('REPO_DIR')
if 'TESTDATA_DIR' in os.environ:
  TESTDATA_DIR = os.getenv('TESTDATA_DIR')
if 'MEDIA_ROOT' in os.environ:
  MEDIA_ROOT = os.getenv('MEDIA_ROOT')

if 'UPLOAD_DIR' in os.environ:
  UPLOAD_DIR = os.getenv('UPLOAD_DIR')
if 'MIRROR_DIR' in os.environ:
  MIRROR_DIR = os.getenv('MIRROR_DIR')
if 'GENERATE_DIR' in os.environ:
  GENERATE_DIR = os.getenv('GENERATE_DIR')

# database

DATABASES = {
  'default': {
    'ENGINE': 'django.db.backends.mysql',
    'NAME': os.getenv('DATABASE_NAME', 'eoj'),
    'CONN_MAX_AGE': 2,
    'HOST': os.getenv('DATABASE_HOST', '127.0.0.1'),
    'PORT': int(os.getenv('DATABASE_PORT', '3306')),
    'USER': os.getenv('DATABASE_USER', 'eoj'),
    'PASSWORD': os.getenv('DATABASE_PASSWD', 'eoj'),
  }
}

# cache

CACHES = {
  "default": {
    "BACKEND": "django_redis.cache.RedisCache",
    "LOCATION": "redis://" + os.getenv('REDIS_HOST', '127.0.0.1:6379') + "/1",
    "OPTIONS": {
      "CLIENT_CLASS": "django_redis.client.DefaultClient",
      "MAX_ENTRIES": 65536,
    }
  },
  "judge": {
    "BACKEND": "django_redis.cache.RedisCache",
    "LOCATION": "redis://" + os.getenv('REDIS_HOST', '127.0.0.1:6379') + "/2",
    "OPTIONS": {
      "CLIENT_CLASS": "django_redis.client.DefaultClient",
      "MAX_ENTRIES": 65536,
    }
  }
}

# security

SECRET_KEY = os.getenv('SECRET_KEY')
DEBUG = os.getenv('DEBUG', 'False') == 'True'

# qcluster

if 'CLUSTER_WORKER' in os.environ:
  Q_CLUSTER = {
    'name': 'eoj_cluster',
    'workers': int(os.getenv('CLUSTER_WORKER', '24')),
    'recycle': 20,
    'timeout': 14400,  # 4 hours
    'retry': None,
    'cached': 3600,
    'queue_limit': 3000,
    'cpu_affinity': 1,
    'django_redis': 'default',
    'log_level': 'WARNING',
  }

# email

if 'EMAIL_HOST' in os.environ:
  EMAIL_HOST = os.getenv('EMAIL_HOST')
  EMAIL_HOST_USER = os.getenv('EMAIL_USER')
  EMAIL_HOST_PASSWORD = os.getenv('EMAIL_PASSWD')
  SERVER_EMAIL = EMAIL_HOST_USER
  DEFAULT_FROM_EMAIL = EMAIL_HOST_USER
  EMAIL_PORT = int(os.getenv('EMAIL_PORT', '465'))
  EMAIL_USE_SSL = os.getenv('EMAIL_SSD', 'True') == 'True'

if 'ADMIN_EMAIL' in os.environ:
  ADMIN_EMAIL_LIST = os.getenv('ADMIN_EMAIL').split(';')
  ADMINS = [(os.getenv('ADMIN_NAME', 'support'), ADMIN_EMAIL_LIST[0])]

# recommendation service

if 'RECOMMENDATION_SERVICE' in os.environ:
  RECOMMENDATION_SERVICE_URL = os.getenv('RECOMMENDATION_SERVICE')
