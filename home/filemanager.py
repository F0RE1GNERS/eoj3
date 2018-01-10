from datetime import datetime
from os import path, listdir
from threading import Thread

import requests
from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.shortcuts import render, redirect
from django.urls import reverse

from account.permissions import is_admin_or_root
from utils import random_string
from utils.upload import save_uploaded_file_to


def file_manager(request):
    def slugify(text):
        import re
        return re.sub(r'[ /"#!:]+', '_', text)

    if not is_admin_or_root(request.user):
        raise PermissionDenied
    if request.method == 'POST':
        try:
            file = request.FILES['file']
            save_uploaded_file_to(file, settings.UPLOAD_DIR, filename=slugify(file.name))
        except Exception as e:
            raise PermissionDenied(repr(e))
    return render(request, 'filemanager.jinja2', context={
        'file_list': list(map(lambda x: {
            'name': x,
            'modified_time': datetime.fromtimestamp(path.getmtime(path.join(settings.UPLOAD_DIR, x))).
                              strftime(settings.DATETIME_FORMAT_TEMPLATE),
            'size': str(path.getsize(path.join(settings.UPLOAD_DIR, x)) // 1024) + "K"
        }, filter(lambda x: path.isfile(path.join(settings.UPLOAD_DIR, x)), listdir(settings.UPLOAD_DIR))))
    })


def proxy_file_downloader(request):
    if not is_admin_or_root(request.user):
        raise PermissionDenied

    def download_file(url):
        local_filename = url.split('/')[-1]
        if local_filename == '':
            local_filename = random_string()
        r = requests.get(url, stream=True, timeout=30)
        with open(path.join(settings.UPLOAD_DIR, local_filename), 'wb') as f:
            for chunk in r.iter_content(chunk_size=1024):
                if chunk:
                    f.write(chunk)

    if request.method == 'POST':
        try:
            url = request.POST['url']
            Thread(target=download_file, args=(url,)).start()
        except Exception as e:
            raise PermissionDenied(repr(e))
    return redirect(reverse('filemanager'))