# schemas/base.py
from sqlalchemy import MetaData
from sqlalchemy.orm import declarative_base

# Use a consistent naming convention (recommended for Alembic & team projects)
naming_convention = {
    "ix": "ix_%(table_name)s_%(column_0_name)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

metadata = MetaData(naming_convention=naming_convention)

# Declarative base used across the app
Base = declarative_base(metadata=metadata)
