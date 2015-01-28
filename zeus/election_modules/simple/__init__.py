import os
import json
import zipfile

from django.utils.translation import ugettext_lazy as _
from django.forms.formsets import formset_factory
from django.forms import ValidationError
from django.http import HttpResponseRedirect
from django.conf import settings

from zeus.election_modules import ElectionModuleBase, election_module
from zeus.views.utils import set_menu

from helios.view_utils import render_template


@election_module
class SimpleElection(ElectionModuleBase):

    module_id = 'simple'
    description = _('Simple election with one or more questions')
    messages = {}
    auto_append_answer = True
    count_empty_question = False
    booth_questions_tpl = ''
    no_questions_added_message = _('No questions set')
    manage_questions_title = _('Manage questions')

    def extract_question_data(self, questions):
        questions_data = []
        for question in questions:
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
        return questions_data

    def questions_formset(self, extra=1):
        from zeus.forms import QuestionForm
        return formset_factory(QuestionForm, extra=extra,
                               can_delete=True, can_order=True)

    def questions_update_view(self, request, election, poll):
        from zeus.utils import poll_reverse
        from zeus.forms import QuestionForm, DEFAULT_ANSWERS_COUNT, \
                MAX_QUESTIONS_LIMIT

        extra = 1
        if poll.questions_data:
            extra = 0

        questions_formset = self.questions_formset(extra)
        if request.method == 'POST':
            formset = questions_formset(request.POST)
            if formset.is_valid():
                cleaned_data = formset.cleaned_data
                questions_data = self.extract_question_data(cleaned_data)

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
        tpl = 'election_modules/simple/election_poll_questions_manage'
        return render_template(request, tpl, context)

    def update_answers(self):
        answers = []
        questions_data = self.poll.questions_data or []
        prepend_empty_answer = True

        if self.auto_append_answer:
            prepend_empty_answer = True

        for index, q in enumerate(questions_data):
            question = q['question'].replace(":", "{semi}") \
                                    .replace("\r\n","{newline}") \
                                    .replace("\n","{newline}")
            q_answers = ["%s: %s" % (question, ans) for ans in \
                         q['answers']]
            group = 0
            if prepend_empty_answer:
                params_max = int(q['max_answers'])
                params_min = int(q['min_answers'])
                if self.count_empty_question:
                    params_min = 0
                params = "%d-%d, %d" % (params_min, params_max, group)
                q_answers.insert(0, "%s: %s" % (question, params))
            answers = answers + q_answers
        self.poll._init_questions(len(answers))
        self.poll.questions[0]['answers'] = answers
    
    def compute_results(self):
        self.generate_json_file()
        for lang in settings.LANGUAGES:
            self.generate_csv_file(lang)
            self.generate_result_docs(lang)

    def compute_election_results(self):
        for lang in settings.LANGUAGES:
            self.generate_election_csv_file(lang)   
            self.generate_election_result_docs(lang)
            self.generate_election_zip_file(lang)

    def get_booth_template(self, request):
        raise NotImplemented
