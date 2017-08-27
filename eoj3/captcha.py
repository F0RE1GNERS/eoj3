from random import randint, choice


def random_math_challenge():
    a = randint(1, 30)
    b = randint(1, a)
    a /= 10
    b /= 10
    c = choice('+-')
    if c == '+':
        d = a + b
    elif c == '-':
        d = a - b
    else:
        d = a * b
    return '%.1f%s%.1f=' % (a, c, b), str(d)
