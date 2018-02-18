from django.core.files.uploadedfile import SimpleUploadedFile, UploadedFile
from django.test import TestCase
from django.urls import reverse
from os import path

from account.models import User
from polygon.models import Case, Revision, Asset, Statement
from problem.models import Problem

BASE_LOCATION = path.dirname(path.abspath(__file__))


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
        response = self.client.post(reverse('polygon:revision_update', kwargs=self.kwargs), data={
            "time_limit": 1000, "memory_limit": 1024, "well_form_policy": False
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

    def test_statement(self):
        response = self.client.post(reverse('polygon:revision_statement_create', kwargs=self.kwargs), data={
            "name": "default",
            "title": "my title",
            "description": "my description"
        })
        # print(response)
        self.assertEqual(self.revision.statements.count(), 1)
        response = self.client.post(reverse('polygon:revision_statement_create', kwargs=self.kwargs), data={
            "name": "another",
            "title": "another title",
            "description": "another description"
        })
        self.assertEqual(self.revision.statements.count(), 2)
        self.revision.refresh_from_db()
        self.assertEqual(self.revision.active_statement.name, "default")
        my_kwargs = {"spk": 1}
        my_kwargs.update(self.kwargs)
        self.client.post(reverse('polygon:revision_statement_update', kwargs=my_kwargs), data={
            "name": "default2",
            "title": "my title"
        })
        self.revision.active_statement.refresh_from_db()
        self.revision.refresh_from_db()
        self.assertEqual(Statement.objects.count(), 3)
        self.assertEqual(self.revision.statements.count(), 2)
        self.assertEqual(self.revision.active_statement.pk, 3)
        my_kwargs.update(spk=2)
        self.client.post(reverse('polygon:revision_statement_activate', kwargs=my_kwargs))
        self.revision.refresh_from_db()
        self.assertEqual(self.revision.active_statement.name, "another")

    def test_program(self):
        response = self.client.post(reverse('polygon:revision_program_create', kwargs=self.kwargs), data={
            "name": "default",
            "lang": "cpp",
            "tag": "checker",
            "code": "int main() { }"
        })
        self.assertEqual(self.revision.programs.count(), 1)
        response = self.client.post(reverse('polygon:revision_program_create', kwargs=self.kwargs), data={
            "name": "int",
            "lang": "cpp",
            "tag": "interactor",
            "code": "int main() { }"
        })
        self.assertEqual(self.revision.programs.count(), 2)
        program_kwargs = {"ppk": 1}
        program_kwargs.update(self.kwargs)
        response = self.client.post(reverse('polygon:revision_program_toggle', kwargs=program_kwargs))
        self.revision.refresh_from_db()
        self.assertEqual(self.revision.active_checker_id, 1)
        self.assertIsNone(self.revision.active_validator)
        self.assertIsNone(self.revision.active_interactor)
        response = self.client.post(reverse('polygon:revision_program_toggle', kwargs=program_kwargs))
        self.revision.refresh_from_db()
        self.assertIsNone(self.revision.active_checker)
        response = self.client.post(reverse('polygon:revision_program_toggle', kwargs=program_kwargs))
        response = self.client.post(reverse('polygon:revision_program_update', kwargs=program_kwargs), data={
            "name": "int",
            "lang": "cpp",
            "tag": "interactor",
            "code": "int main() { }"
        })
        self.revision.refresh_from_db()
        self.assertEqual(self.revision.active_interactor_id, 3)
        self.assertIsNone(self.revision.active_validator)
        self.assertIsNone(self.revision.active_checker)
        response = self.client.post(reverse('polygon:revision_program_update', kwargs=program_kwargs), data={
            "name": "int",
            "lang": "cpp",
            "tag": "solution_main",
            "code": "int main() { }"
        })
        self.revision.refresh_from_db()
        self.assertIsNone(self.revision.active_checker)
        self.assertIsNone(self.revision.active_validator)
        self.assertIsNone(self.revision.active_checker)

    def test_case(self):
        response = self.client.post(reverse('polygon:revision_case_create', kwargs=self.kwargs), data={
            "option": "text",
            "input_text": "this is input",
            "output_text": "this is output",
            "in_samples": False,
            "output_lock": False,
            "case_number": 0,
            "activated": True
        })
        self.assertEqual(self.revision.cases.count(), 1)
        my_case = self.revision.cases.first()
        self.assertNotEqual(my_case.fingerprint, "invalid")
        self.assertEqual(my_case.input_preview, "this is input")
        self.assertEqual(my_case.output_preview, "this is output")
        self.assertEqual(my_case.case_number, 1)

        response = self.client.post(reverse('polygon:revision_case_create', kwargs=self.kwargs), data={
            "option": "single",
            "input_file": SimpleUploadedFile("input", b"this is input 3"),
            "output_file": SimpleUploadedFile("output", b"this is output 3"),
            "case_number": 3,
            "activated": True
        })
        self.assertEqual(self.revision.cases.count(), 2)
        my_case = self.revision.cases.get(pk=2)
        self.assertNotEqual(my_case.fingerprint, "invalid")
        self.assertEqual(my_case.input_preview, "this is input 3")
        self.assertEqual(my_case.output_preview, "this is output 3")
        self.assertEqual(my_case.case_number, 3)

        zip_location = path.join(BASE_LOCATION, "asset", "d.zip")
        with open(zip_location, "rb") as f:
            response = self.client.post(reverse('polygon:revision_case_create', kwargs=self.kwargs), data={
                "option": "batch",
                "batch_file": UploadedFile(f),
                "case_number": 2,
                "activated": True
            })
        self.assertEqual(self.revision.cases.count(), 4)
        mmap = {1: 1, 2: 4, 3: 2, 4: 3, 5: 4}
        input_map = {1: "this", 2: "this", 3: "1 2", 4: "2 2", 5: "this"}
        for case in self.revision.cases.all():
            self.assertNotEqual(case.pk, 2)
            self.assertEqual(mmap[case.pk], case.case_number)
            self.assertIn(input_map[case.pk], case.input_preview)

        with open(zip_location, "rb") as f:
            response = self.client.post(reverse('polygon:revision_case_create', kwargs=self.kwargs), data={
                "option": "batch",
                "batch_file": UploadedFile(f),
                "case_number": 0,
                "activated": True
            })
        self.assertEqual(self.revision.cases.count(), 6)
        self.assertEqual(len(set(self.revision.cases.all().values_list("fingerprint", flat=True))), 4)

        # update case
        p_kwargs = {"cpk": 1}
        p_kwargs.update(self.kwargs)
        response = self.client.post(reverse('polygon:revision_case_update_file', kwargs=p_kwargs), data={
            "option": "text",
            "input_text": "new input",
            "output_text": "new output"
        })
        self.assertEqual(self.revision.cases.count(), 6)
        for case in self.revision.cases.all():
            self.assertNotEqual(case.pk, 1)
