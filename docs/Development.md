# Development

This tutorial will help you get started with development of EOJ.

## Installation

1. `pip install -r requirements.txt`. Try to use a virtualenv (avoid conda or global env).
2. Install and build static files: `cd static && yarn install && yarn build`.
3. Add your `local_settings.py`. A typical `local_settings.py` would be:

```python
import os

DEBUG = True
PROJECT_PATH = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))

DATABASES = {
  'default': {
    'ENGINE': 'django.db.backends.sqlite3',
    'NAME': os.path.join(PROJECT_PATH, 'database.sqlite'),
  }
}
```

4. Install a Redis server and get it running at 6379.
5. Initialize database: `python manage.py migrate`.
6. Create your first account with `python manage.py createsuperuser`.
7. Launch your development server with `python manage.py runserver 8080`.

## Troublshooting

1. Failed to install `mysqlclient`. This dependency is optional. Temporarily disable `mysqlclient` if installing it is troublesome and you are not using MySQL anyway.
2. Failed to install pycrypto on macOS. The following ticket might be helpful: https://github.com/trailofbits/algo/issues/516.
