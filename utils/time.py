from django.conf import settings
from datetime import datetime

def datetime_display(time):
    """
    :type time: datetime
    :return: str
    """
    try:
        return time.strftime(settings.DATETIME_FORMAT_TEMPLATE)
    except:
        return ""