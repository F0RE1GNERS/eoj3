import time
import traceback
import uuid
from datetime import datetime
from random import randint

import requests
from django.conf import settings
from django.core.cache import cache
from django.core.mail import send_mail

from utils import random_string
from utils.detail_formatter import response_fail_with_timestamp, add_timestamp_to_reply
from utils.site_settings import nonstop_judge
from .manage import DEFAULT_USERNAME


class RedisSemaphore(object):
    """
    Gist: https://gist.github.com/jhorman/8062862
    Redis base semaphore. Supports timeouts of semaphore locks.
    """

    def __init__(self, redis, name, limit, timeout_seconds=10):
        """
        Timeout specifies how long taken semaphores are valid. Expired semaphores don't count
        toward the total taken count. Crashed clients therefore will release their locks after
        timeout seconds.
        @name Redis key name for zset
        @limit Number of locks to allow
        @timeout_seconds How long to allow old locks to persist.
        """
        super(RedisSemaphore, self).__init__()
        self.__redis = redis
        self.__name = 'semaphore:%s' % name
        self.__limit = limit
        self.__timeout = timeout_seconds
        self.__lock_id = uuid.uuid4().hex

    def __enter__(self, blocking=True, wait_for_seconds=5):
        """
        Take out a semaphore. Must be released later. Returns false
        if a lock couldn't be acquired.
        @block If true keeps trying to get the lock for timeout seconds.
        @timeout How long to wait for the lock. Returns false if lock not avail.
        """

        def acquire_lock(transaction):
            # how many locks are already taken in the set. ignores locks that have timed out.
            now = time.time()
            count = transaction.zcount(self.__name, now - self.__timeout, now + 1)
            # set the pipline back to buffered mode
            transaction.multi()
            # if there is space in the set for an additional lock append it to the list
            if count < self.__limit:
                # the score of the lock is current time so that locks can expire
                transaction.zadd(self.__name, self.__lock_id, time.time())
                return True
            # no space available, return False
            return False

        # keep trying to get the lock for wait_for_seconds seconds
        start = time.time()
        while (time.time() - start) < wait_for_seconds:
            if self.__redis.transaction(acquire_lock, self.__name, value_from_callable=True):
                now = time.time()
                return True
            elif blocking:
                self.cleanup()
                time.sleep(.5)

        return False

    acquire = __enter__

    def __exit__(self, exc_type=None, exc_value=None, traceback=None):
        """ Release lock by removing from redis sorted set. """
        self.__redis.zrem(self.__name, self.__lock_id)

    release = __exit__

    def cleanup(self):
        """ Removes all locks after timeout expiration from the sorted set. """
        return self.__redis.zremrangebyscore(self.__name, 0, time.time() - self.__timeout)


def process_runtime(server, data):
    try:
        for item in data["detail"]:
            if "time" in item:
                item["time"] = round(item["time"] / server.runtime_multiplier, ndigits=3)
    except:
        pass


def send_judge_through_http(server, code, lang, max_time, max_memory, run_until_complete, cases, checker,
                            interactor, group_config, callback, timeout=1800):
    # server.last_seen_time = datetime.now()
    # server.save(update_fields=['last_seen_time'])
    data = _prepare_judge_json_data(server, code, lang, max_time, max_memory, run_until_complete, cases, checker,
                                    interactor)
    url = server.http_address + '/judge'
    try:
        data = add_timestamp_to_reply(requests.post(url, json=data, auth=(DEFAULT_USERNAME, server.token),
                                                    timeout=timeout).json())
        process_runtime(server, data)
        callback(data)
    except:
        callback(response_fail_with_timestamp())


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
                                    interactor,
                                    group_config)
    data.update(hold=False)
    judge_url = server.http_address + '/judge'
    watch_url = server.http_address + '/query'
    watch_report = server.http_address + '/query/report'
    timeout_count = 0

    # redis_server = get_redis_connection("default")

    # enter zone
    cache_key = "s%d:%d" % (server.pk, randint(0, 1e9))
    if server.concurrency <= 0:
        raise ValueError("Server should have concurrency at least 1.")
    wait_interval = 1.0
    while True:
        if len(cache.keys("s%d:*" % server.pk)) < server.concurrency:
            cache.set(cache_key, 1, timeout)
            break
        time.sleep(wait_interval)
        if wait_interval > 0.2:
            wait_interval -= 0.01

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

    # exit zone
    cache.delete(cache_key)


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
