from datetime import datetime
from threading import Thread

from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django import forms
from django.core.exceptions import PermissionDenied
from django.core.mail import send_mail
from django.db.models import Count
from django.http import Http404
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.template import Context
from django.template import loader
from django.urls import reverse
from django.views import View
from django.views.generic import CreateView
from django.views.generic import ListView
from django.views.generic import TemplateView
from django.views.generic import UpdateView

from account.models import User, School
from account.permissions import is_admin_or_root, StaffRequiredMixin
from contest.models import Activity, ActivityParticipant
from utils.hash import token_generator


class SchoolForm(forms.ModelForm):
    class Meta:
        model = School
        fields = "__all__"


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
        return self.cleaned_data["graduate_year"]


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
        fields = ['real_name', 'student_id', 'school', 'email', 'phone', 'major', 'gender', 'graduate_year',
                  'is_deleted', 'is_confirmed']


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
        data["confirm_count"] = ActivityParticipant.objects.filter(activity=data["activity"], is_deleted=False, is_confirmed=True).count()
        return data


class ActivityParticipantConfirmEmailSent(StaffRequiredMixin, View):
    @staticmethod
    def run(activity):
        template = loader.get_template('contest/activity/confirmation.jinja2')
        for participant in ActivityParticipant.objects.filter(activity=activity, is_confirmed=False):
            # TODO: hard code
            c = Context({'participant': participant, 'activity': activity,
                         'link': "https://acm.ecnu.edu.cn" + reverse("contest:activity_confirm_complete") +
                                 "?t=" + token_generator.make_token(participant.user, participant) +
                                 "&id=" + str(participant.pk)})
            send_mail(subject=activity.title, message='', html_message=template.render(c), from_email=None,
                      recipient_list=[participant.email], fail_silently=True)

    def post(self, request, *args, **kwargs):
        activity = get_object_or_404(Activity, pk=self.kwargs.get('pk'))
        Thread(target=self.run, args=(activity,)).start()
        return HttpResponse()


class ActivityParticipantConfirmComplete(TemplateView):
    template_name = 'contest/activity/confirm_complete.jinja2'

    def get(self, request, *args, **kwargs):
        if "id" not in request.GET or "t" not in request.GET or not request.GET["id"].isdigit():
            raise Http404
        id = request.GET["id"]
        token = request.GET["t"]
        participant = get_object_or_404(ActivityParticipant, id=id)
        if token_generator.check_token(participant.user, token) == participant:
            participant.is_confirmed = True
            participant.save(update_fields=['is_confirmed'])
            return super().get(request, *args, **kwargs)
        raise Http404


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


class ActivityAddSchoolView(LoginRequiredMixin, CreateView):
    form_class = SchoolForm
    template_name = 'contest/activity/school_form.jinja2'

    def get_success_url(self):
        return self.request.POST.get("next", self.request.path)
