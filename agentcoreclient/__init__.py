try:
    from .client import AgentCoreClient
except ImportError:
    pass  # importing msgpack might fail when importing from setup.py

from .version import __version__


class IgnoreResultException(Exception):
    """IgnoreResultException should be raised by a check if the result needs
    to be ignored.
    Nothing for this check will be returned to the AgentCore.
    """
    pass
