"""Department taxonomy for operations routing (cascade notifications)."""

from __future__ import annotations

import enum


class Department(str, enum.Enum):
    """Canonical department labels for team membership and cascade routing."""

    SALES = "sales"
    PURCHASE = "purchase"
    PRODUCTION = "production"
    ACCOUNTS = "accounts"
    STORES = "stores"
    PROJECTS = "projects"
    ADMIN = "admin"

    @classmethod
    def values(cls) -> list[str]:
        return [d.value for d in cls]

    @classmethod
    def is_valid(cls, value: str | None) -> bool:
        if not value:
            return False
        return value.strip().lower() in cls.values()

    @classmethod
    def normalize(cls, value: str | None) -> str | None:
        if not value:
            return None
        normalized = value.strip().lower()
        if normalized in cls.values():
            return normalized
        return None


DEPARTMENT_LABELS: dict[str, str] = {
    Department.SALES.value: "Sales",
    Department.PURCHASE.value: "Purchase",
    Department.PRODUCTION.value: "Production",
    Department.ACCOUNTS.value: "Accounts",
    Department.STORES.value: "Stores / Inventory",
    Department.PROJECTS.value: "Projects",
    Department.ADMIN.value: "Admin",
}
