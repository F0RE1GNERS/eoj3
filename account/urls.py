from django.conf.urls import url

from .views import security_view, MyGroup

urlpatterns = [
    url(r'^$', security_view, name='security'),
    url(r'^group', MyGroup.as_view(), name='group')
]