from random import SystemRandom


system_random = SystemRandom()
alphabet = 'abcdefghkmnpqrstuvwxyzABCDEFGHKLMNPQRSTUVWXYZ23456789'


def random_password(size=12, alphabet=alphabet, random=system_random):
    s = ''
    for i in xrange(size):
        s += random.choice(alphabet)
    return s
