from django.conf.urls import url
from . import views

app_name = "blog"

urlpatterns = [
  url(r'^(?P<pk>\d+)/$', views.GenericView.as_view(), name='index'),
  url(r'^create/$', views.BlogCreate.as_view(), name='create'),
  url(r'^update/(?P<pk>\d+)/$', views.BlogUpdate.as_view(), name='update'),
  url(r'^entry/(?P<pk>\d+)/$', views.BlogView.as_view(), name='detail'),
  url(r'^entry/(?P<pk>\d+)/revision/(?P<rpk>\d+)/$', views.BlogRevisionView.as_view(), name='revision_detail'),
  url(r'^entry/(?P<pk>\d+)/comment/$', views.BlogAddComment.as_view(), name='add_comment'),
  url(r'^entry/(?P<pk>\d+)/comment/(?P<comment_id>\d+)/delete/$', views.BlogDeleteComment.as_view(),
      name='delete_comment'),
  url(r'^feedback/', views.LikeBlog.as_view(), name='like'),
  url(r'^reward/$', views.RewardView.as_view(), name='reward')
]
