import re
from datetime import datetime
from os import path, listdir

from django.conf import settings


def sort_out_directory(directory):
  if not path.exists(directory):
    return []
  return sorted(list(map(lambda file: {'filename': path.basename(file),
                                       'modified_time': datetime.fromtimestamp(path.getmtime(file)).\
                                                        strftime(settings.DATETIME_FORMAT_TEMPLATE),
                                       'size': path.getsize(file)},
                         listdir_with_prefix(directory))),
                key=lambda d: d['modified_time'], reverse=True)


def listdir_with_prefix(directory):
  return list(map(lambda file: path.join(directory, file),
                  filter(lambda f2: not f2.startswith('.'),
                         listdir(directory))))


def normal_regex_check(alias):
  return re.match(r"^[\.a-z0-9_-]{4,64}$", alias)


def valid_fingerprint_check(fingerprint):
  return re.match(r"^[a-z0-9]{16,128}$", fingerprint)
