from django.db import transaction

from .models import Contest
from account.models import User
from submission.models import SubmissionStatus


def recalculate_for_participant(contest, submissions, problems):
    """
    :param contest: contest
    :param submissions: submissions
    :param problems: contest problems
    :return: (calculated score, penalty, cache)

    Penalty is the same for all rules: Every failed submission till the accepted one
    will add 1200 to it. And the accepted one will add the time (seconds) to it

    Score is different for rules:
    1. ACM Rule: solved problems
    2. OI Rule: The sum of passed percentage for every problem

    Cache is different for rules:
    1. ACM Rule: solved, penalty, <td>
        <span class="font-weight-bold text-success">+</span>
        or
        <span class="text-danger">-1</span>
        <br><span class="text-small">i:s(if accepted)</span></td>
        Note that CE is ignored on the board.
    2. OI Rule: score, penalty, <td>
        <span class="font-weight-bold text-success">100</span>
        or
        <span class="text-warning">30</span>
        or
        <span class="text-danger">0</span>
        <br><span class="text-small">i:s(if accepted)</span></td>
    """

    def get_penalty(start_time, submit_time):
        """
        :param start_time: time in DateTimeField
        :param submit_time: time in DateTimeField
        :return: penalty in seconds
        """
        return (submit_time - start_time).seconds

    def get_time_display(time):
        """
        :param time: time in seconds
        :return: mm:ss
        """
        time_in_minutes = time // 60
        return "%.2d:%.2d" % (time_in_minutes // 60, time_in_minutes % 60)

    # Get the cache: problem => contest_problem identifier
    from collections import Counter, defaultdict
    wrong = Counter()
    accept = set()
    max_score = defaultdict(int)
    accept_time = dict()
    penalty = 0

    identify_problem = dict()
    for problem in problems:
        identify_problem[problem.problem.pk] = problem.identifier
    subs = [(identify_problem[submission.problem.pk], submission.status, submission.status_percent,
             submission.create_time) for submission in submissions]

    # From beginning to the end
    for sub in reversed(subs):
        problem, status, score, create_time = sub
        print(problem, status, score, create_time)
        max_score[problem] = max(max_score[problem], score)
        if problem not in accept:
            if status == SubmissionStatus.ACCEPTED:
                accept.add(problem)
                accept_time[problem] = get_penalty(contest.start_time, create_time)
                penalty += accept_time[problem] + wrong[problem] * 1200
            elif SubmissionStatus.is_penalty(status):
                wrong[problem] += 1

    score = 0
    cache = ''

    # HTML Caching and global score
    html_danger = '<span class="text-danger">{text}</span>'
    html_success = '<span class="font-weight-bold text-success">{text}</span>'
    html_warning = '<span class="text-warning">{text}</span>'
    html_small = '<span class="text-small">{text}</span>'
    html_column = '<td>{column}</td>'

    # ACM Rule
    if contest.rule == 'acm':
        score = len(accept)
        for problem in sorted(identify_problem.values()):
            if problem in accept:
                success_cache = '+' + (str(wrong[problem]) if wrong[problem] > 0 else '')
                sub_cache = html_success.format(text=success_cache)
                sub_cache += '<br>' + html_small.format(text=get_time_display(accept_time[problem]))
            elif wrong[problem] > 0:
                danger_cache = '-' + (str(wrong[problem]))
                sub_cache = html_danger.format(text=danger_cache)
            else:
                sub_cache = ''
            cache += html_column.format(column=sub_cache)
    elif contest.rule == 'oi':
        score = sum(max_score.values())
        for problem in sorted(identify_problem.values()):
            local_score = max_score[problem]
            if local_score == 100:
                sub_cache = html_success.format(text=local_score)
                sub_cache += '<br>' + html_small.format(text=get_time_display(accept_time[problem]))
            elif local_score > 0:
                sub_cache = html_warning.format(text=local_score)
            elif wrong[problem] > 0 and local_score == 0:
                sub_cache = html_danger.format(text=local_score)
            else:
                sub_cache = ''
            cache += html_column.format(column=sub_cache)
    cache = html_column.format(column=score) + html_column.format(column=penalty) + cache

    print(score, penalty, cache)
    return score, penalty, cache


def update_problem_and_participant(contest_id, problem_id, user_id, accept_increment=0):
    """
    This function is used when judge result changed

    The three things we are going to do:
    1. update AC / Submit for ContestProblem
    2. update User (Participant) score
    3. update standings
    :param contest_id: the contest that is going to be affected
    :param problem_id: the problem that is going to be affected
    :param user_id: the user that is going to be affected
    :param accept_increment: does the submission increase AC or decrease?
    """
    with transaction.atomic():
        contest = Contest.objects.get(pk=contest_id)
        if accept_increment != 0:
            problem = contest.contestproblem_set.select_for_update().get(problem__pk=problem_id)
            problem.add_accept(accept_increment)
            problem.save()

        participant, _ = contest.contestparticipants_set.select_for_update().\
            get_or_create(user__pk=user_id, defaults={'user': User.objects.get(pk=user_id), 'contest': contest})
        _update_participant(contest, participant)


def _update_participant(contest, participant):
    submissions = contest.submission_set.filter(author=participant.user).all()
    problems = contest.contestproblem_set.all()
    participant.score, participant.penalty, participant.html_cache = \
        recalculate_for_participant(contest, submissions, problems)
    participant.save()


def _update_header(contest):

    def _get_standings_header(rule, contest_problems):
        template = '<th class="col-width-{width}">{info}</th>'

        if rule == 'oi':
            res = template.format(width=3, info='=')
        else:
            res = template.format(width=2, info='=')
        res += template.format(width=5, info='Penalty')
        for contest_problem in contest_problems:
            res += template.format(width=4, info=contest_problem.identifier)
        return res

    contest.contest_header = _get_standings_header(contest.rule, contest.contestproblem_set.all())
    contest.save()


def update_contest(contest):
    with transaction.atomic():
        _update_header(contest)
        participants = contest.contestparticipants_set.select_for_update().all()
        for participant in participants:
            _update_participant(contest, participant)
