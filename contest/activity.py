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

from account.models import User
from account.permissions import is_admin_or_root, StaffRequiredMixin
from contest.models import Activity, ActivityParticipant


class ActivityUpdateForm(forms.ModelForm):
    class Meta:
        model = Activity
        fields = ['title', 'description', 'register_start_time', 'register_end_time']


class ActivityUserUpdateForm(forms.ModelForm):
    class Meta:
        model = ActivityParticipant
        fields = ['real_name', 'student_id', 'school', 'email', 'phone', 'major', 'gender', 'graduate_year']

    def clean_graduate_year(self):
        if self.cleaned_data["graduate_year"] is not None and \
                (self.cleaned_data["graduate_year"] < 2000 or self.cleaned_data["graduate_year"] > 2035):
            raise forms.ValidationError("Graduate year must be between 2000 and 2035")


class ActivityUserAdminAddForm(forms.ModelForm):
    class Meta:
        model = ActivityParticipant
        fields = ['real_name', 'student_id', 'school', 'email', 'phone', 'major', 'gender', 'graduate_year']

    username = forms.CharField()

    def clean(self):
        try:
            self.cleaned_data["user"] = User.objects.get(username=self.cleaned_data["username"])
        except User.DoesNotExist:
            raise forms.ValidationError("Such user does not exist")


class ActivityUserAdminEditForm(forms.ModelForm):
    class Meta:
        model = ActivityParticipant
        fields = ['real_name', 'student_id', 'school', 'email', 'phone', 'is_deleted']


class ActivityList(ListView):
    template_name = 'contest/activity/list.jinja2'
    context_object_name = 'activity_list'

    def get_queryset(self):
        return Activity.objects.all().prefetch_related('participants').\
            annotate(Count('participants', distinct=True)).order_by("-pk")

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        data["privileged"] = is_admin_or_root(self.request.user)
        return data


class ActivityParticipantList(StaffRequiredMixin, ListView):
    template_name = 'contest/activity/participants.jinja2'
    context_object_name = 'participant_list'

    def get_queryset(self):
        return ActivityParticipant.objects.filter(activity_id=self.kwargs.get('pk'))

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        data["activity"] = get_object_or_404(Activity, pk=self.kwargs.get('pk'))
        data["active_member_count"] = ActivityParticipant.objects.filter(activity=data["activity"], is_deleted=False).count()
        data["member_count"] = ActivityParticipant.objects.filter(activity=data["activity"]).count()
        return data


class ActivityAddView(StaffRequiredMixin, CreateView):
    template_name = 'contest/activity/add.jinja2'
    form_class = ActivityUpdateForm

    def form_valid(self, form):
        form.instance.author = self.request.user
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('contest:activity_list')


class ActivityUpdateView(StaffRequiredMixin, UpdateView):
    template_name = 'contest/activity/edit.jinja2'
    form_class = ActivityUpdateForm
    queryset = Activity.objects.all()

    def get_success_url(self):
        return reverse('contest:activity_register', kwargs=self.kwargs)


class ActivityRegisterView(LoginRequiredMixin, UpdateView):
    form_class = ActivityUserUpdateForm
    template_name = 'contest/activity/register.jinja2'

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
        data["register_open"] = (data["activity"].register_start_time <= datetime.now() <= data["activity"].register_end_time)
        data["privileged"] = is_admin_or_root(self.request.user)
        return data

    def form_valid(self, form):
        activity = get_object_or_404(Activity, id=self.kwargs["pk"])
        if not (activity.register_start_time <= datetime.now() <= activity.register_end_time) and \
                not is_admin_or_root(self.request.user):
            raise PermissionDenied
        if form.instance.activity_id is None:
            form.instance.activity = activity
        if form.instance.user_id is None:
            form.instance.user = self.request.user
        form.instance.is_deleted = False
        return super().form_valid(form)


class ActivityQuitView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        ActivityParticipant.objects.filter(activity_id=self.kwargs["pk"],
                                           user_id=self.request.user.id).update(is_deleted=True)
        return HttpResponse()


class ActivityAdminAddUserView(StaffRequiredMixin, CreateView):

    form_class = ActivityUserAdminAddForm
    template_name = 'contest/activity/admin_add.jinja2'

    def get_success_url(self):
        return reverse('contest:activity_participant', kwargs=self.kwargs)

    def form_valid(self, form):
        form.instance.user = form.cleaned_data["user"]
        form.instance.activity = get_object_or_404(Activity, id=self.kwargs["pk"])
        return super().form_valid(form)


class ActivityAdminUpdateUserView(StaffRequiredMixin, UpdateView):
    form_class = ActivityUserAdminEditForm
    template_name = 'contest/activity/admin_update.jinja2'

    def get_object(self, queryset=None):
        return get_object_or_404(ActivityParticipant, pk=self.kwargs["upk"])

    def get_success_url(self):
        return reverse('contest:activity_participant', kwargs={"pk": self.kwargs["pk"]})
