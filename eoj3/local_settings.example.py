DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'eoj',
        'CONN_MAX_AGE': 5,
        'HOST': '127.0.0.1',
        'PORT': 3306,
        'USER': 'root',
        'PASSWORD': 'root'
    }
}

SECRET_KEY = 'naive'
DEBUG = False

EMAIL_HOST = ""
EMAIL_HOST_USER = ""
EMAIL_HOST_PASSWORD = ""
DEFAULT_FROM_EMAIL = ""
EMAIL_PORT = 25
EMAIL_USE_TLS = True
ADMINS = [('ultmaster', 'scottyugochang@hotmail.com'), ('zerol', 'zerolfx0@gmail.com')]
ADMIN_EMAIL = ""
