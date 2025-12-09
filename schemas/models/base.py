# schemas/models/base.py
from __future__ import annotations
from typing import Any

import sqlalchemy as sa
from sqlalchemy.orm import declarative_base, declared_attr
from sqlalchemy.ext.declarative import DeclarativeMeta

metadata = sa.MetaData()
Base: DeclarativeMeta = declarative_base(metadata=metadata)

class ReprMixin:
    def __repr__(self) -> str:
        values = ", ".join(
            f"{k}={getattr(self, k)!r}" for k in getattr(self, "__repr_keys__", ("id",))
        )
        return f"<{self.__class__.__name__}({values})>"

def now_sql() -> sa.sql.expression.TextClause:
    return sa.text("now()")
