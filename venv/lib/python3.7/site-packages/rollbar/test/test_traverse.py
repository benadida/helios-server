from rollbar.lib.traverse import traverse

from rollbar.test import BaseTest


class NamedTuple(tuple):
    """
    Modeled after NamedTuple and KeyedTuple from SQLAlchemy 0.7 and 0.8.
    """
    def __new__(cls, vals, labels=None):
        t = tuple.__new__(cls, vals)
        if labels:
            t.__dict__.update(zip(labels, vals))
            t._labels = labels
        return t

    def keys(self):
        return [l for l in self._labels if l is not None]


class RollbarTraverseTest(BaseTest):
    """
    Objects that appear to be a namedtuple, like SQLAlchemy's KeyedTuple,
    will cause an Exception while identifying them if they don't implement
    the _make method.
    """
    def setUp(self):
        self.tuple = NamedTuple((1, 2, 3), labels=["one", "two", "three"])

    def test_base_case(self):
        self.assertEqual(traverse(self.tuple), (1, 2, 3))

    def test_bad_object(self):
        setattr(self.tuple, '_fields', 'not quite a named tuple')
        self.assertEqual(traverse(self.tuple), (1, 2, 3))
