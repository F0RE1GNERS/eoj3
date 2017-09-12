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

    # To inspect details for the below code, see http://greenbytes.de/tech/tc2231/
    if 'WebKit' in request.META['HTTP_USER_AGENT']:
        # Safari 3.0 and Chrome 2.0 accepts UTF-8 encoded string directly.
        filename_header = 'filename=%s' % original_filename
    elif 'MSIE' in request.META['HTTP_USER_AGENT']:
        # IE does not support internationalized filename at all.
        # It can only recognize internationalized URL, so we do the trick via routing rules.
        filename_header = ''
    else:
        # For others like Firefox, we follow RFC2231 (encoding extension in HTTP headers).
        filename_header = 'filename*=UTF-8\'\'%s' % parse.quote(original_filename)
    response['Content-Disposition'] = 'attachment; ' + filename_header
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
