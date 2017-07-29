import base64
import io
import json
import logging
import re

import chardet
import requests

from utils import random_string

white_space_reg = re.compile(r'[\x00-\x20]+')

SERVER_URL = 'http://123.57.161.63:5002'
TOKEN = ('ejudge', 'naive')
TIMEOUT = 60
VALIDATE_URL = SERVER_URL + '/validate'
OUTPUT_URL = SERVER_URL + '/judge/output'
CHECKER_URL = SERVER_URL + '/judge/checker'



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
        'max_time': max_time / 1000,
        'max_memory': -1,
        'input': base64encode(binary)
    }
    val_data.update(_pre_json_program_from_kwargs(lang=validator_lang, code=validator_code))
    return requests.post(VALIDATE_URL, json=json.dumps(val_data), auth=TOKEN, timeout=TIMEOUT).json()


def run_output(model_code, model_lang, max_time, input):
    data = {
        "input": base64encode(input),
        "max_time": max_time / 1000,
        "max_memory": -1,
        "submission": _pre_json_program_from_kwargs(lang=model_lang, code=model_code)
    }
    return requests.post(OUTPUT_URL, json=json.dumps(data), auth=TOKEN, timeout=TIMEOUT).json()


def check_output_with_result(submission, checker, max_time, max_memory, input, output, interactor=None):
    """
    :type submission: tuple
    :param submission: (code, lang)
    :type submission: tuple
    :param checker: (code, lang)
    """
    data = {
        "input": base64encode(input),
        "output": base64encode(output),
        "max_time": max_time / 1000,
        "max_memory": max_memory,
        "submission": _pre_json_program_from_kwargs(submission),
        "checker": _pre_json_program_from_kwargs(checker)
    }
    if interactor:
        data.update(interactor=_pre_json_program_from_kwargs(interactor))
    return requests.post(CHECKER_URL, json=json.dumps(data), auth=TOKEN, timeout=TIMEOUT).json()


def validate_input_multiple(binary, validator_code, validator_lang, max_time):
    val_data = {
        'max_time': max_time / 1000,
        'max_memory': -1,
        'input': list(map(base64encode, binary)),
        'multiple': True
    }
    val_data.update(_pre_json_program_from_kwargs(lang=validator_lang, code=validator_code))
    return requests.post(VALIDATE_URL, json=json.dumps(val_data), auth=TOKEN, timeout=TIMEOUT).json()


def run_output_multiple(model_code, model_lang, max_time, input):
    data = {
        "input": list(map(base64encode, input)),
        "max_time": max_time / 1000,
        "max_memory": -1,
        "submission": _pre_json_program_from_kwargs(lang=model_lang, code=model_code),
        'multiple': True
    }
    return requests.post(OUTPUT_URL, json=json.dumps(data), auth=TOKEN, timeout=TIMEOUT).json()


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
    return requests.post(CHECKER_URL, json=json.dumps(data), auth=TOKEN, timeout=TIMEOUT).json()


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


