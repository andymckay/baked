import ast
from collections import namedtuple, defaultdict
import json
import os.path


class Parser(object):

    def __init__(self, filename):
        self.filename = filename
        self.file = os.path.basename(filename)
        self.order = ('stdlib', 'unknown')
        self.modules = {}
        self.parsed = []
        self.record = namedtuple('Tree', ('type', 'module', 'name', 'number',
                                          'source'))

        self.load_config()
        self.parse()

    def load_config(self):
        config = os.path.expanduser('~/.bakedconfig')
        if os.path.exists(config):
            data = json.load(open(config, 'rb'))
            self.order = data.get('ordering')
            if 'unknown' not in self.order:
                self.order.append('unknown')
            for k, values in data['modules'].items():
                for v in values:
                    self.modules[v] = k

    def get_source(self, module, name):
        return self.modules.get(module or name, 'unknown')

    def parse(self):
        source = open(filename, 'rb').read()
        parsed = ast.parse(source)
        self.source = source.split('\n')

        for obj in parsed.body:
            if isinstance(obj, ast.Import):
                for n in obj.names:
                    source = self.get_source(None, n.name)
                    self.parsed.append(self.record('import', None,
                                                   n.name, obj.lineno, source))

            if isinstance(obj, ast.ImportFrom):
                for n in obj.names:
                    source = self.get_source(obj.module, n.name)
                    self.parsed.append(self.record('from', obj.module,
                                                   n.name, obj.lineno, source))

    def dump(self, rec):
        return 'line %s: %s' % (rec.number, self.source[rec.number-1])

    def dumps(self):
        for record in self.parsed:
            print self.dump(record)

    def check(self):
        reported = set()
        current = self.order[0]
        order = defaultdict(list)

        for rec in self.parsed:
            # Find out where a module import is in the wrong order.
            order[rec.module].append(rec.name)
            sorted_order = sorted(order[rec.module])
            if order[rec.module] != sorted_order:
                reported.add('%s:%s: "%s" out of order' %
                             (self.file, rec.number, rec.name))

            # Find out when the import grouping is in the wrong order.
            if current != rec.source:
                if self.order.index(rec.source) < self.order.index(current):
                    reported.add('%s:%s: "%s" before "%s"' %
                                 (self.file, rec.number, rec.source, current))
                    continue
                current = rec.source

            if rec.source == 'unknown':
                reported.add('%s:%s: unknown lib' % (self.file, rec.number))

        for report in reported:
            print report


filename = '/Users/andy/sandboxes/zamboni/test.py'
parser = Parser(filename)
parser.check()
#parser.dumps()
