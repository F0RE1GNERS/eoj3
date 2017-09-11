from utils.models import SiteSettings
from django.shortcuts import HttpResponseRedirect, reverse
from utils.permission import is_admin_or_root


class CloseSiteMiddleware(object):
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        return response

    @staticmethod
    def process_view(request, view_func, view_args, view_kwargs):
        force_open = view_kwargs.pop('force_open', False)
        if SiteSettings.objects.filter(key='SITE_CLOSE').exists() and not force_open and not is_admin_or_root(request.user):
            return HttpResponseRedirect(reverse('contest:list'))
        else:
            return view_func(request, *view_args, **view_kwargs)

