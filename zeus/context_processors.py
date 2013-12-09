from django.conf import settings

from zeus import messages

def user(request):
    data = {}
    user = request.zeususer
    if not user.is_authenticated():
        return data
    if user.is_admin:
        key = 'admin'
    if user.is_trustee:
        key = 'trustee'
    if user.is_voter:
        key = 'voter'
    data[key] = user._user
    data['user'] = user
    return data


def confirm_messages(request):
    msg_dict = {}
    for msg in dir(messages):
        if msg.upper() == msg:
            msg_dict[msg.lower()] = getattr(messages, msg)
    return msg_dict


def theme(request):
    return {
        'THEME_HEADER_BG_URL': settings.ZEUS_HEADER_BG_URL
    }
