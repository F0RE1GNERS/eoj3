# Generated by Django 2.1.7 on 2019-03-05 19:34

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('problem', '0026_auto_20190115_1821'),
    ]

    operations = [
        migrations.AddField(
            model_name='userstatus',
            name='predict_list',
            field=models.TextField(blank=True),
        ),
        migrations.AlterField(
            model_name='userstatus',
            name='ac_list',
            field=models.TextField(blank=True),
        ),
        migrations.AlterField(
            model_name='userstatus',
            name='total_list',
            field=models.TextField(blank=True),
        ),
    ]
