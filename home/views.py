from random import randint

from django.core.cache import cache
from django.shortcuts import render, redirect
from django.urls import reverse
from django.views.generic import TemplateView
from django_comments_xtd.models import XtdComment

from account.models import User
from account.permissions import StaffRequiredMixin
from blog.models import Blog
from problem.statistics import get_accept_problem_count
from utils.hash import sha_hash
from utils.site_settings import is_site_closed, site_settings_get


def home_view(request):
  if request.user.is_authenticated:
    ctx = {'solved': get_accept_problem_count(request.user.pk),
           'bulletin': site_settings_get('BULLETIN', ''),
           'global_rating': User.objects.filter(rating__gt=0).order_by("-rating")[:10],
           }
    if not is_site_closed(request):
      LIMIT, LIMIT_BLOG = 20, 15
      ctx['blog_list'] = Blog.objects.with_likes().with_likes_flag(request.user).select_related(
        "author").order_by("-create_time").filter(visible=True, recommend=True)[:LIMIT_BLOG]
      comment_list, blog_list = XtdComment.objects.filter(is_public=True, is_removed=False).order_by(
        "-submit_date").select_related("user", "content_type").prefetch_related('content_object').all()[:LIMIT], \
                                Blog.objects.order_by("-create_time").select_related("author").filter(
                                  visible=True)[:LIMIT]
      ctx['comment_list'] = []
      i, j = 0, 0
      for k in range(LIMIT):
        if i < len(comment_list) and (j == len(blog_list) or (
            j < len(blog_list) and comment_list[i].submit_date > blog_list[j].create_time)):
          ctx['comment_list'].append(comment_list[i])
          i += 1
        elif j < len(blog_list):
          ctx['comment_list'].append(blog_list[j])
          j += 1
        else:
          break
      for comment in ctx['comment_list']:
        if isinstance(comment, XtdComment) and len(comment.comment) > LIMIT:
          comment.comment = comment.comment[:LIMIT] + '...'
    return render(request, 'home_logged_in.jinja2', context=ctx)
  else:
    return render(request, 'home.jinja2', context={'bg': '/static/image/bg/%d.jpg' % randint(1, 14), })


def forbidden_view(request, exception):
  return render(request, 'error/403.jinja2', context={"exception": exception}, status=403)


def not_found_view(request, *args, **kwargs):
  return render(request, 'error/404.jinja2', status=404)


def server_error_view(request, *args, **kwargs):
  return render(request, 'error/500.jinja2', status=500)


def faq_view(request):
  return render(request, 'faq.jinja2')


class TestView(TemplateView):
  template_name = 'test.jinja2'


class PasteView(StaffRequiredMixin, TemplateView):
  template_name = 'pastebin.jinja2'

  def post(self, request, *args, **kwargs):
    code = request.POST["code"]
    expire_seconds = int(request.POST["expire"])
    h = sha_hash(code)[:8]
    cache.set("PASTEBIN" + h, code, min(max(expire_seconds, 10), 86400))
    return redirect(reverse('pastebin') + '?id=' + h)

  def get_context_data(self, **kwargs):
    data = super().get_context_data(**kwargs)
    data['code'] = None

    chasing = self.request.GET.get('id', '')

    history_keys = cache.keys("PASTEBIN*")

    data['history'] = []
    for key in history_keys:
      code = cache.get(key)
      if code:
        id = key.lstrip("PASTEBIN")
        data['history'].append({
          'code': code,
          'length': len(code),
          'id': id,
          'ttl': cache.ttl(key)
        })
        if id == chasing:
          data['code'] = code
    data['history'].sort(key=lambda x: x['ttl'])
    if data['history'] and not data['code']:
      data['code'] = data['history'][0]['code']
    return data
