from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from polygon.models import Case


class ModelsTest(TestCase):
    def setUp(self):
        self.case = Case.objects.create()
        self.case.input_file = SimpleUploadedFile('hello', b'here is some content')
        self.case.output_file = SimpleUploadedFile('hello again', b'another content')
        self.case.save()

    def test_working_ok(self):
        self.assertIn("repo/cases", self.case.input_file.path)
        self.assertEqual(b"here is some content", self.case.input_file.read())

    def test_duplicate(self):
        pass
        # case2 = self.case
        # case2.pk = None
        # case2.save()
        # self.assertNotEqual(self.case.input_file.path, case2.input_file.path)
