from functools import partial
from django.test import TestCase

from zeus.utils import parse_q_param, get_filters, VOTER_TABLE_HEADERS, \
    VOTER_SEARCH_FIELDS, VOTER_BOOL_KEYS_MAP, VOTER_EXTRA_HEADERS


get_voters_filters = lambda inp: get_filters(inp, VOTER_TABLE_HEADERS,
                                                  VOTER_SEARCH_FIELDS,
                                                  VOTER_BOOL_KEYS_MAP,
                                                  VOTER_EXTRA_HEADERS)

class TestUtils(TestCase):

    def test_q_args(self):
        q = "voter- +vote"
        self.assertEqual(parse_q_param(q), ('voter-', ['+vote']))

    def test_voters_filters(self):
        qs = get_voters_filters("+voted")
        self.assertEqual(qs.children[1], ('cast_votes__id__isnull', False))

        qs = get_voters_filters("-voted")
        self.assertEqual(qs.children[1], ('cast_votes__id__isnull', True))
