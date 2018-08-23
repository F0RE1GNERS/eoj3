import os
import re

import subprocess
import traceback
from datetime import datetime, timedelta

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Sum

from account.models import User
from django.http import HttpResponse
from django.shortcuts import redirect, get_object_or_404
from django.views import View
from django.views.generic import ListView
from django.views.generic import TemplateView

from account.permissions import StaffRequiredMixin
from submission.models import PrintManager, PrintCode
from utils import random_string


def latex_replace(s):
    d = {
        "&": "\\&",
        "%": "\\%",
        "$": "\\$",
        "#": "\\#",
        "_": "\\_",
        "{": "\\{",
        "}": "\\}",
        "~": "\\textasciitilde",
        "^": "\\textasciicircum",
        "\\": "\\textbackslash"
    }
    res = ''
    for x in s:
        if x in d:
            res += d[x]
        else: res += x
    return res


def process_code(code: PrintCode):
    base_dir, gen_dir = settings.BASE_DIR, settings.GENERATE_DIR
    os.chdir(gen_dir)
    try:
        with open(os.path.join(base_dir, "submission/assets/template.tex")) as f:
            tex_code = f.read()
            tex_code = tex_code.replace("$$username$$", latex_replace(code.user.username))
            tex_code = tex_code.replace("$$comment$$", latex_replace(code.comment))
            tex_code = tex_code.replace("$$code$$", code.code.replace("\\end{lstlisting}", ""))
        secret_key = random_string()
        tex_file_path = secret_key + ".tex"
        pdf_file_path = secret_key + ".pdf"
        with open(tex_file_path, "w") as f:
            f.write(tex_code)
        tex_gen = subprocess.run(["/usr/bin/xelatex", tex_file_path])
        if tex_gen.returncode != 0 or not os.path.exists(pdf_file_path):
            raise ValueError("TeX generation failed")
        pdfinfo = subprocess.check_output(["/usr/bin/pdfinfo", pdf_file_path]).decode()
        pdfinfo_match = re.match(r"Pages:\s+(\d+)", pdfinfo)
        if pdfinfo_match:
            code.pages = int(pdfinfo_match.group(1))
        code.save()
        if code.pages > code.manager.limit or \
                code.manager.printcode_set.filter(create_time__gt=datetime.now() - timedelta(days=1)).aggregate(Sum("pages")) > code.manager.limit:
            # limit pages
            raise ValueError("Too many pages")
        subprocess.run(["/usr/bin/lp", "-d", "LaserJet", pdf_file_path])
        code.status = 0
        code.generated_pdf = secret_key
    except:
        traceback.print_exc()
        code.status = 1
    os.chdir(base_dir)
    code.save()


class PrintAdminView(StaffRequiredMixin, ListView):
    context_object_name = 'print_manager_list'
    template_name = 'print/admin.jinja2'

    def get_queryset(self):
        return PrintManager.objects.all().order_by("-create_time")

    def post(self, request, *args, **kwargs):
        if request.POST.get('users').strip():
            for username in request.POST['users'].split():
                if not PrintManager.objects.filter(user__username=username).exists() and \
                        User.objects.filter(username=username).exists():
                    PrintManager.objects.create(user=User.objects.get(username=username))
        if int(request.POST.get('limit')):
            for manager in PrintManager.objects.all():
                manager.limit = min(int(request.POST['limit']), 200)
                manager.save()
        return redirect(request.path)


class PrintCodeView(LoginRequiredMixin, ListView):
    context_object_name = 'code_list'
    template_name = 'print/index.jinja2'

    def get_queryset(self):
        self.manager = get_object_or_404(PrintManager, user=self.request.user)
        return self.manager.printcode_set.all().order_by("-create_time")

    def post(self, request, *args, **kwargs):
        code = request.POST.get('code')
        comment = request.POST.get('comment')[:20]
        noprint = request.POST.get('noprint') == 'on'
        if len(code) < 6 or len(code) > 65536:
            messages.error(request, "Length of code is either too short or too long.")
            return redirect(request.path)
        manager = get_object_or_404(PrintManager, user=self.request.user)
        p = manager.printcode_set.create(code=code, user=self.request.user, comment=comment)
        if noprint:
            p.status = 2
            p.pages = 0
            p.save()
        else:
            process_code(p)
        return redirect(request.path)


class PrintCodeDownload(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        try:
            code = self.request.user.printcode_set.get(pk=self.kwargs['pk']).code
        except:
            code = ''
        return HttpResponse(code, content_type="text/plain; charset=utf-8")
