from django.shortcuts import render

from utils.site_settings import is_site_closed


class CloseSiteException(Exception):
  pass


class CloseSiteMiddleware(object):

  def __init__(self, get_response):
    self.get_response = get_response

  def __call__(self, request):
    response = self.get_response(request)
    return response

  @staticmethod
  def process_view(request, view_func, view_args, view_kwargs):
    force_closed = view_kwargs.pop('force_closed', False)
    try:
      if force_closed and is_site_closed(request):
        raise CloseSiteException
      return view_func(request, *view_args, **view_kwargs)
    except CloseSiteException:
      return render(request, 'error/closed.jinja2')
