"""Supertext SDK. Everything that talks to the API is versioned with it:

    from supertext import v1          # or: from supertext.v1 import SupertextClient

    client = v1.SupertextClient(api_key)

A later API version gets ``supertext.v2`` next to ``v1``. The HTTP layer every version shares is
:mod:`supertext.transport` (also re-exported from ``supertext.v1``).
"""

from . import v1
from .version import SDK_VERSION

__version__ = SDK_VERSION

__all__ = ["SDK_VERSION", "__version__", "v1"]
