import zipfile
from os import path, replace, remove, environ
from shutil import rmtree
from django.conf import settings
from problem.models import Problem, get_input_path, get_output_path
from polygon.case import well_form_text
from utils import random_string
from utils.file_preview import sort_data_list_from_directory
from utils.hash import case_hash
import re
import traceback


def strip_and_remove_slash(text):
    def remove_slash_at_the_beginning(text):
        if text.startswith('\\'):
            text = text[1:]
        return text

    text = text.strip()
    return '\n'.join(map(remove_slash_at_the_beginning, text.strip().split('\n')))


def is_hexdigest(value):
    d = '0123456789abcdef'
    return len(value) == 64 and all(v in d for v in value)


def run():
    try:
        for problem in Problem.objects.all():
            case_zipfile = path.join(settings.TESTDATA_DIR, '%d.zip' % problem.id)
            tmp_directory = '/tmp/' + random_string()

            if path.exists(case_zipfile):
                case_list = []
                with zipfile.ZipFile(case_zipfile) as myZip:
                    myZip.extractall(path=tmp_directory)
                for inf, ouf in sort_data_list_from_directory(tmp_directory):
                    with open(path.join(tmp_directory, inf), 'rb') as ins, open(path.join(tmp_directory, ouf), 'rb') as ous:
                        ha = case_hash(problem.id, ins.read(), ous.read())
                    input_path, output_path = get_input_path(ha), get_output_path(ha)
                    replace(path.join(tmp_directory, inf), input_path)
                    replace(path.join(tmp_directory, ouf), output_path)
                    case_list.append(ha)
                rmtree(tmp_directory)
                remove(case_zipfile)
                problem.cases = ','.join(case_list)
                problem.points = ','.join('10' for i in range(len(case_list)))
                problem.save(update_fields=['cases', 'points'])

            if not is_hexdigest(problem.sample[:64]):
                samples = [list(filter(lambda x: x, map(strip_and_remove_slash, re.split(r'(\r?\n)(?<!\\)-+(\1)', problem.sample))))]
                lst = list(filter(lambda x: x, map(strip_and_remove_slash, re.split(r'(\r?\n)(?<!\\)-+(\1)', problem.sample))))
                case_list = problem.case_list
                sample_list = []
                for i in range(0, len(lst), 2):
                    if i + 1 >= len(lst):
                        continue
                    I, O = well_form_text(lst[i]).encode(), well_form_text(lst[i + 1]).encode()
                    ha = case_hash(problem.id, I, O)
                    input_path, output_path = get_input_path(ha), get_output_path(ha)
                    with open(input_path, 'wb') as inf, open(output_path, 'wb') as ouf:
                        inf.write(I)
                        ouf.write(O)
                    case_list.append(ha)
                    sample_list.append(ha)
                problem.sample = ','.join(sample_list)
                problem.cases = ','.join(case_list)
                problem.points = ','.join('10' for i in range(len(case_list)))
                problem.save(update_fields=['cases', 'points', 'sample'])
    except:
        traceback.print_exc()