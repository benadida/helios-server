import os
import threading

from django.conf import settings

import logging

_locals = threading.local()

ELECTION_LOG_DIR = getattr(settings, 'ZEUS_ELECTION_LOG_DIR', '/tmp/')
ELECTION_STREAM_HANDLER = getattr(settings, 'ZEUS_ELECTION_STREAM_HANDLER', False)


def _get_user_id(user=None):
    thread_user = None
    if hasattr(_locals, 'user_id'):
        thread_user = unicode(_locals.user_id)
    user_id = None
    if thread_user:
        user_id = thread_user
    if user:
        user_id = user.user_id
    return user_id


def _get_logger(uuid, obj, user, fmt, extra={}):
    user_id = _get_user_id(user)
    key = '%s_%s' % (obj.__class__.__name__, obj.uuid)

    thread_ip = "UNKNOWN"
    if hasattr(_locals, 'ip'):
        thread_ip = unicode(_locals.ip)

    if user_id:
        key = key + '_%s' % user_id
    else:
        user_id = "SYSTEM"
        thread_ip = "SYSTEM"


    logger = logging.getLogger(key)
    logger.setLevel(logging.DEBUG)
    logger.propagate = False
    extra['user'] = user_id
    extra['ip'] = thread_ip

    # logger already initialized
    if logger.handlers:
        return logging.LoggerAdapter(logger, extra)

    log_file_path = os.path.join(ELECTION_LOG_DIR, '%s.log' % uuid)
    fh = logging.FileHandler(log_file_path)
    fh.setLevel(logging.DEBUG)

    _fmt = '%(asctime)s - %(ip)s - %(user)s - ' + fmt + '%(levelname)s - %(message)s'
    formatter = logging.Formatter(_fmt)
    fh.setFormatter(formatter)
    logger.addHandler(fh)

    if ELECTION_STREAM_HANDLER:
        handler = logging.StreamHandler()
        _fmt = '%(asctime)s - %(user)s - ' + fmt + '%(levelname)s - %(message)s'
        formatter = logging.Formatter(_fmt)
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logging.LoggerAdapter(logger, extra)


def init_election_logger(election, user=None):
    return _get_logger(election.uuid, election, user, '', {})


def init_poll_logger(poll, user=None):
    extra = {
        'poll': poll.short_name,
        'poll_uuid': poll.uuid
    }
    return _get_logger(poll.election.uuid, poll, user,
                       '%(poll)s (%(poll_uuid)s) - ', extra)
