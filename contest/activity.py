from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django import forms
from django.db.models import Count
from django.urls import reverse
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
