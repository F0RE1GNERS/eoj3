from django.db import models
from django.core.cache import cache
from dateutil.parser import parse as datetime_parse
from datetime import datetime as dt
import datetime


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


def is_site_closed():
    site_close = site_settings_get("SITE_CLOSE")
    if site_close is None or site_close == '0':
        return False
    try:
        def default():
            st, ed = site_settings_get("SITE_CLOSE_START"), site_settings_get('SITE_CLOSE_END')
            if st and ed:
                return datetime_parse(st), datetime_parse(ed)
            return dt(1970, 1, 1), dt(2999, 12, 31)
        start_time, end_time = cache.get_or_set("SITE_CLOSE_TIME_INTERVAL", default)
        return start_time <= dt.now() <= end_time
    except ValueError:
        return True


def is_festival():
    return site_settings_get("FESTIVAL", default=False, use_cache=True)