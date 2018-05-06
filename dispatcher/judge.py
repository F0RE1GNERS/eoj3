import traceback
import requests
import time
from datetime import datetime

from django.core.mail import send_mail
from django.conf import settings

from utils.detail_formatter import response_fail_with_timestamp, add_timestamp_to_reply
from utils import random_string

from .manage import DEFAULT_USERNAME


def send_judge_through_http(server, code, lang, max_time, max_memory, run_until_complete, cases, checker,
                            interactor, callback, timeout=1800):
    server.last_seen_time = datetime.now()
    server.save(update_fields=['last_seen_time'])
    data = _prepare_judge_json_data(code, lang, max_time, max_memory, run_until_complete, cases, checker, interactor)
    url = server.http_address + '/judge'
    try:
        callback(add_timestamp_to_reply(requests.post(url, json=data, auth=(DEFAULT_USERNAME, server.token),
                                                      timeout=timeout).json()))
    except:
        callback(response_fail_with_timestamp())


def send_judge_through_watch(server, code, lang, max_time, max_memory, run_until_complete, cases, checker,
                             interactor, callback, timeout=900, fallback=True, report_file_path=None):
    """
    :param interactor: None or '' if there is no interactor
    :param callback: function, to call when something is returned (possibly preliminary results)
                     callback should return True when it thinks the result is final result, return False otherwise
                     callback will receive exactly one param, which is the data returned by judge server as a dict
    :param timeout: will fail if it has not heard from judge server for `timeout` seconds
    :param fallback: this method automatically provides a fallback called send_judge_through_http, in case it fails.
                     setting fallback to False will disable such fallback
    """

    # server.last_seen_time = datetime.now()
    # server.save(update_fields=['last_seen_time'])

    data = _prepare_judge_json_data(code, lang, max_time, max_memory, run_until_complete, cases, checker, interactor)
    data.update(hold=False)
    judge_url = server.http_address + '/judge'
    watch_url = server.http_address + '/query'
    watch_report = server.http_address + '/query/report'
    timeout_count = 0

    try:
        response = add_timestamp_to_reply(requests.post(judge_url, json=data, auth=(DEFAULT_USERNAME, server.token),
                                                        timeout=timeout).json())
        if response.get('status') != 'received':
            callback(response)
        while timeout_count < timeout:
            interval = 0.5
            time.sleep(interval)
            response = add_timestamp_to_reply(requests.get(watch_url, json={'fingerprint': data['fingerprint']},
                                              auth=(DEFAULT_USERNAME, server.token), timeout=timeout).json())
            if callback(response):
                if report_file_path:
                    with open(report_file_path, 'w') as handler:
                        handler.write(requests.get(watch_report, json={'fingerprint': data['fingerprint']},
                                                   auth=(DEFAULT_USERNAME, server.token), timeout=timeout).text)
                break
            timeout_count += interval
            interval += 0.1
        if timeout_count >= timeout:
            raise RuntimeError("Send judge through socketio timed out.")
    except:
        if fallback:
            msg = traceback.format_exc()
            send_mail(subject="Submit fail notice", message=msg, from_email=None, recipient_list=settings.ADMIN_EMAIL_LIST,
                      fail_silently=True)
            print(msg)
            send_judge_through_http(server, code, lang, max_time, max_memory, run_until_complete, cases, checker,
                                    interactor, callback)
        else:
            callback(response_fail_with_timestamp())


def _prepare_judge_json_data(code, lang, max_time, max_memory, run_until_complete, cases, checker, interactor):
    all_params = locals().copy()
    if not interactor:
        all_params.pop('interactor')
    all_params['max_time'] /= 1000
    all_params['fingerprint'] = random_string()
    return all_params
