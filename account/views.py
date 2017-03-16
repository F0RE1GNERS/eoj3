from django.shortcuts import render, redirect, HttpResponseRedirect, reverse
from django.views import View
from utils.auth_view import password_change, login
from django.contrib import messages
from .forms import RegisterForm, LoginForm, MyPasswordChangeForm
from utils.invitation import activate


def profile_view(request):
    return render(request, 'account/profile.html')


def register_view(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.create()
            login(request, user)
            return HttpResponseRedirect('/')
    else:
        form = RegisterForm()
    return render(request, 'register.html', {'form': form})


class MyGroup(View):
    template_name = 'account/group.html'

    def get_context_data(self):
        user = self.request.user
        group_list = user.group_set.all()
        return dict(group_list=group_list)

    def post(self, request):
        code = request.POST.get('code')
        group_membership, error = activate(request.user, code)
        if group_membership:
            messages.success(request, "You successfully join group <strong>%s</strong>." % group_membership.group.name)
        else:
            messages.error(request, error)
        return render(request, self.template_name, self.get_context_data())

    def get(self, request):
        return render(request, self.template_name, self.get_context_data())


def my_password_change(request):
    return password_change(request, template_name='account/security.html',
                           post_change_redirect=reverse('account:profile'),
                           password_change_form=MyPasswordChangeForm,
                           message="Your password was changed successfully")


def my_login(request):
    return login(request, template_name='login.html')
