from random import randint

from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt


def response_ok():
  return {"status": "received"}


@csrf_exempt
def judge_mock(request):
  return JsonResponse(response_ok())


@csrf_exempt
def query_mock(request):
  return JsonResponse({"status": "received", "verdict": randint(-2, 0)})


@csrf_exempt
def query_report_mock(request):
  return HttpResponse()