#!/usr/bin/env python
# -*- coding: utf-8 -*-

import smtplib
import traceback
from email.mime.text import MIMEText
from email.Charset import add_charset, QP
add_charset('utf-8', QP, QP, 'utf-8')
from time import time, sleep

def csv_reader(csv_data, **kwargs):
    if not isinstance(csv_data, str):
        m = "Please provide string data to csv_reader, not %s" % type(csv_data)
        raise ValueError(m)
    encodings = ['utf-8', 'iso8859-7', 'utf-16', 'utf-16le', 'utf-16be']
    encodings.reverse()
    rows = []
    append = rows.append
    while 1:
        if not encodings:
            m = "Cannot decode csv data!"
            raise ValueError(m)
        encoding = encodings[-1]
        try:
            data = csv_data.decode(encoding)
            data = data.strip(u'\ufeff')
            if data.count(u'\x00') > 0:
                m = "Wrong encoding detected (heuristic)"
                raise ValueError(m)
            if data.count(u'\u2000') > data.count(u'\u0020'):
                m = "Wrong endianess (heuristic)"
                raise ValueError(m)
            break
        except (UnicodeDecodeError, ValueError), e:
            encodings.pop()
            continue

    for line in data.splitlines():
        line = line.strip()
        if not line:
            continue
        cells = line.split(',', 3)
        if len(cells) < 3:
            cells = line.split(';')
            if len(cells) < 3:
                m = ("CSV must have at least 3 fields "
                     "(email, last_name, name)")
                raise ValueError(m)
        cells += [u''] * (4 - len(cells))
        append(cells)

    return rows

from sys import argv
argc = len(argv)

def usage():
    usage = """
    {0} <email-name-surname-fathername.csv> <subject.txt> <body.txt> [<rate_per_second>]
    """
    print usage.format(argv[0])
    raise SystemExit

if argc < 3:
    usage()

csv_file = argv[1]
subject_file = argv[2]
body_file = argv[3]
rate = float(argv[4]) if argc >= 5 else 2.0

with open(csv_file) as f:
    csv_data = f.read()
with open(subject_file) as f:
    subject = f.read().decode('utf-8')
with open(body_file) as f:
    body = f.read().decode('utf-8')

rows = csv_reader(csv_data)
nr_rows = len(rows)
row = 0

s = smtplib.SMTP('localhost')

t0 = time()
for addr, name, surname, fathername in rows:
    data = {'email': addr.strip(),
            'name': name.strip(),
            'surname': surname.strip(),
            'fathername': fathername.strip()}
    subject_text = subject.format(**data).encode('utf-8')
    body_text = body.format(**data).encode('utf-8')
    msg = MIMEText(body_text, _subtype='plain', _charset='utf-8')

    From = u"Ψηφιακή κάλπη «Ζεύς» <elections@zeus.grnet.gr>".encode('utf-8')
    fullname = u' '.join((data['surname'], data['name'], data['fathername']))
    fullname = fullname.strip()
    To = u'"{fullname}" <{email}>'.format(email=data['email'],
                                          fullname=fullname).encode('utf-8')
    msg['From'] = From
    msg['To'] = To
    msg['Subject'] = subject_text
    row += 1
    data['i'] = row
    data['t'] = nr_rows
    print '{i}/{t} {email}'.format(**data)

    t = time() - t0
    if row / t > rate:
        sleep(0.2)

    try:
        s.sendmail(From, [To], msg.as_string())
    except:
        traceback.print_exc()
        s = smtplib.SMTP('localhost')

s.quit()

