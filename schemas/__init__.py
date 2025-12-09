# schemas/__init__.py

# import Base so consumers can do: from schemas import Base, models...
from .base import Base

# import models to ensure they are registered with Base.metadata
from . import clients  # noqa: F401
from . import projects  # noqa: F401

__all__ = ["Base", "clients", "projects"]
