from django.db import models
from django.core.cache import cache


class SiteSettings(models.Model):
    # We store key, value pair here
    key = models.CharField(max_length=254, primary_key=True)
    val = models.TextField(blank=True)


def site_settings_get(key, use_cache=False):
    try:
        cache_key = 'site_settings_' + key
        get_from_cache = cache.get(cache_key)
        if use_cache and get_from_cache:
            return get_from_cache
        value = SiteSettings.objects.get(key=key).val
        cache.set(cache_key, value, 300)
        return value
    except models.Model.DoesNotExist:
        return None


def site_settings_set(key, val):
    SiteSettings.objects.update_or_create(key=key, val=val)
    cache.set('site_settings_' + key, val, 300)
