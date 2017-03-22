from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.views.generic import TemplateView
from django.contrib import messages
from django.shortcuts import HttpResponseRedirect, render
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import UserPassesTestMixin

from account.models import Privilege


class BaseBackstageMixin(UserPassesTestMixin):
    raise_exception = True

    def test_func(self):
        user = self.request.user
        return user.is_authenticated and user.privilege in (Privilege.ROOT, Privilege.ADMIN)


class BaseCreateView(BaseBackstageMixin, CreateView):

    def post_create(self, instance):
        """
        Do something here
        """
        pass

    def form_valid(self, form):
        instance = form.save(commit=False)
        instance.created_by = self.request.user
        self.post_create(instance)
        instance.save()
        messages.success(self.request, "%s was successfully added." % self.form_class.Meta.model.__name__)
        return HttpResponseRedirect(self.get_redirect_url(instance))

    def get_redirect_url(self, instance):
        raise NotImplementedError("Method get_redirect_url should be implemented")


class BaseUpdateView(BaseBackstageMixin, UpdateView):

    def post_update(self, instance):
        """
        Do something here
        """
        pass

    def form_valid(self, form):
        instance = form.save(commit=False)
        self.post_update(instance)
        instance.save()
        messages.success(self.request, "Your changes have been saved.")
        return HttpResponseRedirect(self.get_redirect_url(instance))

    def get_redirect_url(self, instance):
        return self.request.path


class Index(BaseBackstageMixin, TemplateView):
    template_name = 'backstage/index.jinja2'