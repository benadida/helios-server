from django.utils.translation import ugettext_lazy as _
from django.forms.formsets import formset_factory
from django.http import HttpResponseRedirect

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

                    answers = [x[1] for x in sorted_answers]
                    question['answers'] = answers
                    for k in question.keys():
                        if k in ['DELETE', 'ORDER']:
                            del question[k]

                    question['scores'] = filter(lambda p: p is not None, question['scores'])
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
        tpl = 'election_modules/simple/election_poll_questions_manage'
        return render_template(request, tpl, context)

    def update_answers(self):
        answers = []
        questions_data = self.poll.questions_data or []
        prepend_empty_answer = True

        if self.auto_append_answer:
            prepend_empty_answer = True

        for index, q in enumerate(questions_data):

            import pdb; pdb.set_trace()
            maxsize = max(len(q['answers']), len(q['scores']))
            sparelist = q['answers'] if len(q['scores']) == maxsize else q['scores']
            for i in range(len(sparelist), maxsize):
                sparelist.append(None)

            q_answers = []
            for answer, score in zip(q['answers'], q['scores']):
                if answer is not None:
                    q_answers.append("%s: %s" % (q['question'], answer))
                if score is not None:
                    q_answers.append(score)
            answers = answers + q_answers
        
        q['scores'] = filter(lambda p: p is not None, q['scores'])
        q['answers'] = filter(lambda p: p is not None, q['answers'])

        self.poll._init_questions(len(answers))
        self.poll.questions[0]['answers'] = answers

    def calculate_results(self, request):
        raise NotImplemented

    def get_booth_template(self, request):
        raise NotImplemented

