from django.contrib.auth.mixins import UserPassesTestMixin
from django.core.exceptions import PermissionDenied
from django.core.serializers import json
from django.db.models import Count, Sum, Case, When, IntegerField
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, HttpResponseRedirect, reverse
from django.views.generic import View, TemplateView
from django.views.generic.edit import CreateView, UpdateView
from django.views.generic.edit import FormMixin
from django.views.generic.list import ListView

from account.models import User
from account.permissions import is_admin_or_root
from problem.models import Problem
from submission.statistics import get_accept_problem_count
from utils.authentication import test_site_open
from utils.comment import CommentForm
from .forms import BlogEditForm
from .models import Blog, Comment, BlogLikes


class GenericView(UserPassesTestMixin, ListView):
    template_name = 'generic.jinja2'
    paginate_by = 50
    context_object_name = 'blog_list'

    def test_func(self):
        return test_site_open(self.request)

    def get_queryset(self):
        self.user = get_object_or_404(User, pk=self.kwargs.get('pk'))
        blogswithlikes = self.user.blog_set.annotate(
                likes__count=Sum(Case(When(bloglikes__flag='like', then=1), default=0, output_field=IntegerField()))
            )
        if is_admin_or_root(self.request.user) or self.request.user == self.user:
            return blogswithlikes.all()
        else:
            return blogswithlikes.filter(visibile=True).all()

    def get_context_data(self, **kwargs):
        res = super(GenericView, self).get_context_data(**kwargs)
        res['profile'] = self.user
        res['solved'] = get_accept_problem_count(self.user.pk)
        if is_admin_or_root(self.request.user):
            res['is_privileged'] = True
        if self.request.user == self.user:
            res['is_author'] = res['is_privileged'] = True
        return res


class BlogGoto(View):

    def post(self, request):
        user = get_object_or_404(User, username=request.POST['name'])
        return HttpResponseRedirect(reverse('generic', kwargs={'pk': user.pk}))


class BlogView(UserPassesTestMixin, FormMixin, TemplateView):
    form_class = CommentForm
    template_name = 'blog/blog_detail.jinja2'

    def get_form_kwargs(self):
        kw = super(BlogView, self).get_form_kwargs()
        kw['target_object'] = self.blog
        return kw

    def dispatch(self, request, *args, **kwargs):
        self.blog = get_object_or_404(Blog, pk=kwargs.get('pk'))
        return super(BlogView, self).dispatch(request, *args, **kwargs)

    def test_func(self):
        if is_admin_or_root(self.request.user):
            return True
        if not test_site_open(self.request):
            return False
        if self.request.user == self.blog.author or self.blog.visible:
            return True
        return False

    def get_context_data(self, **kwargs):
        context = super(BlogView, self).get_context_data(**kwargs)
        context['blog'] = self.blog
        context['action_path'] = reverse('comments-post-comment')
        if is_admin_or_root(self.request.user) or self.request.user == self.blog.author:
            context['is_privileged'] = True
        context['like_count'] = self.blog.bloglikes_set.filter(flag='like').count()
        context['dislike_count'] = self.blog.bloglikes_set.filter(flag='dislike').count()
        if self.request.user.is_authenticated:
            try:
                context['flag'] = self.blog.bloglikes_set.get(user=self.request.user).flag
            except BlogLikes.DoesNotExist:
                pass
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
        return HttpResponseRedirect(reverse('generic', kwargs={'pk': self.request.user.pk}))


class BlogUpdate(UserPassesTestMixin, UpdateView):
    form_class = BlogEditForm
    queryset = Blog.objects.all()
    template_name = 'blog/blog_edit.jinja2'

    def test_func(self):
        return test_site_open(self.request)

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


class LikeBlog(View):

    def post(self, request):
        if not request.user.is_authenticated:
            return HttpResponse('no', content_type="application/json")
        flag = request.POST['flag']
        if flag != 'like' and flag != 'dislike':
            return HttpResponse('no', content_type="application/json")
        pk = request.POST['comment']
        bloglike, created = BlogLikes.objects.get_or_create(user=request.user, blog_id=pk)
        if created:
            bloglike.flag = flag
            bloglike.save()
        else:
            if bloglike.flag != flag:
                bloglike.flag = flag
                bloglike.save()
            else:
                bloglike.delete()
                return HttpResponse('')
        return HttpResponse('{}', content_type="application/json")


class BlogDeleteComment(UserPassesTestMixin, View):

    def test_func(self):
        return self.request.user.is_authenticated

    def post(self, request, pk, comment_id):
        instance = get_object_or_404(Comment, pk=comment_id)
        if is_admin_or_root(request.user) or request.user == instance.author:
            instance.delete()
        elif instance.blog is not None and instance.blog.author == request.author:
            instance.delete()
        else:
            return PermissionDenied("You don't have the access.")
        return HttpResponseRedirect(reverse('blog:detail', kwargs={'pk': self.kwargs.get('pk')}))


class ProblemDiscuss(UserPassesTestMixin, ListView):
    template_name = 'discuss.jinja2'
    paginate_by = 100
    context_object_name = 'comment_list'

    def test_func(self):
        if is_admin_or_root(self.request.user):
            return True
        if test_site_open(self.request):
            return True
        return False

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