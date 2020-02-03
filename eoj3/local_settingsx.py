import os

BASE_DIR = '/eoj3'

REPO_DIR = os.path.join(BASE_DIR, 'repo')
TESTDATA_DIR = os.path.join(BASE_DIR, 'testdata')
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
UPLOAD_DIR = os.path.join(BASE_DIR, "upload")
MIRROR_DIR = os.path.join(BASE_DIR, "upload", "mirror")
GENERATE_DIR = os.path.join(BASE_DIR, "generate")

DATABASES = {
  'default': {
    'ENGINE': 'django.db.backends.mysql',
    'NAME': 'eoj',
    'CONN_MAX_AGE': 2,
    'HOST': '172.25.0.4',
    'PORT': 3306,
    'USER': 'root',
    'PASSWORD': '123456'
  }
}