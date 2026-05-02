"""Python-first static codebase intelligence for agents and reviewers."""

from .analysis import analyze
from .config import load_config
from .models import VERSION

__version__ = VERSION

__all__ = ["VERSION", "__version__", "analyze", "load_config"]
