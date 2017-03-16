from django.db import models
from account.models import User


class Group(models.Model):
    name = models.CharField(max_length=30, unique=True)
    description = models.TextField()
    members = models.ManyToManyField(User, through='GroupMembership')
    created_by = models.ForeignKey(User, related_name='my_groups')

    def __str__(self):
        return self.name


class GroupMembership(models.Model):
    group = models.ForeignKey(Group)
    user = models.ForeignKey(User)
    comment = models.CharField(max_length=48, blank=True)
    join_time = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('group', 'user')

    def __str__(self):
        return "%s - %s" % (self.group.name, self.user.username)