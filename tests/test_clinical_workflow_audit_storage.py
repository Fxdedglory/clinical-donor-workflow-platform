import json
from datetime import UTC, datetime
from pathlib import Path

from app.models import ClinicalWorkflowAuditEvent
from app.schemas.clinical import WorkflowOperation
from app.schemas.clinical_reports import ReportFilterRequest
from app.services.clinical_quality import audit_evidence_response
from app.services.clinical_reports import audit_activity_report
from app.services.clinical_workflows import (
    append_workflow_operation,
    backfill_workflow_operations_from_json,
    read_workflow_operations,
    workflow_operation_to_audit_event,
)


class _Rows:
    def __init__(self, rows: list[object]) -> None:
        self.rows = rows

    def scalars(self):
        return self

    def all(self):
        return self.rows


def _compiled(statement) -> str:
    try:
        return str(statement.compile(compile_kwargs={"literal_binds": True}))
    except Exception:
        return str(statement)


class _WorkflowAuditDb:
    def __init__(self, audit_events: list[ClinicalWorkflowAuditEvent] | None = None) -> None:
        self.audit_events = audit_events or []
        self.committed = False
        self.rolled_back = False

    def execute(self, statement, *_args, **_kwargs):
        sql = _compiled(statement)
        if "clinical_workflow_audit_events" in sql:
            return _Rows(self.audit_events)
        return _Rows([])

    def add(self, row) -> None:
        if isinstance(row, ClinicalWorkflowAuditEvent) and row not in self.audit_events:
            self.audit_events.append(row)

    def flush(self) -> None:
        timestamp = datetime.now(UTC)
        for index, event in enumerate(self.audit_events, start=1):
            if event.id is None:
                event.id = index
            if event.created_at is None:
                event.created_at = timestamp

    def commit(self) -> None:
        self.committed = True

    def rollback(self) -> None:
        self.rolled_back = True


def _operation(**overrides) -> WorkflowOperation:
    values = {
        "operation_id": "op-db-001",
        "workflow": "quality.event_create",
        "entity_type": "clinical_quality_event",
        "entity_id": "QE-DB-001",
        "actor": "QA User",
        "timestamp": datetime.now(UTC),
        "preview_hash": "sha256-db",
        "commit_confirmed": True,
        "status_before": "draft",
        "status_after": "open",
        "reason": "Persist workflow audit",
        "changes": {"source_module": "clinical_quality", "field": "value"},
    }
    values.update(overrides)
    return WorkflowOperation(**values)


def test_db_audit_event_created_on_append_and_required_fields_populated(tmp_path: Path) -> None:
    audit_path = tmp_path / "workflow_operations.json"
    db = _WorkflowAuditDb()
    operation = _operation()

    append_workflow_operation(operation, path=audit_path, db=db)

    assert len(db.audit_events) == 1
    event = db.audit_events[0]
    assert event.operation_id == operation.operation_id
    assert event.workflow == "quality.event_create"
    assert event.entity_type == "clinical_quality_event"
    assert event.entity_id == "QE-DB-001"
    assert event.actor == "QA User"
    assert event.preview_hash == "sha256-db"
    assert event.commit_confirmed is True
    assert event.status_before == "draft"
    assert event.status_after == "open"
    assert event.reason == "Persist workflow audit"
    assert event.changes_json == operation.changes
    assert event.source == "workflow_commit"
    assert event.timestamp is not None
    assert db.committed is True


def test_json_mirror_created_and_append_is_non_destructive(tmp_path: Path) -> None:
    audit_path = tmp_path / "workflow_operations.json"
    existing = {
        "operation_id": "existing",
        "workflow": "clinical.seed",
        "entity_type": "clinical_shell",
        "entity_id": "seed",
        "actor": "Seeder",
        "timestamp": "2026-06-12T00:00:00+00:00",
        "preview_hash": "sha256-seed",
        "commit_confirmed": True,
        "status_before": None,
        "status_after": "seeded",
        "reason": "Seed",
        "changes": {"seed": True},
    }
    audit_path.write_text(json.dumps([existing], indent=2) + "\n", encoding="utf-8")
    db = _WorkflowAuditDb()

    append_workflow_operation(_operation(operation_id="op-db-002"), path=audit_path, db=db)

    entries = json.loads(audit_path.read_text(encoding="utf-8"))
    assert entries[0] == existing
    assert entries[1]["operation_id"] == "op-db-002"
    assert len(db.audit_events) == 1


def test_read_workflow_operations_uses_db_first_and_json_fallback(tmp_path: Path) -> None:
    audit_path = tmp_path / "workflow_operations.json"
    audit_path.write_text(
        json.dumps([_operation(operation_id="json-op", workflow="clinical.json").model_dump(mode="json")]),
        encoding="utf-8",
    )
    db = _WorkflowAuditDb([workflow_operation_to_audit_event(_operation(operation_id="db-op"))])
    db.flush()

    db_first = read_workflow_operations(audit_path, db=db)
    fallback = read_workflow_operations(audit_path, db=_WorkflowAuditDb())

    assert [entry["operation_id"] for entry in db_first] == ["db-op"]
    assert [entry["operation_id"] for entry in fallback] == ["json-op"]


def test_quality_audit_evidence_reads_db_backed_entries() -> None:
    db = _WorkflowAuditDb([workflow_operation_to_audit_event(_operation())])
    db.flush()

    response = audit_evidence_response(db, workflow="quality.event_create")

    assert response.total_operations == 1
    assert response.operations[0]["operation_id"] == "op-db-001"
    assert response.operations[0]["source"] == "workflow_commit"


def test_reports_audit_activity_reads_db_backed_entries() -> None:
    operation = _operation(
        operation_id="report-op",
        workflow="reports.analytics_export",
        entity_type="clinical_report_export",
        entity_id="REXP-001",
    )
    db = _WorkflowAuditDb([workflow_operation_to_audit_event(operation)])
    db.flush()

    response = audit_activity_report(db, ReportFilterRequest(workflow="reports.analytics_export"))

    assert response.total_operations == 1
    assert response.operations[0]["operation_id"] == "report-op"
    assert response.workflow_counts["reports.analytics_export"] == 1


def test_backfill_helper_parses_json_without_deleting_source(tmp_path: Path) -> None:
    source_path = tmp_path / "workflow_operations.json"
    existing = _operation(operation_id="existing-op").model_dump(mode="json")
    incoming = _operation(operation_id="incoming-op", workflow="screening.session_create").model_dump(mode="json")
    rejected = {"operation_id": "bad-op", "workflow": "missing-required-fields"}
    payload = [existing, incoming, rejected]
    source_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    db = _WorkflowAuditDb([workflow_operation_to_audit_event(_operation(operation_id="existing-op"))])
    db.flush()

    result = backfill_workflow_operations_from_json(db, source_path)

    assert result == {
        "source_path": str(source_path),
        "inserted": 1,
        "skipped": 1,
        "rejected": 1,
        "source_deleted": False,
    }
    assert source_path.exists()
    assert json.loads(source_path.read_text(encoding="utf-8")) == payload
    assert [event.operation_id for event in db.audit_events] == ["existing-op", "incoming-op"]
