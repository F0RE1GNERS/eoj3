def url_linker(host, port, path):
  if not host.startswith('http'):
    if host.startswith('//'):
      host = 'http:' + host
    else:
      host = 'http://' + host
  if not path.startswith('/'):
    path = '/' + path
  return host + ':' + str(port) + path


def upload_linker(host, port, pid):
  return url_linker(host, port, 'upload/%s' % str(pid))


def judge_linker(host, port):
  return url_linker(host, port, 'judge')
