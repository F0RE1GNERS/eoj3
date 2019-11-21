"""
WSGI config for eoj3 project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/1.10/howto/deployment/wsgi/
"""

import os
from os.path import dirname, abspath

from django.core.wsgi import get_wsgi_application

PROJECT_DIR = dirname(dirname(abspath(__file__)))
import sys  # pylint: disable=wrong-import-position,wrong-import-order

sys.path.insert(0, PROJECT_DIR)
sys.path.insert(0, dirname(PROJECT_DIR))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "eoj3.settings")

application = get_wsgi_application()
