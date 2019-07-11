class SubmissionStatus(object):

    SUBMITTED = -4
    WAITING = -3
    JUDGING = -2
    WRONG_ANSWER = -1
    ACCEPTED = 0
    TIME_LIMIT_EXCEEDED = 1
    IDLENESS_LIMIT_EXCEEDED = 2
    MEMORY_LIMIT_EXCEEDED = 3
    RUNTIME_ERROR = 4
    SYSTEM_ERROR = 5
    COMPILE_ERROR = 6
    SCORED = 7
    REJECTED = 10
    JUDGE_ERROR = 11
    PRETEST_PASSED = 12

    @staticmethod
    def is_judged(status):
        return status >= SubmissionStatus.WRONG_ANSWER

    @staticmethod
    def is_penalty(status):
        return SubmissionStatus.is_judged(status) and status != SubmissionStatus.COMPILE_ERROR

    @staticmethod
    def is_accepted(status):
        return status == SubmissionStatus.ACCEPTED or status == SubmissionStatus.PRETEST_PASSED

    @staticmethod
    def is_scored(status):
        return status == SubmissionStatus.SCORED


STATUS_CHOICE = (
    (-4, 'Submitted'),
    (-3, 'In queue'),
    (-2, 'Running'),
    (-1, 'Wrong answer'),
    (0, 'Accepted'),
    (1, 'Time limit exceeded'),
    (2, 'Idleness limit exceeded'),
    (3, 'Memory limit exceeded'),
    (4, 'Runtime error'),
    (5, 'Denial of judgement'),
    (6, 'Compilation error'),
    (7, 'Partial score'),
    (10, 'Rejected'),
    (11, 'Checker error'),
    (12, 'Pretest passed'),
)