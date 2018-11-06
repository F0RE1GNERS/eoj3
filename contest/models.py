import json

import shortuuid
from django.core.validators import EmailValidator
from django.db import models
from django.db.models import Count
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _

from account.models import User, School
from problem.models import Problem
from utils.language import LANG_CHOICE


def get_invitation_code():
    return shortuuid.ShortUUID().random(12)


def get_language_all_list():
    return ','.join(sorted(dict(LANG_CHOICE).keys()))


class ContestManager(models.Manager):

    def get_status_list(self, show_all=False, filter_user=None, sorting_by_id=False, contest_type=None):
        q = models.Q()
        if not show_all:
            q &= models.Q(access_level__gt=0)
            if filter_user:
                q |= models.Q(managers=filter_user)
        if contest_type is not None:
            q &= models.Q(contest_type=contest_type)
        contest_list = self.get_queryset().prefetch_related('authors', 'managers').\
            annotate(Count('participants', distinct=True)).filter(q)

        if sorting_by_id:
            contest_list = contest_list.order_by("-pk").distinct()
        else:
            contest_list = contest_list.order_by("-start_time").distinct()
            for contest in contest_list:
                contest.length = contest.end_time - contest.start_time
        return contest_list


class Contest(models.Model):

    SCORING_METHOD_CHOICE = (
        ('acm', "ACM 赛制"),
        ('oi', "OI 赛制"),
        ('cf', "School of Data Analysis (SDA) 赛制 (Codeforces...)"),
        ('tcmtime', "TCM/TIME 赛制 (GCJ...)"),
    )

    TEST_DURING_CONTEST_CHOICE = (
        ('all', "所有测试点"),
        ('pretest', "只测试 Pretests"),
        ('sample', "只测试样例"),
        ('none', "不作测试")
    )

    CODE_SHARE_CHOICE = (
        (0, "不允许"),
        (1, "代码在赛后对 AC 用户公开（默认）"),
        (2, "代码在赛后完全公开"),
        (3, "代码在比赛过程中对 AC 用户公开"),
    )

    CASE_PUBLIC_CHOICE = (
        (0, '不允许'),
        (1, '评测报告有偿公开'),
        (2, '评测报告总是开放'),
    )

    ACCESS_LEVEL_OPTIONS = (
        (0, '仅比赛管理员可见'),
        (10, '仅受邀用户可见，赛后题目不公开'),
        (15, '仅受邀用户可见，赛后允许虚拟参赛'),
        (20, '仅受邀用户可见，赛后题目直接公开'),
        (30, '公开，需要比赛前注册'),
        (40, '公开')
    )

    COMMON_STATUS_ACCESS_LEVEL_OPTIONS = (
        (-10, '不可见'),
        (0, '默认'),
        (10, '总是可见')
    )

    title = models.CharField("标题", max_length=192)
    description = models.TextField("描述", blank=True)
    allowed_lang = models.CharField("允许语言", max_length=192, default=get_language_all_list())

    contest_type = models.IntegerField(default=0, choices=(
        (0, '常规比赛'),
        (1, '作业'),
    ))
    start_time = models.DateTimeField("开始时间", blank=True, null=True, default=timezone.now)
    end_time = models.DateTimeField("结束时间", blank=True, null=True, default=timezone.now)
    create_time = models.DateTimeField("创建时间", auto_now_add=True)
    standings_update_time = models.DateTimeField("榜单更新时间", blank=True, null=True)

    freeze = models.BooleanField("是否封榜", default=False)
    freeze_time = models.DateTimeField("封榜时间", blank=True, null=True)
    scoring_method = models.CharField("计分规则", default='acm', max_length=10, choices=SCORING_METHOD_CHOICE)
    run_tests_during_contest = models.CharField("比赛过程中对代码进行评测", max_length=10, choices=TEST_DURING_CONTEST_CHOICE, default=TEST_DURING_CONTEST_CHOICE[0][0])
    allow_code_share = models.IntegerField("允许代码共享", default=1, choices=CODE_SHARE_CHOICE)  # Can view others' codes after AC

    last_counts = models.BooleanField("认为最后一次提交有效（默认使用成绩最好的）", default=False)  # Treat last submission as valid submission
    penalty_counts = models.PositiveIntegerField('错误提交罚时（秒）', default=1200)
    standings_without_problem = models.BooleanField('排行榜上不显示具体题目的通过情况',
                                                    default=False)  # Have a standing without specific problems
    case_public = models.PositiveIntegerField(choices=CASE_PUBLIC_CHOICE, default=0)

    system_tested = models.BooleanField("系统测试准备就绪", default=False)  # Passing system test or not, shall be available for run_tests_during_contest none, sample and pretest

    problems = models.ManyToManyField(Problem, through='ContestProblem')
    participants = models.ManyToManyField(User, through='ContestParticipant', related_name='contests')

    access_level = models.PositiveIntegerField("访问控制", default=0, choices=ACCESS_LEVEL_OPTIONS)
    common_status_access_level = models.IntegerField("所有提交和榜单的访问控制", default=0, choices=COMMON_STATUS_ACCESS_LEVEL_OPTIONS)
    ip_sensitive = models.BooleanField("首次登录绑定 IP", default=False)
    analysis_blog_id = models.IntegerField("题解博客 ID", default=0)   # related to a blog id
    pdf_statement = models.FileField('PDF 题面', upload_to='contest_statements/%Y%m%d/', null=True, blank=True)

    objects = ContestManager()
    managers = models.ManyToManyField(User, related_name='managing_contests')
    authors = models.ManyToManyField(User, related_name='written_contests')
    volunteers = models.ManyToManyField(User, related_name='volunteering_contests')

    class Meta:
        ordering = ['-pk']

    @property
    def status(self):
        now = timezone.now()
        if self.start_time is not None and now < self.start_time:
            return -1
        if self.end_time is not None and now > self.end_time:
            return 1
        return 0

    @property
    def is_frozen(self):
        if self.freeze and self.freeze_time <= timezone.now() <= self.end_time:
            return True
        return False

    @property
    def pending_system_tests(self):
        return self.status > 0 and self.run_tests_during_contest != 'all' and not self.system_tested

    @property
    def supported_language_list(self):
        return list(filter(lambda x: x, map(lambda x: x.strip(), self.allowed_lang.split(','))))

    @property
    def verbose_supported_language_list(self):
        def rreplace(s, old, new, count):
            return (s[::-1].replace(old[::-1], new[::-1], count))[::-1]

        lang_choices = dict(LANG_CHOICE)
        return rreplace(', '.join(list(map(lambda x: lang_choices[x], self.supported_language_list))), ', ', ' and ', 1)

    @property
    def contest_problem_list(self):
        if not hasattr(self, '_contest_problem_list'):
            self._contest_problem_list = list(self.contestproblem_set.select_related('problem').
                                              defer('problem__description', 'problem__input', 'problem__output',
                                                    'problem__hint', 'problem__cases').all())
        return self._contest_problem_list

    def get_contest_problem(self, problem_id):
        get_result = list(filter(lambda p: p.problem_id == problem_id, self.contest_problem_list))
        if len(get_result) > 0:
            return get_result[0]
        else:
            return None

    def add_contest_problem_to_submissions(self, submissions):
        find_contest_problem = {k.problem_id: k for k in self.contest_problem_list}
        for submission in submissions:
            submission.contest_problem = find_contest_problem.get(submission.problem_id)

    @property
    def participants_ids(self):
        if not hasattr(self, '_contest_user_ids'):
            self._contest_user_ids = list(self.contestparticipant_set.order_by().values_list("user_id", flat=True))
        return self._contest_user_ids

    def __str__(self):
        return self.title


class ContestProblem(models.Model):
    problem = models.ForeignKey(Problem, on_delete=models.CASCADE)
    contest = models.ForeignKey(Contest, on_delete=models.CASCADE)
    identifier = models.CharField(max_length=12)
    weight = models.IntegerField(default=100)

    class Meta:
        unique_together = ('problem', 'contest')
        ordering = ['identifier']

    def __str__(self):
        return self.identifier + '. ' + self.problem.title


class ContestClarification(models.Model):

    contest = models.ForeignKey(Contest, on_delete=models.CASCADE)
    text = models.TextField(blank=True)
    time = models.DateTimeField(auto_now=True)
    important = models.BooleanField(default=False)
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    answer = models.TextField(blank=True)

    class Meta:
        ordering = ["-time"]

    def __str__(self):
        return self.text


class ContestParticipant(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    star = models.BooleanField(default=False)
    comment = models.TextField(blank=True)
    hidden_comment = models.TextField(blank=True)
    contest = models.ForeignKey(Contest, on_delete=models.CASCADE)
    score = models.IntegerField(default=0)
    penalty = models.BigIntegerField(default=0)
    detail_raw = models.TextField(blank=True)
    is_disabled = models.BooleanField(default=False)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    join_time = models.DateTimeField(blank=True, null=True) # default: join when contest begins
    is_confirmed = models.BooleanField(default=False)

    @property
    def detail(self):
        try:
            if hasattr(self, "_detail"):
                return self._detail
            if not self.detail_raw:
                return {}
            self._detail = {int(k): v for k, v in json.loads(self.detail_raw).items()}
            return self._detail
        except:
            return {}

    @detail.setter
    def detail(self, d):
        self.detail_raw = json.dumps(d)

    class Meta:
        unique_together = ["user", "contest"]
        ordering = ("-is_confirmed", "-score", "penalty", "star")


class ContestInvitation(models.Model):

    contest = models.ForeignKey(Contest, on_delete=models.CASCADE)
    star = models.BooleanField(default=False)
    code = models.CharField(max_length=24)
    comment = models.TextField(blank=True)

    class Meta:
        unique_together = ('contest', 'code')
        ordering = ['-pk']


class ContestUserRating(models.Model):
    rating = models.IntegerField(default=1500)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    contest = models.ForeignKey(Contest, on_delete=models.CASCADE)
    solved = models.IntegerField()
    rank = models.IntegerField()
    modified = models.DateTimeField()

    class Meta:
        unique_together = ('contest', 'user')
        ordering = ["-modified"]

    def __str__(self):
        return 'ContestUserRating: {user: %d, rating: %d}' % (self.user_id, self.rating)


class Activity(models.Model):
    title = models.CharField("标题", unique=True, max_length=192)
    description = models.TextField("内容", blank=True)
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    create_time = models.DateTimeField(auto_now_add=True)
    update_time = models.DateTimeField(auto_now_add=True)
    register_start_time = models.DateTimeField("开始注册时间", blank=True)
    register_end_time = models.DateTimeField("结束注册时间", blank=True)
    participants = models.ManyToManyField(User, through='ActivityParticipant', related_name="activities")


class ActivityParticipant(models.Model):
    MAJOR_CHOICES = (
        ('art', '艺术'),
        ('accounting', '会计'),
        ('business', '商业'),
        ('business_admin', '工商管理'),
        ('chemistry', '化学'),
        ('communication', '通信'),
        ('ce', '计算机工程'),
        ('cs', '计算机科学'),
        ('economics', '经济'),
        ('education', '教育'),
        ('ee', '电子工程'),
        ('finance', '金融'),
        ('geology', '地理'),
        ('interaction', '人机交互'),
        ('it', '信息技术'),
        ('life', '生命科学'),
        ('mechanics', '机械'),
        ('linguistics', '语言学'),
        ('literature', '文学'),
        ('math', '数学'),
        ('se', '软件工程'),
        ('philosophy', '哲学'),
        ('physics', '物理'),
        ('politics', '政治学'),
        ('psycho', '心理学'),
        ('social', '社会学'),
        ('translation', '翻译'),
        ('others', '其他')
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    activity = models.ForeignKey(Activity, on_delete=models.CASCADE)
    real_name = models.CharField("真实姓名", max_length=30)
    student_id = models.CharField("学号", max_length=30)
    school = models.ForeignKey(School, verbose_name="学校", on_delete=models.CASCADE)
    email = models.CharField("电子邮箱", max_length=192, validators=[EmailValidator()])
    phone = models.CharField("电话", max_length=30, blank=True)
    major = models.CharField("专业", max_length=30, choices=MAJOR_CHOICES, blank=True)
    gender = models.CharField("性别", max_length=5, choices=(
        ('m', '男'),
        ('f', '女'),
        ('d', '拒绝回答')
    ), blank=True)
    graduate_year = models.IntegerField("毕业年份", blank=True, null=True)
    is_deleted = models.BooleanField("已删除", default=False)
    is_confirmed = models.BooleanField("已确认", default=False)

    class Meta:
        unique_together = ('user', 'activity')
