from random import randint, choice


def random_math_challenge():
    a, b = randint(1, 10), randint(1, 9)
    c = choice('+-*/')
    if c == '+':
        d = a + b
    elif c == '-':
        d = a - b
    elif c == '*':
        d = a * b
    else:
        d = a // b
    return '%d%s%d=' % (a, c, b), str(d)
