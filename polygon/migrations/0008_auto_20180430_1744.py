# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2018-04-30 17:44
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('polygon', '0007_task'),
    ]

    operations = [
        migrations.AddField(
            model_name='case',
            name='group',
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='revision',
            name='enable_group',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='revision',
            name='group_dependencies',
            field=models.TextField(blank=True),
        ),
    ]
