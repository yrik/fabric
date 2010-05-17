"""
Fabfile generation mechanisms driving the "fabfile" binary script.
"""

from __future__ import with_statement

import os.path
import re
from contextlib import nested
from optparse import OptionParser
from sys import version_info


def process(text, comments=True, python25=True):
    """
    Process sample fabfile text ``text`` to remove comments/future imports.

    ``comments`` is a Boolean determining whether explanatory comments will be
    stripped out (if ``False``, any lines beginning with ``'#'`` will be
    stripped).

    ``python25`` is a Boolean specifying whether to include Python 2.5 specific
    imports such as ``from __future__ import with_statement``.
    """
    # Comments are obvious...
    if not comments:
        text = re.sub(re.compile(r'^#.*', re.M), '', text)
    # Makes some (hopefully limited enough) assumptions about the line(s)
    # dealing with the with_statement import.
    if not python25:
        regex = r'^.*(with_statement|Python 2\.5).*'
        text = re.sub(re.compile(regex, re.M), '', text)
    # Clean up whitespace a bit before returning
    return re.sub(r'\n{3,}', "\n\n", text.strip()) + "\n"


def fabfile(destination, **kwargs):
    """
    Write out the sample fabfile to ``destination`` file path.

    ``destination`` must be a full filename path, not a directory path.

    Keyword arguments are passed to `process`.
    """
    template = os.path.join(os.path.dirname(__file__), 'sample_fabfile.py')
    with nested(open(template), open(destination, 'w')) as (source, output):
        output.write(process(source.read(), **kwargs))


def parse_options():
    parser = OptionParser(usage="fabfile [options] [fabfile_path, ...]")

    opts, args = parser.parse_args()
    return parser, opts, args


def main():
    """
    Primary CLI invocation.
    """
    parser, options, arguments = parse_options()
