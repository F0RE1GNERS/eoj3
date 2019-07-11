from datetime import datetime, timedelta

from django.db import models

from account.models import User
from utils.language import LANG_CHOICE


class Paste(models.Model):
    fingerprint = models.CharField("指纹", unique=True, max_length=64)
    code = models.TextField("代码", blank=False)
    lang = models.CharField("语言", default='cpp', max_length=12, choices=LANG_CHOICE)
    created_by = models.ForeignKey(User, null=True, related_name="created_pastes", on_delete=models.SET_NULL)
    public_access = models.PositiveIntegerField("访问权限", choices=(
        (0, '只有自己可见'),
        (10, '对受邀用户可见'),
        (20, '对所有人可见')
    ), default=20)
    create_time = models.DateTimeField(auto_now_add=True)
    invited_users = models.ManyToManyField(User, verbose_name="受邀用户", related_name="invited_pastes")
    is_deleted = models.BooleanField(default=False)
    expire_after = models.IntegerField(verbose_name="过期", choices=(
        (-1, '永不'),
        (1, '1 分钟'),
        (10, '10 分钟'),
        (60, '1 小时'),
        (300, '5 小时'),
        (1440, '1 天'),
        (43200, '30 天'),
    ), default=-1)

    @property
    def expired(self):
        return self.expire_after > 0 and datetime.now() > timedelta(minutes=self.expire_after) + self.create_time
