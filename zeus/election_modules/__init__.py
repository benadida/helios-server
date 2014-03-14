import copy

from django.utils.translation import ugettext_lazy as _


ELECTION_MODULES_CHOICES = []
MODULES_REGISTRY = {}


def election_module(cls):
    MODULES_REGISTRY[cls.module_id] = cls
    ELECTION_MODULES_CHOICES.append((cls.module_id, cls.description))
    return cls


def get_election_module(election):
    return MODULES_REGISTRY.get(election.election_module)(election)


def get_poll_module(poll):
    return MODULES_REGISTRY.get(poll.election.election_module)(poll.election,
                                                               poll)


class ElectionModuleBase(object):

    module_id =  None
    
    pdf_result = True
    csv_result = True
    json_result = True

    module_params = {}

    default_messages = {
        'description': _('Simple election with one or more questions'),
        'questions_title': _(u'Ballot'),
        'question_title': _(u'Question'),
        'answer_title': _(u'Answer'),
        'questions_view': 'helios.views.one_election_questions',
        'questions_empty_issue': _("Add questions to the election"),
        'max_limit_error': _("Too many choices"),
        'min_limit_error': _("Question '{0}' requires at least {1} choices."),
        'auto_append_answer': True,
        'count_empty_question': False
    }

    auto_append_answer = True
    count_empty_question = False

    def __init__(self, election, poll=None):
        self.election = election
        self.poll = poll

        self._messages = copy.copy(self.default_messages)
        self._messages.update(self.messages)

    def __getattr__(self, name, *args, **kwargs):
        if name.endswith('_message'):
            msgkey = name.replace('_message', '')
            if msgkey in self._messages:
                return self._messages.get(msgkey)
        return super(ElectionModuleBase, self).__getattribute__(name, *args,
                                                                **kwargs)

    def questions_set(self):
        return self.poll.questions_count > 0

    def questions_list_view(self, request):
        raise NotImplemented

    def questions_update_view(self, request):
        raise NotImplemented

    def calculate_results(self, request):
        raise NotImplemented

    def get_booth_template(self, request):
        raise NotImplemented

    @property
    def params(self):
        data = dict()
        data.update(self._messages)
        data.update({
            'auto_append_answer': self.auto_append_answer,
            'count_empty_question': self.count_empty_question
        })
        if self.module_params:
            data.update(self.module_params)
        return data

from zeus.election_modules.simple import *
from zeus.election_modules.parties import *
from zeus.election_modules.score import *
