from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.views.generic.list import ListView
from django.contrib.auth.mixins import UserPassesTestMixin
from django.shortcuts import render
from django.shortcuts import get_object_or_404, HttpResponseRedirect, reverse
from account.models import User
from account.permissions import is_admin_or_root
from .forms import BlogEditForm

def generic_view(request, name):
    return render(request, 'generic.jinja2', {'profile': get_object_or_404(User, username=name)})


class GenericView(ListView):
    template_name = 'generic.jinja2'
    paginate_by = 50
    context_object_name = 'blog_list'

    def get_queryset(self):
        user = get_object_or_404(User, username=self.kwargs.get('name'))
        if is_admin_or_root(self.request.user) or self.request.user == user:
            return user.blog_set.all()
        else:
            return user.blog_set.filter(visible=True).all()

    def get_context_data(self, **kwargs):
        user = get_object_or_404(User, username=self.kwargs.get('name'))
        res = super(GenericView, self).get_context_data(**kwargs)
        res['profile'] = user
        if is_admin_or_root(self.request.user):
            res['is_privileged'] = True
        if self.request.user == user:
            res['is_author'] = res['is_privileged'] = True
        return res


class BlogCreate(UserPassesTestMixin, CreateView):
    form_class = BlogEditForm
    template_name = 'blog/blog_add.jinja2'

    def test_func(self):
        return self.request.user.is_authenticated

    def form_valid(self, form):
        instance = form.save(commit=False)
        instance.author = self.request.user
        instance.save()
        return HttpResponseRedirect(reverse('generic', kwargs={'name': self.request.user.username}))

    def get_redirect_url(self, instance):
        return reverse("backstage:problem")
