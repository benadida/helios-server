# -*- coding: utf-8 -*-
import csv

class ElectionReport(object):
    
    def __init__(self, elections):
        self.elections = elections
        self.csvData = []
        self.objectData = []
        self.header = ["ΙΔΡΥΜΑ", "ΕΚΛΕΚΤΟΡΕΣ", "ΨΗΦΙΣΑΝΤΕΣ", "ΕΝΑΡΞΗ", "ΛΗΞΗ",
                       "uuid", "ΟΝΟΜΑ", "ΚΑΛΠΕΣ" , "ΔΙΑΧΕΙΡΙΣΤΗΣ"]

    def getElections(self):
        return self.elections

    def setElections(self, election_list):
        self.elections = election_list

    def appendElections(election_list):
        self.elections += election_list


    def parseCSV(self, csv_file_path):
        data = []
        with open(csv_file_path, 'rb') as f:
            reader = csv.reader(f)
            for row in reader:
                if row[0] == "ΙΔΡΥΜΑ":
                    print 'skipped header'
                    continue
                keys = ('inst', 'nr_voters', 'nr_voters_voted', 'start',
                        'end', 'uuid', 'election_name', 'admin')
                new_row = {}
                for index, key in enumerate(keys):
                    new_row[key] = row[index]
                new_row['nr_polls'] = '-'
                data.append(new_row)
        self.csvData += data

    def parse_object(self):
        data = []
        for e in self.elections:
            row = {}
            row['inst'] = e.institution.name
            row['nr_voters'] = e.voters.count()
            row['nr_voters_voted'] = e.voters.cast().count()
            start = e.voting_starts_at
            start = start.strftime("%Y-%m-%d %H:%M") if start else ''
            end = e.voting_ended_at
            end = end.strftime("%Y-%m-%d %H:%M") if end else ''
            row['start'] = start
            row['end'] = end
            row['uuid'] = e.uuid
            row['election_name'] = e.name
            row['nr_polls'] = e.polls.count()
            admins = [admin.user_id for admin in e.admins.all()]
            admins = ",".join(map(str, admins))
            row['admin'] = admins
            data.append(row)
        self.objectData += data
    
    def make_output(self, filename):
        data = self.csvData + self.objectData
        keys = ('inst', 'nr_voters', 'nr_voters_voted', 'start',
                'end', 'uuid', 'election_name', 'nr_polls', 'admin')
        with open("{}.csv".format(filename), 'wb') as f:
            writer = csv.writer(f, delimiter=',')
            writer.writerow(self.header)
            for row in data:
                writer.writerow([row[k] for k in keys])
