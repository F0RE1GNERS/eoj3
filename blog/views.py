from django.contrib.auth.mixins import UserPassesTestMixin, LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, HttpResponseRedirect, reverse, redirect
from django.views.generic import View, TemplateView
from django.views.generic.edit import CreateView, UpdateView
from django.views.generic.edit import FormMixin
from django.views.generic.list import ListView
from django.utils.translation import ugettext_lazy as _

from account.models import User
from account.permissions import is_admin_or_root
from problem.models import Problem
from submission.statistics import get_accept_problem_count
from utils.comment import CommentForm
from .forms import BlogEditForm
from .models import Blog, Comment, BlogLikes


class GenericView(ListView):
    template_name = 'generic.jinja2'
    paginate_by = 50
    context_object_name = 'blog_list'

    def get_queryset(self):
        self.user = get_object_or_404(User, pk=self.kwargs.get('pk'))
        qs = self.user.blog_set.all().with_likes().with_likes_flag(self.request.user)
        if not is_admin_or_root(self.request.user) and not self.request.user == self.user:
            qs = qs.filter(visible=True)
        return qs

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
        user = get_object_or_404(User, username=request.POST.get('name', ''))
        return HttpResponseRedirect(reverse('generic', kwargs={'pk': user.pk}))


class BlogView(UserPassesTestMixin, FormMixin, TemplateView):
    form_class = CommentForm
    template_name = 'blog/blog_detail.jinja2'

    def get_form_kwargs(self):
        kw = super(BlogView, self).get_form_kwargs()
        kw['target_object'] = self.blog
        return kw

    def dispatch(self, request, *args, **kwargs):
        blogs = Blog.objects.with_likes().with_dislikes().with_likes_flag(request.user)
        self.blog = get_object_or_404(blogs, pk=kwargs.get('pk'))
        return super(BlogView, self).dispatch(request, *args, **kwargs)

    def test_func(self):
        if is_admin_or_root(self.request.user):
            return True
        if self.request.user == self.blog.author or self.blog.visible:
            return True
        return False

    def get_context_data(self, **kwargs):
        context = super(BlogView, self).get_context_data(**kwargs)
        context['blog'] = self.blog
        context['blog_revisions'] = self.blog.revisions.select_related("author").all()
        context['action_path'] = reverse('comments-post-comment')
        if is_admin_or_root(self.request.user) or self.request.user == self.blog.author:
            context['is_privileged'] = True
        return context


class BlogRevisionView(UserPassesTestMixin, TemplateView):
    template_name = 'blog/blog_revision_detail.jinja2'
    raise_exception = True

    def dispatch(self, request, *args, **kwargs):
        self.blog = get_object_or_404(Blog, pk=kwargs['pk'])
        return super().dispatch(request, *args, **kwargs)

    def test_func(self):
        if is_admin_or_root(self.request.user) or self.request.user == self.blog.author:
            return True
        return self.blog.visible and not self.blog.hide_revisions

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['blog'] = self.blog
        context['revision'] = self.blog.revisions.get(pk=kwargs['rpk'])
        context['blog_revisions'] = context['blog'].revisions.select_related("author").all()
        return context


class BlogCreate(LoginRequiredMixin, CreateView):
    form_class = BlogEditForm
    template_name = 'blog/blog_add.jinja2'

    def form_valid(self, form):
        instance = form.save(commit=False)
        instance.author = self.request.user
        instance.save()
        return HttpResponseRedirect(reverse('generic', kwargs={'pk': self.request.user.pk}))


class BlogUpdate(UpdateView):
    form_class = BlogEditForm
    queryset = Blog.objects.all()
    template_name = 'blog/blog_edit.jinja2'

    def form_valid(self, form):
        instance = form.save(commit=False)
        if not is_admin_or_root(self.request.user) and instance.author != self.request.user:
            raise PermissionDenied(_("You don't have the access."))
        with transaction.atomic():
            instance.save()
            instance.revisions.create(title=instance.title, text=instance.text, author=self.request.user)
        return redirect(reverse('blog:detail', kwargs=self.kwargs))


class BlogAddComment(LoginRequiredMixin, View):
    def post(self, request, pk):
        if 'text' in request.POST and request.POST['text']:
            Comment.objects.create(text=request.POST['text'], author=request.user, blog_id=pk)
        return redirect(reverse('blog:detail', kwargs={'pk': pk}))


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


class BlogDeleteComment(LoginRequiredMixin, View):
    def post(self, request, pk, comment_id):
        instance = get_object_or_404(Comment, pk=comment_id)
        if is_admin_or_root(request.user) or request.user == instance.author:
            instance.delete()
        elif instance.blog is not None and instance.blog.author == request.author:
            instance.delete()
        else:
            return PermissionDenied(_("You don't have the access."))
        return HttpResponseRedirect(reverse('blog:detail', kwargs={'pk': self.kwargs.get('pk')}))
