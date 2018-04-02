from django.conf import settings
from django.db import models
from django.core.cache import cache
from dateutil.parser import parse as datetime_parse
from datetime import datetime as dt
import datetime

from account.permissions import is_admin_or_root


class SiteSettings(models.Model):
    # We store key, value pair here
    key = models.CharField(max_length=254, primary_key=True)
    val = models.TextField(blank=True)


def site_settings_get(key, default=None, use_cache=False):
    try:
        cache_key = 'site_settings_' + key
        get_from_cache = cache.get(cache_key)
        if use_cache and get_from_cache:
            return get_from_cache
        value = SiteSettings.objects.get(key=key).val
        cache.set(cache_key, value, 300)
        return value
    except SiteSettings.DoesNotExist:
        return default


def site_settings_set(key, val):
    if not SiteSettings.objects.filter(key=key).exists():
        SiteSettings.objects.create(key=key, val=val)
    else:
        settings = SiteSettings.objects.get(key=key)
        settings.val = val
        settings.save(update_fields=['val'])
    cache.set('site_settings_' + key, val, 300)


def is_site_closed(request):
    if is_admin_or_root(request.user):
        return False
    if request.META.get("HTTP_HOST", '').split(":")[0] in settings.WHITE_LIST_HOST:
        return False
    return True


def is_festival():
    return site_settings_get("FESTIVAL", default=False, use_cache=True)


def force_closed():
    return {"force_closed": True}
