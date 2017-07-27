import io
import re
import chardet
import base64
import requests
import json
import traceback
from threading import Thread

from functools import wraps
from utils import random_string
from utils.middleware.globalrequestmiddleware import GlobalRequestMiddleware
from .models import Run

white_space_reg = re.compile(r'[\x00-\x20]+')

SERVER_URL = 'http://123.57.161.63:5002'
TOKEN = ('ejudge', 'naive')
TIMEOUT = 60
VALIDATE_URL = SERVER_URL + '/validate'
OUTPUT_URL = SERVER_URL + '/judge/output'



def read_by_formed_lines(fileobj):
    for line in fileobj:
        yield ' '.join(white_space_reg.split(line.strip()))


def well_form_text(text):
    stream = io.StringIO(text.strip())
    out_stream = io.StringIO()
    for line in read_by_formed_lines(stream):
        out_stream.writelines([line, '\n'])
    out_stream.seek(0)
    return out_stream.read()


def well_form_binary(binary):
    try:
        encoding = chardet.detect(binary).get('encoding', 'utf-8')
        return well_form_text(binary.decode(encoding))
    except:
        return ''


def base64encode(binary):
    return base64.b64encode(binary).decode()


def base64decode(binary):
    return base64.b64decode(binary).decode()


def validate_input(binary, validator_code, validator_lang, max_time):
    val_data = {
        'fingerprint': random_string(),
        'code': validator_code,
        'lang': validator_lang,
        'max_time': max_time / 1000,
        'max_memory': -1,
        'input': base64encode(binary)
    }
    return requests.post(VALIDATE_URL, json=json.dumps(val_data), auth=TOKEN, timeout=TIMEOUT).json()


def run_output(model_code, model_lang, max_time, input):
    data = {
        "input": base64encode(input),
        "max_time": max_time / 1000,
        "max_memory": -1,
        "submission": {
            "lang": model_lang,
            "fingerprint": random_string(),
            "code": model_code
        }
    }
    return requests.post(OUTPUT_URL, json=json.dumps(data), auth=TOKEN, timeout=TIMEOUT).json()

