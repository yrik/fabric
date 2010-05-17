from nose.tools import eq_

from fabric.generation import process


# Test text may resemble actual sample fabfile, but doesn't have to.
# Ideally the sample fabfile can change drastically and still be processed
# correctly -- we only target a few things.
text = """# Comment
# Another comment
# This comment mentions Python 2.5
from __future__ import with_statement

# Comment
from fabric.api import *



# More
# comments
# here
"""

def test_process_defaults_and_whitespace():
    """
    With default/true args, process() only cleans whitespace.
    """
    eq_(process(text), """# Comment
# Another comment
# This comment mentions Python 2.5
from __future__ import with_statement

# Comment
from fabric.api import *

# More
# comments
# here
""")


def test_process_comments():
    """
    With comments=False, process() strips all comments.
    """
    eq_(process(text, comments=False), """from __future__ import with_statement

from fabric.api import *
""")


def test_process_python25():
    """
    With python25=False, process() strips any with_statement imports.
    """
    eq_(process(text, python25=False), """# Comment
# Another comment

# Comment
from fabric.api import *

# More
# comments
# here
""")


def test_process_neither():
    """
    With both kwargs false, process() looks nice and clean.
    """
    eq_(process(text, comments=False, python25=False),
"""from fabric.api import *
""")


def test_argument_parsing():
    # []: fabfile.py
    # ['foo']: foo/fabfile.py
    # ['foo.py']: foo.py
    # ['foo', 'bar']: foo/fabfile.py, bar/fabfile.py


def test_package_creation():
    # ['foo/web.py']: foo/web.py, foo/__init__.py
    # ['foo/web.py', 'foo/system.py']: foo/web.py, foo/system.py, foo/__init__.py


def test_no_package():
    # ['foo/web.py'] (no_package=True): foo/web.py


def test_directory_creation():
    # ['foo'] (no foo dir): foo, foo/fabfile.py


def test_no_directory_creation():
    # ['foo'] (no foo dir, no_mkdir=True): abort/error
