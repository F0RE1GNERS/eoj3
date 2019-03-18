from .models import Server
from .utils import is_success_response
import requests
from django.conf import settings
from os import path
import traceback

DEFAULT_USERNAME = 'ejudge'


def ping(server):
  url = server.http_address + '/ping'
  try:
    if requests.get(url).text == "pong":
      return True
    return False
  except:
    return False


def update_token(server, new_password):
  """
  :type server: Server
  :return:
  """
  if server.version >= 3:
    return
  url = server.http_address + '/config/token'
  res = requests.post(url, json={'token': new_password}, auth=(DEFAULT_USERNAME, server.token)).json()
  if is_success_response(res):
    server.token = new_password
    server.save(update_fields=['token'])
    return True
  return False


def upload_case(server, case):
  if server.version >= 3:
    return
  url_check_exist = server.http_address + '/exist/case/%s' % case
  url_input = server.http_address + '/upload/case/%s/input' % case
  url_output = server.http_address + '/upload/case/%s/output' % case
  if requests.get(url_check_exist).json().get('exist'):
    return True
  with open(path.join(settings.TESTDATA_DIR, 'in', case[:2], case[2:4], case), 'rb') as inf, \
      open(path.join(settings.TESTDATA_DIR, 'out', case[:2], case[2:4], case), 'rb') as ouf:  # TODO: unsafe
    res1 = requests.post(url_input, data=inf.read(), auth=(DEFAULT_USERNAME, server.token)).json()
    res2 = requests.post(url_output, data=ouf.read(), auth=(DEFAULT_USERNAME, server.token)).json()
  if not is_success_response(res1) and is_success_response(res2):
    raise ValueError("%s; %s" % (res1, res2))


def upload_spj(server, sp):
  if not server.master:
    return {"status": "received"}
  url = server.http_address + "/upload/spj"
  return requests.post(url, json={
    'fingerprint': sp.fingerprint,
    'lang': sp.lang,
    'code': sp.code
  }, auth=(DEFAULT_USERNAME, server.token)).json()


def _upload_special_program(server, url, sp):
  return requests.post(url, json={
    'fingerprint': sp.fingerprint,
    'lang': sp.lang,
    'code': sp.code
  }, auth=(DEFAULT_USERNAME, server.token)).json()


def upload_checker(server, checker):
  if server.version >= 3:
    res = upload_spj(server, checker)
  else:
    url = server.http_address + '/upload/checker'
    res = _upload_special_program(server, url, checker)
  if not is_success_response(res):
    raise ValueError(str(res))


def upload_validator(server, validator):
  if server.version >= 3:
    return
  url = server.http_address + '/upload/validator'
  res = _upload_special_program(server, url, validator)
  if not is_success_response(res):
    raise ValueError(str(res))


def upload_interactor(server, interactor):
  if server.version >= 3:
    res = upload_spj(server, interactor)
  else:
    url = server.http_address + '/upload/interactor'
    res = _upload_special_program(server, url, interactor)
  if not is_success_response(res):
    raise ValueError(str(res))


def list_spj(server):
  if server.version <= 2:
    return []
  else:
    res = requests.get(server.http_address + "/list/spj", auth=(DEFAULT_USERNAME, server.token)).json()
    if not is_success_response(res):
      raise ValueError(str(res))
    return set(pr[:pr.rfind(".")] for pr in res["spj"])
