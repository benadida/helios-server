import json
import logging
import StringIO

from django.utils.translation import ugettext_lazy as _
from django.forms.formsets import formset_factory
from django.forms import ValidationError
from django.http import HttpResponseRedirect

from zeus.election_modules import ElectionModuleBase, election_module
from zeus.views.utils import set_menu

from helios.view_utils import render_template
from stv.stv import count_stv, Ballot
from zeus.core import gamma_decode, to_absolute_answers


@election_module
class StvElection(ElectionModuleBase):
    module_id = 'stv'
    description = _('Single transferable vote election')
    messages = {
        'answer_title': _('Candidate'),
        'question_title': _('Candidates List')
    }
    auto_append_answer = True
    count_empty_question = False
    booth_questions_tpl = 'question_ecounting'
    no_questions_added_message = _('No questions set')
    module_params = {
        'ranked': True
    }

    results_template = "election_modules/stv/results.html"

    pdf_result = False
    csv_result = False
    json_result = True

    def questions_update_view(self, request, election, poll):
        from zeus.utils import poll_reverse
        from zeus.forms import StvForm, DEFAULT_ANSWERS_COUNT, \
                MAX_QUESTIONS_LIMIT

        if not poll.questions_data:
            poll.questions_data = [{}]

        poll.questions_data[0]['departments_data'] = election.departments
        initial = poll.questions_data

        extra = 1
        if poll.questions_data:
            extra = 0

        questions_formset = formset_factory(StvForm, extra=extra,
                                            can_delete=True, can_order=True)


        if request.method == 'POST':
            formset = questions_formset(request.POST, initial=initial)
            
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

                    answers = [json.loads(x[1])[0] for x in sorted_answers]
                    departments = [json.loads(x[1])[1] for x in sorted_answers]

                    final_answers = []
                    for a,d in zip(answers, departments):
                        final_answers.append(a+':'+d)
                    question['answers'] = final_answers
                    for k in question.keys():
                        if k in ['DELETE', 'ORDER']:
                            del question[k]

                    questions_data.append(question)

                poll.questions_data = questions_data
                poll.update_answers()
                poll.logger.info("Poll ballot updated")
                poll.eligibles_count = int(formset.cleaned_data[0]['eligibles'])
                poll.has_department_limit = formset.cleaned_data[0]['department_limit']
                poll.save()

                url = poll_reverse(poll, 'questions')
                return HttpResponseRedirect(url)
        else:
            formset = questions_formset(initial=initial)

        context = {
            'default_answers_count': DEFAULT_ANSWERS_COUNT,
            'formset': formset,
            'max_questions_limit': 1,
            'election': election,
            'poll': poll,
            'module': self
        }
        set_menu('questions', context)

        tpl = 'election_modules/stv/election_poll_questions_manage'
        return render_template(request, tpl, context)

    def update_answers(self):
        answers = []
        questions_data = self.poll.questions_data or []
        prepend_empty_answer = True
        if self.auto_append_answer:
            prepend_empty_answer = True
        for index, q in enumerate(questions_data):
            q_answers = ["%s" % (ans) for ans in \
                         q['answers']]
            group = index
            if prepend_empty_answer:
                #remove params and q questions
                params_max = len(q_answers)
                params_min = 0
                if self.count_empty_question:
                    params_min = 0
                params = "%d-%d, %d" % (params_min, params_max, group)
                q_answers.insert(0, "%s: %s" % (q.get('question'), params))
            answers = answers + q_answers
        answers = questions_data[0]['answers']
        self.poll._init_questions(len(answers))
        self.poll.questions[0]['answers'] = answers

    def compute_results(self):
        cands_data = self.poll.questions_data[0]['answers']
        cands_count =  len(cands_data)
        constituencies = {}
        count_id = 0

        for item in cands_data:
            cand_and_dep = item.split(':')
            constituencies[str(count_id)] = cand_and_dep[1]
            count_id += 1

        seats = self.poll.eligibles_count
        droop = False
        rnd_gen = None # TODO: should be generated and stored on poll freeze
        quota_limit = 0 
        if self.poll.has_department_limit:
            quota_limit = 2 #FIXME (not sure if 2 is correct)
        ballots_data = self.poll.result[0]
        ballots = []
        for ballot in ballots_data:
            if not ballot:
                continue
            ballot = to_absolute_answers(gamma_decode(ballot, cands_count,cands_count),
                                         cands_count)
            ballot = [str(i) for i in ballot]
            ballots.append(Ballot(ballot))

        stv_stream = StringIO.StringIO()
        stv_logger = logging.Logger(self.poll.uuid)
        handler = logging.StreamHandler(stv_stream)
        stv_logger.addHandler(handler)
        stv_logger.setLevel(logging.DEBUG)
        results = count_stv(ballots, seats, droop, constituencies, quota_limit,
                            rnd_gen, logger=stv_logger)
        results = list(results)
        handler.close()
        stv_stream.seek(0)
        results.append(stv_stream.read())
        stv_stream.close()
        self.poll.stv_results = json.dumps(results)
        self.poll.save()

        # build docs
        self.poll.generate_result_docs()

    def get_booth_template(self, request):
        raise NotImplemented
