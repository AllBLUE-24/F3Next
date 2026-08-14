"""Regression tests for project-target handoff into an IS session."""

import asyncio
from types import SimpleNamespace
from uuid import uuid4

from containers.implementation.file_io.load_project_target_structure import (
    _materialize_session_target,
)


class _ScalarResult:
    def __init__(self, value):
        self._value = value

    def scalar_one_or_none(self):
        return self._value


class _FakeDb:
    def __init__(self, existing=None):
        self.existing = existing
        self.added = None
        self.committed = False

    async def execute(self, _stmt):
        return _ScalarResult(self.existing)

    def add(self, value):
        self.added = value

    async def commit(self):
        self.committed = True


def _project_target():
    return SimpleNamespace(
        f3iche="chemical_manufacturing",
        llm_enhanced=True,
        llm_reasoning="validated bottleneck scope",
        r2_target_path=None,
        validation_rules={"BOM": ["items_required"]},
    )


def test_materialize_creates_session_target_when_missing():
    db = _FakeDb()
    session_id = uuid4()

    asyncio.run(
        _materialize_session_target(
            db,
            session_id=session_id,
            project_target=_project_target(),
            required_doctypes=["Item", "BOM"],
            setup_steps=[{"doctype": "Item"}, {"doctype": "BOM"}],
            import_phases={"phase_b_master": {"doctypes": ["Item"]}},
        )
    )

    assert db.committed is True
    assert db.added is not None
    assert db.added.session_id == session_id
    assert db.added.required_doctypes == ["Item", "BOM"]
    assert db.added.total_doctypes == 2


def test_materialize_refreshes_existing_session_target():
    existing = SimpleNamespace()
    db = _FakeDb(existing=existing)

    asyncio.run(
        _materialize_session_target(
            db,
            session_id=uuid4(),
            project_target=_project_target(),
            required_doctypes=["Customer", "Sales Order"],
            setup_steps=[{"doctype": "Customer"}],
            import_phases={"phase_c_transactional": {"doctypes": ["Sales Order"]}},
        )
    )

    assert db.added is None
    assert existing.required_doctypes == ["Customer", "Sales Order"]
    assert existing.total_setup_steps == 1
    assert existing.validation_rules == {"BOM": ["items_required"]}
    assert db.committed is True
