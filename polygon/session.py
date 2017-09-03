import base64
import copy
import logging
import re
import traceback
import zipfile
import time
from datetime import datetime
from functools import wraps
from os import path, makedirs, listdir, remove, walk, replace
from shutil import copyfile, rmtree
from threading import Thread

import yaml
from django.conf import settings

from account.models import User
from dispatcher.models import Server
from problem.models import Problem, SpecialProgram, get_input_path, get_output_path
from problem.tasks import upload_problem_to_judge_server
from utils import random_string
from utils.file_preview import sort_data_list_from_directory
from utils.hash import file_hash, case_hash
from utils.language import LANG_EXT
from utils.middleware.globalrequestmiddleware import GlobalRequestMiddleware
from .case import (
    well_form_binary, validate_input, run_output, check_output_with_result,
    check_output_with_result_multiple, run_output_multiple, validate_input_multiple,
    stress_test, generate_multiple
)
from .models import EditSession
from .models import Run

CONFIG_FILE_NAME = 'config.yml'
STATEMENT_DIR = 'statement'
TESTS_DIR = 'tests'
PROGRAM_DIR = 'program'
DEFAULT_POINT = 10
PROGRAM_TYPE_LIST = ['checker', 'validator', 'interactor', 'generator', 'solution']
USED_PROGRAM_IN_CONFIG_LIST = ['checker', 'validator', 'interactor', 'model']
STATEMENT_TYPE_LIST = ['description', 'input', 'output', 'hint']
MAXIMUM_CASE_SIZE = 128  # in megabytes
USUAL_READ_SIZE = 1024
MESSAGE_STORAGE_SIZE = 4096


def run_with_report(func, run, *args, **kwargs):
    try:
        start = time.time()
        d = func(*args, **kwargs)
        ed = time.time()
        logging.info('%.3fs %s' % (ed - start, str(d)))
        run.status = 1 if d.get('status') == 'received' else -1
        run.message = d.get('message', '')[:MESSAGE_STORAGE_SIZE]
    except:
        run.status = -1
        run.message = traceback.format_exc()[:MESSAGE_STORAGE_SIZE]
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
    :return: None
    """
    fingerprint = random_string()
    session = EditSession.objects.create(problem=problem, user=user, fingerprint=fingerprint,
                                         last_synchronize=datetime.now())
    rmtree(path.join(settings.REPO_DIR, fingerprint), ignore_errors=True)
    makedirs(path.join(settings.REPO_DIR, fingerprint))
    pull_session(session)


def pull_session(session):
    """
    Make a session up-to-date with the problem
    :type session: EditSession
    :return: None
    """
    problem = session.problem
    session_dir = get_session_dir(session)
    config = load_config(session)
    config['alias'] = problem.alias
    config['title'] = problem.title
    config['time_limit'] = problem.time_limit
    config['memory_limit'] = problem.memory_limit
    config['source'] = problem.source

    description_file = config.setdefault('description', 'description.md')
    input_file = config.setdefault('input', 'input.md')
    output_file = config.setdefault('output', 'output.md')
    hint_file = config.setdefault('hint', 'hint.md')
    statement_dir = path.join(session_dir, STATEMENT_DIR)
    makedirs(statement_dir, exist_ok=True)
    with open(path.join(statement_dir, description_file), 'w') as f1, \
            open(path.join(statement_dir, input_file), 'w') as f2, \
            open(path.join(statement_dir, output_file), 'w') as f3,\
            open(path.join(statement_dir, hint_file), 'w') as f4:
        f1.write(problem.description)
        f2.write(problem.input)
        f3.write(problem.output)
        f4.write(problem.hint)

    tests_dir = path.join(session_dir, TESTS_DIR)
    case_dict = config.setdefault('case', dict())
    point_list = problem.point_list
    for key in case_dict.keys():
        case_dict[key]["order"] = 0
        case_dict[key]["point"] = DEFAULT_POINT
        case_dict[key]["pretest"] = False
        case_dict[key]["sample"] = False
    makedirs(tests_dir, exist_ok=True)
    for case in problem.sample_list:
        if case not in case_dict.keys():
            case_dict[case] = dict(order=0, point=10, sample=True)
            now_input_path, now_output_path = get_test_file_path(session, case)
            copyfile(get_input_path(case), now_input_path)
            copyfile(get_output_path(case), now_output_path)
        case_dict[case]['sample'] = True
    for ind, case in enumerate(problem.case_list, start=1):
        if case not in case_dict.keys():
            case_dict[case] = dict()
            now_input_path, now_output_path = get_test_file_path(session, case)
            copyfile(get_input_path(case), now_input_path)
            copyfile(get_output_path(case), now_output_path)
        case_dict[case]["order"] = ind
        case_dict[case]["point"] = point_list[ind - 1]
        if case in problem.pretest_list:
            case_dict[case]["pretest"] = True
        if case in problem.sample_list:
            case_dict[case]["sample"] = True
    config['case'] = case_dict

    programs = config.setdefault('program', dict())
    # pull top-relevant programs first
    to_pull_programs = list(filter(lambda x: x, [problem.checker, problem.interactor, problem.validator]))
    config["checker"] = problem.checker  # This is fingerprint, to be converted to filename later
    config["interactor"] = problem.interactor
    config["validator"] = problem.validator
    config["interactive"] = bool(problem.interactor)
    config.setdefault('model', '')
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
    if any(s.last_synchronize > session.last_synchronize for s in problem.editsession_set.all()):
        raise Exception('Sorry, there has been a newer session, try to re-pull.')
    config = load_config(session)
    problem.alias = config['alias']
    problem.title = config['title']
    problem.time_limit = config['time_limit']
    problem.memory_limit = config['memory_limit']
    problem.source = config['source']
    for type in ['checker', 'validator', 'interactor']:
        file = config[type]
        if type == 'interactor' and not config['interactive']:
            file = ''
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
    cases, points = zip(*sorted(case_list, key=lambda x: case_order[x[0]]))
    pretest_list.sort(key=lambda x: case_order[x])
    sample_list.sort(key=lambda x: case_order[x])
    problem.cases = ','.join(cases)
    problem.points = ','.join(map(str, points))
    problem.pretests = ','.join(pretest_list)
    problem.sample = ','.join(sample_list)
    problem.save()

    for server in Server.objects.filter(enabled=True).all():
        upload_problem_to_judge_server(problem, server)
        server.last_synchronize_time = datetime.now()
        server.save(update_fields=['last_synchronize_time'])
    pull_session(session)


def sort_out_directory(directory):
    if not path.exists(directory):
        return []
    return sorted(list(map(lambda file: {'filename': path.basename(file),
                                         'modified_time': datetime.fromtimestamp(path.getmtime(file)).
                                                          strftime(settings.DATETIME_FORMAT_TEMPLATE),
                                         'size': path.getsize(file)},
                           listdir_with_prefix(directory))),
                  key=lambda d: d['modified_time'], reverse=True)


def load_statement_file_list(session):
    return sort_out_directory(path.join(get_session_dir(session), STATEMENT_DIR))


def create_statement_file(session, filename):
    filepath = _get_statement_file_path(session, filename)
    if path.exists(filepath):
        raise ValueError("File already exists")
    with open(filepath, 'w'):
        pass


def delete_statement_file(session, filename):
    filepath = _get_statement_file_path(session, filename)
    if not path.exists(filepath):
        raise ValueError("File does not exist")
    config = load_config(session)
    if filename in list(map(lambda x: config[x], STATEMENT_TYPE_LIST)):
        raise ValueError("File is still in use")
    remove(filepath)


def read_statement_file(session, filename):
    filepath = _get_statement_file_path(session, filename)
    with open(filepath) as fs:
        return fs.read()


def write_statement_file(session, filename, text):
    filepath = _get_statement_file_path(session, filename)
    with open(filepath, 'w') as fs:
        fs.write(text)


def update_statement(session, description, input, output, hint):
    config = load_config(session)
    description_file, input_file, output_file, hint_file = map(lambda x: config.get, STATEMENT_TYPE_LIST)
    write_statement_file(session, description_file, description)
    write_statement_file(session, input_file, input)
    write_statement_file(session, output_file, output)
    write_statement_file(session, hint_file, hint)


def statement_file_exists(session, filename):
    filepath = _get_statement_file_path(session, filename)
    return path.exists(filepath)


def load_regular_file_list(session):
    return sort_out_directory(path.join(settings.UPLOAD_DIR, str(session.problem_id)))


def load_volume(session):
    def get_size(start_path='.'):
        total_size = 0
        for dirpath, dirnames, filenames in walk(start_path):
            for f in filenames:
                fp = path.join(dirpath, f)
                total_size += path.getsize(fp)
        return total_size

    session_dir = get_session_dir(session)
    return get_size(session_dir) // 1024576, 256


def load_program_file_list(session):
    return sort_out_directory(path.join(get_session_dir(session), PROGRAM_DIR))


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
        if config['program'].get(filename):
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


def preview_case(session, fingerprint):
    inp, oup = get_test_file_path(session, fingerprint)
    with open(inp, 'r') as fs, open(oup, 'r') as gs:
        res = {'input': fs.read(USUAL_READ_SIZE), 'output': gs.read(USUAL_READ_SIZE)}
        if fs.read(1):
            res['input'] += '...'
        if gs.read(1):
            res['output'] += '...'
        return res


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


def readjust_case_point(session, fingerprint, point):
    if point <= 0 or point > 100:
        raise ValueError("Point not in range")
    update_case_config(session, fingerprint, point=point)


def reorder_case(session, orders):
    """
    :type orders: dict
    :param orders: {fingerprint -> order_number}
    """
    config = load_config(session)
    for fingerprint, d in config['case'].items():
        d.update(order=0)  # clear first
        if orders.get(fingerprint):
            d.update(order=orders[fingerprint])
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
def validate_case(session, validator, fingerprint=None):
    config = load_config(session)
    all_fingerprints = list(config['case'].keys())
    if fingerprint:
        input = _get_test_input(session, fingerprint)
        call_func = validate_input
        multiple = False
    else:
        input = list(map(lambda fp: _get_test_input(session, fp), all_fingerprints))
        call_func = validate_input_multiple
        multiple = True
    result = call_func(input, read_program_file(session, validator),
                       config['program'][validator]['lang'], config['time_limit'])
    if success_response(result):
        config = load_config(session)
        if multiple:
            for i, res in zip(all_fingerprints, result['result']):
                config['case'][i]['validated'] = -1 if res['verdict'] != 0 else 1
        else:
            config['case'][fingerprint]['validated'] = -1 if result['verdict'] != 0 else 1
        dump_config(session, config)
    return result


@run_async_with_report
def get_case_output(session, model, fingerprint=None):
    config = load_config(session)
    all_fingerprints = list(config['case'].keys())
    if fingerprint:
        input = _get_test_input(session, fingerprint)
        call_func = run_output
        multiple = False
    else:
        input = list(map(lambda fp: _get_test_input(session, fp), all_fingerprints))
        call_func = run_output_multiple
        multiple = True
    result = call_func(read_program_file(session, model), config['program'][model]['lang'],
                       config['time_limit'], input)
    if success_response(result):
        if multiple:
            for i, inp, res in zip(all_fingerprints, input, result['result']):
                save_case(session, inp, base64.b64decode(res['output']), raw_fingerprint=i, model=True)
        else:
            save_case(session, input, base64.b64decode(result['output']), raw_fingerprint=fingerprint, model=True)
    return result


@run_async_with_report
def check_case(session, submission, checker, fingerprint=None):
    config = load_config(session)
    all_fingerprints = list(config['case'].keys())
    if fingerprint:
        input, output = _get_test_input_and_output(session, fingerprint)
        call_func = check_output_with_result
        multiple = False
    else:
        inp_with_oup = list(map(lambda fp: _get_test_input_and_output(session, fp), all_fingerprints))
        input, output = zip(*inp_with_oup)
        call_func = check_output_with_result_multiple
        multiple = True
    kw = {}
    if config.get('interactive'):
        kw.update(interactor=_get_program_tuple(session, config['interactor'], config))
    result = call_func(_get_program_tuple(session, submission, config),
                       _get_program_tuple(session, checker, config),
                       config['time_limit'], config['memory_limit'],
                       input, output, **kw)
    if success_response(result):
        if multiple:
            for i, res in zip(all_fingerprints, result['result']):
                update_case_config(session, i, checked=1 if res['verdict'] == 0 else -1)
        else:
            update_case_config(session, fingerprint, checked=1 if result['verdict'] == 0 else -1)
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
        outputs = result['output']
        for output in outputs:
            save_case(session, base64.b64decode(output), b'')
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
    if config.get('interactive'):
        kw.update(interactor=_get_program_tuple(session, config['interactor'], config))
    result = stress_test(_get_program_tuple(session, model, config),
                         _get_program_tuple(session, submission, config),
                         _get_program_tuple(session, generator, config),
                         param_list, config['time_limit'], config['memory_limit'], time,
                         _get_program_tuple(session, config['checker'], config), kw)

    if success_response(result):
        outputs = result['output']
        for output in outputs:
            save_case(session, base64.b64decode(output), b'')
        result.update(message='[ Successfully created %d cases ]\n%s' % (len(outputs), result.get('message', '')))
    return result



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


def dump_config(session, config):
    config_file = path.join(settings.REPO_DIR, session.fingerprint, CONFIG_FILE_NAME)
    with open(config_file, 'w') as f:
        yaml.dump(config, f, default_flow_style=False)


def update_config(config, **kwargs):
    def pop_and_check(kw, conf, prop, varname, convert_func, check_func, ):
        _var = kw.pop(prop, None)
        if _var is not None:
            if convert_func:
                _var = convert_func(_var)
            if check_func and not check_func(_var):
                raise ValueError("Invalid %s" % varname)
            conf.update({prop: _var})

    new_config = copy.deepcopy(config)

    pop_and_check(kwargs, new_config, 'title', 'title', None, None)
    pop_and_check(kwargs, new_config, 'alias', 'alias', None, normal_regex_check)
    pop_and_check(kwargs, new_config, 'time_limit', 'time limit', int, lambda x: x >= 200 and x <= 30000)
    pop_and_check(kwargs, new_config, 'memory_limit', 'memory limit', int, lambda x: x >= 64 and x <= 4096)
    pop_and_check(kwargs, new_config, 'source', 'source', None, lambda x: len(x) <= 128)
    pop_and_check(kwargs, new_config, 'interactive', 'interactive', None, None)
    for i in STATEMENT_TYPE_LIST + USED_PROGRAM_IN_CONFIG_LIST:
        # Please check in advance
        pop_and_check(kwargs, new_config, i, i, None, None)

    return new_config

    # TODO: is there another param?


def get_config_update_time(session):
    config_file = path.join(settings.REPO_DIR, session.fingerprint, CONFIG_FILE_NAME)
    return datetime.fromtimestamp(path.getmtime(config_file)).strftime(settings.DATETIME_FORMAT_TEMPLATE)


def get_session_dir(session):
    return path.join(settings.REPO_DIR, session.fingerprint)


def _get_statement_file_path(session, filename):
    statement_dir = path.join(get_session_dir(session), STATEMENT_DIR)
    if not normal_regex_check(filename):
        raise ValueError("Invalid filename")
    return path.join(statement_dir, filename)


def _get_program_file_path(session, filename):
    program_dir = path.join(get_session_dir(session), PROGRAM_DIR)
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


def normal_regex_check(alias):
    return re.match(r"^[\.a-z0-9_-]{4,64}$", alias)


def valid_fingerprint_check(fingerprint):
    return re.match(r"^[a-z0-9]{16,128}$", fingerprint)


def listdir_with_prefix(directory):
    return list(map(lambda file: path.join(directory, file),
                    filter(lambda f2: not f2.startswith('.'),
                           listdir(directory))))
