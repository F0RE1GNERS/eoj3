from django.shortcuts import render, HttpResponseRedirect, reverse, HttpResponse
from django.db.models import Q
from utils.models import SiteSettings
from migrate.models import OldSubmission
from submission.models import SubmissionStatus
from django.views.generic import ListView, View
from pygments import highlight
from pygments.lexers import get_lexer_by_name
from pygments.formatters.html import HtmlFormatter
from .forms import SiteSettingsForm
from .tasks import OldSubmissionRejudgeThread
import json

from ..base_views import BaseUpdateView, BaseBackstageMixin


class SiteSettingsUpdate(BaseUpdateView):
    form_class = SiteSettingsForm
    template_name = 'backstage/site/site.jinja2'

    def get_object(self, queryset=None):
        if not SiteSettings.objects.exists():
            SiteSettings.objects.create()
        return SiteSettings.objects.first()

    def get_redirect_url(self, instance):
        return reverse('backstage:site')


class MigrateList(BaseBackstageMixin, ListView):
    template_name = 'backstage/site/migrate.jinja2'
    queryset = OldSubmission.objects.all()
    paginate_by = 200
    context_object_name = 'old_submission_list'

    @staticmethod
    def get_queryset_for_keyword(kw):
        queryset = OldSubmission.objects
        if kw:
            q = Q(author__iexact=kw)
            if kw.isdigit():
                q |= Q(pk__exact=kw) | Q(problem__exact=int(kw))
            if kw == 'system':
                q |= Q(status=SubmissionStatus.SYSTEM_ERROR)
            queryset = queryset.filter(q)
        return queryset.all()

    def get_queryset(self):
        return self.get_queryset_for_keyword(self.request.GET.get('keyword'))

    def get_context_data(self, **kwargs):
        data = super(MigrateList, self).get_context_data(**kwargs)
        data['keyword'] = self.request.GET.get('keyword')
        return data

    def post(self, request, *args, **kwargs):
        kw = self.request.POST.get('judge')
        skip = False
        if kw == 'all':
            queryset = OldSubmission.objects
            skip = True
        elif kw == 'system':
            queryset = OldSubmission.objects.filter(status=SubmissionStatus.SYSTEM_ERROR)
        elif kw and kw.isdigit():
            queryset = OldSubmission.objects.filter(problem=int(kw))
        else:
            return HttpResponseRedirect(reverse('backstage:migrate'))
        OldSubmissionRejudgeThread([x.pk for x in queryset.all()], skip=skip).start()
        return HttpResponseRedirect(reverse('backstage:migrate'))


class OldSubmissionQuery(BaseBackstageMixin, View):
    def get(self, request, submission_id):
        submission = OldSubmission.objects.get(pk=submission_id)
        return HttpResponse(json.dumps({'code': highlight(submission.code, get_lexer_by_name(submission.lang), HtmlFormatter())}))


class OldSubmissionRejudge(BaseBackstageMixin, View):
    def get(self, request, submission_id):
        OldSubmissionRejudgeThread([submission_id]).start()
        return HttpResponse(json.dumps({'result': 'success'}))
