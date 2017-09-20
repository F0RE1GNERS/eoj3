import base64
import io
import json
import logging
import re

import chardet
import requests

from utils import random_string

white_space_reg = re.compile(r'[\x00-\x20\s]+')

SERVER_URL = 'http://123.57.161.63:5002'
TOKEN = ('ejudge', 'naive')
TIMEOUT = 60
LONG_TEST_TIMEOUT = 600
MAX_GENERATE = 5
VALIDATE_URL = SERVER_URL + '/validate'
OUTPUT_URL = SERVER_URL + '/judge/output'
CHECKER_URL = SERVER_URL + '/judge/checker'
GENERATOR_URL = SERVER_URL + '/generate'
STRESS_URL = SERVER_URL + '/stress'



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


def validate_input_multiple(binary, validator_code, validator_lang, max_time):
    val_data = {
        'max_time': max_time / 1000,
        'max_memory': -1,
        'input': list(map(base64encode, binary)),
        'multiple': True
    }
    val_data.update(_pre_json_program_from_kwargs(lang=validator_lang, code=validator_code))
    return requests.post(VALIDATE_URL, json=val_data, auth=TOKEN, timeout=LONG_TEST_TIMEOUT).json()


def run_output_multiple(model_code, model_lang, max_time, input):
    data = {
        "input": list(map(base64encode, input)),
        "max_time": max_time / 1000,
        "max_memory": -1,
        "submission": _pre_json_program_from_kwargs(lang=model_lang, code=model_code),
        'multiple': True
    }
    return requests.post(OUTPUT_URL, json=data, auth=TOKEN, timeout=LONG_TEST_TIMEOUT).json()


def check_output_with_result_multiple(submission, checker, max_time, max_memory, input, output, interactor=None):
    data = {
        "input": list(map(base64encode, input)),
        "output": list(map(base64encode, output)),
        "max_time": max_time / 1000,
        "max_memory": max_memory,
        "submission": _pre_json_program_from_kwargs(submission),
        "checker": _pre_json_program_from_kwargs(checker),
        'multiple': True
    }
    if interactor:
        data.update(interactor=_pre_json_program_from_kwargs(interactor))
    return requests.post(CHECKER_URL, json=data, auth=TOKEN, timeout=LONG_TEST_TIMEOUT).json()


def generate_multiple(generator, max_time, max_memory, command_line_args):
    data = {
        'max_time': max_time / 1000,
        'max_memory': -1,
        "command_line_args": command_line_args,
        'multiple': True
    }
    data.update(_pre_json_program_from_kwargs(generator))
    return requests.post(GENERATOR_URL, json=data, auth=TOKEN, timeout=LONG_TEST_TIMEOUT).json()


def stress_test(model, submission, generator, command_line_args_list, max_time, max_memory, max_sum_time,
                checker, interactor=None):
    data = {
        "std": _pre_json_program_from_kwargs(model),
        "submission": _pre_json_program_from_kwargs(submission),
        "generator": _pre_json_program_from_kwargs(generator),
        "checker": _pre_json_program_from_kwargs(checker),
        "max_time": max_time,
        "max_sum_time": max_sum_time,
        "max_memory": max_memory,
        "command_line_args_list": command_line_args_list,
        "max_generate": MAX_GENERATE
    }
    if interactor:
        data.update(interactor=_pre_json_program_from_kwargs(interactor))
    return requests.post(STRESS_URL, json=data, auth=TOKEN, timeout=LONG_TEST_TIMEOUT).json()


def _pre_json_program_from_kwargs(*args, **kwargs):
    if len(args) == 1:
        assert isinstance(args[0], tuple)
        code, lang = args[0]
    elif len(args) == 2:
        assert isinstance(args[0], str)
        assert isinstance(args[1], str)
        code, lang = args
    else:
        code, lang = kwargs["code"], kwargs["lang"]
    return {
        "lang": lang,
        "fingerprint": random_string(),
        "code": code
    }
