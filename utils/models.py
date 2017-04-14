from django.db import models


class SiteSettings(models.Model):
    open = models.BooleanField('site open', default=True)
