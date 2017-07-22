import re
import copy
from datetime import datetime
from os import path, makedirs, listdir, stat, remove, walk
from shutil import copyfile, rmtree

import yaml
from django.conf import settings

from account.models import User
from problem.models import Problem, SpecialProgram, get_input_path, get_output_path
from utils import random_string
from utils.language import LANG_EXT
from .models import EditSession

CONFIG_FILE_NAME = 'config.yml'
STATEMENT_DIR = 'statement'
TESTS_DIR = 'tests'
PROGRAM_DIR = 'program'
DEFAULT_POINT = 10


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
        open(path.join(statement_dir, output_file), 'w') as f3, \
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
    for ind, case in enumerate(problem.case_list, start=1):
        if case not in case_dict.keys():
            case_dict[case] = dict()
            copyfile(get_input_path(case), path.join(tests_dir, case + '.in'))
            copyfile(get_output_path(case), path.join(tests_dir, case + '.out'))
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

    for program in programs.values():
        if isinstance(program, dict) and program.get('used'):
            program.pop('used')

    dump_config(session, config)
    session.last_synchronize = datetime.now()
    session.save(update_fields=["last_synchronize"])


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


def _get_statement_file_path(session, filename):
    statement_dir = path.join(get_session_dir(session), STATEMENT_DIR)
    if not normal_regex_check(filename):
        raise ValueError("Invalid filename")
    return path.join(statement_dir, filename)


def _get_program_file_path(session, filename):
    statement_dir = path.join(get_session_dir(session), PROGRAM_DIR)
    if not normal_regex_check(filename):
        raise ValueError("Invalid filename")
    return path.join(statement_dir, filename)


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
    if filename in [config["input"], config["output"], config["description"], config["hint"]]:
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
        if _var:
            if convert_func:
                _var = convert_func(_var)
            if check_func and not check_func(_var):
                raise ValueError("Invalid %s" % varname)
            conf.update({prop: _var})

    new_config = copy.deepcopy(config)

    pop_and_check(kwargs, new_config, 'alias', 'alias', None, normal_regex_check)
    pop_and_check(kwargs, new_config, 'time_limit', 'time limit', int, lambda x: x >= 200 and x <= 30000)
    pop_and_check(kwargs, new_config, 'memory_limit', 'memory limit', int, lambda x: x >= 64 and x <= 4096)
    pop_and_check(kwargs, new_config, 'source', 'source', None, lambda x: len(x) <= 128)
    for i in ['input', 'output', 'description', 'hint', 'checker', 'validator', 'interactor']:
        # Please check in advance
        pop_and_check(kwargs, new_config, i, i, None, None)

    return new_config

    # TODO: is there another param?


def get_config_update_time(session):
    config_file = path.join(settings.REPO_DIR, session.fingerprint, CONFIG_FILE_NAME)
    return datetime.fromtimestamp(path.getmtime(config_file)).strftime(settings.DATETIME_FORMAT_TEMPLATE)


def get_session_dir(session):
    return path.join(settings.REPO_DIR, session.fingerprint)


def normal_regex_check(alias):
    return re.match(r"^[\.a-z0-9_-]{4,64}$", alias)


def listdir_with_prefix(directory):
    return list(map(lambda file: path.join(directory, file),
                    filter(lambda f2: not f2.startswith('.'),
                           listdir(directory))))
