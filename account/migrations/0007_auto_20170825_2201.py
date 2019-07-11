# -*- coding: utf-8 -*-
# Generated by Django 1.10.4 on 2017-08-25 22:01
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('account', '0006_auto_20170729_1034'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='polygon_enabled',
            field=models.BooleanField(default=False),
        ),
        migrations.AlterField(
            model_name='user',
            name='preferred_lang',
            field=models.CharField(choices=[('c', 'C'), ('cpp', 'C++11'), ('python', 'Python 3'), ('java', 'Java 8'), ('cc14', 'C++14'), ('cs', 'C#'), ('py2', 'Python 2'), ('php', 'PHP 7'), ('perl', 'Perl'), ('hs', 'Haskell'), ('js', 'Javascript'), ('ocaml', 'OCaml'), ('pypy', 'PyPy'), ('pas', 'Pascal'), ('rs', 'Rust')], default='cpp', max_length=12, verbose_name='preferred language'),
        ),
    ]
