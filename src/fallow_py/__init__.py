"""Python-first static codebase intelligence for agents and reviewers."""

from .analysis import analyze
from .config import load_config
from .models import VERSION
from .predict import verify_imports

__version__ = VERSION

__all__ = ["VERSION", "__version__", "analyze", "load_config", "verify_imports"]
