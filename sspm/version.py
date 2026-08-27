import sys
from collections import namedtuple

_SSPM_VERSION_CLS = namedtuple("_SSPM_VERSION_CLS", "major minor bugfix pre post dev")

version_tuple = _SSPM_VERSION_CLS(1, 0, 0, None, None, None)

version = "{0.major:d}.{0.minor:d}.{0.bugfix:d}".format(version_tuple)
if version_tuple.pre is not None:
    version += version_tuple.pre
if version_tuple.post is not None:
    version += ".post{0.post:d}".format(version_tuple)
if version_tuple.dev is not None:
    version += ".dev{0.dev:d}".format(version_tuple)

info = """\
Summary of the SSPM configuration
---------------------------------

SSPM    %(sspm)s
Python  %(python)s
Platform    %(platform)s
""" % {
    'sspm': version,
    'python': sys.version,
    'platform': sys.platform,
}
