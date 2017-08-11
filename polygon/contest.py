from .forms import ContestEditForm
from contest.models import Contest
from .views import PolygonBaseMixin, response_ok
from django.views.generic.edit import UpdateView
from django.views.generic import ListView, View
from django.views.generic.base import TemplateResponseMixin, ContextMixin
from account.permissions import is_admin_or_root
from django.shortcuts import get_object_or_404, reverse, redirect


class ContestEdit(PolygonBaseMixin, UpdateView):

    form_class = ContestEditForm
    template_name = 'polygon/contest_edit.jinja2'
    queryset = Contest.objects.all()

    def form_valid(self, form):
        instance = form.save(commit=False)
        instance.allowed_lang = ','.join(form.cleaned_data['allowed_lang'])
        instance.save()
        return redirect(self.request.path)


class ContestList(PolygonBaseMixin, ListView):
    template_name = 'polygon/contest_list.jinja2'
    context_object_name = 'contest_list'

    def get_queryset(self):
        if is_admin_or_root(self.request.user):
            return Contest.objects.all()
        else:
            return self.request.user.managing_contests.all()


class PolygonContestMixin(TemplateResponseMixin, ContextMixin, PolygonBaseMixin):
    raise_exception = True

    def dispatch(self, request, *args, **kwargs):
        self.contest = get_object_or_404(Contest, pk=kwargs.get('sid'))
        return super(PolygonContestMixin, self).dispatch(request, *args, **kwargs)

    def test_func(self):
        if not is_admin_or_root(self.request.user) and not self.contest.manager.filter(user=self.request.user).exists():
            return False
        return super(PolygonContestMixin, self).test_func()

    def get_context_data(self, **kwargs):
        data = super(PolygonContestMixin, self).get_context_data(**kwargs)
        data['contest'] = self.contest
        return data


class ContestToggleVisible(PolygonContestMixin, View):

    def post(self, request, pk):
        self.contest.visible = request.POST.get('checked') == 'true'
        self.contest.save(update_fields=['visible'])
        return response_ok()

