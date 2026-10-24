"""Assistant package: importing it registers all skills."""
from . import skills  # noqa: F401  (registers skills via decorators)
from .core import Session, handle

__all__ = ["Session", "handle"]
