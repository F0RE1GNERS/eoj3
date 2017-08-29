from django.contrib.contenttypes.models import ContentType
from django_comments_xtd.models import XtdComment
from blog.models import Comment, Blog
from problem.models import Problem
import traceback


def run():
    try:
        blog_content_type = ContentType.objects.get_for_model(Blog)
        problem_content_type = ContentType.objects.get_for_model(Problem)
        for c in Comment.objects.all():
            if c.author.is_active:
                print(c.author)
                if c.blog:
                    XtdComment.objects.create(user=c.author,
                                              submit_date=c.create_time,
                                              object_pk=c.blog.pk,
                                              comment=c.text,
                                              content_type=blog_content_type,
                                              site_id=1)
                elif c.problem:
                    XtdComment.objects.create(user=c.author,
                                              submit_date=c.create_time,
                                              object_pk=c.problem.pk,
                                              comment=c.text,
                                              content_type=problem_content_type,
                                              site_id=1)
                else:
                    assert 0
    except:
        traceback.print_exc()
