#!/usr/bin/python
# -*- coding: utf-8 -*-

import copy
import json
import os
import datetime
try:
    from django.utils.translation import ugettext as _
except ImportError:
    def _(x):
        return x

from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.platypus import Spacer, Image, PageBreak
from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfdoc
from django.conf import settings
from django.utils import translation
from django.utils.translation import ugettext as _

from zeus.core import PARTY_SEPARATOR
from stv.parser import STVParser


PAGE_WIDTH, PAGE_HEIGHT = A4

pageinfo = _("Zeus Elections - Poll Results")

default_path = '/usr/share/fonts/truetype/linux-libertine/LinLibertine_Re.ttf'
linlibertine = TTFont('LinLibertine',
#                      '/Users/Panos/Library/Fonts/LinLibertine_Rah.ttf')
                      getattr(settings, 'ZEUS_RESULTS_FONT_REGULAR_PATH', default_path))
pdfmetrics.registerFont(linlibertine)

default_path = '/usr/share/fonts/truetype/linux-libertine/LinLibertine_Bd.ttf'
linlibertineb = TTFont('LinLibertineBd',
#                       '/Users/Panos/Library/Fonts/LinLibertine_RBah.ttf')
                        getattr(settings, 'ZEUS_RESULTS_FONT_BOLD_PATH', default_path))
pdfmetrics.registerFont(linlibertineb)

ZEUS_LOGO = os.path.join(os.path.abspath(os.path.dirname(__file__)),
                         'logo-positive.jpg')

def load_results(data, repr_data, qdata):
    qdata = copy.deepcopy(qdata)
    parties_results = []
    candidates_results = {}
    total_votes = 0
    blank_votes = 0
    parties_indexes = {}
    candidates_indexes = {}

    index = 0
    for qi, q in enumerate(repr_data):
        parties_indexes[index] = q['question']
        qdata[index] = qdata[index].split(PARTY_SEPARATOR, 1)[0]
        index = index + 1
        for ai, a in enumerate(q['answers']):
            candidates_indexes[index] = a
            index = index + 1

    if isinstance(data, basestring):
        jsondata = json.loads(data)
    else:
        jsondata = data
    for result, party in jsondata['party_counts']:
        party = parties_indexes[qdata.index(party)]
        parties_results.append((party, result))
        total_votes += result

    blank_votes = jsondata['blank_count']
    total_votes = jsondata['ballot_count']

    for candidate_result in jsondata['candidate_counts']:
        (result, full_candidate) = candidate_result
        (party, candidate) = full_candidate.split(PARTY_SEPARATOR, 1)
        party = parties_indexes[qdata.index(party)]
        candidate = candidates_indexes[qdata.index(full_candidate)]

        if party in candidates_results:
            candidates_results[party].append((candidate, result))
        else:
            candidates_results[party] = [(candidate, result)]
    return (total_votes, blank_votes, parties_results, candidates_results)


def load_parties_results(data, repr_data, qdata):
    qdata = copy.deepcopy(qdata)
    parties_results = []
    candidates_results = {}
    total_votes = 0
    blank_votes = 0
    parties_indexes = {}
    candidates_indexes = {}
    if isinstance(data, basestring):
        jsondata = json.loads(data)
    else:
        jsondata = data
    for result, party in jsondata['party_counts']:
        parties_results.append((party, result))
        total_votes += result

    blank_votes = jsondata['blank_count']
    total_votes += blank_votes

    index = 0
    for qi, q in enumerate(repr_data):
        parties_indexes[index] = q['question']
        qdata[index] = qdata[index].split(PARTY_SEPARATOR, 1)[0]
        index = index + 1
        for ai, a in enumerate(q['answers']):
            candidates_indexes[index] = a
            index = index + 1

    for candidate_result in jsondata['candidate_counts']:
        (result, full_candidate) = candidate_result
        (party, candidate) = full_candidate.split(PARTY_SEPARATOR, 1)
        party = parties_indexes[qdata.index(party)]
        candidate = candidates_indexes[qdata.index(full_candidate)]
        if party in candidates_results:
            candidates_results[party].append((candidate, result))
        else:
            candidates_results[party] = [(candidate, result)]
    return (total_votes, blank_votes, parties_results, candidates_results)


def load_score_results(data, repr_data, qdata):
    parties_results = []
    candidates_results = {}
    if isinstance(data, basestring):
        jsondata = json.loads(data)
    else:
        jsondata = data

    parties_results = [('', len(jsondata['ballots']))]
    total_votes = len(jsondata['ballots'])
    blank_votes = len([b for b in jsondata['ballots'] if not b['candidates']])
    candidates_results = {'': [(c.replace("{newline}", " "), t) for t, c in jsondata['totals']]} 
    return (total_votes, blank_votes, parties_results, candidates_results)


def make_first_page_hf(canvas, doc):
    canvas.saveState()
    canvas.drawImage(ZEUS_LOGO,
                     x = PAGE_WIDTH - 5 * cm,
                     y = PAGE_HEIGHT - 2 * cm,
                     width = PAGE_WIDTH / 8,
                     height = 1.1 * cm)
    canvas.restoreState()

def make_later_pages_hf(canvas, doc):
    canvas.saveState()
    canvas.setFont('LinLibertine',9)
    canvas.drawImage(ZEUS_LOGO,
                     x = 2 * cm,
                     y = PAGE_HEIGHT - 2 * cm,
                     width = PAGE_WIDTH / 8,
                     height = 1.1 * cm)
    canvas.drawString(PAGE_WIDTH - 9 * cm, PAGE_HEIGHT - 2 * cm,
                      "%s" % (pageinfo, ))
    canvas.restoreState()


def make_heading(elements, styles, contents):
    for x in range(0, 5):
        elements.append(Spacer(1, 12))
    for pcontent in contents:
        elements.append(Paragraph(escape(pcontent), styles["ZeusHeading"]))

def make_subheading(elements, styles, contents):
    for pcontent in contents:
        elements.append(Paragraph(escape(pcontent), styles["ZeusSubHeading"]))
    elements.append(Spacer(1, 12))

def make_intro(elements, styles, contents):
    for pcontent in contents:
        elements.append(Paragraph(escape(pcontent), styles["Zeus"]))
    elements.append(Spacer(1, 12))

def make_totals(elements, styles, total_votes, blank_votes):
    elements.append(Paragraph(escape(_('Total votes: %d') % total_votes), styles['Zeus']))
    elements.append(Paragraph(escape(_('Blank: %d') % blank_votes), styles['Zeus']))
    elements.append(Spacer(1, 12))

def make_party_list_heading(elements, styles, party, count):
    heading = '%(title)s: %(count)d' % {'title': party,
                                        'count': count}
    elements.append(Paragraph(escape(heading), styles['Zeus']))
    elements.append(Spacer(1, 12))

def make_party_list_table(elements, styles, party_results):

    table_style = TableStyle([('FONT', (0, 0), (-1, -1), 'LinLibertine')])
    t = Table(party_results, style = table_style)
    elements.append(t)

def make_results(elements, styles, total_votes, blank_votes,
                 parties_results, candidates_results):

    make_totals(elements, styles, total_votes, blank_votes)
    for party_result in parties_results:
        (party, count) = party_result
        if (len(parties_results) > 1):
            make_party_list_heading(elements, styles, party, count)
        if party in candidates_results:
            make_party_list_table(elements, styles, candidates_results[party])

def build_stv_doc(title, name, institution_name, voting_start, voting_end,
              extended_until, data, language, filename="election_results.pdf", new_page=True):
    with translation.override(language[0]):
        title = _('Results')
        DATE_FMT = "%d/%m/%Y %H:%S"
        if isinstance(voting_start, datetime.datetime):
            voting_start = _('Start: %(date)s') % {'date':
            voting_start.strftime(DATE_FMT)}

        if isinstance(voting_end, datetime.datetime):
            voting_end = _('End: %(date)s') % {'date':
            voting_end.strftime(DATE_FMT)}

        if extended_until and isinstance(extended_until, datetime.datetime):
            extended_until = _('Extension: %(date)s') % {'date':
            extended_until.strftime(DATE_FMT)}
        else:
            extended_until = ""

        if not isinstance(data, list):
            data = [(name, data)]

        # reset pdfdoc timestamp in order to force a fresh one to be used in
        # pdf document metadata.
        pdfdoc._NOWT = None

        elements = []

        doc = SimpleDocTemplate(filename, pagesize=A4)

        styles = getSampleStyleSheet()
        styles.add(ParagraphStyle(name='Zeus',
                                  fontName='LinLibertine',
                                  fontSize=12,
                                  leading=16,
                                  alignment=TA_JUSTIFY))

        styles.add(ParagraphStyle(name='ZeusSubHeading',
                                  fontName='LinLibertineBd',
                                  fontSize=14,
                                  alignment=TA_JUSTIFY,
                                  spaceAfter=16))

        styles.add(ParagraphStyle(name='ZeusHeading',
                                  fontName='LinLibertineBd',
                                  fontSize=16,
                                  alignment=TA_CENTER,
                                  spaceAfter=16))
        intro_contents = [
            voting_start,
            voting_end,
            extended_until
        ]

        make_heading(elements, styles, [title, name, institution_name])
        make_intro(elements, styles, intro_contents)

        for poll_name, poll_results, questions in data:
            poll_intro_contents = [
                poll_name
            ]
            parties_results = []
            candidates_results = {}

            #total_votes, blank_votes, parties_results, candidates_results = \
            #    load_results(poll_results)
            if new_page:
                elements.append(PageBreak())
            elements.append(Spacer(1, 12))
            elements.append(Spacer(1, 12))
            elements.append(Spacer(1, 12))
            make_subheading(elements, styles, poll_intro_contents)
            elements.append(Spacer(1, 12))
            make_intro(elements, styles, intro_contents)
            elements.append(Spacer(1, 12))
            #make dict with indexing as key and name as value
            counter = 0
            indexed_cands = {}
            for item in questions[0]['answers']:
                indexed_cands[str(counter)] = item
                counter += 1
            elected = [[_('Elected')]]
            json_data = poll_results[0]
            for item in json_data:
                elected.append([indexed_cands[item[0]]])
            t = Table(elected)
            my_table_style = TableStyle([('FONT', (0, 0), (-1, -1),'LinLibertine'),
                                         ('ALIGN',(1,1),(-2,-2),'LEFT'),
                                         ('INNERGRID', (0,0), (-1,-1), 0.25, colors.black),
                                         ('BOX', (0,0), (-1,-1), 0.25, colors.black),
                                         ])
            t.setStyle(my_table_style)
            elements.append(t)

            actions_desc = {
                'elect': _('Elect'),
                'eliminate': _('Eliminated'),
                'quota': _('Eliminated due to quota restriction')}

            table_header = [_('Candidate'), _('Votes'), _('Draw'), _('Action')]

            stv = STVParser(poll_results[2])
            rounds = list(stv.rounds())

            for num, round in rounds:
                round_name = _('Round ')
                round_name += str(num)
                elements.append(Paragraph(round_name,styles['Zeus']))
                round_table = []
                temp_table = []
                temp_table.append(table_header)
                for name, cand in round['candidates'].iteritems():
                    actions = map(lambda x: x[0], cand['actions'])
                    draw = _("NO")
                    if 'random' in actions:
                        draw = _("YES")
                    action = None
                    if len(actions):
                        action = actions_desc.get(actions[-1])
                    votes = cand['votes']
                    cand_name = indexed_cands[str(name)]
                    cand_name = cand_name.split(':')[0]
                    row = [cand_name, votes, draw, action]
                    temp_table.append(row)
                round_table = Table(temp_table)
                round_table.setStyle(my_table_style)
                elements.append(round_table)
                elements.append(Spacer(1, 12))

        doc.build(elements, onFirstPage = make_first_page_hf,
                  onLaterPages = make_later_pages_hf)


def build_doc(title, name, institution_name, voting_start, voting_end,
              extended_until, data, language, filename="election_results.pdf",
              new_page=True, score=False, parties=False):
    with translation.override(language[0]):
        title = _('Results')
        DATE_FMT = "%d/%m/%Y %H:%S"
        if isinstance(voting_start, datetime.datetime):
            voting_start = _('Start: %(date)s') % {'date':
            voting_start.strftime(DATE_FMT)}

        if isinstance(voting_end, datetime.datetime):
            voting_end = _('End: %(date)s') % {'date':
            voting_end.strftime(DATE_FMT)}

        if extended_until and isinstance(extended_until, datetime.datetime):
            extended_until = _('Extension: %(date)s') % {'date':
            extended_until.strftime(DATE_FMT)}
        else:
            extended_until = ""


        if not isinstance(data, list):
            data = [(name, data)]

        # reset pdfdoc timestamp in order to force a fresh one to be used in
        # pdf document metadata.
        pdfdoc._NOWT = None

        elements = []

        doc = SimpleDocTemplate(filename, pagesize=A4)

        styles = getSampleStyleSheet()
        styles.add(ParagraphStyle(name='Zeus',
                                  fontName='LinLibertine',
                                  fontSize=12,
                                  leading=16,
                                  alignment=TA_JUSTIFY))

        styles.add(ParagraphStyle(name='ZeusSubHeading',
                                  fontName='LinLibertineBd',
                                  fontSize=14,
                                  alignment=TA_JUSTIFY,
                                  spaceAfter=16))

        styles.add(ParagraphStyle(name='ZeusHeading',
                                  fontName='LinLibertineBd',
                                  fontSize=16,
                                  alignment=TA_CENTER,
                                  spaceAfter=16))
        intro_contents = [
            voting_start,
            voting_end,
            extended_until
        ]

        make_heading(elements, styles, [title, name, institution_name])
        make_intro(elements, styles, intro_contents)

        for poll_name, poll_results, q_repr_data, qdata in data:
            poll_intro_contents = [
                poll_name
            ]
            parties_results = []
            candidates_results = {}

            load_results_fn = load_results
            if score:
                load_results_fn = load_score_results
            if parties:
                load_results_fn = load_parties_results

            total_votes, blank_votes, parties_results, candidates_results = \
                load_results_fn(poll_results, q_repr_data, qdata)

            if new_page:
                elements.append(PageBreak())
            elements.append(Spacer(1, 12))
            elements.append(Spacer(1, 12))
            elements.append(Spacer(1, 12))
            make_subheading(elements, styles, poll_intro_contents)
            elements.append(Spacer(1, 12))
            make_intro(elements, styles, intro_contents)
            elements.append(Spacer(1, 12))
            make_results(elements, styles, total_votes, blank_votes,
                         parties_results, candidates_results)

        doc.build(elements, onFirstPage = make_first_page_hf,
                  onLaterPages = make_later_pages_hf)


def main():
    import sys
    title = 'Αποτελέσματα'
    name = 'Εκλογές ΠΟΣΔΕΠ'
    institution_name = 'Οικονομικό Πανεπιστήμιο Αθηνών'
    voting_start = 'Έναρξη: 21/1/2013 9:00'
    voting_end = 'Λήξη: 21/1/2013 17:00'
    extended_until = 'Παράταση: 21/1/2013 18:00'

    build_doc(title, name, institution_name, voting_start, voting_end,
              extended_until, file(sys.argv[1]).read())


if __name__ == "__main__":
    main()
