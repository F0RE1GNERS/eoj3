from random import choice
import string

def random_string(length=24):
    return ''.join(choice(string.ascii_letters + string.digits) for _ in range(length))