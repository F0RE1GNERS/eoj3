import zipfile
from contest.models import Contest
from os import path, replace, remove, environ
from shutil import rmtree
from django.conf import settings
from problem.models import Problem, get_input_path, get_output_path
from submission.models import Submission, SubmissionStatus
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
                rmtree(tmp_directory, ignore_errors=True)
                remove(case_zipfile)
                problem.cases = ','.join(case_list)
                problem.points = ','.join('10' for i in range(len(case_list)))
                problem.save(update_fields=['cases', 'points'])

            if not is_hexdigest(problem.sample[:64]):
                lst = list(filter(lambda x: x, map(strip_and_remove_slash, re.split(r'(\r?\n)(?<!\\)-+(\1)', problem.sample))))
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
                    sample_list.append(ha)
                problem.sample = ','.join(sample_list)
                problem.save(update_fields=['cases', 'points', 'sample'])

        for contest in Contest.objects.all():
            contest.allowed_lang = ','.join(contest.allowed_lang.split(', '))
            contest.save(update_fields=['allowed_lang'])

        for submission in Submission.objects.all():
            submission.status_time /= 1000
            submission.status_private = submission.status
            if submission.status == SubmissionStatus.COMPILE_ERROR:
                submission.status_message = submission.status_detail
            A = []
            for detail in submission.status_detail_list:
                if 'time' in detail:
                    detail['time'] /= 1000
                A.append(detail)
            submission.status_detail_list = A
            submission.save(update_fields=['status_detail', 'status_time', 'status_message', 'status_private'])

    except:
        traceback.print_exc()