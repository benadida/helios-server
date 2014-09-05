from random import SystemRandom


system_random = SystemRandom()
alphabet = 'abcdefghkmnpqrstuvwxyzABCDEFGHKLMNPQRSTUVWXYZ23456789'


def random_password(size=12, alphabet=alphabet, random=system_random):
    s = ''
    for i in xrange(size):
        s += random.choice(alphabet)
    return s

def can_do(logged_user, user):
    if((user.management_p
            or user.superadmin_p)
            and logged_user.superadmin_p):
        can_edit = True
    elif((user.management_p
            or user.superadmin_p)
            and logged_user.management_p):
        can_edit = False
    else:
        can_edit = True
    return can_edit

def sanitize_get_param(param):
    try:
        param = int(param)
    except(ValueError, TypeError):
        param = None
    return param

