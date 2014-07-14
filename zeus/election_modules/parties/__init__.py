import json

from django.utils.translation import ugettext_lazy as _
from django.forms.formsets import formset_factory
from django.forms import ValidationError
from django.http import HttpResponseRedirect
from django.conf import settings

from zeus.election_modules import ElectionModuleBase, election_module
from zeus.views.utils import set_menu

from helios.view_utils import render_template


@election_module
class PartiesListElection(ElectionModuleBase):

    module_id = 'parties'
    description = _('Party lists election')
    messages = {
        'answer_title': _('Candidate'),
        'question_title': _('Party'),
    }
    auto_append_answer = True
    count_empty_question = True

    def questions_update_view(self, request, election, poll):
        from zeus.utils import poll_reverse
        from zeus.forms import PartyForm, DEFAULT_ANSWERS_COUNT, \
                MAX_QUESTIONS_LIMIT

        extra = 1
        if poll.questions_data:
            extra = 0

        questions_formset = formset_factory(PartyForm, extra=extra,
                                            can_delete=True, can_order=True)
        if request.method == 'POST':
            formset = questions_formset(request.POST)
            if formset.is_valid():
                questions_data = []
                for question in formset.cleaned_data:
                    if not question:
                        continue

                    # force sort of answers by extracting index from answer key.
                    # cast answer index to integer, otherwise answer_10 would
                    # be placed before answer_2
                    answer_index = lambda a: int(a[0].replace('answer_', ''))
                    isanswer = lambda a: a[0].startswith('answer_')
                    answer_values = filter(isanswer, question.iteritems())
                    sorted_answers = sorted(answer_values, key=answer_index)

                    answers = [x[1] for x in sorted_answers]
                    question['answers'] = answers
                    for k in question.keys():
                        if k in ['DELETE', 'ORDER']:
                            del question[k]

                    questions_data.append(question)

                poll.questions_data = questions_data
                poll.update_answers()
                poll.logger.info("Poll ballot updated")
                poll.save()

                url = poll_reverse(poll, 'questions')
                return HttpResponseRedirect(url)
        else:
            formset = questions_formset(initial=poll.questions_data)

        context = {
            'default_answers_count': DEFAULT_ANSWERS_COUNT,
            'formset': formset,
            'max_questions_limit': MAX_QUESTIONS_LIMIT,
            'election': election,
            'poll': poll,
            'module': self
        }
        set_menu('questions', context)
        tpl = 'election_modules/parties/election_poll_questions_manage'
        return render_template(request, tpl, context)

    def generate_result_docs(self, lang):
        from zeus.results_report import build_doc
        results_json = self.poll.zeus.get_results()
        results_name = self.election.name
        build_doc(_(u'Results'), self.election.name,
                    self.election.institution.name,
                    self.election.voting_starts_at, self.election.voting_ends_at,
                    self.election.voting_extended_until,
                    [(self.election.name, json.dumps(results_json))],
                    lang,
                    self.get_result_file_path('pdf', 'pdf', lang[0]))

    def compute_results(self):
        self.generate_json_file()
        for lang in settings.LANGUAGES:
            self.generate_csv_file(lang)
            self.generate_result_docs(lang)

    def get_booth_template(self, request):
        raise NotImplemented

    def update_answers(self):
        answers = []
        questions_data = self.poll.questions_data or []
        prepend_empty_answer = True

        if self.auto_append_answer:
            prepend_empty_answer = True

        for index, q in enumerate(questions_data):
            q_answers = ["%s: %s" % (q['question'], ans) for ans in \
                         q['answers']]
            group = index
            if prepend_empty_answer:
                params_max = int(q['max_answers'])
                params_min = int(q['min_answers'])
                if self.count_empty_question:
                    params_min = 0
                params = "%d-%d, %d" % (params_min, params_max, group)
                q_answers.insert(0, "%s: %s" % (q['question'], params))
            answers = answers + q_answers
        self.poll._init_questions(len(answers))
        self.poll.questions[0]['answers'] = answers

