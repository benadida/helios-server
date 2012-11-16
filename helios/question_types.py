from django.utils.translation import ugettext_lazy as _

# types registry
QUESTION_TYPES = {}


class QuestionTypeBase(type):
  def __new__(cls, name, bases, dct):
    if [b for b in bases if isinstance(b, QuestionTypeBase)]:
      type_id, type_name = dct.get('name')
      QUESTION_TYPES[type_id] = {'name': type_name, 'cls': cls}

    return super(QuestionTypeBase, cls).__new__(cls, name, bases, dct)


class QuestionType(object):
  __metaclass__ = QuestionTypeBase


class RankedQuestion(QuestionType):
  name = ('choice', _('Choice'))


class ChoiceQuestion(QuestionType):
  name = ('ranked', _('Ranked'))


class STVQuestion(QuestionType):
  name = ('stv', _('STV'))

