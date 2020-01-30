from os import getenv
from functools import partial
from dispatcher.models import Server


def env(key, default=None, name="DEFAULT"):
  return getenv('ADD_JUDGE_' + name + '_' + key, default=default)

def run(*args):
  origin_count = Server.objects.count()

  judges = getenv('ADD_JUDGE', '').split(',')

  if origin_count > 0 and judges:
    print('judges exist, will do nothing')
    return

  judges = list(filter(None, judges))

  for judge_name in judges:
    _env = partial(env, name=judge_name)

    judge_ip = _env('IP')
    judge_port = int(_env('PORT', '5000'))
    judge_token = _env('TOKEN')
    judge_concurrency = int(_env('CONCURRENCY'))
    judge_multiplier = float(_env('MULTIPLIER', '1'))
    judge_is_master = _env('MASTER', 'False') == 'True'

    assert judge_ip is not None
    assert judge_port >= 0 and judge_port <= 65535
    assert judge_token is not None

    print('add server %s %s:%d [%s] *%d *%f %s'%
          (judge_name, judge_ip, judge_port, judge_token,
           judge_concurrency, judge_multiplier, 'master' if judge_is_master else 'node'))

    (server, _created) = Server.objects.get_or_create(name=judge_name, defaults={
      'ip': judge_ip,
      'port': judge_port,
      'token': judge_token,
      'version': 3,
    })

    server.ip = judge_ip
    server.port = judge_port
    server.token = judge_token
    server.enabled = True
    server.concurrency = judge_concurrency
    server.runtime_multiplier = judge_multiplier
    server.master = judge_is_master

    server.save()
