#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re
import sys
import json

from zeus.core import ( c2048, get_random_selection,
                        gamma_encode,
                        encrypt, prove_encryption,
                        mix_ciphers)
from os.path import exists
import urllib, urllib2

def do_download(url, mixfile):
    if exists(mixfile):
        m = "file '%s' already exists, will not overwrite" % (mixfile,)
        raise ValueError(m)

    with open(mixfile, "w") as f:
        mix_data = urllib.urlopen(url).read()
        f.write(mix_data)

    return mix_data

def do_mix(mixfile, newfile, nr_rounds, nr_parallel):
    if exists(newfile):
        m = "file '%s' already exists, will not overwrite" % (newfile,)
        raise ValueError(m)

    with open(mixfile) as f:
        mix = json.load(f)

    new_mix = mix_ciphers(mix, nr_rounds=nr_rounds,
                          nr_parallel=nr_parallel)
    with open(newfile, "w") as f:
        json.dump(new_mix, f)

    return new_mix

def do_upload(mixfile, url):
    with open(mixfile) as f:
        mix_data = json.load(f)
    data = {'mix': mix_data}
    values = urllib.urlencode(data)
    req = urllib2.Request(url, values)
    response = urllib2.urlopen(req)
    print reponse

def main_help():
    usage = ("Usage: ./zeus-mixer <url> <nr_rounds> <nr_parallel>\n"
             "       ./zeus-mixer download <url> <mixfile>\n"
             "       ./zeus-mixer mix      <mixfile> <mixfile.new> <nr_rounds> <nr_parallel>\n"
             "       ./zeus-mixer upload   <mixfile.new> <url>\n")
    sys.stderr.write(usage)
    raise SystemExit

def main():
    from sys import argv
    argc = len(argv)
    if argc < 4:
        main_help()

    cmd = argv[1]
    if cmd == 'download':
        do_download(argv[2], argv[3])
    elif cmd == 'mix':
        if argc < 6:
            main_help()
        do_mix(argv[2], argv[3], int(argv[4]), int(argv[5]))
    elif cmd == 'upload':
        do_upload(argv[2], argv[3])
    else:
        mixfile = argv[4] if argc > 4 else "mixfile"
        newfile = mixfile + '.new'
        url = argv[1]
        nr_rounds = int(argv[2])
        nr_parallel = int(argv[3])
        do_download(url, mixfile)
        do_mix(mixfile, newfile, nr_rounds, nr_parallel)
        do_upload(newfile, url)

if __name__ == '__main__':
    main()

