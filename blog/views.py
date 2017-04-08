from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.views.generic import View
from django.views.generic.list import ListView
from django.contrib.auth.mixins import UserPassesTestMixin
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.shortcuts import render
from django.shortcuts import get_object_or_404, HttpResponseRedirect, reverse
from account.models import User
from account.permissions import is_admin_or_root
from .forms import BlogEditForm
from .models import Blog, Comment
from problem.models import Problem

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


class BlogGoto(View):

    def post(self, request):
        return HttpResponseRedirect(reverse('generic', kwargs={'name': request.POST.get('name')}))


class BlogView(UserPassesTestMixin, ListView):
    template_name = 'blog/blog_detail.jinja2'
    paginate_by = 100
    context_object_name = 'comment_list'

    def dispatch(self, request, *args, **kwargs):
        self.blog = get_object_or_404(Blog, pk=kwargs.get('pk'))
        return super(BlogView, self).dispatch(request, *args, **kwargs)

    def test_func(self):
        if is_admin_or_root(self.request.user) or self.request.user == self.blog.author or self.blog.visible:
            return True
        return False

    def get_queryset(self):
        return self.blog.comment_set.all()

    def get_context_data(self, **kwargs):
        context = super(BlogView, self).get_context_data(**kwargs)
        context['blog'] = self.blog
        if is_admin_or_root(self.request.user) or self.request.user == self.blog.author:
            context['is_privileged'] = True
        for comment in context['comment_list']:
            if context.get('is_privileged') or self.request.user == comment.author:
                comment.is_privileged = True
        return context


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


class BlogUpdate(UserPassesTestMixin, UpdateView):
    form_class = BlogEditForm
    queryset = Blog.objects.all()
    template_name = 'blog/blog_edit.jinja2'

    def test_func(self):
        return self.request.user.is_authenticated

    def form_valid(self, form):
        instance = form.save(commit=False)
        if not is_admin_or_root(self.request.user) and instance.author != self.request.user:
            raise PermissionDenied("You don't have the access.")
        instance.save()
        return HttpResponseRedirect(reverse('blog:detail', kwargs={'pk': self.kwargs.get('pk')}))


class BlogAddComment(UserPassesTestMixin, View):

    def test_func(self):
        return self.request.user.is_authenticated

    def post(self, request, pk):
        Comment.objects.create(text=request.POST['text'], author=request.user, blog_id=pk)
        return HttpResponseRedirect(reverse('blog:detail', kwargs={'pk': pk}))


class BlogDeleteComment(UserPassesTestMixin, View):

    def test_func(self):
        return self.request.user.is_authenticated

    def get(self, request, pk, comment_id):
        instance = get_object_or_404(Comment, pk=comment_id)
        if is_admin_or_root(request.user) or request.user == instance.author:
            instance.delete()
        elif instance.blog is not None and instance.blog.author == request.author:
            instance.delete()
        else:
            return PermissionDenied("You don't have the access.")
        return HttpResponseRedirect(reverse('blog:detail', kwargs={'pk': self.kwargs.get('pk')}))


class ProblemDiscuss(ListView):
    template_name = 'discuss.jinja2'
    paginate_by = 100
    context_object_name = 'comment_list'

    def get_queryset(self):
        if is_admin_or_root(self.request.user):
            problem = get_object_or_404(Problem, pk=self.kwargs.get('pk'))
        else:
            problem = get_object_or_404(Problem, pk=self.kwargs.get('pk'), visible=True)
        return problem.comment_set.all()

    def get_context_data(self, **kwargs):
        context = super(ProblemDiscuss, self).get_context_data(**kwargs)
        context['pk'] = self.kwargs.get('pk')
        for comment in context['comment_list']:
            if is_admin_or_root(self.request.user) or self.request.user == comment.author:
                comment.is_privileged = True
        return context


class ProblemAddComment(UserPassesTestMixin, View):

    def test_func(self):
        return self.request.user.is_authenticated

    def post(self, request, pk):
        Comment.objects.create(text=request.POST['text'], author=request.user, problem_id=pk)
        return HttpResponseRedirect(reverse('blog:discuss', kwargs={'pk': pk}))


class ProblemDeleteComment(UserPassesTestMixin, View):

    def test_func(self):
        return self.request.user.is_authenticated

    def get(self, request, pk, comment_id):
        instance = get_object_or_404(Comment, pk=comment_id)
        if is_admin_or_root(request.user) or request.user == instance.author:
            instance.delete()
        else:
            return PermissionDenied("You don't have the access.")
        return HttpResponseRedirect(reverse('blog:discuss', kwargs={'pk': self.kwargs.get('pk')}))