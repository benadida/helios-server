"""
Integration with Flask
"""

from flask import request
import rollbar


def report_exception(app, exception):
    rollbar.report_exc_info(request=request)


def _hook(request, data):
    data['framework'] = 'flask'

    if request:
        data['context'] = str(request.url_rule)

rollbar.BASE_DATA_HOOK = _hook
