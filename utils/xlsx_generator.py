import xlsxwriter
from django.conf import settings
from django.template.loader import get_template
from contest.models import Contest
from bs4 import BeautifulSoup
import datetime
import os


def generate(cid):
    def _convert(value):
        res = [text for text in value.stripped_strings]
        if len(res) == 0:
            return ' '
        if len(res) == 1:
            res2 = str(res[0])
        else:
            res2 = str(res[0]) + ' (%s)' % (', '.join(res[1:]))
        res2 = res2.strip()
        if res2 == '=': # not a formula
            res2 = 'Score'
        return res2

    file_name = 'ContestStandings-%s-%s.xlsx' % (str(cid), datetime.datetime.now().strftime('%Y-%m-%d-%H-%M-%S'))
    file_path = os.path.join(settings.GENERATE_DIR, file_name)
    contest = Contest.objects.get(pk=cid)
    rank_list = contest.contestparticipant_set.all()
    template = get_template('contest/standing_table.jinja2')
    html = template.render(dict(contest=contest, rank_list=rank_list))
    soup = BeautifulSoup(html, "html.parser")
    data = []
    table = soup.find('table')

    rows = table.find_all('tr')
    for row in rows:
        cols = row.find_all(['td', 'th'])
        cols = [_convert(ele) for ele in cols]
        data.append([ele for ele in cols if ele])

    workbook = xlsxwriter.Workbook(file_path)
    worksheet = workbook.add_worksheet()
    for (i, row) in enumerate(data):
        for (j, col) in enumerate(row):
            worksheet.write(i, j, col)
    workbook.close()

    return file_name


def generate_participant(cid):
    file_name = 'ContestParticipants-%s-%s.xlsx' % (str(cid), datetime.datetime.now().strftime('%Y-%m-%d-%H-%M-%S'))
    file_path = os.path.join(settings.GENERATE_DIR, file_name)
    contest = Contest.objects.get(pk=cid)
    participant_list = contest.contestparticipant_set.select_related('user').all()

    workbook = xlsxwriter.Workbook(file_path)
    worksheet = workbook.add_worksheet()
    for (i, row) in enumerate(participant_list):
        worksheet.write(i, 0, row.comment)
        worksheet.write(i, 1, row.user.username)
        worksheet.write(i, 2, row.hidden_comment)
    workbook.close()

    return file_name


def generate_invitation(cid):
    file_name = 'ContestInvitation-%s-%s.xlsx' % (str(cid), datetime.datetime.now().strftime('%Y-%m-%d-%H-%M-%S'))
    file_path = os.path.join(settings.GENERATE_DIR, file_name)
    contest = Contest.objects.get(pk=cid)
    participant_list = contest.contestinvitation_set.all()

    workbook = xlsxwriter.Workbook(file_path)
    worksheet = workbook.add_worksheet()
    for (i, row) in enumerate(participant_list):
        worksheet.write(i, 0, row.comment)
        worksheet.write(i, 1, row.code)
    workbook.close()

    return file_name
