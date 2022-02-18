try:
    from .client import AgentCoreClient
except ImportError:
    pass  # importing msgpack might fail when importing from setup.py

from .version import __version__
