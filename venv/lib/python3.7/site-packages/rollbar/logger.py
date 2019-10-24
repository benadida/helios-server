"""
Hooks for integrating with the python logging framework.

Usage:
    import logging
    from rollbar.logger import RollbarHandler

    rollbar.init('ACCESS_TOKEN', 'ENVIRONMENT')

    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)

    # report ERROR and above to Rollbar
    rollbar_handler = RollbarHandler()
    rollbar_handler.setLevel(logging.ERROR)

    # attach the handlers to the root logger
    logger.addHandler(rollbar_handler)

"""
import copy
import logging
import threading
import time

import rollbar


class RollbarHandler(logging.Handler):
    SUPPORTED_LEVELS = set(('debug', 'info', 'warning', 'error', 'critical'))

    _history = threading.local()

    def __init__(self,
                 access_token=None,
                 environment=None,
                 level=logging.INFO,
                 history_size=10,
                 history_level=logging.DEBUG):

        logging.Handler.__init__(self)

        if access_token is not None:
            rollbar.init(access_token, environment)

        self.notify_level = level

        self.history_size = history_size
        if history_size > 0:
            self._history.records = []

        self.setHistoryLevel(history_level)

    def setLevel(self, level):
        """
        Override so we set the effective level for which
        log records we notify Rollbar about instead of which
        records we save to the history.
        """
        self.notify_level = level

    def setHistoryLevel(self, level):
        """
        Use this method to determine which records we record history
        for. Use setLevel() to determine which level we report records
        to Rollbar for.
        """
        logging.Handler.setLevel(self, level)

    def emit(self, record):
        level = record.levelname.lower()

        if level not in self.SUPPORTED_LEVELS:
            return

        exc_info = record.exc_info

        # use the original message, not the formatted one
        message = record.msg
        extra_data = {
            'args': record.args,
            'record': {
                'created': record.created,
                'funcName': record.funcName,
                'lineno': record.lineno,
                'module': record.module,
                'name': record.name,
                'pathname': record.pathname,
                'process': record.process,
                'processName': record.processName,
                'relativeCreated': record.relativeCreated,
                'thread': record.thread,
                'threadName': record.threadName
            }
        }

        extra_data.update(getattr(record, 'extra_data', {}))

        payload_data = getattr(record, 'payload_data', {})

        self._add_history(record, payload_data)

        # after we've added the history data, check to see if the
        # notify level is satisfied
        if record.levelno < self.notify_level:
            return

        # Wait until we know we're going to send a report before trying to
        # load the request
        request = getattr(record, "request", None) or rollbar.get_request()

        uuid = None
        try:
            # when not in an exception handler, exc_info == (None, None, None)
            if exc_info and exc_info[0]:
                if message:
                    message_template = {
                        'body': {
                            'trace': {
                                'exception': {
                                    'description': message
                                }
                            }
                        }
                    }
                    payload_data = rollbar.dict_merge(payload_data, message_template)

                uuid = rollbar.report_exc_info(exc_info,
                                               level=level,
                                               request=request,
                                               extra_data=extra_data,
                                               payload_data=payload_data)
            else:
                uuid = rollbar.report_message(message,
                                              level=level,
                                              request=request,
                                              extra_data=extra_data,
                                              payload_data=payload_data)
        except:
            self.handleError(record)
        else:
            if uuid:
                record.rollbar_uuid = uuid

    def _add_history(self, record, payload_data):
        if hasattr(self._history, 'records'):
            records = self._history.records
            history = list(records[-self.history_size:])

            if history:
                history_data = [self._build_history_data(r) for r in history]
                payload_data.setdefault('server', {})['history'] = history_data

            records.append(record)

            # prune the messages if we have too many
            self._history.records = list(records[-self.history_size:])

    def _build_history_data(self, record):
        data = {'timestamp': record.created,
                'message': record.getMessage()}

        if hasattr(record, 'rollbar_uuid'):
            data['uuid'] = record.rollbar_uuid

        return data
