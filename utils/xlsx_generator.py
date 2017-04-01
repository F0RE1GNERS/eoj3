import xlsxwriter
from django.template.loader import get_template
from contest.models import Contest
import pandas


def generate(cid):
    def _convert(value):
        if value == '=':
            return ' ='  # I am not a formula.
        if value != value:
            return ''  # I am nan.
        return value
    contest = Contest.objects.get(pk=cid)
    rank_list = contest.contestparticipant_set.all()
    template = get_template('contest/standing_table.jinja2')
    html = template.render(dict(contest=contest, rank_list=rank_list))
    data = pandas.read_html(html)[0]
    workbook = xlsxwriter.Workbook('test.xlsx')
    worksheet = workbook.add_worksheet()
    for i, row in enumerate(data.itertuples()):
        for j, v in enumerate(row):
            print(i, j, v, type(v))
            worksheet.write(i, j, _convert(v))
    workbook.close()
