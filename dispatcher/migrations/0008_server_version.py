# Generated by Django 2.1.7 on 2019-03-17 20:36

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dispatcher', '0007_auto_20181106_1212'),
    ]

    operations = [
        migrations.AddField(
            model_name='server',
            name='version',
            field=models.PositiveIntegerField(default=2, verbose_name='判题机版本'),
            preserve_default=False,
        ),
    ]
