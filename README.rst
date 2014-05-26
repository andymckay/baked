A script to detect that the import order matches Mozilla WebDev Python
guidelines.

Example::

    [baked] zamboni $ p ~/sandboxes/baked/baked.py lib/video/ffmpeg.py -p
    lib/video/ffmpeg.py:9: order wrong for check_output, subprocess, VideoBase
    --- /Users/andy/sandboxes/zamboni/lib/video/ffmpeg.py	2014-05-23 16:11:56.000000000 -0700
    +++ /var/folders/15/3crpnr7j4sj75xynpsqkqbr00000gp/T/tmpXvc_Ml.py	2014-05-23 16:12:11.000000000 -0700
    @@ -1,14 +1,14 @@
     import logging
    +import logging
     import re
     import tempfile

     from django.conf import settings

    +from django_statsd.clients import statsd
     from tower import ugettext as _

    -from django_statsd.clients import statsd
     from .utils import check_output, subprocess, VideoBase
    -import logging

Notice that it detected that `logging` should be up at the top and
`django_statsd` with the 3rd party imports.

Usage::

    baked.py [filename] [filename..]

Filename can be a glob. Or multiple filenames. For example::

    baked.py apps/*.py mkt/*.py

Baked will also accept files being piped to it, for example::

    git diff-index HEAD^ --name-only | baked

Baked loads a confg file as JSON. It will look in the following places for the file:

* in the current and parent directories of the file being checked for
  ``.baked``
* the current directory for ``.baked``
* the users profile directory for ``.baked``

For an example see:

https://gist.github.com/andymckay/5507339

The config file contains:

* *order*: the list of orders of import ``blocks``. This allows you to group your imports into categories.
* *fallback*: if a category is not found for lib, what should it fall back to, for most this will be ``local``.
* *from_order*: a dictionary of sections with a boolean value for each section. If the value is false, then baked will not care that an ``import`` came before ``from``. Default is true for each category.
* *modules*: a dictionary of categories and a list of modules. This allows baked to put each module in the category.

If you'd like to exclude an import from baked add the comment ``#NOQA``.

Guidelines:

http://mozweb.readthedocs.org/en/latest/coding.html#import-statements

With one exception, we ignore that imports should be ordered ``CONSTANT``,
``Class``, ``var``. Just sort by alpha, case insensitive. That's easier for
everyone to parse.

Config params:

* ``-i`` change the file in place, but note that it doesn't fix the order of
  imports on the same line, for example: ``from foo import XX, bar`` is raised
  as a warning, but the order of ``XX`` and ``bar`` is not fixed.
* ``-p``: print the diff that baked has calculated

Changes
-------

0.2.1: lower case import names, so ``import StringIO`` comes after ``import
  os`` for example

0.2: Is a backwards incompatible change, it focuses on generating diffs which
  is a lot easier to read than some rules. For imports statements on one
  line which are out of order, it still prints the import order and
  doesn't try to fix it up.
