import ast
import imp
import inspect
import json
import os
import sys
from collections import defaultdict, namedtuple
from glob import glob
from subprocess import PIPE, Popen

stdlib = [
    'abc', 'anydbm', 'argparse', 'array',
    'asynchat', 'asyncore', 'atexit', 'base64', 'BaseHTTPServer',
    'bisect', 'bz2', 'calendar', 'cgitb', 'cmd', 'codecs', 'collections',
    'commands', 'compileall', 'ConfigParser', 'contextlib', 'Cookie',
    'copy', 'cPickle', 'cProfile', 'cStringIO', 'csv', 'datetime',
    'dbhash', 'dbm', 'decimal', 'difflib', 'dircache', 'dis', 'doctest',
    'dumbdbm', 'EasyDialogs', 'exceptions', 'filecmp', 'fileinput',
    'fnmatch', 'fractions', 'functools', 'gc', 'gdbm', 'getopt',
    'getpass', 'gettext', 'glob', 'grp', 'gzip', 'hashlib', 'heapq',
    'hmac', 'imaplib', 'imp', 'inspect', 'itertools', 'json', 'linecache',
    'locale', 'logging', 'mailbox', 'math', 'mhlib', 'mmap',
    'multiprocessing', 'operator', 'optparse', 'os', 'os.path', 'pdb',
    'pickle', 'pipes', 'pkgutil', 'platform', 'plistlib', 'pprint',
    'profile', 'pstats', 'pwd', 'pyclbr', 'pydoc', 'Queue', 'random',
    're', 'readline', 'resource', 'rlcompleter', 'robotparser', 'sched',
    'select', 'shelve', 'shlex', 'shutil', 'signal', 'SimpleXMLRPCServer',
    'site', 'sitecustomize', 'smtpd', 'smtplib', 'socket', 'SocketServer',
    'sqlite3', 'string', 'StringIO', 'struct', 'subprocess', 'sys',
    'sysconfig', 'tabnanny', 'tarfile', 'tempfile', 'textwrap',
    'threading', 'time', 'timeit', 'trace', 'traceback', 'unittest',
    'urllib', 'urllib2', 'urlparse', 'usercustomize', 'uuid', 'warnings',
    'weakref', 'webbrowser', 'whichdb', 'xml', 'xml.etree.ElementTree',
    'xmlrpclib', 'zipfile', 'zipimport', 'zlib'
]


class Parser(object):

    def __init__(self, filename):
        self.filename = os.path.abspath(filename)
        self.file = filename
        cwd = os.getcwd()
        if self.file.startswith(cwd):
            self.file = filename[len(cwd):]
        self.order = ('stdlib', 'unknown')
        self.modules = {}
        [self.modules.__setitem__(k, 'stdlib') for k in stdlib]
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
        last = {}
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
                    if current in last:
                        _last = last[current]
                        reported.add('%s:% 3s: first %s import was "%s"' % (
                            self.file, _last.number, current, _last.module))
                    continue
                last[rec.source] = rec
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

        return len(reported)


def git_hook(strict=False, lazy=True):
    """
    Use to hooking up to a git pre-commit hook.

    Enable by adding the following to your .git/hooks/pre-commit::

        #!/usr/bin/env python
        import sys
        from baked import git_hook

        if __name__ == '__main__':
            sys.exit(git_hook(strict=True, lazy=True))

    Don't forget to `chmod 755 .git/hooks/pre-commit`.

    :param bool strict: (optional), if True, this returns the total number of
    errors which will cause the hook to fail
    :param bool lazy: (optional), allows for the instances where you don't add
    the files to the index before running a commit, e.g., git commit -a

    :returns: total number of errors if strict is True, otherwise 0
    """
    gitcmd = "git diff-index --cached --name-only --diff-filter=ACMRTUXB HEAD"
    if lazy:
        # Catch all files, including those not added to the index.
        gitcmd = gitcmd.replace('--cached ', '')

    p = Popen(gitcmd.split(), stdout=PIPE, stderr=PIPE)
    (stdout, stderr) = p.communicate()
    files_modified = [line.strip() for line in stdout.splitlines()]

    # Run the checks.
    errors = 0
    for file in files_modified:
        errors += Parser(file).check()

    return errors if strict else 0


def main():
    if sys.argv[1:]:
        args = []
        for arg in sys.argv[1:]:
            for f in glob(arg):
                args.append(f)
    else:
        # Try to find files piped to us.
        args = [f for f in sys.stdin.readlines()]

    # Remove any non-Python files.
    py_args = []
    for f in args:
        f = f.strip()
        mod = inspect.getmoduleinfo(f)
        if mod and mod[3] in (imp.PY_SOURCE,):
            py_args.append(f)

    for arg in py_args:
        parser = Parser(arg)
        parser.check()


if __name__ == '__main__':
    main()
