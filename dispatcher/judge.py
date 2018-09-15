import time
import traceback
from datetime import datetime
from random import randint

import requests
from django.conf import settings
from django.core.cache import cache
from django.core.mail import send_mail
from django_redis import get_redis_connection

from dispatcher.semaphore import RedisSemaphore
from utils import random_string
from utils.detail_formatter import response_fail_with_timestamp, add_timestamp_to_reply
from utils.site_settings import nonstop_judge
from .manage import DEFAULT_USERNAME


def process_runtime(server, data):
    try:
        for item in data["detail"]:
            if "time" in item:
                item["time"] = round(item["time"] / server.runtime_multiplier, ndigits=3)
    except:
        pass


def send_judge_through_watch(server, code, lang, max_time, max_memory, run_until_complete, cases, checker,
                             interactor, group_config, callback, timeout=900, fallback=True, report_file_path=None):
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

    data = _prepare_judge_json_data(server, code, lang, max_time, max_memory, run_until_complete, cases, checker,
                                    interactor, group_config)
    data.update(hold=False)
    judge_url = server.http_address + '/judge'
    watch_url = server.http_address + '/query'
    watch_report = server.http_address + '/query/report'
    timeout_count = 0

    redis_server = get_redis_connection("judge")

    with RedisSemaphore(redis_server, "judge:%d" % server.pk, server.concurrency, timeout_seconds=timeout):
        try:
            response = add_timestamp_to_reply(requests.post(judge_url, json=data, auth=(DEFAULT_USERNAME, server.token),
                                                            timeout=timeout).json())
            process_runtime(server, response)
            if response.get('status') != 'received':
                callback(response)
            while timeout_count < timeout:
                interval = 0.5
                time.sleep(interval)
                response = add_timestamp_to_reply(requests.get(watch_url, json={'fingerprint': data['fingerprint']},
                                                               auth=(DEFAULT_USERNAME, server.token),
                                                               timeout=timeout).json())
                process_runtime(server, response)
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
                msg = "Time: %s\n%s" % (datetime.now(), traceback.format_exc())
                send_mail(subject="Submit fail notice", message=msg, from_email=None,
                          recipient_list=settings.ADMIN_EMAIL_LIST,
                          fail_silently=True)
                print(msg)
            else:
                callback(response_fail_with_timestamp())


def _prepare_judge_json_data(server, code, lang, max_time, max_memory, run_until_complete, cases, checker, interactor,
                             group_config):
    all_params = locals().copy()
    all_params.pop("server")
    all_params.pop("group_config")
    if not interactor:
        all_params.pop('interactor')
    all_params['max_time'] /= 1000
    all_params['max_time'] *= server.runtime_multiplier
    all_params['fingerprint'] = random_string()
    if group_config.get("on"):
        all_params['group_list'] = group_config["group_list"]
        all_params['group_dependencies'] = group_config["group_dependencies"]
    if nonstop_judge():
        all_params['run_until_complete'] = True
    return all_params
