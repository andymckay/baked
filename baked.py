import ast
import json
import os
import sys
from collections import defaultdict, namedtuple
from glob import glob


class Parser(object):

    def __init__(self, filename):
        self.filename = os.path.abspath(filename)
        self.file = filename
        cwd = os.getcwd()
        if self.file.startswith(cwd):
            self.file = filename[len(cwd):]
        self.order = ('stdlib', 'unknown')
        self.modules = {}
        self.parsed = []
        self.fallback = 'unknown'
        self.record = namedtuple('Tree', ('type', 'module', 'name', 'number',
                                          'source'))

        self.load_configs()
        self.parse()

    def load_configs(self, *configs):
        configs = configs + ('.baked', os.path.expanduser('~/.baked'))
        for config in configs:
            if os.path.exists(config):
                self.load_config(config)
                break

    def load_config(self, config):
        if os.path.exists(config):
            data = json.load(open(config, 'rb'))
            self.order = data.get('order')
            if 'unknown' not in self.order:
                self.order.append('unknown')
            for k, values in data['modules'].items():
                for v in values:
                    self.modules[v] = k
            self.fallback = data['fallback']
            self.from_order = data['from_order']

    def get_source(self, type, module, name, level):
        # This is a . import.
        if type == 'from' and level > 0:
            return 'local'
        target = (module or name).split('.')[0]
        result = self.modules.get(target)
        if not result:
            return self.fallback
        return result

    def parse(self):
        source = open(self.filename, 'rb').read()
        parsed = ast.parse(source)
        self.source = source.split('\n')

        for obj in parsed.body:
            if isinstance(obj, (ast.Import, ast.ImportFrom)):
                type = 'import' if isinstance(obj, ast.Import) else 'from'
                module = getattr(obj, 'module', None)
                if '#NOQA' in self.source[obj.lineno-1]:
                    continue

                for n in obj.names:
                    source = self.get_source(type, module, n.name, 0)
                    self.parsed.append(self.record(type, module,
                                                   n.name, obj.lineno, source))

    def dump(self, rec):
        return 'line %s: %s' % (rec.number, self.source[rec.number - 1])

    def dumps(self):
        for record in self.parsed:
            print self.dump(record)

    def check(self):
        reported = set()
        current = self.order[0]
        current_from = False
        order = defaultdict(list)

        for rec in self.parsed:
            # Find out where a module import is in the wrong order.
            key = rec.module or rec.source
            order[key].append(rec.name)
            sorted_order = sorted(order[key], key=str.lower)
            if order[key] != sorted_order:
                reported.add('%s:% 3s: "%s" not in order should be: %s' %
                             (self.file, rec.number, rec.name,
                              ', '.join(sorted_order)))

            # Find out when the import grouping is in the wrong order.
            if current != rec.source:
                if self.order.index(rec.source) < self.order.index(current):
                    reported.add('%s:% 3s: "%s" should be before "%s"' %
                                 (self.file, rec.number, rec.source, current))
                    continue
                current = rec.source
                current_from = False

            if rec.type == 'from':
                current_from = True

            if (rec.type == 'import'
                and current_from is True
                and self.from_order.get(rec.source, True)):
                reported.add('%s:% 3s: "%s" from after import' %
                             (self.file, rec.number, rec.name))

        for report in sorted(reported):
            print report


def main():
    for arg in sys.argv[1:]:
        for file in glob(arg):
            parser = Parser(arg)
            parser.check()


if __name__ == '__main__':
    main()
