DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'eoj',
        'CONN_MAX_AGE': 0.1,
        'HOST': '127.0.0.1',
        'PORT': 3306,
        'USER': 'root',
        'PASSWORD': 'root'
    }
}

SECRET_KEY = 'naive'
DEBUG = True