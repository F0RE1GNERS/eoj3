# Generated by Django 2.1.7 on 2019-03-15 11:34

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('submission', '0030_submissionreport'),
    ]

    operations = [
        migrations.AlterField(
            model_name='submission',
            name='lang',
            field=models.CharField(choices=[('c', 'C'), ('cpp', 'C++11'), ('cc14', 'C++14'), ('cc17', 'C++17'), ('py2', 'Python 2'), ('python', 'Python 3'), ('pypy', 'PyPy'), ('pypy3', 'PyPy 3'), ('java', 'Java 8'), ('pas', 'Pascal'), ('scala', 'Scala'), ('text', 'Text')], default='cpp', max_length=12, null=True),
        ),
    ]
