from django.contrib import admin
from .models import Group, GroupMembership

admin.site.register(Group)
admin.site.register(GroupMembership)