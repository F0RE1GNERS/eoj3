from .forms import ContestEditForm
from contest.models import Contest
from .views import PolygonBaseMixin, response_ok
from django.views.generic.edit import UpdateView
from django.views.generic import ListView, View
from django.views.generic.base import TemplateResponseMixin, ContextMixin
from account.permissions import is_admin_or_root
from account.models import User
from django.shortcuts import get_object_or_404, reverse, redirect


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
        self.contest = get_object_or_404(Contest, pk=kwargs.get('pk'))
        return super(PolygonContestMixin, self).dispatch(request, *args, **kwargs)

    def test_func(self):
        if not is_admin_or_root(self.request.user) and not self.contest.manager.filter(user=self.request.user).exists():
            return False
        return super(PolygonContestMixin, self).test_func()

    def get_context_data(self, **kwargs):
        data = super(PolygonContestMixin, self).get_context_data(**kwargs)
        data['contest'] = self.contest
        return data


class ContestEdit(PolygonContestMixin, UpdateView):

    form_class = ContestEditForm
    template_name = 'polygon/contest_edit.jinja2'
    queryset = Contest.objects.all()

    def get_context_data(self, **kwargs):
        data = super(ContestEdit, self).get_context_data(**kwargs)
        data['admin_list'] = self.contest.manager.all()
        return data

    def form_valid(self, form):
        instance = form.save(commit=False)
        instance.allowed_lang = ','.join(form.cleaned_data['allowed_lang'])
        instance.save()
        return redirect(self.request.path)


class ContestCreate(PolygonBaseMixin, View):

    def post(self, request):
        """
        It is actually "repository create"
        named "session create" for convenience
        """
        if request.method == 'POST':
            contest = Contest.objects.create(title='Contest')
            contest.title = 'Contest #%d' % contest.id
            contest.save(update_fields=['title'])
            return redirect(reverse('polygon:contest_meta', kwargs={'pk': str(contest.id)}))


class ContestToggleVisible(PolygonContestMixin, View):

    def post(self, request, pk):
        self.contest.visible = request.POST.get('checked') == 'true'
        self.contest.save(update_fields=['visible'])
        return response_ok()


class ContestAccessManage(PolygonContestMixin, View):

    def post(self, request, pk):
        upload_permission_set = set(map(int, filter(lambda x: x, request.POST['admin'].split(','))))
        for record in self.contest.manager.all():
            if record.id in upload_permission_set:
                upload_permission_set.remove(record.id)
            else:
                record.delete()
        for key in upload_permission_set:
            self.contest.manager.add(User.objects.get(pk=key))
        return redirect(reverse('polygon:contest_meta', kwargs={'pk': str(pk)}))
