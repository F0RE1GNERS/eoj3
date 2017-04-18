from django.db import models


class SiteSettings(models.Model):
    open = models.BooleanField('site open', default=True)
    migrate_open = models.BooleanField('Open for migrations', default=False)
    broadcast_message = models.CharField('Broadcast', max_length=224, blank=True)
    broadcast_link = models.CharField('Broadcast Link', max_length=224, blank=True)


def get_site_settings():
    if not SiteSettings.objects.exists():
        SiteSettings.objects.create()
    return SiteSettings.objects.first()
