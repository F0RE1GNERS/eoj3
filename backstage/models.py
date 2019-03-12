from django.db import models

from account.models import User
from dispatcher.models import Server
from problem.models import Problem


class Email(models.Model):
    title = models.CharField("标题", max_length=192)
    content = models.TextField("内容", blank=True)
    create_time = models.DateTimeField("创建时间", auto_now_add=True)
    update_time = models.DateTimeField("更新时间", auto_now=True)
    created_by = models.ForeignKey(User, null=True, related_name="sent_emails", on_delete=models.SET_NULL)
    recipients = models.ManyToManyField(User, through='EmailRecipient', related_name='received_emails')


class EmailRecipient(models.Model):
    email = models.ForeignKey(Email, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    status = models.IntegerField(choices=(
        (-1, 'Pending'),
        (0, 'OK'),
        (1, 'Failed')
    ), default=-1)
    create_time = models.DateTimeField(auto_now_add=True)
    update_time = models.DateTimeField(auto_now=True)
    error_message = models.TextField(blank=True)


class UpdateLog(models.Model):
    create_time = models.DateTimeField(auto_now_add=True)
    log_type = models.CharField(max_length=10, choices=(
        ('fix', '问题修复'),
        ('add', '新功能'),
        ('del', '删除功能'),
        ('ref', '重构'),
        ('upd', '更新'),
        ('enhance', '加强'),
    ))
    priority = models.PositiveIntegerField(choices=(
        (0, 'CRITICAL'),
        (1, 'HIGH'),
        (2, 'MEDIUM'),
        (3, 'LOW'),
    ))
    is_about_polygon = models.BooleanField(default=False)
    created_by = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)
    content = models.TextField()
