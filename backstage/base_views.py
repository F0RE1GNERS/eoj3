from django.contrib import messages
from django.contrib.auth.mixins import UserPassesTestMixin
from django.shortcuts import HttpResponseRedirect
from django.views.generic import TemplateView
from django.views.generic.edit import CreateView, UpdateView

from account.permissions import is_admin_or_root


class BaseBackstageMixin(UserPassesTestMixin):
  raise_exception = True

  def test_func(self):
    return is_admin_or_root(self.request.user)


class BaseCreateView(BaseBackstageMixin, CreateView):

  def post_create(self, instance, form):
    """
    Do something here
    """

  def form_valid(self, form):
    instance = form.save(commit=False)
    if hasattr(instance, 'created_by'):
      instance.created_by = self.request.user
    instance.save()
    self.post_create(instance, form=form)
    messages.success(self.request, "%s was successfully added." % self.form_class.Meta.model.__name__)
    return HttpResponseRedirect(self.get_redirect_url(instance))

  def get_redirect_url(self, instance):
    raise NotImplementedError("Method get_redirect_url should be implemented")


class BaseUpdateView(BaseBackstageMixin, UpdateView):

  def post_update(self, instance, form):
    """
    Do something here
    """

  def form_valid(self, form):
    instance = form.save(commit=False)
    self.post_update(instance, form)
    instance.save()
    messages.success(self.request, "Your changes have been saved.")
    return HttpResponseRedirect(self.get_redirect_url(instance))

  def get_redirect_url(self, instance):
    return self.request.path


class Index(BaseBackstageMixin, TemplateView):
  template_name = 'backstage/index.jinja2'
