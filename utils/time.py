from django.conf import settings


def datetime_display(time):
  try:
    return time.strftime(settings.DATETIME_FORMAT_TEMPLATE)
  except:
    return ""
