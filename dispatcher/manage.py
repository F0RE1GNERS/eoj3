from .models import Server
from .utils import is_success_response
import requests


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