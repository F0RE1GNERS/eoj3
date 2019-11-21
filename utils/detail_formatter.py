import traceback
from datetime import datetime


def add_timestamp_to_reply(data):
  data.update(timestamp=datetime.now().timestamp())
  return data


def response_fail_with_timestamp():
  return add_timestamp_to_reply({'status': 'reject', 'message': traceback.format_exc()})
