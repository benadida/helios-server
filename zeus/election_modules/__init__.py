import copy
import json
import os 

from django.conf import settings 
from django.utils.translation import ugettext_lazy as _

from zeus.reports import csv_from_polls, csv_from_score_polls,\
                         csv_from_stv_polls


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

    def get_poll_result_file_path(self, name, ext, lang=None):
        RESULTS_PATH = getattr(settings, 'ZEUS_RESULTS_PATH',\
            os.path.join(settings.MEDIA_ROOT, 'results'))
        election = self.election.short_name
        poll = self.poll.short_name
        if lang:
            return os.path.join(RESULTS_PATH, '%s-%s-%s-results-%s.%s' % \
                                (election, poll, name, lang, ext))
        else:
            return os.path.join(RESULTS_PATH, '%s-%s-%s-results.%s' % \
                                (election, poll, name, ext))

    def get_election_result_file_path(self, name, ext, lang=None):
            RESULTS_PATH = getattr(settings, 'ZEUS_RESULTS_PATH',\
                os.path.join(settings.MEDIA_ROOT, 'results'))
            election = self.election.short_name
            if lang:
                return os.path.join(RESULTS_PATH, '%s-%s-results-%s.%s' % \
                                    (election, name, lang, ext))
            else:
                return os.path.join(RESULTS_PATH, '%s-%s-results.%s' % \
                                    (election, name, ext))

    def generate_json_file(self):
        results_json = self.poll.zeus.get_results()
        jsonfile = file(self.get_poll_result_file_path('json', 'json'), 'w')
        json.dump(results_json, jsonfile)
        jsonfile.close()

    def generate_csv_file(self, lang):
        csvfile = file(self.get_poll_result_file_path('csv', 'csv', lang[0]), "w")
        if self.module_id == "score":
            csv_from_score_polls(self.election, [self.poll], lang[0], csvfile)
        elif self.module_id == "stv":
            csv_from_stv_polls(self.election, [self.poll], lang[0], csvfile)
        else:
            csv_from_polls(self.election, [self.poll], lang[0], csvfile)
        csvfile.close()

    def generate_election_csv_file(self, lang):
        csvpath = self.get_election_result_file_path('csv', 'csv', lang[0])
        csvfile = file(self.get_election_result_file_path('csv', 'csv', lang[0]), "w")
        if self.module_id == "score":
            csv_from_score_polls(self.election, self.election.polls.all(),\
                lang[0], csvfile)
        elif self.module_id == "stv":
            csv_from_stv_polls(self.election, self.election.polls.all(),\
                               lang[0], csvfile)
        else:
            csv_from_polls(self.election, self.election.polls.all(),\
                           lang[0], csvfile)
        csvfile.close()

    def generate_election_zip_file(self, lang):
        zippath = self.get_election_result_file_path('zip', 'zip', lang[0])
        all_docs_zip = zipfile.ZipFile(zippath, 'w')

        election_csvpath = self.get_election_result_file_path('csv', 'csv',
                                                              lang[0])
        if not os.path.exists(election_csvpath):
            self.generate_electon_csv_file(lang)
        basename = os.path.basename(election_csvpath)
        all_docs_zip.write(election_csvpath, basename)
        if self.module_id !='score':
            election_pdfpath = self.get_election_result_file_path('pdf', 'pdf',
                                                                  lang[0])
            if not os.path.exists(election_pdfpath):
                module.generate_election_result_docs(lang)
            basename = os.path.basename(election_pdfpath)
            all_docs_zip.write(election_pdfpath, basename)

        poll_docpaths = []
        for poll in self.election.polls.all():
            module = poll.get_module()
            poll_csvpath = module.get_poll_result_file_path('csv', 'csv', lang[0])
            poll_docpaths.append(poll_csvpath)
            if not os.path.exists(poll_csvpath):
                module.generate_csv_file(lang)
            poll_jsonpath = module.get_poll_result_file_path('json', 'json')
            poll_docpaths.append(poll_jsonpath)
            if not os.path.exists(poll_jsonpath):
                module.generate_json_file()
            poll_docpaths.append(poll_jsonpath)
            if module.module_id !='score':
                poll_pdfpath = module.get_poll_result_file_path('pdf', 'pdf', lang[0])
                poll_docpaths.append(poll_pdfpath)
                if not os.path.exists(poll_pdfpath):
                    module.generate_result_docs(lang)
        poll_docpaths = set(poll_docpaths)
        for path in poll_docpaths:
            basename = os.path.basename(path)
            all_docs_zip.write(path, basename)
        
        all_docs_zip.close()

    def generate_result_docs(self, lang):
        from zeus.results_report import build_doc
        results_name = self.election.name
        score = self.election.election_module == "score"
        parties = self.election.election_module == "parties"
        poll = self.poll
        build_doc(_(u'Results'), self.election.name,
                      self.election.institution.name,
                      self.election.voting_starts_at, self.election.voting_ends_at,
                      self.election.voting_extended_until,
                      [(poll.name,
                        poll.zeus.get_results(),
                        poll.questions_data,
                        poll.questions[0]['answers'],
                        poll.voters.all())],
                      lang,
                      self.get_poll_result_file_path('pdf', 'pdf', lang[0]),
                      score=score, parties=parties)
    
    def generate_election_result_docs(self, lang):
        from zeus.results_report import build_doc
        pdfpath = self.get_election_result_file_path('pdf', 'pdf', lang[0])
        polls_data = []
        score = self.election.election_module == "score"
        parties = self.election.election_module == "parties"

        for poll in self.election.polls.filter():
            polls_data.append((poll.name, 
                               poll.zeus.get_results(),
                               poll.questions_data,
                               poll.questions[0]['answers'],
                               poll.voters.all()))

        build_doc(_(u'Results'), self.election.name, self.election.institution.name,
                self.election.voting_starts_at, self.election.voting_ends_at,
                self.election.voting_extended_until,
                polls_data,
                lang,
                pdfpath, score=score, parties=score)


from zeus.election_modules.simple import *
from zeus.election_modules.parties import *
from zeus.election_modules.score import *
from zeus.election_modules.stv import *
