#!/usr/bin/python
# -*- coding: utf-8 -*-

import json
import os
import datetime

from xml.sax.saxutils import escape

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.platypus import Spacer, Image, PageBreak
from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfdoc

from zeus.core import PARTY_SEPARATOR

PAGE_WIDTH, PAGE_HEIGHT = A4

pageinfo = "Ζευς - Αποτελέσματα Ψηφοφορίας"

linlibertine = TTFont('LinLibertine',
#                      '/Users/Panos/Library/Fonts/LinLibertine_Rah.ttf')
                      '/usr/share/fonts/truetype/linux-libertine/LinLibertine_Re.ttf')
pdfmetrics.registerFont(linlibertine)

linlibertineb = TTFont('LinLibertineBd',
#                       '/Users/Panos/Library/Fonts/LinLibertine_RBah.ttf')
                       '/usr/share/fonts/truetype/linux-libertine/LinLibertine_Bd.ttf')
pdfmetrics.registerFont(linlibertineb)

ZEUS_LOGO = os.path.join(os.path.abspath(os.path.dirname(__file__)),
                         'logo-positive.jpg')
def load_results(data):
    parties_results = []
    candidates_results = {}
    total_votes = 0
    blank_votes = 0
    if isinstance(data, basestring):
        jsondata = json.loads(data)
    else:
        jsondata = data
    for result, party in jsondata['party_counts']:
        parties_results.append((party, result))
        total_votes += result

    blank_votes = jsondata['blank_count']
    total_votes += blank_votes

    for candidate_result in jsondata['candidate_counts']:
        (result, full_candidate) = candidate_result
        (party, candidate) = full_candidate.split(PARTY_SEPARATOR, 1)
        if party in candidates_results:
            candidates_results[party].append((candidate, result))
        else:
            candidates_results[party] = [(candidate, result)]
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
    canvas.drawString(PAGE_WIDTH - 7 * cm, PAGE_HEIGHT - 2 * cm,
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
    elements.append(Paragraph(escape('Σύνολο ψήφων: %d' % total_votes), styles['Zeus']))
    elements.append(Paragraph(escape('Λευκά: %d' % blank_votes), styles['Zeus']))
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


def build_doc(title, name, institution_name, voting_start, voting_end,
              extended_until, data, filename="election_results.pdf",
              new_page=True):


    DATE_FMT = "%d/%m/%Y %H:%S"
    if isinstance(voting_start, datetime.datetime):
        voting_start = 'Έναρξη: %s' % (voting_start.strftime(DATE_FMT))

    if isinstance(voting_end, datetime.datetime):
        voting_end = 'Λήξη: %s' % (voting_end.strftime(DATE_FMT))

    if extended_until and isinstance(extended_until, datetime.datetime):
        extended_until = 'Παράταση: %s' % (extended_until.strftime(DATE_FMT))
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

    for poll_name, poll_results in data:
        poll_intro_contents = [
            poll_name
        ]
        parties_results = []
        candidates_results = {}

        total_votes, blank_votes, parties_results, candidates_results = \
            load_results(poll_results)
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
