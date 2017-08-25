from problem.models import Problem, SpecialProgram
import traceback


def run():
    # try:
    #     for problem in Problem.objects.all():
    #         if problem.judge == '' or problem.judge == 'fcmp':
    #             continue
    #         if SpecialProgram.objects.filter(filename__contains=problem.judge).exists():
    #             problem.checker = SpecialProgram.objects.filter(filename__contains=problem.judge).first().fingerprint
    #         else:
    #             problem.visible = False
    #         problem.save(update_fields=['checker', 'visible'])
    # except:
    #     traceback.print_exc()
    try:
        for problem in Problem.objects.all():
            if not SpecialProgram.objects.filter(fingerprint=problem.checker).exists():
                print(problem.checker)
    except:
        traceback.print_exc()