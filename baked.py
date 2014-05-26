import argparse
import ast
import imp
import inspect
import json
import os
import shutil
import sys
import tempfile
from glob import glob
from subprocess import PIPE, Popen

stdlib = [
    'abc', 'anydbm', 'argparse', 'array',
    'asynchat', 'asyncore', 'asyncio', 'atexit', 'base64', 'BaseHTTPServer',
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
        self.load_configs()
        self.parse()

    def load_configs(self, *configs):
        abspath = os.path.abspath(os.path.dirname(self.file))
        splitpath = abspath.split(os.sep)
        for x in range(0, len(splitpath)-2):
            dirname = os.path.join(os.sep, *splitpath[1:-(x+1)])
            config = os.path.join(dirname, '.baked')
            if os.path.exists(config):
                configs = configs + (config,)
                continue

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

    def get_source(self, type_, module, name, level):
        # This is a . import.
        if type_ and level > 0:
            return 'local'
        target = (name if module is None else module).split('.')[0]
        result = self.modules.get(target)
        if not result:
            return self.fallback
        return result

    def parse(self):
        source = open(self.filename, 'rb').read()
        counter = 0
        self.source = source.split('\n')
        self.start = 0
        self.end = 0
        stop_flag = False
        start_flag = True

        for x in range(0, len(self.source)):
            if stop_flag:
                break

            for x in range(1, 100):
                code = '\n'.join(self.source[counter:counter+x])
                if '#NOQA' in code:
                    break
                try:
                    node = ast.parse(code)
                except (SyntaxError, IndentationError):
                    continue
                start = counter
                end = counter + x
                counter = end
                break

            for obj in ast.iter_child_nodes(node):
                start_flag = False
                if isinstance(obj, (ast.Import, ast.ImportFrom)):
                    type = 0 if isinstance(obj, ast.Import) else 1
                    module = getattr(obj, 'module', None)

                    names = [x.name for x in obj.names]
                    sources = [self.get_source(type, module, n, 0)
                               for n in names]
                    if len(set(sources)) > 1:
                        raise ValueError('Multiple sources on one line.')

                    self.parsed.append({'type': type, 'module': module,
                                        'names': names, 'source': sources[0],
                                        'start': start, 'end': end})
                    self.end = end
                else:
                    stop_flag = True
                    break

            else:
                # Ensure any leading comments remain.
                if start_flag:
                    self.start += 1


    def dump(self, rec):
        return 'line %s: %s' % (rec['start'], self.source[rec['start'] - 1])

    def dumps(self):
        for record in self.parsed:
            print self.dump(record)

    def diff(self):
        out = []
        for module in self.order:
            section = []
            for rec in self.parsed:
                if rec['source'] == module:
                    section.append(rec)

            order = []
            for r in section:
                if sorted(r['names']) != r['names']:
                    print '{0}:{1}: order wrong for {2}'.format(
                        self.file, r['start'], ', '.join(r['names']))

                order.append(([r['type'],
                    r['module'].lower() if r['module'] else r['module'],
                    [n.lower() for n in r['names']]
                  ], r))

            # If an import came before and one comes after, add in a newline.
            if out and order:
                out.append('')

            order = sorted(order)
            for sorting, item in order:
                out.extend(self.source[item['start']:item['end']])

        total = self.source[:self.start]
        total += out
        total += self.source[self.end:]

        result = '\n'.join(total)
        dest = tempfile.mkstemp(suffix='.py')[1]
        open(dest, 'w').write(result)
        return dest

    def inplace(self):
        dest = self.diff()
        shutil.copy(dest, self.filename)
        os.remove(dest)

    def get_diff(self):
        dest = self.diff()
        diff = 'diff {0} {1} -u'.format(self.filename, dest)
        p = Popen(diff.split(), stdout=PIPE, stderr=PIPE)
        (stdout, stderr) = p.communicate()
        return dest, stdout

    def show(self):
        print self.get_diff()[1]

    def check(self):
        dest, stdout = self.get_diff()
        if stdout:
            print '{0}: has import fixes: {1}'.format(self.file, dest)


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
    parser = argparse.ArgumentParser()
    parser.add_argument('-i', help='Changes file in place', const=True,
                        action='store_const')
    parser.add_argument('-p', help='Prints changes', const=True,
                        action='store_const')
    parser.add_argument('files', nargs='*')
    args = parser.parse_args()
    files = []

    for arg in args.files:
        for f in glob(arg):
            files.append(f)
    if not args.files:
        # Try to find files piped to us.
        files = [f for f in sys.stdin.readlines()]

    # Remove any non-Python files.
    py_files = []
    for f in files:
        f = f.strip()
        mod = inspect.getmoduleinfo(f)
        if mod and mod[3] in (imp.PY_SOURCE,):
            py_files.append(f)

    for arg in py_files:
        parser = Parser(arg)
        if args.i:
            parser.inplace()
        elif args.p:
            parser.show()
        else:
            parser.check()


if __name__ == '__main__':
    main()
