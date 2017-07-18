from shortuuid import ShortUUID

random_gen = ShortUUID()

def random_string(length=24):
    return random_gen.random(length)
