import json
from datetime import UTC, datetime
from pathlib import Path

from app.models import ClinicalWorkflowAuditEvent, ClinicalWorkflowAuditMirrorEvent
from app.schemas.clinical import WorkflowOperation
from app.services.clinical_audit_mirror import (
    AUDIT_MIRROR_STATUS_FAILED,
    AUDIT_MIRROR_STATUS_MIRRORED,
    AuditMirrorConfig,
    AuditMirrorError,
    audit_mirror_checksum,
    audit_mirror_payload,
    mirror_unmirrored_workflow_audit_events,
)
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
    def __init__(
        self,
        audit_events: list[ClinicalWorkflowAuditEvent] | None = None,
        mirror_events: list[ClinicalWorkflowAuditMirrorEvent] | None = None,
    ) -> None:
        self.audit_events = audit_events or []
        self.mirror_events = mirror_events or []
        self.committed = False
        self.rolled_back = False

    def execute(self, statement, *_args, **_kwargs):
        sql = _compiled(statement)
        if "clinical_workflow_audit_mirror_events" in sql:
            return _Rows(self.mirror_events)
        if "clinical_workflow_audit_events" in sql:
            return _Rows(self.audit_events)
        return _Rows([])

    def add(self, row) -> None:
        if isinstance(row, ClinicalWorkflowAuditEvent) and row not in self.audit_events:
            self.audit_events.append(row)
        if isinstance(row, ClinicalWorkflowAuditMirrorEvent) and row not in self.mirror_events:
            self.mirror_events.append(row)

    def flush(self) -> None:
        timestamp = datetime.now(UTC)
        for index, event in enumerate(self.audit_events, start=1):
            if event.id is None:
                event.id = index
            if event.created_at is None:
                event.created_at = timestamp
        for index, event in enumerate(self.mirror_events, start=1):
            if event.mirror_event_id is None:
                event.mirror_event_id = index
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


def test_audit_object_mirror_disabled_does_not_break_db_append(tmp_path: Path) -> None:
    audit_path = tmp_path / "workflow_operations.json"
    db = _WorkflowAuditDb()

    append_workflow_operation(
        _operation(operation_id="mirror-disabled-op"),
        path=audit_path,
        db=db,
        object_mirror_config=AuditMirrorConfig(mode="disabled"),
    )

    assert [event.operation_id for event in db.audit_events] == ["mirror-disabled-op"]
    assert db.mirror_events == []
    assert audit_path.exists()


def test_local_audit_object_mirror_writes_redacted_payload_and_metadata(tmp_path: Path) -> None:
    audit_path = tmp_path / "workflow_operations.json"
    mirror_root = tmp_path / "worm"
    db = _WorkflowAuditDb()
    operation = _operation(
        operation_id="mirror-local-op",
        changes={
            "patient_id": "PT-SECRET",
            "note": "Detailed clinical narrative",
            "status": "open",
        },
    )

    append_workflow_operation(
        operation,
        path=audit_path,
        db=db,
        object_mirror_config=AuditMirrorConfig(mode="local_filesystem", local_root=mirror_root),
    )

    files = list(mirror_root.rglob("*.json"))
    assert len(files) == 1
    mirror_payload = json.loads(files[0].read_text(encoding="utf-8"))
    serialized = json.dumps(mirror_payload)
    assert "PT-SECRET" not in serialized
    assert "Detailed clinical narrative" not in serialized
    assert mirror_payload["payload_profile"] == "audit_metadata"
    assert mirror_payload["operation"]["changes"]["patient_id"] == "[redacted]"
    assert mirror_payload["operation"]["changes"]["note"] == "[redacted]"
    assert mirror_payload["operation"]["changes"]["status"] == "open"

    assert len(db.mirror_events) == 1
    event = db.mirror_events[0]
    assert event.operation_id == "mirror-local-op"
    assert event.mirror_status == AUDIT_MIRROR_STATUS_MIRRORED
    assert event.mirror_uri
    assert event.mirror_checksum == audit_mirror_checksum(mirror_payload)
    assert event.mirror_error is None


def test_audit_object_mirror_checksum_is_deterministic_and_redacted() -> None:
    operation = _operation(
        operation_id="checksum-op",
        changes={"patient_id": "PT-SECRET", "field": "status"},
    )
    first_payload = audit_mirror_payload(operation)
    second_payload = audit_mirror_payload(operation)

    assert first_payload == second_payload
    assert audit_mirror_checksum(first_payload) == audit_mirror_checksum(second_payload)
    assert "PT-SECRET" not in json.dumps(first_payload)


def test_optional_audit_object_mirror_failure_records_error(tmp_path: Path) -> None:
    audit_path = tmp_path / "workflow_operations.json"
    db = _WorkflowAuditDb()

    append_workflow_operation(
        _operation(operation_id="mirror-failure-op"),
        path=audit_path,
        db=db,
        object_mirror_config=AuditMirrorConfig(mode="unsupported"),
    )

    assert len(db.audit_events) == 1
    assert len(db.mirror_events) == 1
    assert db.mirror_events[0].mirror_status == AUDIT_MIRROR_STATUS_FAILED
    assert "Unsupported audit object mirror mode" in db.mirror_events[0].mirror_error


def test_required_audit_object_mirror_failure_raises_after_recording_error(tmp_path: Path) -> None:
    audit_path = tmp_path / "workflow_operations.json"
    db = _WorkflowAuditDb()

    try:
        append_workflow_operation(
            _operation(operation_id="mirror-required-failure-op"),
            path=audit_path,
            db=db,
            object_mirror_config=AuditMirrorConfig(mode="unsupported", required=True),
        )
    except AuditMirrorError:
        pass
    else:
        raise AssertionError("required mirror failure should raise")

    assert len(db.audit_events) == 1
    assert len(db.mirror_events) == 1
    assert db.mirror_events[0].mirror_status == AUDIT_MIRROR_STATUS_FAILED
    assert db.rolled_back is True
    assert json.loads(audit_path.read_text(encoding="utf-8"))[0]["operation_id"] == "mirror-required-failure-op"


def test_audit_object_mirror_replay_mirrors_unmirrored_and_skips_existing(tmp_path: Path) -> None:
    mirrored_operation = _operation(operation_id="already-mirrored-op")
    pending_operation = _operation(operation_id="pending-mirror-op", workflow="orders.result_add")
    db = _WorkflowAuditDb(
        audit_events=[
            workflow_operation_to_audit_event(mirrored_operation),
            workflow_operation_to_audit_event(pending_operation),
        ],
        mirror_events=[
            ClinicalWorkflowAuditMirrorEvent(
                operation_id="already-mirrored-op",
                mirror_mode="local_filesystem",
                mirror_status=AUDIT_MIRROR_STATUS_MIRRORED,
                payload_profile="audit_metadata",
                mirror_uri="local-worm://clinical-audit/existing.json",
                mirror_checksum="sha256-existing",
            )
        ],
    )
    db.flush()

    result = mirror_unmirrored_workflow_audit_events(
        db,
        config=AuditMirrorConfig(mode="local_filesystem", local_root=tmp_path / "worm"),
    )

    assert result["mirrored"] == 1
    assert result["skipped"] == 1
    assert result["failed"] == 0
    assert [event.operation_id for event in db.mirror_events] == ["already-mirrored-op", "pending-mirror-op"]


def test_audit_object_mirror_replay_dry_run_does_not_write_or_record(tmp_path: Path) -> None:
    db = _WorkflowAuditDb([workflow_operation_to_audit_event(_operation(operation_id="dry-run-op"))])
    db.flush()

    result = mirror_unmirrored_workflow_audit_events(
        db,
        config=AuditMirrorConfig(mode="local_filesystem", local_root=tmp_path / "worm"),
        dry_run=True,
    )

    assert result["dry_run"] == 1
    assert result["mirrored"] == 0
    assert db.mirror_events == []
    assert not (tmp_path / "worm").exists()
