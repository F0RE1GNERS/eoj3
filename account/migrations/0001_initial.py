# Generated by Django 2.2.9 on 2020-02-04 02:08

import account.models
from django.conf import settings
import django.contrib.auth.models
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('auth', '0011_update_proxy_permissions'),
    ]

    operations = [
        migrations.CreateModel(
            name='User',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('password', models.CharField(max_length=128, verbose_name='password')),
                ('last_login', models.DateTimeField(blank=True, null=True, verbose_name='last login')),
                ('is_superuser', models.BooleanField(default=False, help_text='Designates that this user has all permissions without explicitly assigning them.', verbose_name='superuser status')),
                ('first_name', models.CharField(blank=True, max_length=30, verbose_name='first name')),
                ('last_name', models.CharField(blank=True, max_length=150, verbose_name='last name')),
                ('is_staff', models.BooleanField(default=False, help_text='Designates whether the user can log into this admin site.', verbose_name='staff status')),
                ('is_active', models.BooleanField(default=True, help_text='Designates whether this user should be treated as active. Unselect this instead of deleting accounts.', verbose_name='active')),
                ('date_joined', models.DateTimeField(default=django.utils.timezone.now, verbose_name='date joined')),
                ('username', models.CharField(error_messages={'unique': 'A user with that username already exists.'}, max_length=30, unique=True, validators=[account.models.UsernameValidator(), account.models.UsernameLengthValidator(6)], verbose_name='用户名')),
                ('email', models.EmailField(error_messages={'unique': 'This email has already been used.'}, max_length=192, unique=True, verbose_name='邮箱')),
                ('school', models.CharField(blank=True, max_length=64, verbose_name='学校')),
                ('name', models.CharField(blank=True, max_length=30, verbose_name='真实姓名')),
                ('student_id', models.CharField(blank=True, max_length=30, verbose_name='学号')),
                ('magic', models.CharField(blank=True, choices=[('red', 'Red'), ('green', 'Green'), ('teal', 'Teal'), ('blue', 'Blue'), ('purple', 'Purple'), ('orange', 'Orange'), ('grey', 'Grey')], max_length=18, verbose_name='魔法')),
                ('show_tags', models.BooleanField(default=True, verbose_name='显示标签')),
                ('preferred_lang', models.CharField(choices=[('c', 'C'), ('cpp', 'C++11'), ('cc14', 'C++14'), ('cc17', 'C++17'), ('py2', 'Python 2'), ('python', 'Python 3'), ('pypy', 'PyPy'), ('pypy3', 'PyPy 3'), ('java', 'Java 8'), ('pas', 'Pascal'), ('text', 'Text')], default='cpp', max_length=12, verbose_name='偏好语言')),
                ('motto', models.CharField(blank=True, max_length=192, verbose_name='警句')),
                ('avatar', models.ImageField(default='avatar/default.jpg', upload_to='avatar', verbose_name='头像')),
                ('polygon_enabled', models.BooleanField(default=False)),
                ('score', models.FloatField(default=0)),
                ('username_change_attempt', models.IntegerField(default=0)),
                ('email_subscription', models.BooleanField(default=True, verbose_name='邮件订阅')),
                ('rating', models.IntegerField(default=0)),
                ('groups', models.ManyToManyField(blank=True, help_text='The groups this user belongs to. A user will get all permissions granted to each of their groups.', related_name='user_set', related_query_name='user', to='auth.Group', verbose_name='groups')),
                ('user_permissions', models.ManyToManyField(blank=True, help_text='Specific permissions for this user.', related_name='user_set', related_query_name='user', to='auth.Permission', verbose_name='user permissions')),
            ],
            options={
                'ordering': ['-score'],
            },
            managers=[
                ('objects', django.contrib.auth.models.UserManager()),
            ],
        ),
        migrations.CreateModel(
            name='School',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=192, unique=True)),
                ('abbr', models.CharField(max_length=192, unique=True)),
                ('alias', models.CharField(blank=True, max_length=192)),
            ],
        ),
        migrations.CreateModel(
            name='Payment',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('type', models.CharField(choices=[('change_username', 'Change Username'), ('download_case', 'Download Case'), ('reward', 'Reward'), ('transfer', 'Transfer')], max_length=20)),
                ('detail_message', models.TextField(blank=True)),
                ('create_time', models.DateTimeField(auto_now_add=True)),
                ('credit', models.FloatField()),
                ('balance', models.FloatField()),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-create_time'],
            },
        ),
    ]
