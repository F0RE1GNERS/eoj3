from problem.models import Problem, SpecialProgram, FCMP_FINGERPRINT
import traceback


def run():
    try:
        for problem in Problem.objects.all():
            if problem.judge == 'fcmp' or problem.judge == '':
                continue
            if SpecialProgram.objects.filter(filename=problem.judge + '.cpp', category='checker').exists():
                if SpecialProgram.objects.filter(filename=problem.judge + '.cpp', category='checker').count() > 1:
                    print(problem.judge)
                problem.checker = SpecialProgram.objects.get(filename=problem.judge + '.cpp', category='checker').fingerprint
                problem.save(update_fields=['checker'])
            else:
                problem.visible = False

    except:
        traceback.print_exc()
    try:
        for problem in Problem.objects.all():
            if not SpecialProgram.objects.filter(fingerprint=problem.checker).exists():
                problem.checker = FCMP_FINGERPRINT
                problem.save(update_fields=['checker'])
    except:
        traceback.print_exc()