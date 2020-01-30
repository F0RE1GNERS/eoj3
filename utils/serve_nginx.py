from django.http import HttpResponse


def serve_with_nginx(request, path, root_name=None):
  response = HttpResponse()
  response['X-Accel-Redirect'] = "/fake/{0}/{1}".format(root_name, path)
  return response
