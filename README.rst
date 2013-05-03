A script to detect that the import order matches Mozilla WebDev Python
guidelines. Usage::

    baked.py [filename] [filename..]

Filename can be a glob. Or multiple filenames. For example::

    baked.py apps/*.py mkt/*.py

Loads a confg file as JSON. It will look in the following places for the file:

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
