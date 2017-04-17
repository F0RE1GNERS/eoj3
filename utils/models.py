from django.db import models


class SiteSettings(models.Model):
    open = models.BooleanField('site open', default=True)
    broadcast_message = models.CharField('Broadcast', max_length=224, blank=True)
    broadcast_link = models.CharField('Broadcast Link', max_length=224, blank=True)
