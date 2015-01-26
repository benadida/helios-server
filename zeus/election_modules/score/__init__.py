import zipfile
import os
from itertools import izip_longest

from django.utils.translation import ugettext_lazy as _
from django.forms.formsets import formset_factory
from django.http import HttpResponseRedirect
from django.conf import settings

from zeus.election_modules import ElectionModuleBase, election_module
from zeus.views.utils import set_menu
from helios.view_utils import render_template



@election_module
class ScoreBallotElection(ElectionModuleBase):

    module_id = 'score'
    description = _('Score voting election')
    messages = {}
    auto_append_answer = True
    count_empty_question = False
    results_template = "election_modules/score/results.html"
    manage_questions_title = _('Manage questions')
    csv_result = True
    pdf_result = False

    module_params = {
        'all_scores_required': True
    }

    messages = {
        'invalid_scores_selection': _('Please assign the remaining choices: {0}')
    }

    def questions_update_view(self, request, election, poll):
        from zeus.utils import poll_reverse
        from zeus.forms import ScoresForm, DEFAULT_ANSWERS_COUNT, \
                MAX_QUESTIONS_LIMIT

        extra = 1
        if poll.questions_data:
            extra = 0

        questions_formset = formset_factory(ScoresForm, extra=extra,
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

                    question['answers'] = [x[1] for x in sorted_answers]
                    question['scores'] = filter(lambda p: p is not None, question['scores'])
                    question['question_subtitle'] = ",".join(question['scores'])

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
            'max_questions_limit': 1,
            'election': election,
            'poll': poll,
            'module': self
        }

        set_menu('questions', context)
        tpl = 'election_modules/simple/election_poll_questions_manage'
        return render_template(request, tpl, context)

    def update_answers(self):
        answers = []
        scores = []
        questions_data = self.poll.questions_data or []
        prepend_empty_answer = True

        if self.auto_append_answer:
            prepend_empty_answer = True

        for index, q in enumerate(questions_data):
            question = q['question'].replace(":", "{semi}") \
                                    .replace("\r\n","{newline}") \
                                    .replace("\n","{newline}")
            q_answers = []
            for answer in q['answers']:
                q_answers.append("%s: %s" % (question, answer))
            scores += map(lambda x: str(100 * index+int(x)), q['scores'])
            answers = answers + q_answers

        poll_answers = []
        scores = reversed(scores)
        for answer, score in izip_longest(answers, scores):
            if answer is not None:
                poll_answers.append(answer)
            if score is not None:
                poll_answers.append(score)

        self.poll._init_questions(len(poll_answers))
        self.poll.questions[0]['answers'] = poll_answers

        # save index references
        for index, q in enumerate(self.poll.questions_data):
            question = q['question'].replace(":", "{semi}") \
                                    .replace("\r\n","{newline}") \
                                    .replace("\n","{newline}")
            q['answer_indexes'] = {}
            q['score_indexes'] = {}
            for answer in q['answers']:
                q['answer_indexes'][answer] = poll_answers.index("%s: %s" % (question, answer))
            for score in q['scores']:
                q['score_indexes'][score] = poll_answers.index(str(100 * index+int(score)))

    def calculate_results(self, request):
        raise NotImplemented

    def get_booth_template(self, request):
        raise NotImplemented
    
    def compute_results(self):
        self.generate_json_file()
        for lang in settings.LANGUAGES:
            self.generate_csv_file(lang)

    def compute_election_results(self):
        for lang in settings.LANGUAGES:
            self.generate_election_csv_file(lang)
            self.generate_election_zip_file(lang)
