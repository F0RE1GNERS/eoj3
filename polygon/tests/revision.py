from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from account.models import User
from polygon.models import Case, Revision, Asset
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

    def test_asset(self):
        my_file = SimpleUploadedFile("this_file.mp4", b"file_content")
        response = self.client.post(reverse('polygon:revision_asset_create', kwargs=self.kwargs), data={
            "file": my_file, "name": "my_name"
        })
        self.assertTrue(self.revision.assets.count())
        self.assertEqual(self.revision.assets.all().first().name, "my_name")
        asset_kwargs = {"apk": self.revision.assets.all().first().id}
        asset_kwargs.update(self.kwargs)

        # test update
        another_file = SimpleUploadedFile("another_file.mp4", b"file_content_again")
        response = self.client.post(reverse('polygon:revision_asset_update', kwargs=asset_kwargs), data={
            "file": another_file, "name": "my_name_2"
        })
        self.assertEqual(self.revision.assets.count(), 1)
        self.assertEqual(Asset.objects.count(), 2)
        asset_list = Asset.objects.all()
        self.assertNotEqual(asset_list[0].name, asset_list[1].name)
        self.assertNotEqual(asset_list[0].file.path, asset_list[1].file.path)
        self.assertNotEqual(asset_list[0].file.read(), asset_list[1].file.read())
        self.assertEqual(self.revision.assets.all().first().name, "my_name_2")

        # test rename
        response = self.client.post(reverse('polygon:revision_asset_rename', kwargs=asset_kwargs), data={
            "name": "my_name_3"
        })
        # self.assertContains(response, "No assets")
        asset_kwargs.update(apk=self.revision.assets.all().first().pk)
        response = self.client.post(reverse('polygon:revision_asset_rename', kwargs=asset_kwargs), data={
            "name": "my_name_3"
        })
        self.assertEqual(self.revision.assets.count(), 1)
        self.assertEqual(Asset.objects.count(), 3)
        old_revision = Asset.objects.get(name='my_name_2')
        new_revision = Asset.objects.get(name='my_name_3')
        self.assertEqual(old_revision.file.path, new_revision.file.path)
        self.assertEqual(len(set(map(lambda x: x.file.path, Asset.objects.all()))), 2)
        self.assertEqual(len(set(map(lambda x: x.create_time, Asset.objects.all()))), 1)
        self.assertEqual(new_revision, self.revision.assets.all().first())

        asset_kwargs.update(apk=new_revision.pk)
        response = self.client.post(reverse('polygon:revision_asset_rename', kwargs=asset_kwargs), data={
            "name": "##########"
        })
        self.assertEqual(new_revision, self.revision.assets.all().first())
        self.assertEqual("my_name_3", self.revision.assets.all().first().name)
        self.assertEqual(Asset.objects.get(pk=3).parent_id, 2)
        self.assertEqual(Asset.objects.get(pk=2).parent_id, 1)
        self.assertEqual(Asset.objects.get(pk=1).parent_id, 0)
