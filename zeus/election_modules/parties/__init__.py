from django.utils.translation import ugettext_lazy as _

from zeus.election_modules import ElectionModuleBase, election_module


@election_module
class PartiesListElection(ElectionModuleBase):

    module_id = 'parties'
    description = _('Party lists election')
    messages = {}
    auto_append_answer = True
    count_empty_question = True

    def questions_update_view(self, request):
        raise NotImplemented

    def calculate_results(self, request):
        raise NotImplemented

    def get_booth_template(self, request):
        raise NotImplemented

    def update_questions(self):
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
                if self.type_params.get('count_empty_question', False):
                    params_min = 0
                params = "%d-%d, %d" % (params_min, params_max, group)
                q_answers.insert(0, "%s: %s" % (q['question'], params))
            answers = answers + q_answers
        self.poll._init_questions(len(answers))
        self.poll.questions[0]['answers'] = answers
