from datetime import datetime

from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django import forms
from django.core.exceptions import PermissionDenied
from django.db.models import Count
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.views import View
from django.views.generic import CreateView
from django.views.generic import ListView
from django.views.generic import UpdateView

from account.permissions import is_admin_or_root
from contest.models import Activity, ActivityParticipant


class ActivityUpdateForm(forms.ModelForm):
    class Meta:
        model = Activity
        fields = ['title', 'description', 'register_start_time', 'register_end_time']


class ActivityUserUpdateForm(forms.ModelForm):
    class Meta:
        model = ActivityParticipant
        fields = ['real_name', 'student_id', 'school', 'email', 'phone']

    # def __init__(self, *args, **kwargs):
        # user = kwargs.pop('user', '')
        # super(DocumentForm, self).__init__(*args, **kwargs)
        # self.fields['user_defined_code'] = forms.ModelChoiceField(queryset=UserDefinedCode.objects.filter(owner=user))


class ActivityList(ListView):
    template_name = 'contest/activity/list.jinja2'
    context_object_name = 'activity_list'

    def get_queryset(self):
        return Activity.objects.all().prefetch_related('participants').\
            annotate(Count('participants', distinct=True)).order_by("-pk")


class ActivityParticipantList(UserPassesTestMixin, ListView):
    template_name = 'contest/activity/participants.jinja2'
    context_object_name = 'participant_list'

    def test_func(self):
        return is_admin_or_root(self.request.user)

    def get_queryset(self):
        return ActivityParticipant.objects.filter(activity_id=self.kwargs.get('pk'))

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        data["activity"] = get_object_or_404(Activity, pk=self.kwargs.get('pk'))
        return data


class ActivityAddView(UserPassesTestMixin, CreateView):
    template_name = 'contest/activity/add.jinja2'
    form_class = ActivityUpdateForm

    def test_func(self):
        return is_admin_or_root(self.request.user)

    def form_valid(self, form):
        form.instance.author = self.request.user
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('contest:activity_list')


class ActivityUpdateView(UserPassesTestMixin, UpdateView):
    template_name = 'contest/activity/edit.jinja2'
    form_class = ActivityUpdateForm
    queryset = Activity.objects.all()

    def test_func(self):
        return is_admin_or_root(self.request.user)

    def get_success_url(self):
        return reverse('contest:activity_list')


class ActivityRegisterView(LoginRequiredMixin, UpdateView):
    form_class = ActivityUserUpdateForm
    template_name = 'contest/activity/register.jinja2'
    raise_exception = True

    def get_success_url(self):
        return self.request.path

    def get_object(self, queryset=None):
        qs = ActivityParticipant.objects.filter(activity_id=self.kwargs["pk"],
                                                user_id=self.request.user.id)
        if len(qs) == 0:
            return None
        else:
            return qs[0]

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        data["activity"] = get_object_or_404(Activity, id=self.kwargs["pk"])
        data["registered"] = ActivityParticipant.objects.filter(activity_id=self.kwargs["pk"],
                                                                user_id=self.request.user.id,
                                                                is_deleted=False).exists()
        if not (data["activity"].register_start_time <= datetime.now() <= data["activity"].register_end_time) and \
                not is_admin_or_root(self.request.user):
            raise PermissionDenied
        return data

    def form_valid(self, form):
        if form.instance.activity_id is None:
            form.instance.activity_id = self.kwargs["pk"]
        if form.instance.user_id is None:
            form.instance.user = self.request.user
        form.instance.is_deleted = False
        return super().form_valid(form)


class ActivityQuitView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        ActivityParticipant.objects.filter(activity_id=self.kwargs["pk"],
                                           user_id=self.request.user.id).update(is_deleted=True)
        return HttpResponse()