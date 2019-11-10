from random import randint, choice

SIGN = {
  '+': 'plus',
  '-': 'minus',
  '*': 'times',
}


def random_math_challenge():
  a, b = randint(1, 10), randint(1, 9)
  c = choice('+-*')
  if c == '+':
    d = a + b
  elif c == '-':
    d = a - b
  elif c == '*':
    d = a * b
  else:
    d = 0
  return '%d %s %d' % (a, SIGN[c], b), str(d)
