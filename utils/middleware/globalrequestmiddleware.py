import threading


class GlobalRequestMiddleware(object):
  _threadmap = {}

  def __init__(self, get_response):
    self.get_response = get_response

  def __call__(self, request):
    self.process_request(request)
    response = self.get_response(request)
    return self.process_response(request, response)

  @classmethod
  def get_current_request(cls):
    return cls._threadmap[threading.get_ident()]

  def process_request(self, request):
    self._threadmap[threading.get_ident()] = request

  def process_exception(self, request, exception):
    try:
      del self._threadmap[threading.get_ident()]
    except KeyError:
      pass

  def process_response(self, request, response):
    try:
      del self._threadmap[threading.get_ident()]
    except KeyError:
      pass
    return response
