from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from account.models import User
from polygon.models import Case, Revision
from problem.models import Problem


class RevisionTest(TestCase):
    def setUp(self):
        self.user = User.objects.create(email="something@user.com", username="myusername", is_staff=True, polygon_enabled=True)
        self.user.set_password("password")
        self.user.save()

        self.client.login(username='myusername', password='password')
        self.assertContains(self.client.post(reverse('polygon:problem_create')), '')
        self.assertEqual(1, Problem.objects.all().count())
        self.problem = Problem.objects.all().first()

        self.client.post(reverse('polygon:revision_create', kwargs={'pk': self.problem.id}))
        self.assertEqual(1, self.problem.revisions.all().count())
        self.revision = self.problem.revisions.all().first()

        self.kwargs = {'pk': self.problem.id, 'rpk': self.revision.id}

    def test_fork_revision(self):
        self.client.post(reverse('polygon:revision_fork', kwargs=self.kwargs))
        self.assertGreater(self.problem.revisions.all().count(), 1)
        for revision in self.problem.revisions.all():
            if revision != self.revision:
                self.assertEqual(revision.parent_id, self.revision.id)

    def test_revision_update(self):
        response = self.client.post(reverse('polygon:revision_view', kwargs=self.kwargs), data={
            "time_limit": 1000, "memory_limit": 1024, "alias": "hello", "well_form_policy": False
        })
        self.revision.refresh_from_db()
        self.assertEqual(1000, self.revision.time_limit)
        self.assertEqual(1024, self.revision.memory_limit)
        self.assertEqual("hello", self.revision.alias)
        self.assertEqual(False, self.revision.well_form_policy)
