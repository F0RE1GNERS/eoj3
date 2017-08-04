from .models import Server
from .utils import is_success_response
import requests
from django.conf import settings
from os import path

DEFAULT_USERNAME = 'ejudge'


def update_token(server, new_password):
    """
    :type server: Server
    :return:
    """
    url = server.http_address + '/config/token'
    res = requests.post(url, json={'token': new_password}, auth=(DEFAULT_USERNAME, server.token)).json()
    if is_success_response(res):
        server.token = new_password
        server.save(update_fields=['token'])
        return True
    return False


def upload_case(server, case):
    url_check_exist = server.http_address + '/exist/case/%s' % case
    url_input = server.http_address + '/upload/case/%s/input' % case
    url_output = server.http_address + '/upload/case/%s/output' % case
    if requests.get(url_check_exist).json().get('exist'):
        return True
    with open(path.join(settings.TESTDATA_DIR, case + '.in'), 'rb') as inf,\
            open(path.join(settings.TESTDATA_DIR, case + '.out'), 'wb') as ouf:
        res1 = requests.post(url_input, data=inf.read(), auth=(DEFAULT_USERNAME, server.token)).json()
        res2 = requests.post(url_output, data=ouf.read(), auth=(DEFAULT_USERNAME, server.token)).json()
    return is_success_response(res1) and is_success_response(res2)


def _upload_special_program(server, url, sp):
    return requests.post(url, json={
        'fingerprint': sp.fingerprint,
        'lang': sp.lang,
        'code': sp.code
    }).json()


def upload_checker(server, checker):
    url = server.http_address + '/upload/checker'
    return is_success_response(_upload_special_program(server, url, checker))


def upload_validator(server, validator):
    url = server.http_address + '/upload/validator'
    return is_success_response(_upload_special_program(server, url, validator))


def upload_interactor(server, interactor):
    url = server.http_address + '/upload/interactor'
    return is_success_response(_upload_special_program(server, url, interactor))
