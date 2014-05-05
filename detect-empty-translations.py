#!/usr/bin/env python

import sys

po_files = sys.argv[1:]
if not po_files:
    print "Usage: %s <path/to/some.po> ..." % sys.argv[0]
    raise SystemExit

for po_file in po_files:
    state = 0
    msgid = None
    msgstr = None
    msgid_line = 0
    fuzzy = False
    line = None

    for line in open(po_file):
        msgid_line += 1
        if line.startswith('#') and 'fuzzy' in line:
            fuzzy = True
        elif state == 0 and line.startswith('msgid'):
            if line != 'msgid ""\n':
                msgid = line
                if fuzzy:
                    print "%s:%d: %s" % (po_file, msgid_line, msgid),
                    msgid = None
                    state = 0
                else:
                    state = 1
            fuzzy = False
        elif state == 1:
            fuzzy = False
            if line == 'msgstr ""\n':
                state = 2
            elif line.startswith('msgstr') or line == '\n':
                state = 0
                msgid = None
                fuzzy = False
        elif state == 2:
            fuzzy = False
            if line == '\n':
                print "%s:%d: %s" % (po_file, msgid_line, msgid),
            state = 0
            msgid = None
            fuzzy = False

    if None not in (line, msgid) and (state == 0 and fuzzy) \
       or (state == 2 and msgid is not None):
        # last-in-file empty translation
        print "%s:%d: %s" % (po_file, msgid_line, msgid),

