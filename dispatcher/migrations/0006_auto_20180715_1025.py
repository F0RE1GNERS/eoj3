# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2018-07-15 10:25
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('problem', '0021_auto_20180713_1421'),
        ('dispatcher', '0005_server_runtime_multiplier'),
    ]

    operations = [
        migrations.CreateModel(
            name='ServerProblemStatus',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('last_status', models.TextField(blank=True)),
                ('last_synchronize', models.DateTimeField(auto_now=True)),
                ('problem', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='problem.Problem')),
                ('server', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='dispatcher.Server')),
            ],
        ),
        migrations.AlterUniqueTogether(
            name='serverproblemstatus',
            unique_together=set([('server', 'problem')]),
        ),
    ]
