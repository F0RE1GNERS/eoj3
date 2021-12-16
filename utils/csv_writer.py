import csv
from os import path

from django.conf import settings

from . import random_string


def write_csv(data):
  """
  :param data:
  :return: csv file name
  """
  file_name = random_string()
  file_path = path.join(settings.GENERATE_DIR, file_name)
  with open(file_path, 'w', newline='', encoding='utf-8-sig') as csvfile:
  # csv files need to be encoded using UTF-8 BOM to be correctly opened in Excel on Windows
    writer = csv.writer(csvfile)
    for d in data:
      writer.writerow(d)
  return file_path
