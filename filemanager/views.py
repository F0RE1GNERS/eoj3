import os
import shutil
from datetime import datetime
from os import path, listdir, makedirs
from threading import Thread

import requests
from django.conf import settings
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.urls import reverse
from django.views.generic import TemplateView

from account.permissions import is_admin_or_root
from utils import random_string
from utils.upload import save_uploaded_file_to


class FileManager(UserPassesTestMixin, TemplateView):
    template_name = 'filemanager.jinja2'

    @staticmethod
    def slugify(text):
        import re
        return re.sub(r'[ /"#!:]+', '_', text)

    def dispatch(self, request, *args, **kwargs):
        makedirs(settings.MIRROR_DIR, exist_ok=True)
        self.position = request.POST.get('q', request.GET.get('q', ''))
        self.root = path.join(settings.MIRROR_DIR, self.position)
        return super().dispatch(request, *args, **kwargs)

    def test_func(self):
        if not is_admin_or_root(self.request.user):
            return False
        if path.commonpath([self.root, settings.MIRROR_DIR]) != settings.MIRROR_DIR:
            raise False
        return True

    def get_context_data(self, **kwargs):
        display_dir = self.position + '/'
        if '/' in self.position:
            parent_link = ''
        else:
            parent_link = self.position[0:self.position.rfind('/')]

        file_list = []
        if not path.isdir(self.root):
            file_list = []
            messages.add_message(self.request, messages.WARNING, "Directory '%s' does not exist." % display_dir)
        else:
            for file in listdir(self.root):
                file_path = path.join(self.root, file)
                file_pos = path.join(self.position, file)
                if path.isdir(file_path):
                    size = '--'
                    link = reverse('filemanager:index') + '?q=%s' % file_pos
                    is_dir = True
                else:
                    size = "%d" % path.getsize(file_path)
                    link = '/upload/mirror/' + file_pos
                    is_dir = False
                file_list.append(dict(name=file, modified=datetime.fromtimestamp(path.getmtime(file_path)).
                                      strftime(settings.DATETIME_FORMAT_TEMPLATE), size=size, link=link, is_dir=is_dir))
        return {
            'file_list': file_list,
            'display_dir': display_dir,
            'position': self.position,
            'parent_link': parent_link
        }

    def handle_upload(self, request):
        file = request.FILES['file']
        save_uploaded_file_to(file, self.root, filename=self.slugify(file.name))

    def handle_download(self, request):
        def download_file(url, to):
            local_filename = url.split('/')[-1]
            if local_filename == '':
                local_filename = random_string()
            r = requests.get(url, stream=True, timeout=30)
            with open(path.join(to, local_filename), 'wb') as f:
                for chunk in r.iter_content(chunk_size=1024):
                    if chunk:
                        f.write(chunk)

        url = request.POST['url']
        Thread(target=download_file, args=(url, self.root)).start()

    def handle_rename(self, request):
        new_path = path.join(self.root, self.slugify(request.POST['name']))
        old_path = path.join(self.root, request.POST['oldName'].replace('/', '_'))
        os.rename(old_path, new_path)

    def handle_delete(self, request):
        file_path = path.join(self.root, request.POST['name'].replace('/', '_'))
        if path.isfile(file_path):
            os.remove(file_path)
        else:
            shutil.rmtree(file_path)

    def handle_create_new_dir(self, request):
        file_path = path.join(self.root, request.POST['name'].replace('/', '_'))
        print(file_path)
        os.makedirs(file_path, exist_ok=True)

    def post(self, request, *args, **kwargs):
        t = 'upload'
        try:
            t = request.POST['type']
            if t == 'upload':
                self.handle_upload(request)
            elif t == 'download':
                self.handle_download(request)
            elif t == 'rename':
                self.handle_rename(request)
            elif t == 'delete':
                self.handle_delete(request)
            elif t == 'createdir':
                self.handle_create_new_dir(request)
            else:
                raise NotImplementedError("Unrecognized query type")
        except Exception as e:
            messages.add_message(request, messages.ERROR, repr(e))
        if t in ['upload', 'download']:
            return redirect(reverse('filemanager:index') + '?q=%s' % self.position)
        else:
            return HttpResponse()
