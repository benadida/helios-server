# -*- coding: utf-8 -*-
import uuid
import urllib

from xml.etree import ElementTree as etree


def Element(tag, text=None, *args, **kwargs):
    e = etree.Element(tag, *args, **kwargs)
    if text:
        e.text = text
    return e


class Loco(object):

    apiurl = "http://www.locosms.gr/xmlsend.php"

    def __init__(self, from_mobile, user, password):
        self.user = user
        self.password = password
        self.from_mobile = from_mobile

    def _cosntruct(self, uid, msisdn, message, fields={}):
        msg = Element("msg")
        msg.append(Element("username", self.user))
        msg.append(Element("password", self.password))
        msg.append(Element("text", message.decode('utf8')))
        msg.append(Element("totalfields", str(len(fields.keys()))))

        recipient = Element("recipient")
        recipient.append(Element("uid", uid))
        recipient.append(Element("msisdn", msisdn))
        recipient.append(Element("mobile", self.from_mobile))
        for field, value in fields.iteritems():
            recipient.append(Element(field, value))
        msg.append(recipient)
        return msg

    def send(self, mobile, msg, fields={}, uid=None):
        if not uid:
            uid = unicode(uuid.uuid4())

        msg = self._cosntruct(uid, mobile, msg, fields)
        _msg = etree.tostring(msg)
        http_response = urllib.urlopen(self.apiurl, data=_msg)
        self._last_uid = uid
        try:
            response = etree.fromstring(http_response.read())
            status = response.find("status").text
            if status not in ['OK', 'FAIL']:
                return False, "Invalid response status %s" % status
            if status == 'OK':
                return True, response.find("smsid").text
            else:
                return False, response.find("reason").text
            status = response.find("status").text
        except etree.ParseError:
            return False, "Cannot parse response"
