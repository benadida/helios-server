# -*- coding: utf-8 -*-
import uuid
import urllib
import json

from xml.sax.saxutils import escape

escape_dict = {
}


def Element(tag, text=None, *args, **kwargs):
    e = etree.Element(tag, *args, **kwargs)
    if text:
        e.text = text
    return e


class Client(object):

    apiurl = "https://mybsms.gr/ws/send.json"
    id = "mybsms"

    def __init__(self, from_mobile, user, password, dlr_url):
        self.user = user
        self.password = password
        self.from_mobile = from_mobile
        self.delivery_url = dlr_url
        assert self.delivery_url

    def _construct(self, uid, msisdn, message):
        req = {}
        req['username'] = self.user
        req['password'] = self.password
        req['recipients'] = [str(msisdn)]
        message = message.decode("utf8")
        message = escape(message, escape_dict)
        req['message'] = message
        if self.delivery_url:
            req['dlr-url'] = self.delivery_url
        req['senderId'] = self.from_mobile
        return req

    def status(self, msgid):
        raise NotImplementedError

    def send(self, mobile, msg, fields={}, uid=None):
        if not uid:
            uid = unicode(uuid.uuid4())

        msg = self._construct(uid, mobile, msg)
        data = json.dumps(msg)
        http_response = urllib.urlopen(self.apiurl, data=data)
        self._last_uid = uid
        try:
            resp = http_response.read()
            response = json.loads(resp)
            status = 'FAIL' if response['error'] else 'OK'

            if status not in ['OK', 'FAIL']:
                return False, "Invalid response status %s" % status
            if status == 'OK':
                return True, response['id']
            else:
                return False, response['error']
        except ValueError:
            return False, "Cannot parse response"
        except KeyError:
            return False, "Cannot read response"
