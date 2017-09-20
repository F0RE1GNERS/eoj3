from threading import Thread

from django.shortcuts import HttpResponse, get_object_or_404
from django.template import loader
from django.views import View
from django.views.generic.list import ListView

from account.models import User
from contest.models import Contest
from utils.email import send_mail_with_bcc
from ..base_views import BaseBackstageMixin


class ContestSendInvitationMail(BaseBackstageMixin, View):

    def post(self, request, pk):
        recipient_list = list(filter(lambda x: x, [u.email for u in User.objects.filter(is_active=True).all()]))
        contest = get_object_or_404(Contest, pk=pk)
        host = ('https' if request.is_secure() else 'http') + '://' + request.get_host()
        Thread(target=send_mail_with_bcc, args=(contest.title,
                                                loader.render_to_string('notification/email_invitation.jinja2',
                                                                        context=dict(host=host, contest=contest)),),
               kwargs=(dict(recipient_list=recipient_list,
                            fail_silently=True))).start()
        return HttpResponse()


class ContestList(BaseBackstageMixin, ListView):
    template_name = 'backstage/contest/contest.jinja2'
    queryset = Contest.objects.all()
    paginate_by = 100
    context_object_name = 'contest_list'
