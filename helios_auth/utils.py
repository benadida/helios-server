"""
Some basic utils 
(previously were in helios module, but making things less interdependent

2010-08-17
"""

import json


## JSON
def to_json(d):
    return json.dumps(d, sort_keys=True)


def from_json(value):
    if value == "" or value is None:
        return None

    if isinstance(value, str):
        try:
            return json.loads(value)
        except Exception as e:
            # import ast
            # try:
            #     parsed_value = ast.literal_eval(parsed_value)
            # except Exception as e1:
            raise Exception("value is not JSON parseable, that's bad news") from e

    return value


def JSONFiletoDict(filename):
    with open(filename, 'r') as f:
        content = f.read()
    return from_json(content)


def format_recipient(name, email):
    """
    Format an email recipient as "name" <email>.
    Truncates name to 70 characters to avoid issues with Python3's email module.
    Quotes the name per RFC 5322 to handle special characters.
    """
    truncated_name = name[:70] if name else email
    return "\"%s\" <%s>" % (truncated_name, email)
