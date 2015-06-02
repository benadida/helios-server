# -*- coding: utf-8 -*-
from cStringIO import StringIO
from csv import (Sniffer, excel, Error as csvError,
                 reader as imported_csv_reader)
from codecs import BOM_LE, BOM_BE, getreader


class CSVReader(object):

    def __init__(self, csv_data, min_fields=2, max_fields=6, **kwargs):

        if hasattr(csv_data, 'read') and hasattr(csv_data, 'seek'):
            f = csv_data
        elif isinstance(csv_data, str):
            f = StringIO(csv_data)
        else:
            m = "Please provide str or file to name_of_class, not{type}"
            m = m.format(type=type(csv_data))
            raise ValueError(m)
        if min_fields == 0 or max_fields == 0:
            m = "Invalid arguments, min_fields or max_fields can't be 0"
            raise ValueError(m)
        if min_fields > max_fields:
            m = "Invalid arguments, min_fields must be less than max_fields"
            raise ValueError(m)

        self.min_fields = min_fields
        self.max_fields = max_fields
        sample_data = pick_sample(f.read(65536))
        f.seek(0)
        encoding = get_encoding(sample_data)
        dialect = get_dialect(sample_data)
        self.reader = UnicodeReader(f, dialect, encoding)

    def next(self):
        row = self.reader.next()
        if len(row) < self.min_fields or len(row) > self.max_fields:
            raise CSVCellError(len(row), self.min_fields, self.max_fields)
        row += [u''] * (self.max_fields - len(row))
        return row

    def __iter__(self):
        return self


class UTF8Recoder(object):
    """
    Iterator that reads an encoded stream and reencodes the input to UTF-8
    """
    def __init__(self, f, encoding):
        self.reader = getreader(encoding)(f)

    def __iter__(self):
        return self

    def next(self):
        return self.reader.next().encode("utf-8")


class UnicodeReader(object):
    """
    A CSV reader which will iterate over lines in the CSV file "f",
    which is encoded in the given encoding.
    """

    def __init__(self, f, dialect=excel, encoding="utf-8", **kwds):
        f = UTF8Recoder(f, encoding)
        self.reader = imported_csv_reader(f, dialect, **kwds)

    def next(self):
        row = self.reader.next()
        return [unicode(s, "utf-8") for s in row]

    def __iter__(self):
        return self


class CSVCellError(Exception):

    def __init__(self, cell_num, min_fields, max_fields):
        if cell_num < min_fields:
            self.m = ("CSV cells(" + str(cell_num) +
                      ") < min_fields(" + str(min_fields)+")")
        if cell_num > max_fields:
            self.m = ("CSV cells(" + str(cell_num) +
                      ") > max_fields("+str(max_fields)+")")

    def __str__(self):
        return self.m


def get_encoding(csv_data):
    encodings = ['utf-8', 'iso8859-7', 'utf-16', 'utf-16le', 'utf-16be']
    encodings.reverse()
    while 1:
        m = "Cannot decode csv data!"
        if not encodings:
            raise ValueError(m)
        encoding = encodings[-1]
        try:
            if (encoding == "utf-16" and
                    (not csv_data or csv_data[0:2] not in (BOM_LE, BOM_BE))):
                raise ValueError
            data = csv_data.decode(encoding)
            if (encoding in ('utf-16be', 'utf-16le')
                    and data and data[0] == u'\ufffe'):
                data = data[1:]
            if data.count(u'\x00') > 0:
                m = "Wrong encoding detected (heuristic)"
                raise ValueError(m)
            if data.count(u'\u0A00') > data.count(u'\u000A'):
                m = "Wrong endianess (heuristic)"
                raise ValueError(m)
            break
        except (UnicodeDecodeError, ValueError):
            encodings.pop()
            continue
    return encoding


def pick_sample(part):
    sample, sep, junk = part.rpartition('\x0a')
    if len(sample) & 1:
        sample += sep
    return sample


def get_dialect(sample):
    try:
        dialect = Sniffer().sniff(sample, (',', ':', ' ', '\t', ';'))
    except (csvError):
        dialect = excel
    return dialect
