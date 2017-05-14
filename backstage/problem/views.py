import json

from django.shortcuts import render, HttpResponseRedirect, HttpResponse, reverse
from django.contrib.auth.decorators import login_required
from django.views.generic.list import ListView
from django.db import transaction
from django.contrib import messages
from django.views.generic import View
from django.views.static import serve

from .forms import ProblemEditForm
from problem.models import Problem
from submission.models import Submission
from eoj3.settings import TESTDATA_DIR, UPLOAD_DIR
from utils.file_preview import sort_data_from_zipfile, get_file_list
from dispatcher.tasks import ProblemRejudgeThread

from ..base_views import BaseCreateView, BaseUpdateView, BaseBackstageMixin


class TestData(BaseBackstageMixin, View):
    template_name = 'backstage/problem/problem_testdata.jinja2'

    def post(self, request, pk):
        import os
        os.makedirs(TESTDATA_DIR, exist_ok=True)
        file_path = os.path.join(TESTDATA_DIR, str(pk) + '.zip')

        if request.FILES['data'].size > 128 * 1048576:
            messages.error(request, 'File is too large.')
        else:
            # Chunk is not used for the convenience of hash
            data = request.FILES['data'].read()
            import hashlib
            with open(file_path, 'wb') as destination:
                destination.write(data)
            with transaction.atomic():
                problem = Problem.objects.select_for_update().get(pk=pk)
                problem.testdata_hash = hashlib.md5(data).hexdigest()
                problem.testdata_size = len(sort_data_from_zipfile(file_path))
                problem.save()
            messages.success(request, 'Testdata has been successfully updated.')
        return HttpResponseRedirect(request.path)

    def get(self, request, pk):
        import os
        file_path = os.path.join(TESTDATA_DIR, str(pk) + '.zip')
        problem = Problem.objects.get(pk=pk)
        data = {'data_set': sort_data_from_zipfile(file_path),
                'hash': problem.testdata_hash,
                'pid': str(pk)}
        return render(request, self.template_name, data)


class FileManager(BaseBackstageMixin, View):
    template_name = 'backstage/problem/problem_file.jinja2'

    def post(self, request, pk):
        import os
        file_dir = os.path.join(UPLOAD_DIR, str(pk))
        os.makedirs(file_dir, exist_ok=True)

        if request.FILES['file'].size > 128 * 1048576:
            messages.error(request, 'File is too large.')
        else:
            # Chunk is not used for the convenience of hash
            data = request.FILES['file'].read()
            # Get file name
            import hashlib
            original_name, ext_name = os.path.splitext(request.FILES['file'].name)
            original_name = original_name.replace(' ', '.') # for possible space problems
            hash = hashlib.md5(data).hexdigest()
            file_name = original_name + '.' + hash + ext_name
            file_path = os.path.join(file_dir, file_name)
            with open(file_path, 'wb') as destination:
                destination.write(data)
            messages.success(request, 'The file has been successfully updated.')
        return HttpResponseRedirect(request.path)

    def get(self, request, pk):
        import os
        file_path = os.path.join(UPLOAD_DIR, str(pk))
        data = {'file_set': get_file_list(file_path, str(pk)),
                'pid': pk}
        return render(request, self.template_name, data)


class FileDelete(BaseBackstageMixin, View):
    def get(self, request, pk, path):
        import os
        file_path = os.path.join(UPLOAD_DIR, str(pk), path)
        try:
            os.remove(file_path) # unsafe: possibly outside file removing
            messages.success(request, 'The file has been successfully deleted.')
        except OSError as e:
            print(repr(e))
        return HttpResponseRedirect(reverse('backstage:problem_file', kwargs={'pk': pk}))


class SPJCompiler(BaseBackstageMixin, View):
    template_name = 'backstage/problem/compiler.jinja2'

    def post(self, request):
        import os, shutil, json, zipfile, subprocess
        result = {'result': 'failed', 'message': ''}
        try:
            TMP_COMPILER_DIR = '/tmp/spj'
            source_path = os.path.join(TMP_COMPILER_DIR, 'upload.zip')
            COMPILE_DIRECTIVE = '/usr/bin/g++ -DONLINE_JUDGE -O2 -w -fmax-errors=3 -std=c++11 {src_path} -lm -o {exe_path}'
            shutil.rmtree(TMP_COMPILER_DIR, ignore_errors=True)
            os.makedirs(TMP_COMPILER_DIR, exist_ok=False)
            with open(source_path, 'wb') as f:
                f.write(request.FILES['file'].read())
            source_zip = zipfile.ZipFile(source_path)
            source_zip.extractall(TMP_COMPILER_DIR)
            for file in os.listdir(TMP_COMPILER_DIR):
                if file.endswith('.cpp'):
                    src = os.path.join(TMP_COMPILER_DIR, file)
                    exe = os.path.join(TMP_COMPILER_DIR, file[:-4])
                    running_direct = COMPILE_DIRECTIVE.format(src_path=src, exe_path=exe).split()
                    p = subprocess.run(running_direct, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30)
                    if p.returncode != 0:
                        raise RuntimeError('Compiler Error:\n%s\n%s' % (p.stdout, p.stderr))
                    else:
                        return serve(request, file[:-4], document_root=TMP_COMPILER_DIR)
            raise FileNotFoundError('Did you forget to provide a cpp file?')
        except Exception as e:
            result['message'] = repr(e)
            return HttpResponse(json.dumps(result))

    def get(self, request):
        return render(request, self.template_name)


class ProblemDelete(BaseBackstageMixin, View):
    def get(self, request, pk):
        problem = Problem.objects.get(pk=pk)
        problem.delete()
        messages.success(request, "Problem <strong>%s</strong> has been successfully deleted." % str(problem))
        return HttpResponseRedirect(reverse('backstage:problem'))


class ProblemCreate(BaseCreateView):
    form_class = ProblemEditForm
    template_name = 'backstage/problem/problem_add.jinja2'

    def post_create(self, instance, form):
        instance.tags = form.cleaned_data['tags']

    def get_redirect_url(self, instance):
        return reverse("backstage:problem")


class ProblemUpdate(BaseUpdateView):
    form_class = ProblemEditForm
    queryset = Problem.objects.all()
    template_name = 'backstage/problem/problem_edit.jinja2'

    def post_update(self, instance, form):
        instance.tags = form.cleaned_data['tags']


class ProblemList(BaseBackstageMixin, ListView):
    template_name = 'backstage/problem/problem.jinja2'
    queryset = Problem.objects.order_by("-pk").all()
    paginate_by = 100
    context_object_name = 'problem_list'


class ProblemRejudge(BaseBackstageMixin, View):

    def post(self, request):
        try:
            problem = request.POST['problem']
            submissions = [x.pk for x in Submission.objects.filter(problem__pk=problem).all().reverse()]
            ProblemRejudgeThread(submissions).start()
            messages.success(request, 'Rejudge has been sent.')
        except Exception as e:
            print(repr(e))
            messages.error(request, 'Rejudge failed.')
        return HttpResponseRedirect(request.POST['next'])


class ProblemVisibleSwitch(BaseBackstageMixin, View):

    def get(self, request, pk):
        with transaction.atomic():
            problem = Problem.objects.select_for_update().get(pk=pk)
            problem.visible = True if not problem.visible else False
            problem.save(update_fields=["visible"])
        return HttpResponse(json.dumps({'result': 'success'}))