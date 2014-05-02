import re

class STVParser(object):

    actions_map = {
        '@': 'round',
        '>': 'transfer',
        '-': 'eliminate',
        '!': 'quota',
        '+': 'elect',
        '.': 'count',
        '~': 'zombies',
        '*': 'random',
        '^': 'threshold',
    }

    regex = {
        'count': re.compile('(?:([0-9]+) = ([e\-0-9\.]+)[;]{0,1})'),
        'random': re.compile('([0-9]+) from \[((?:\'[0-9]+\'(?:, ){0,1})+)\] to (.*)'),
        'elect': re.compile('([0-9]+) = ([e\-0-9\.]+)'),
        'quota': re.compile('([0-9]+) = ([e\-0-9\.]+)'),
        'eliminate': re.compile('([0-9]+) = ([e\-0-9\.]+)'),
        'zombies': re.compile('(?:([0-9]+) = ([e\-0-9\.]+)[;]{0,1})'),
        'transfer': re.compile('from ([0-9]+) to ([0-9]+) ([0-9]+)\*([e\-0-9\.]+)=([e\-0-9\.]+)')
    }

    def _norm_quota(self, data):
        return int(data[0][0]), data[0][1]

    def _norm_random(self, data):
        data = list(data[0])
        data[1] = map(int, re.findall(r'(?:\'([0-9]+)\')+', data[1]))
        return int(data[0]), data[1], data[2]

    def _norm_eliminate(self, data):
        data = data[0]
        return int(data[0]), data[1]

    def _norm_transfer(self, data):
        data = list(data[0])
        _tmp = data[0]
        data[0] = int(data[1])
        data[1] = int(_tmp)
        return data

    def _norm_elect(self, data):
        data = data[0]
        return int(data[0]), float(data[1])

    def _parse_line(self, line):
        action, data = line.split(" ", 1)
        return self.actions_map[action[0]], data

    def _parse_action(self, action, data):
        r = self.regex.get(action, None)
        if r:
            d = data
            data = r.findall(data)

        if hasattr(self, '_norm_%s' % action):
            norm = getattr(self, '_norm_%s' % action, None)
            data = norm(data) if norm else data

        return data

    def __init__(self, data):
        self.lines = data.split("\n")
        action, thres = self._parse_line(self.lines[0])

    def rounds(self):
        self.round = None
        self.round_data = None

        for line in self.lines[1:]:
            if not line:
                continue
            action, data = self._parse_line(line)
            data = self._parse_action(action, data)

            if action == 'round':
                if self.round_data:
                    yield self.round, self.round_data

                self.round_data = None
                self.round = int(data)

            if action == 'count':
                self.round_data = {'candidates': {}}
                for cand, votes in data:
                    self.round_data['candidates'][int(cand)] = {
                        'votes': votes,
                        'actions': []
                    }

            if action == 'zombies':
                if not self.round_data:
                    self.round_data = {'candidates': {}}

                for cand, votes in data:
                    self.round_data['candidates'][int(cand)] = {
                        'votes': votes,
                        'actions': []
                    }

            if action == 'random':
                cands = data[1]
                for cand in data[1]:
                    self.round_data['candidates'][cand]['actions'].append((action, data))

            if action in ['elect', 'eliminate', 'transfer', 'quota']:
                self.round_data['candidates'][data[0]]['actions'].append((action, data))
        
        if self.round_data:
            yield self.round, self.round_data


