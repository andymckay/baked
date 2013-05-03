A script to detect that the import order matches Mozilla WebDev Python
guidelines. Usage::

    baked.py [filename] [filename..]

Filename can be a glob. Or multiple filenames. For example::

    baked.py apps/*.py mkt/*.py

Loads a confg file as JSON. For an example see: https://gist.github.com/andymckay/5507339

The config file contains::

    :param order: the list of orders of import "blocks"
    :param fallback: what imports will be classified as if not defined
    :param from_order: mapping of sections to enforce "from", "import" order
    :param modules: mapping of import classifications
