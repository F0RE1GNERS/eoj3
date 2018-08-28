import mimetypes
import os
import threading
from datetime import datetime, timedelta

from django.conf import settings
from django.http import Http404
from django.http import HttpResponse
from django.utils.encoding import iri_to_uri

from utils.jinja2.globals import url_encode


def respond_as_attachment(request, file_path, original_filename, document_root=None):
    if document_root is not None:
        file_path = os.path.join(document_root, file_path)
    try:
        fp = open(file_path, 'rb')
        response = HttpResponse(fp.read())
        fp.close()
        type, encoding = mimetypes.guess_type(original_filename)
        if type is None:
            type = 'application/octet-stream'
        response['Content-Type'] = type
        response['Content-Length'] = str(os.stat(file_path).st_size)
        if encoding is not None:
            response['Content-Encoding'] = encoding
            url_encode()
        response['Content-Disposition'] = "attachment; filename*=UTF-8''%s" % iri_to_uri(original_filename)
        return response
    except Exception as e:
        raise Http404(e)


def respond_generate_file(request, file_name, file_name_serve_as=None):
    if file_name_serve_as is None:
        file_name_serve_as = file_name
    return respond_as_attachment(request, file_name, file_name_serve_as, settings.GENERATE_DIR)


def clean_outdated_generated_files():
    pass  # disable cleaning
    # for file in os.listdir(settings.GENERATE_DIR):
    #     file_path = os.path.join(settings.GENERATE_DIR, file)
    #     if datetime.now() - datetime.fromtimestamp(os.stat(file_path).st_mtime) > timedelta(hours=24):
    #         # It has not been modified for 24 hours
    #         try:
    #             os.remove(file_path)
    #         except OSError:
    #             pass
