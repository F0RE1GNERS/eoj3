import mimetypes
import os
import threading
from urllib import parse
from datetime import datetime, timedelta

from django.http import HttpResponse
from django.conf import settings


def respond_as_attachment(request, file_path, original_filename, document_root=None):
    if document_root is not None:
        file_path = os.path.join(document_root, file_path)
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
    response['Content-Disposition'] = 'attachment; filename=%s' % original_filename
    return response


def respond_generate_file(request, file_name, file_name_serve_as=None):
    if file_name_serve_as is None:
        file_name_serve_as = file_name
    threading.Thread(target=clean_outdated_generated_files).start()
    return respond_as_attachment(request, file_name, file_name_serve_as, settings.GENERATE_DIR)


def clean_outdated_generated_files():
    for file in os.listdir(settings.GENERATE_DIR):
        file_path = os.path.join(settings.GENERATE_DIR, file)
        if datetime.now() - datetime.fromtimestamp(os.stat(file_path).st_mtime) > timedelta(hours=24):
            # It has not been modified for 24 hours
            try:
                os.remove(file_path)
            except OSError:
                pass
