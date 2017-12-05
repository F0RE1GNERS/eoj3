import base64
import json
import logging
import re
import time
import traceback
import zipfile
from datetime import datetime
from functools import wraps
from os import path, makedirs, remove, replace
from shutil import copyfile, rmtree
from threading import Thread

import yaml
from django.conf import settings
from django.http import Http404
from yaml.scanner import ScannerError

from account.models import User
from dispatcher.models import Server
from polygon.models import EditSession
from polygon.models import Run
from polygon.problem.case import (
    well_form_binary, check_output_with_result_multiple, run_output_multiple, validate_input_multiple,
    stress_test, generate_multiple, base64decode
)
from polygon.problem.utils import valid_fingerprint_check, normal_regex_check
from problem.models import Problem, SpecialProgram, get_input_path, get_output_path
from problem.tasks import upload_problem_to_judge_server
from utils import random_string
from utils.file_preview import sort_data_list_from_directory
from utils.hash import file_hash, case_hash
from utils.language import LANG_EXT
from utils.middleware.globalrequestmiddleware import GlobalRequestMiddleware

CONFIG_FILE_NAME = 'config.yml'
STATEMENT_DIR = 'statement'
TESTS_DIR = 'tests'
PROGRAM_DIR = 'program'
DEFAULT_POINT = 10
PROGRAM_TYPE_LIST = ['checker', 'validator', 'interactor', 'generator', 'solution']
USED_PROGRAM_IN_CONFIG_LIST = ['checker', 'validator', 'interactor', 'solution']
STATEMENT_TYPE_LIST = ['description', 'input', 'output', 'hint']
MAXIMUM_CASE_SIZE = 128  # in megabytes
USUAL_READ_SIZE = 4096


def load_config(session):
    """
    Load config of a session
    If the session does not have a config, return an empty dict
    :type session: EditSession
    :rtype: dict
    """
    config_file = path.join(settings.REPO_DIR, session.fingerprint, CONFIG_FILE_NAME)
    try:
        with open(config_file, 'r') as f:
            return yaml.load(f)
    except FileNotFoundError:
        return dict()
    except ScannerError:
        raise Http404


def dump_config(session, config):
    config_file = path.join(settings.REPO_DIR, session.fingerprint, CONFIG_FILE_NAME)
    with open(config_file, 'w') as f:
        yaml.dump(config, f, default_flow_style=False)


def run_with_report(func, run, *args, **kwargs):
    try:
        start = time.time()
        d = func(*args, **kwargs)
        ed = time.time()
        logging.info('%.3fs %s' % (ed - start, str(d)))
        run.status = 1 if d.get('status') == 'received' else -1
        run.message = json.dumps(d, sort_keys=True, indent=4)
    except:
        run.status = -1
        run.message = traceback.format_exc()
    finally:
        run.save()


def run_async_with_report(f):
    @wraps(f)
    def decorated(label, *args, **kwargs):
        request = GlobalRequestMiddleware.get_current_request()
        run = Run.objects.create(user=request.user, status=0, label=label)
        func_hl = Thread(target=run_with_report, args=(f, run) + args, kwargs=kwargs)
        func_hl.start()
        return run.id

    return decorated


def success_response(response):
    return response.get('status') == 'received'


def init_session(problem, user):
    """
    Init a session
    :type problem: Problem
    :type user: User
    :return: session
    """
    fingerprint = random_string()
    session = EditSession.objects.create(problem=problem, user=user, fingerprint=fingerprint,
                                         last_synchronize=datetime.now())
    rmtree(path.join(settings.REPO_DIR, fingerprint), ignore_errors=True)
    makedirs(path.join(settings.REPO_DIR, fingerprint))
    pull_session(session)
    return session


def pull_session(session):
    """
    Make a session up-to-date with the problem
    :type session: EditSession
    :return: None
    """

    def case_setdefault(d):
        d["order"] = 0
        d["point"] = DEFAULT_POINT
        d["pretest"] = False
        d["sample"] = False

    problem = session.problem
    session_dir = get_session_dir(session)
    config = load_config(session)

    config['time_limit'] = problem.time_limit
    config['memory_limit'] = problem.memory_limit

    tests_dir = path.join(session_dir, TESTS_DIR)
    config['case'] = case_dict = config.setdefault('case', dict())
    point_list = problem.point_list
    for key in case_dict.keys():
        case_setdefault(case_dict[key])

    makedirs(tests_dir, exist_ok=True)
    for case in set(problem.sample_list + problem.pretest_list + problem.case_list):
        if case not in case_dict:
            case_dict[case] = dict()
            case_setdefault(case_dict[case])
            now_input_path, now_output_path = get_test_file_path(session, case)
            copyfile(get_input_path(case), now_input_path)
            copyfile(get_output_path(case), now_output_path)

    for case in set(problem.sample_list):
        case_dict[case]["sample"] = True
    for case in set(problem.pretest_list):
        case_dict[case]["pretest"] = True
    for ind, case in enumerate(problem.case_list, start=1):
        case_dict[case]["order"] = ind
        case_dict[case]["point"] = point_list[ind - 1]

    programs = config.setdefault('program', dict())
    # pull top-relevant programs first
    to_pull_programs = list(filter(lambda x: x, [problem.checker, problem.interactor, problem.validator]))
    config["checker"] = problem.checker  # This is fingerprint, to be converted to filename later
    config["interactor"] = problem.interactor
    config["validator"] = problem.validator
    config.setdefault('solution', '')
    _important_special_program = {
        problem.checker: "checker",
        problem.interactor: "interactor",
        problem.validator: "validator"
    }
    for program in to_pull_programs:
        sub = SpecialProgram.objects.get(fingerprint=program)
        full_path = path.join(session_dir, PROGRAM_DIR, sub.filename)
        # warning: when filename collides, overrides happen
        makedirs(path.dirname(full_path), exist_ok=True)
        with open(full_path, 'w') as sub_fs:
            sub_fs.write(sub.code)
        file_role = _important_special_program.get(sub.fingerprint)
        programs[sub.filename] = dict(fingerprint=sub.fingerprint,
                                      type=sub.category,
                                      lang=sub.lang)
        if file_role:  # in case it is something important
            programs[sub.filename]['used'] = file_role
            config[file_role] = sub.filename  # substitute fingerprint with filename in config file

    for program in programs.values():  # to get a pure config dict, even though it is to be added later
        if isinstance(program, dict) and program.get('used'):
            program.pop('used')

    dump_config(session, config)
    session.last_synchronize = datetime.now()
    session.save(update_fields=["last_synchronize"])


def push_session(session):
    """
    :type session: EditSession
    :return:
    """
    problem = session.problem
    config = load_config(session)
    for type in ['checker', 'validator', 'interactor']:
        file = config[type]
        if file:
            file_config = config['program'][file]
            if not SpecialProgram.objects.filter(fingerprint=file_config['fingerprint']).exists():
                SpecialProgram.objects.create(fingerprint=file_config['fingerprint'], lang=file_config['lang'],
                                              filename=file, category='checker',
                                              code=read_program_file(session, file))
            setattr(problem, type, file_config['fingerprint'])
        else:
            setattr(problem, type, '')
    case_order = {}
    case_list, sample_list, pretest_list = [], [], []
    for k, v in config['case'].items():
        session_case_input, session_case_output = get_test_file_path(session, k)
        problem_case_input, problem_case_output = get_input_path(k), get_output_path(k)
        if not path.exists(problem_case_input):
            copyfile(session_case_input, problem_case_input)
            copyfile(session_case_output, problem_case_output)
        if v['order']:
            case_list.append((k, v['point']))
        if v.get('pretest'):
            pretest_list.append(k)
        if v.get('sample'):
            sample_list.append(k)
        case_order[k] = v['order']
    if case_list:
        cases, points = zip(*sorted(case_list, key=lambda x: case_order[x[0]]))
    else:
        cases, points = [], []
    pretest_list.sort(key=lambda x: case_order[x])
    sample_list.sort(key=lambda x: case_order[x])
    problem.cases = ','.join(cases)
    problem.points = ','.join(map(str, points))
    problem.pretests = ','.join(pretest_list)
    problem.sample = ','.join(sample_list)

    for server in Server.objects.filter(enabled=True).all():
        if not upload_problem_to_judge_server(problem, server):
            raise ValueError("Upload failed. Please recheck your programs.")
        server.last_synchronize_time = datetime.now()
        server.save(update_fields=['last_synchronize_time'])

    problem.save()  # update finally
    pull_session(session)


def program_file_exists(session, filename):
    filepath = _get_program_file_path(session, filename)
    return path.exists(filepath)


def read_program_file(session, filename):
    filepath = _get_program_file_path(session, filename)
    with open(filepath, 'r') as fs:
        return fs.read()


def save_program_file(session, filename, type, lang, code, raw_filename=None):
    extension = dict(LANG_EXT).get(lang)
    if not extension:
        raise ValueError("Unrecognized language")
    if not path.splitext(filename)[1]:
        filename = filename + '.' + extension
    if type not in PROGRAM_TYPE_LIST:
        raise ValueError("Unrecognized program type")

    new_filepath = _get_program_file_path(session, filename)
    config = load_config(session)
    if raw_filename:
        # Pop first. In case something goes wrong, it will throw an exception
        config['program'][filename] = config['program'].pop(raw_filename)
        for identifier in USED_PROGRAM_IN_CONFIG_LIST:
            if config.get(identifier) == raw_filename:
                config[identifier] = filename
        old_filepath = _get_program_file_path(session, raw_filename)
        replace(old_filepath, new_filepath)
    else:
        if filename in config['program']:
            raise ValueError('File %s already exists' % filename)

    with open(new_filepath, 'w') as new_fs:
        new_fs.write(code)
    config['program'].setdefault(filename, dict())
    config['program'][filename].update(fingerprint=file_hash(new_filepath, lang),
                                       type=type, lang=lang)
    dump_config(session, config)


def delete_program_file(session, filename):
    filepath = _get_program_file_path(session, filename)
    if not path.exists(filepath):
        raise ValueError("File does not exist")
    config = load_config(session)
    if filename in list(map(lambda x: config[x], USED_PROGRAM_IN_CONFIG_LIST)):
        raise ValueError("File is still in use")
    config['program'].pop(filename, None)
    dump_config(session, config)
    remove(filepath)


def toggle_program_file_use(session, filename):
    if not program_file_exists(session, filename):
        raise ValueError("File does not exist")
    config = load_config(session)
    t = config['program'][filename]['type']
    if config.get(t) == filename:
        # turn it off
        config[t] = ''
    else:
        config[t] = filename
    dump_config(session, config)


def save_case(session, input_binary, output_binary, raw_fingerprint=None, **kwargs):
    fingerprint = case_hash(session.problem_id, input_binary, output_binary)
    new_input_path, new_output_path = get_test_file_path(session, fingerprint)
    config = load_config(session)
    if raw_fingerprint:
        config['case'][fingerprint] = config['case'].pop(raw_fingerprint)
        old_input_path, old_output_path = get_test_file_path(session, raw_fingerprint)
        replace(old_input_path, new_input_path)
        replace(old_output_path, new_output_path)
    else:
        # This is a new case, should have point, order
        kwargs.setdefault('point', 10)
        try:
            already_have = max(map(lambda d: d['order'], config['case'].values()))
        except ValueError:
            already_have = 0
        kwargs.setdefault('order', already_have + 1)
    with open(new_input_path, 'wb') as fs, open(new_output_path, 'wb') as gs:
        fs.write(input_binary)
        gs.write(output_binary)
    config['case'].setdefault(fingerprint, dict())
    config['case'][fingerprint].update(**kwargs)
    dump_config(session, config)


def update_case_config(session, fingerprint, **kwargs):
    config = load_config(session)
    config['case'][fingerprint].update(**kwargs)
    dump_config(session, config)


def get_case_metadata(session, fingerprint):
    inp, oup = get_test_file_path(session, fingerprint)
    modified_time = max(path.getmtime(inp), path.getmtime(oup))
    return {'modified_time': datetime.fromtimestamp(modified_time).strftime(settings.DATETIME_FORMAT_TEMPLATE),
            'size': path.getsize(inp) + path.getsize(oup)}


def read_case(session, fingerprint, type=None):
    try:
        inp, oup = get_test_file_path(session, fingerprint)
        with open(inp, 'r') as fs, open(oup, 'r') as gs:
            if type == 'in':
                return fs.read()
            elif type == 'out':
                return gs.read()
            else:
                res = {'input': {'nan': False,
                                 'text': fs.read(USUAL_READ_SIZE)},
                       'output': {'nan': False,
                                  'text': gs.read(USUAL_READ_SIZE)}
                       }
                if fs.read(1):
                    res['input']['text'] = 'This file is too large to edit.\n' + res['input']['text']
                    res['input']['nan'] = True
                if gs.read(1):
                    res['output']['text'] = 'This file is too large to edit.\n' + res['output']['text']
                    res['output']['nan'] = True
                return res
    except:
        raise Http404


def process_uploaded_case(session, file_path):
    if re.search(r'\.zip$', file_path, re.IGNORECASE):
        # this is a zip file
        tmp_directory = '/tmp/' + random_string()
        with zipfile.ZipFile(file_path) as myZip:
            myZip.extractall(path=tmp_directory)
        for inf, ouf in sort_data_list_from_directory(tmp_directory):
            with open(path.join(tmp_directory, inf), 'rb') as ins, open(path.join(tmp_directory, ouf), 'rb') as ous:
                save_case(session, ins.read(), ous.read())
        rmtree(tmp_directory)
    else:
        with open(file_path, 'rb') as file:
            save_case(session, file.read(), b'')


def reform_case(session, fingerprint, **kwargs):
    inp, oup = get_test_file_path(session, fingerprint)
    with open(inp, 'rb') as fs, open(oup, 'rb') as gs:
        input, output = fs.read(), gs.read()
    input = well_form_binary(input).encode()
    if not kwargs.get('only_input'):
        output = well_form_binary(output).encode()
    save_case(session, input, output, raw_fingerprint=fingerprint, well_form=True)


def update_multiple_case_config(session, kw):
    config = load_config(session)
    for fingerprint, d in config['case'].items():
        d.update(order=0)  # clear first
        if fingerprint in kw:
            d.update(kw[fingerprint])
    dump_config(session, config)


def _normalize_case_order(config):
    for index, d in enumerate(sorted(filter(lambda x: x.get('order'),
                                            config['case'].values()),
                                     key=lambda x: x['order']),
                              start=1):
        d.update(order=index)


def delete_case(session, fingerprint):
    config = load_config(session)
    config['case'].pop(fingerprint)
    old_input_path, old_output_path = get_test_file_path(session, fingerprint)
    remove(old_input_path)
    remove(old_output_path)
    _normalize_case_order(config)
    dump_config(session, config)


@run_async_with_report
def validate_case(session, validator, fingerprints):
    config = load_config(session)
    input = list(map(lambda fp: _get_test_input(session, fp), fingerprints))
    result = validate_input_multiple(input, read_program_file(session, validator),
                                     config['program'][validator]['lang'], config['time_limit'])
    if success_response(result):
        config = load_config(session)
        for i, res in zip(fingerprints, result['result']):
            config['case'][i]['validated'] = -1 if res['verdict'] != 0 else 1
        dump_config(session, config)
    return result


@run_async_with_report
def get_case_output(session, model, fingerprints):
    config = load_config(session)

    input = list(map(lambda fp: _get_test_input(session, fp), fingerprints))
    result = run_output_multiple(read_program_file(session, model), config['program'][model]['lang'],
                                 config['time_limit'], input)
    if success_response(result):
        for i, inp, res in zip(fingerprints, input, result['result']):
            save_case(session, inp, base64decode(res.pop('output')).encode(), raw_fingerprint=i, model=True)
    return result


@run_async_with_report
def check_case(session, submission, checker, fingerprints):
    config = load_config(session)
    inp_with_oup = list(map(lambda fp: _get_test_input_and_output(session, fp), fingerprints))
    input, output = zip(*inp_with_oup)
    kw = {}
    if config.get('interactor'):
        kw.update(interactor=_get_program_tuple(session, config['interactor'], config))
    result = check_output_with_result_multiple(_get_program_tuple(session, submission, config),
                                               _get_program_tuple(session, checker, config),
                                               config['time_limit'], config['memory_limit'],
                                               input, output, **kw)
    if success_response(result):
        for i, res in zip(fingerprints, result['result']):
            update_case_config(session, i, checked=1 if res['verdict'] == 0 else -1)
    return result


@run_async_with_report
def generate_input(session, generator, param_raw):
    # Parse param
    param_list = []
    for line_num, param_line in enumerate(param_raw.split('\n')):
        param_list.append(re.split(r'\s+', param_line))
    if len(param_list) == 0:
        raise ValueError('Must have at least one set of command line arguments.')
    config = load_config(session)
    result = generate_multiple(_get_program_tuple(session, generator, config), config['time_limit'],
                               config['memory_limit'], param_list)
    if success_response(result):
        outputs = result.pop('output')
        for output in outputs:
            save_case(session, base64decode(output).encode(), b'')
        result.update(message='[ Successfully created %d cases ]\n%s' % (len(outputs), result.get('message', '')))
    return result


@run_async_with_report
def stress(session, generator, submission, param_raw, time):
    config = load_config(session)
    model = config['model']
    if model == submission:
        raise ValueError('Model and your test program are the same.')
    if not model:
        raise ValueError('You must assign a model program.')

    param_list = []
    for line_num, param_line in enumerate(param_raw.split('\n')):
        param_list.append(re.split(r'\s+', param_line))
    if len(param_list) == 0:
        raise ValueError('Must have at least one set of command line arguments.')

    config = load_config(session)

    kw = {}
    if config.get('interactor'):
        kw.update(interactor=_get_program_tuple(session, config['interactor'], config))
    result = stress_test(_get_program_tuple(session, model, config),
                         _get_program_tuple(session, submission, config),
                         _get_program_tuple(session, generator, config),
                         param_list, config['time_limit'], config['memory_limit'], time,
                         _get_program_tuple(session, config['checker'], config), kw)

    if success_response(result):
        outputs = result.pop('output')
        for output in outputs:
            save_case(session, base64decode(output).encode(), b'')
        result.update(message='[ Successfully created %d cases ]\n%s' % (len(outputs), result.get('message', '')))
    return result


def get_session_dir(session):
    return path.join(settings.REPO_DIR, session.fingerprint)


def _get_program_file_path(session, filename):
    program_dir = path.join(get_session_dir(session), PROGRAM_DIR)
    makedirs(program_dir, exist_ok=True)
    if not normal_regex_check(filename):
        raise ValueError("Invalid filename")
    return path.join(program_dir, filename)


def get_test_file_path(session, fingerprint):
    if not valid_fingerprint_check(fingerprint):
        raise ValueError("Invalid fingerprint")
    base = path.join(get_session_dir(session), TESTS_DIR, fingerprint)
    return base + '.in', base + '.out'


def _get_test_input(session, fingerprint):
    inp, _ = get_test_file_path(session, fingerprint)
    with open(inp, 'rb') as fs:
        return fs.read()


def _get_test_input_and_output(session, fingerprint):
    inp, oup = get_test_file_path(session, fingerprint)
    with open(inp, 'rb') as fs, open(oup, 'rb') as gs:
        return fs.read(), gs.read()


def _get_program_tuple(session, filename, config=None):
    if not config:
        config = load_config(session)
    return read_program_file(session, filename), config['program'][filename]['lang']
