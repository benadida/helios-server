# -*- coding: utf-8 -*-

import json

from django.test import TestCase
from django.core.urlresolvers import reverse


class TestSTVCountView(TestCase):

    def setUp(self):
        self.url = reverse('stv_count')
        self.form_url = self.url + "?form=1"
        super(TestSTVCountView, self).setUp()

    def test_subviews(self):
        resp = self.client.get(self.url)
        assert "Choose a file and press submit" in resp.content

        resp = self.client.get(self.form_url)
        assert "STV ballot box import form" in resp.content

    def test_submit_form(self):
        data = {
            "name": u"Όνομα ψηφοφορίας",
            "institution": "Institution name",
        }
        resp = self.client.post(self.form_url, data)
        form = resp.context['form']
        assert 'eligibles_count' in form.errors

        data['voting_starts'] = "42142141"
        data['voting_ends'] = "25/12/2015 07:33 "
        resp = self.client.post(self.form_url)
        form = resp.context['form']
        assert resp.status_code is 200
        assert 'voting_starts' in form.errors
        assert 'voting_ends' in form.errors
        assert resp.context['ballots_form'] is None

        CANDIDATES = u"""
        NAMEA, SURNAMEA, FATHERNAMEA, SCHOOLA
        ΟΝΟΜΑ2, ΕΠΩΝΥΜΟ2, ΠΑΤΡΩΝΥΜΟ2, ΣχολήΒ
        ΟΝΟΜΑ3, ΕΠΩΝΥΜΟ3, ΠΑΤΡΩΝΥΜΟ3, SCHOOLA
        ΟΝΟΜΑ4, ΕΠΩΝΥΜΟ4, ΠΑΤΡΩΝΥΜΟ4, SCHOOLA
        """
        data.update({
            'voting_starts': '25/12/2014 05:03',
            'voting_ends': '25/12/2014 19:03',
            'candidates': CANDIDATES,
            'eligibles_count': '3',
            'has_limit': 'on',
            'ballots_count': '4'
        })

        resp = self.client.post(self.form_url, data)
        assert resp.status_code == 200
        assert resp.context['form'].errors == {}
        assert resp.context['form'].cleaned_data.get('has_limit') is True
        assert resp.context['ballots_form'] is not None

        data['submit_ballots'] = "1"
        data['form-TOTAL_FORMS'] = "4"
        data['form-INITIAL_FORMS'] = "0"
        data['form-MAX_NUM_FORMS'] = "4"

        choices = [[0, 2], [0, 2], [3, 2]]
        for i, choice in enumerate(choices):
            for j, cand in enumerate(choice):
                data['form-%d-choice_%d' % (i, j + 1)] = str(cand)

        data['form-3-choice_1'] = ''
        data['form-3-choice_2'] = ''

        data['form-0-choice_2'] = '0'
        resp = self.client.post(self.form_url, data)
        assert resp.context['ballots_form'].is_valid() is False
        assert '__all__' in resp.context['ballots_form'].errors[0]

        data['form-0-choice_2'] = '2'
        resp = self.client.post(self.form_url, data, follow=True)
        assert "Ballot counting is completed" in resp.content
        assert "download=pdf" in resp.content
        assert "download=json" in resp.content

        json_data = self.client.get(self.url + "?download=json").content
        data = json.loads(json_data, encoding='utf8')
        assert u"ΟΝΟΜΑ2" in json_data.decode('utf8')
