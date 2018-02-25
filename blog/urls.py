from django.conf.urls import url
from . import views

urlpatterns = [
    url('^goto/$', views.BlogGoto.as_view(), name='goto'),
    url('^create/$', views.BlogCreate.as_view(), name='create'),
    url('^update/(?P<pk>\d+)/$', views.BlogUpdate.as_view(), name='update'),
    url('^entry/(?P<pk>\d+)/$', views.BlogView.as_view(), name='detail'),
    url('^entry/(?P<pk>\d+)/revision/(?P<rpk>\d+)/$', views.BlogRevisionView.as_view(), name='revision_detail'),
    url('^entry/(?P<pk>\d+)/comment/$', views.BlogAddComment.as_view(), name='add_comment'),
    url('^entry/(?P<pk>\d+)/comment/(?P<comment_id>\d+)/delete/$', views.BlogDeleteComment.as_view(), name='delete_comment'),
    url('^feedback/', views.LikeBlog.as_view(), name='like'),
    # url('^discuss/(?P<pk>\d+)/$', views.ProblemDiscuss.as_view(), name='discuss'),
    # url('^discuss/(?P<pk>\d+)/comment/$', views.ProblemAddComment.as_view(), name='problem_add_comment'),
    # url('^discuss/(?P<pk>\d+)/comment/(?P<comment_id>\d+)/delete/$', views.ProblemDeleteComment.as_view(), name='problem_delete_comment'),
]
