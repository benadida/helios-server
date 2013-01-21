#!/usr/bin/python
# -*- coding: utf-8 -*-

import json

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.platypus import Spacer, Image
from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

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

parties_results = []
candidates_results = {}
total_votes = 0
blank_votes = 0

def load_results(filename):
    total_votes = 0
    blank_votes = 0
    with open(filename, 'r') as jsonfile:
        jsondata = json.load(jsonfile)
        for party_result in jsondata['parties']:
            (result, party) = party_result
            if party is None:
                blank_votes += result
            else:
                parties_results.append((party, result))
            total_votes += result
        for candidate_result in jsondata['candidates']:
            (result, full_candidate) = candidate_result
            (party, candidate) = full_candidate.split(':')
            if party in candidates_results:
                candidates_results[party].append((candidate, result))
            else:
                candidates_results[party] = [(candidate, result)]
    return (total_votes, blank_votes)

def make_first_page_hf(canvas, doc):
    canvas.saveState()
    canvas.drawImage('logo-positive.jpg',
                     x = PAGE_WIDTH - 5 * cm,
                     y = PAGE_HEIGHT - 2 * cm,
                     width = PAGE_WIDTH / 8,
                     height = 1.1 * cm)
    canvas.restoreState()

def make_later_pages_hf(canvas, doc):
    canvas.saveState()    
    canvas.setFont('LinLibertine',9)
    canvas.drawImage('logo-positive.jpg',
                     x = 2 * cm,
                     y = PAGE_HEIGHT - 2 * cm,
                     width = PAGE_WIDTH / 8,
                     height = 1.1 * cm)
    canvas.drawString(PAGE_WIDTH - 7 * cm, PAGE_HEIGHT - 2 * cm,
                      "%s %d" % (pageinfo, doc.page))
    canvas.restoreState()
    

def make_heading(element, contents):
    for x in range(0, 5):
        elements.append(Spacer(1, 12))
    for pcontent in contents:
        elements.append(Paragraph(pcontent, styles["ZeusHeading"]))
        
def make_intro(elements, contents):
    for pcontent in contents:
        elements.append(Paragraph(pcontent, styles["Zeus"]))
    elements.append(Spacer(1, 12))
    
def make_totals(elements, total_votes, blank_votes):
    elements.append(Paragraph('Σύνολο ψήφων: %d' % total_votes, styles['Zeus']))
    elements.append(Paragraph('Λευκά: %d' % blank_votes, styles['Zeus']))
    elements.append(Spacer(1, 12))
        
def make_party_list_heading(elements, party, count):
    heading = '%(title)s: %(count)d' % {'title': party,
                                        'count': count}
    elements.append(Paragraph(heading, styles['Zeus']))
    elements.append(Spacer(1, 12))

def make_party_list_table(elements, party_results):
    
    table_style = TableStyle([('FONT', (0, 0), (-1, -1), 'LinLibertine')])
    t = Table(party_results, style = table_style)
    elements.append(t)

def make_results(elements, parties_results, candidates_results):

    make_totals(elements, total_votes, blank_votes)
    for party_result in parties_results:
        (party, count) = party_result
        make_party_list_heading(elements, party, count)
        if party in candidates_results:
            make_party_list_table(elements, candidates_results[party])

doc = SimpleDocTemplate("election_results.pdf", pagesize=A4)

elements = []

styles = getSampleStyleSheet()
styles.add(ParagraphStyle(name='Zeus',
                          fontName='LinLibertine',
                          fontSize=12,
                          leading=16,
                          alignment=TA_JUSTIFY))

styles.add(ParagraphStyle(name='ZeusHeading',
                          fontName='LinLibertineBd',
                          fontSize=16,
                          alignment=TA_CENTER,
                          spaceAfter=16))

(total_votes, blank_votes) = load_results('ballots.json')

title = 'Αποτελέσματα'
name = 'Εκλογές ΠΟΣΔΕΠ'
institution_name = 'Οικονομικό Πανεπιστήμιο Αθηνών'
voting_start = 'Έναρξη: 21/1/2013 9:00'
voting_end = 'Λήξη: 21/1/2013 17:00'
extended_until = 'Παράταση: 21/1/2013 18:00'

intro_contents = [
    name,
    institution_name,
    voting_start,
    voting_end,
    extended_until
    ]

make_heading(elements, [title])

make_intro(elements, intro_contents)

make_results(elements, parties_results, candidates_results)

doc.build(elements, onFirstPage = make_first_page_hf,
          onLaterPages = make_later_pages_hf)
