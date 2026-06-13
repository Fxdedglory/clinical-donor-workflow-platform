import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
from app.models import (
    ClinicalWorkflowAuditEvent,
    ClinicalWorkflowAuditMirrorEvent,
    ClinicalWorkflowAuditMirrorManifest,
)
from app.schemas.clinical import WorkflowOperation
from app.schemas.clinical_reports import ReportFilterRequest
from app.services.clinical_audit_manifest import (
    AuditManifestConfig,
    audit_manifest_checksum,
    audit_mirror_recovery_drill_summary,
    generate_audit_mirror_manifest,
    record_audit_mirror_manifest,
    verify_audit_mirror_manifest,
    verify_mirror_inventory,
)
from app.services.clinical_audit_mirror import (
    AUDIT_MIRROR_STATUS_FAILED,
    AUDIT_MIRROR_STATUS_MIRRORED,
    AuditMirrorConfig,
    AuditMirrorError,
    audit_mirror_checksum,
    audit_mirror_payload,
    mirror_unmirrored_workflow_audit_events,
)
from app.services.clinical_audit_mirror_providers import (
    AzureBlobAuditMirrorProvider,
    LocalFilesystemAuditMirrorProvider,
    get_audit_mirror_provider,
    provider_readiness_summary,
)
from app.services.clinical_audit_signing import (
    ALGORITHM_LOCAL_HMAC_SHA256,
    SIGNATURE_STATUS_SIGNED,
    SIGNATURE_VERIFICATION_VERIFIED,
    SIGNING_MODE_LOCAL_HMAC_SHA256,
    AuditManifestSigningConfig,
    canonical_signing_payload,
    sign_manifest_checksum,
)
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
        manifest_events: list[ClinicalWorkflowAuditMirrorManifest] | None = None,
    ) -> None:
        self.audit_events = audit_events or []
        self.mirror_events = mirror_events or []
        self.manifest_events = manifest_events or []
        self.committed = False
        self.rolled_back = False

    def execute(self, statement, *_args, **_kwargs):
        sql = _compiled(statement)
        if "clinical_workflow_audit_mirror_manifests" in sql:
            return _Rows(self.manifest_events)
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
        if isinstance(row, ClinicalWorkflowAuditMirrorManifest) and row not in self.manifest_events:
            self.manifest_events.append(row)

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
        for index, event in enumerate(self.manifest_events, start=1):
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


def _mirror_event(**overrides) -> ClinicalWorkflowAuditMirrorEvent:
    values = {
        "operation_id": "manifest-op-001",
        "mirror_mode": "local_filesystem",
        "mirror_status": AUDIT_MIRROR_STATUS_MIRRORED,
        "payload_profile": "audit_metadata",
        "mirrored_at": datetime(2026, 6, 13, 12, 0, tzinfo=UTC),
        "mirror_uri": "local-worm://clinical-audit/workflow-audit/quality.event_create/2026/06/manifest-op-001.json",
        "mirror_checksum": "sha256-manifest-001",
        "mirror_error": None,
        "dry_run": False,
    }
    values.update(overrides)
    return ClinicalWorkflowAuditMirrorEvent(**values)


class _FakeAzureBlobClient:
    def __init__(self) -> None:
        self.objects: dict[tuple[str, str], dict[str, object]] = {}

    def upload_object(
        self,
        *,
        container: str,
        name: str,
        data: bytes,
        metadata: dict[str, str],
        overwrite: bool = False,
    ) -> dict[str, object]:
        key = (container, name)
        if key in self.objects and not overwrite:
            raise RuntimeError("fake blob already exists")
        self.objects[key] = {
            "name": name,
            "data": data,
            "metadata": dict(metadata),
            "size_bytes": len(data),
            "etag": f"fake-etag-{len(self.objects) + 1}",
        }
        return self.objects[key]

    def get_object_properties(self, *, container: str, name: str) -> dict[str, object] | None:
        return self.objects.get((container, name))

    def list_objects(self, *, container: str, prefix: str) -> list[dict[str, object]]:
        return [
            value
            for (object_container, object_name), value in sorted(self.objects.items())
            if object_container == container and object_name.startswith(prefix)
        ]

    def download_object(self, *, container: str, name: str) -> bytes | None:
        item = self.objects.get((container, name))
        return item["data"] if item is not None else None


def _azure_mirror_config(**overrides) -> AuditMirrorConfig:
    values = {
        "mode": "object_storage",
        "object_provider": "azure_blob",
        "azure_account_url": "https://clinicalaudit.blob.core.windows.net",
        "azure_container": "clinical-audit-worm",
        "azure_prefix": "workflow-audit",
        "azure_credential_mode": "managed_identity",
    }
    values.update(overrides)
    return AuditMirrorConfig(**values)


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


def test_audit_mirror_provider_registry_returns_local_filesystem_provider() -> None:
    provider = get_audit_mirror_provider(AuditMirrorConfig(mode="local_filesystem"))

    assert isinstance(provider, LocalFilesystemAuditMirrorProvider)
    assert provider.capabilities()["put_object"] is True
    assert provider.capabilities()["verify_object_checksum"] is True


def test_local_filesystem_provider_remains_compatible_with_mirror_output(tmp_path: Path) -> None:
    db = _WorkflowAuditDb()
    mirror_config = AuditMirrorConfig(mode="local_filesystem", local_root=tmp_path / "worm")
    append_workflow_operation(
        _operation(operation_id="provider-local-op"),
        path=tmp_path / "workflow_operations.json",
        db=db,
        object_mirror_config=mirror_config,
    )
    event = db.mirror_events[0]
    provider = get_audit_mirror_provider(mirror_config)

    stat = provider.stat_object(event.mirror_uri)
    verification = provider.verify_object_checksum(event.mirror_uri, event.mirror_checksum)

    assert stat.exists is True
    assert stat.checksum == event.mirror_checksum
    assert verification["status"] == "verified"


def test_azure_blob_provider_config_validation_fails_when_required_settings_missing() -> None:
    provider = get_audit_mirror_provider(
        AuditMirrorConfig(
            mode="object_storage",
            object_provider="azure_blob",
            object_container="",
            object_prefix="",
        )
    )

    codes = {issue.code for issue in provider.validate_config()}

    assert isinstance(provider, AzureBlobAuditMirrorProvider)
    assert "azure_account_url_missing" in codes
    assert "azure_container_missing" in codes
    assert "azure_prefix_missing" in codes
    assert "azure_credential_mode_missing" in codes


def test_azure_blob_provider_config_validation_passes_with_safe_placeholder_config() -> None:
    config = AuditMirrorConfig(
        mode="object_storage",
        object_provider="azure_blob",
        azure_account_url="https://clinicalaudit.blob.core.windows.net",
        azure_container="clinical-audit-worm",
        azure_prefix="workflow-audit",
        azure_credential_mode="managed_identity",
        azure_immutability_required=True,
        azure_legal_hold_required=True,
        azure_checksum_validation_required=True,
        retention_policy="RET-7Y-WORM",
        legal_hold_reference="LH-CLINICAL-AUDIT",
    )
    summary = provider_readiness_summary(config)

    assert summary["ready"] is True
    assert summary["provider"] == "azure_blob"
    assert summary["expected_uri_prefix"] == "https://clinicalaudit.blob.core.windows.net/clinical-audit-worm/workflow-audit"
    assert summary["capabilities"]["supports_immutability"] is True
    assert summary["capabilities"]["supports_legal_hold"] is True
    assert summary["capabilities"]["supports_retention_policy"] is True
    assert summary["azure"]["credential_mode"] == "managed_identity"


def test_azure_blob_provider_readiness_does_not_import_sdk_for_dry_run() -> None:
    config = AuditMirrorConfig(
        mode="object_storage",
        object_provider="azure_blob",
        azure_account_url="https://clinicalaudit.blob.core.windows.net",
        azure_container="clinical-audit-worm",
        azure_prefix="workflow-audit",
        azure_credential_mode="managed_identity",
    )
    provider = get_audit_mirror_provider(config)

    summary = provider.readiness_summary()
    verification = provider.verify_object_checksum("https://example.invalid/blob.json", "sha256-placeholder")

    assert isinstance(provider, AzureBlobAuditMirrorProvider)
    assert provider.sdk_imported is False
    assert summary["network_calls_performed"] is False
    assert verification["status"] == "not_checked"
    assert provider.sdk_imported is False


def test_azure_blob_provider_constructs_without_sdk_when_real_io_disabled() -> None:
    provider = AzureBlobAuditMirrorProvider(_azure_mirror_config())
    provider.sdk_available = lambda: False
    provider.identity_sdk_available = lambda: False

    summary = provider.readiness_summary()

    assert provider.sdk_imported is False
    assert summary["sdk_available"] is False
    assert summary["real_io_enabled"] is False
    assert summary["ready"] is True
    assert summary["no_network_dry_run"]["network_calls_performed"] is False


def test_azure_blob_provider_real_io_path_fails_clearly_when_sdk_missing() -> None:
    provider = AzureBlobAuditMirrorProvider(_azure_mirror_config(azure_enable_real_io=True))
    provider._require_sdk = lambda: (_ for _ in ()).throw(RuntimeError("Azure Blob SDK is not installed"))

    with pytest.raises(RuntimeError, match="Azure Blob SDK is not installed"):
        provider.put_object("workflow-audit/quality.event_create/2026/06/sdk-missing.json", {"payload": True}, "sha256")


def test_azure_blob_provider_fake_client_put_object_stores_payload_and_metadata() -> None:
    fake_client = _FakeAzureBlobClient()
    provider = AzureBlobAuditMirrorProvider(_azure_mirror_config(), client=fake_client)
    payload = audit_mirror_payload(_operation(operation_id="azure-put-op"))
    checksum = audit_mirror_checksum(payload)

    stat = provider.put_object(
        "workflow-audit/quality.event_create/2026/06/azure-put-op.json",
        payload,
        checksum,
    )

    stored = fake_client.objects[("clinical-audit-worm", "workflow-audit/quality.event_create/2026/06/azure-put-op.json")]
    assert stat.exists is True
    assert stat.uri == "https://clinicalaudit.blob.core.windows.net/clinical-audit-worm/workflow-audit/quality.event_create/2026/06/azure-put-op.json"
    assert stat.checksum == checksum
    assert json.loads(stored["data"].decode("utf-8")) == payload
    assert stored["metadata"]["audit_checksum"] == checksum
    assert stored["metadata"]["payload_profile"] == "audit_metadata"


def test_azure_blob_provider_fake_client_put_object_is_idempotent_for_matching_checksum() -> None:
    fake_client = _FakeAzureBlobClient()
    provider = AzureBlobAuditMirrorProvider(_azure_mirror_config(), client=fake_client)
    payload = audit_mirror_payload(_operation(operation_id="azure-idempotent-op"))
    checksum = audit_mirror_checksum(payload)
    key = "workflow-audit/quality.event_create/2026/06/azure-idempotent-op.json"

    first = provider.put_object(key, payload, checksum)
    second = provider.put_object(key, payload, checksum)

    assert first.uri == second.uri
    assert second.reason is None
    assert len(fake_client.objects) == 1


def test_azure_blob_provider_fake_client_put_object_detects_existing_checksum_mismatch() -> None:
    fake_client = _FakeAzureBlobClient()
    provider = AzureBlobAuditMirrorProvider(_azure_mirror_config(), client=fake_client)
    payload = audit_mirror_payload(_operation(operation_id="azure-mismatch-existing-op"))
    checksum = audit_mirror_checksum(payload)
    key = "workflow-audit/quality.event_create/2026/06/azure-mismatch-existing-op.json"

    provider.put_object(key, payload, checksum)
    stat = provider.put_object(key, payload, "different-checksum")

    assert stat.exists is True
    assert stat.checksum == checksum
    assert stat.reason == "existing object checksum differs"


def test_azure_blob_provider_fake_client_stat_and_metadata_return_expected_values() -> None:
    fake_client = _FakeAzureBlobClient()
    provider = AzureBlobAuditMirrorProvider(_azure_mirror_config(), client=fake_client)
    payload = audit_mirror_payload(_operation(operation_id="azure-stat-op"))
    checksum = audit_mirror_checksum(payload)
    uri = provider.put_object(
        "workflow-audit/quality.event_create/2026/06/azure-stat-op.json",
        payload,
        checksum,
    ).uri

    stat = provider.stat_object(uri)
    metadata = provider.read_object_metadata(uri)

    assert stat.exists is True
    assert stat.checksum == checksum
    assert metadata["exists"] is True
    assert metadata["audit_checksum"] == checksum
    assert metadata["blob_name"] == "workflow-audit/quality.event_create/2026/06/azure-stat-op.json"


def test_azure_blob_provider_fake_client_list_objects_returns_prefix_matches() -> None:
    fake_client = _FakeAzureBlobClient()
    provider = AzureBlobAuditMirrorProvider(_azure_mirror_config(), client=fake_client)
    payload = audit_mirror_payload(_operation(operation_id="azure-list-op"))
    checksum = audit_mirror_checksum(payload)
    provider.put_object("workflow-audit/quality.event_create/2026/06/azure-list-op.json", payload, checksum)
    provider.put_object("workflow-audit/orders.result_add/2026/06/azure-list-other-op.json", payload, checksum)

    matches = provider.list_objects("workflow-audit/quality.event_create")

    assert [item.metadata["blob_name"] for item in matches] == [
        "workflow-audit/quality.event_create/2026/06/azure-list-op.json"
    ]
    assert matches[0].checksum == checksum


def test_azure_blob_provider_fake_client_checksum_verification_passes_for_match() -> None:
    fake_client = _FakeAzureBlobClient()
    provider = AzureBlobAuditMirrorProvider(_azure_mirror_config(), client=fake_client)
    payload = audit_mirror_payload(_operation(operation_id="azure-verify-op"))
    checksum = audit_mirror_checksum(payload)
    uri = provider.put_object(
        "workflow-audit/quality.event_create/2026/06/azure-verify-op.json",
        payload,
        checksum,
    ).uri

    result = provider.verify_object_checksum(uri, checksum)

    assert result["status"] == "verified"
    assert result["computed_checksum"] == checksum


def test_azure_blob_provider_fake_client_checksum_verification_fails_for_mismatch() -> None:
    fake_client = _FakeAzureBlobClient()
    provider = AzureBlobAuditMirrorProvider(_azure_mirror_config(), client=fake_client)
    payload = audit_mirror_payload(_operation(operation_id="azure-verify-mismatch-op"))
    checksum = audit_mirror_checksum(payload)
    uri = provider.put_object(
        "workflow-audit/quality.event_create/2026/06/azure-verify-mismatch-op.json",
        payload,
        checksum,
    ).uri

    result = provider.verify_object_checksum(uri, "different-checksum")

    assert result["status"] == "checksum_mismatch"
    assert result["computed_checksum"] == checksum


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


def test_manifest_signing_payload_is_canonical_and_deterministic() -> None:
    first = canonical_signing_payload({"b": 2, "a": {"d": 4, "c": 3}})
    second = canonical_signing_payload({"a": {"c": 3, "d": 4}, "b": 2})

    assert first == second
    assert first == '{"a":{"c":3,"d":4},"b":2}'


def test_local_hmac_manifest_signature_is_deterministic() -> None:
    config = AuditManifestSigningConfig(
        mode=SIGNING_MODE_LOCAL_HMAC_SHA256,
        required=True,
        algorithm=ALGORITHM_LOCAL_HMAC_SHA256,
        key_ref="local-dev-hmac-key-v1",
        local_hmac_key="test-only-local-hmac-secret",
    )

    first = sign_manifest_checksum("sha256-manifest-checksum", config)
    second = sign_manifest_checksum("sha256-manifest-checksum", config)

    assert first == second
    assert first.status == SIGNATURE_STATUS_SIGNED
    assert first.signature is not None
    assert first.signature.startswith("hmac-sha256:")


def test_audit_mirror_manifest_generation_is_deterministic_and_includes_inventory() -> None:
    generated_at = datetime(2026, 6, 13, 13, 0, tzinfo=UTC)
    config = AuditManifestConfig(
        environment="test",
        generated_by="audit-system",
        mirror_mode="local_filesystem",
        provider="local",
        uri_prefix="local-worm://clinical-audit",
        retention_policy="RET-7Y-WORM",
        legal_hold=True,
        legal_hold_reference="LH-CLINICAL-001",
        signature_required=True,
        signature_key_ref="local-placeholder-key-v1",
    )
    events = [
        _mirror_event(operation_id="manifest-op-002", mirror_checksum="sha256-002"),
        _mirror_event(operation_id="manifest-op-001", mirror_checksum="sha256-001"),
    ]

    first = generate_audit_mirror_manifest(events, config=config, generated_at=generated_at)
    second = generate_audit_mirror_manifest(events, config=config, generated_at=generated_at)
    unsigned = {
        key: value
        for key, value in first.items()
        if key not in {"manifest_checksum", "signature", "signature_reason"}
    }

    assert first == second
    assert first["audit_event_count"] == 2
    assert first["operation_ids"] == ["manifest-op-001", "manifest-op-002"]
    assert [item["checksum"] for item in first["objects"]] == ["sha256-001", "sha256-002"]
    assert first["retention"]["policy_reference"] == "RET-7Y-WORM"
    assert first["retention"]["legal_hold"] is True
    assert first["signing_mode"] == "checksum_placeholder"
    assert first["signature_status"] == "checksum_placeholder"
    assert first["signature"].startswith("placeholder:")
    assert "not a cryptographic signature" in first["signature_reason"]
    assert first["manifest_checksum"] == audit_manifest_checksum(unsigned)


def test_local_hmac_manifest_signature_verifies_successfully() -> None:
    generated_at = datetime(2026, 6, 13, 13, 0, tzinfo=UTC)
    config = AuditManifestConfig(
        environment="test",
        mirror_mode="local_filesystem",
        signature_required=True,
        signing_mode=SIGNING_MODE_LOCAL_HMAC_SHA256,
        signature_algorithm=ALGORITHM_LOCAL_HMAC_SHA256,
        signature_key_ref="local-dev-hmac-key-v1",
        local_hmac_key="test-only-local-hmac-secret",
    )

    manifest = generate_audit_mirror_manifest(
        [_mirror_event(operation_id="signed-manifest-op", mirror_checksum="sha256-signed")],
        config=config,
        generated_at=generated_at,
    )
    verification = verify_audit_mirror_manifest(manifest, signing_config=config.signing_config())

    assert manifest["signature_status"] == "signed"
    assert manifest["signature_algorithm"] == "hmac-sha256"
    assert manifest["signature_key_ref"] == "local-dev-hmac-key-v1"
    assert manifest["signature"].startswith("hmac-sha256:")
    assert verification["checksum_status"] == "verified"
    assert verification["signature_verification_status"] == SIGNATURE_VERIFICATION_VERIFIED
    assert verification["verified"] is True


def test_local_hmac_manifest_signature_fails_after_tampering() -> None:
    config = AuditManifestConfig(
        environment="test",
        mirror_mode="local_filesystem",
        signature_required=True,
        signing_mode=SIGNING_MODE_LOCAL_HMAC_SHA256,
        signature_algorithm=ALGORITHM_LOCAL_HMAC_SHA256,
        signature_key_ref="local-dev-hmac-key-v1",
        local_hmac_key="test-only-local-hmac-secret",
    )
    manifest = generate_audit_mirror_manifest(
        [_mirror_event(operation_id="tampered-manifest-op", mirror_checksum="sha256-original")],
        config=config,
        generated_at=datetime(2026, 6, 13, 13, 0, tzinfo=UTC),
    )

    manifest["objects"][0]["checksum"] = "sha256-tampered"
    verification = verify_audit_mirror_manifest(manifest, signing_config=config.signing_config())

    assert verification["checksum_status"] == "checksum_mismatch"
    assert verification["signature_verification_status"] == "failed"
    assert verification["blocking"] is True


def test_external_kms_placeholder_manifest_verification_is_pending() -> None:
    config = AuditManifestConfig(
        environment="test",
        mirror_mode="local_filesystem",
        signature_required=True,
        signing_mode="external_kms_placeholder",
        signature_algorithm="rsa-pss-sha256",
        signature_key_ref="kms://clinical-audit-manifest-key-v1",
    )
    manifest = generate_audit_mirror_manifest(
        [_mirror_event(operation_id="external-kms-placeholder-op", mirror_checksum="sha256-kms")],
        config=config,
        generated_at=datetime(2026, 6, 13, 13, 0, tzinfo=UTC),
    )

    verification = verify_audit_mirror_manifest(manifest, signing_config=config.signing_config())

    assert manifest["signature_status"] == "pending_provider_signature"
    assert manifest["signature"] is None
    assert verification["checksum_status"] == "verified"
    assert verification["signature_verification_status"] == "pending_provider_verification"
    assert verification["blocking"] is False


def test_audit_mirror_manifest_checksum_changes_when_inventory_changes() -> None:
    config = AuditManifestConfig(environment="test", mirror_mode="local_filesystem")
    generated_at = datetime(2026, 6, 13, 13, 0, tzinfo=UTC)

    base = generate_audit_mirror_manifest(
        [_mirror_event(operation_id="manifest-op-001", mirror_checksum="sha256-001")],
        config=config,
        generated_at=generated_at,
    )
    changed = generate_audit_mirror_manifest(
        [
            _mirror_event(operation_id="manifest-op-001", mirror_checksum="sha256-001"),
            _mirror_event(operation_id="manifest-op-002", mirror_checksum="sha256-002"),
        ],
        config=config,
        generated_at=generated_at,
    )

    assert base["manifest_checksum"] != changed["manifest_checksum"]
    assert base["manifest_id"] != changed["manifest_id"]


def test_audit_mirror_manifest_persistence_records_append_only_metadata() -> None:
    db = _WorkflowAuditDb()
    manifest = generate_audit_mirror_manifest(
        [_mirror_event(operation_id="persisted-manifest-op", mirror_checksum="sha256-persisted")],
        config=AuditManifestConfig(environment="test", mirror_mode="local_filesystem"),
        generated_at=datetime(2026, 6, 13, 13, 0, tzinfo=UTC),
    )

    row = record_audit_mirror_manifest(db, manifest)

    assert row in db.manifest_events
    assert row.id == 1
    assert row.manifest_id == manifest["manifest_id"]
    assert row.manifest_checksum == manifest["manifest_checksum"]
    assert row.audit_event_count == 1
    assert row.manifest_status == "generated"
    assert db.committed is True


def test_audit_mirror_manifest_persistence_records_signing_metadata() -> None:
    db = _WorkflowAuditDb()
    config = AuditManifestConfig(
        environment="test",
        mirror_mode="local_filesystem",
        signature_required=True,
        signing_mode=SIGNING_MODE_LOCAL_HMAC_SHA256,
        signature_algorithm=ALGORITHM_LOCAL_HMAC_SHA256,
        signature_key_ref="local-dev-hmac-key-v1",
        local_hmac_key="test-only-local-hmac-secret",
    )
    manifest = generate_audit_mirror_manifest(
        [_mirror_event(operation_id="persisted-signed-manifest-op", mirror_checksum="sha256-signed")],
        config=config,
        generated_at=datetime(2026, 6, 13, 13, 0, tzinfo=UTC),
    )

    row = record_audit_mirror_manifest(db, manifest)

    assert row.signature_status == "signed"
    assert row.signature_algorithm == "hmac-sha256"
    assert row.signature_key_ref == "local-dev-hmac-key-v1"


def test_local_mirror_verification_passes_for_valid_payload(tmp_path: Path) -> None:
    db = _WorkflowAuditDb()
    mirror_config = AuditMirrorConfig(mode="local_filesystem", local_root=tmp_path / "worm")
    append_workflow_operation(
        _operation(operation_id="verify-valid-op"),
        path=tmp_path / "workflow_operations.json",
        db=db,
        object_mirror_config=mirror_config,
    )

    result = verify_mirror_inventory(db.mirror_events, config=mirror_config)

    assert result["checked"] == 1
    assert result["verified"] == 1
    assert result["missing"] == 0
    assert result["mismatched"] == 0


def test_local_mirror_verification_detects_missing_payload(tmp_path: Path) -> None:
    db = _WorkflowAuditDb()
    mirror_config = AuditMirrorConfig(mode="local_filesystem", local_root=tmp_path / "worm")
    append_workflow_operation(
        _operation(operation_id="verify-missing-op"),
        path=tmp_path / "workflow_operations.json",
        db=db,
        object_mirror_config=mirror_config,
    )
    for mirror_file in mirror_config.local_root.rglob("*.json"):
        mirror_file.unlink()

    result = verify_mirror_inventory(db.mirror_events, config=mirror_config)

    assert result["verified"] == 0
    assert result["missing"] == 1
    assert result["results"][0]["status"] == "missing"


def test_local_mirror_verification_detects_checksum_mismatch(tmp_path: Path) -> None:
    db = _WorkflowAuditDb()
    mirror_config = AuditMirrorConfig(mode="local_filesystem", local_root=tmp_path / "worm")
    append_workflow_operation(
        _operation(operation_id="verify-mismatch-op"),
        path=tmp_path / "workflow_operations.json",
        db=db,
        object_mirror_config=mirror_config,
    )
    mirror_file = next(mirror_config.local_root.rglob("*.json"))
    mirror_file.write_text(json.dumps({"tampered": True}, indent=2), encoding="utf-8")

    result = verify_mirror_inventory(db.mirror_events, config=mirror_config)

    assert result["verified"] == 0
    assert result["mismatched"] == 1
    assert result["results"][0]["status"] == "checksum_mismatch"


def test_mirror_verification_detects_manifest_object_mismatch(tmp_path: Path) -> None:
    db = _WorkflowAuditDb()
    mirror_config = AuditMirrorConfig(mode="local_filesystem", local_root=tmp_path / "worm")
    append_workflow_operation(
        _operation(operation_id="verify-manifest-mismatch-op"),
        path=tmp_path / "workflow_operations.json",
        db=db,
        object_mirror_config=mirror_config,
    )
    manifest = generate_audit_mirror_manifest(
        db.mirror_events,
        config=AuditManifestConfig(environment="test", mirror_mode="local_filesystem"),
        generated_at=datetime(2026, 6, 13, 13, 0, tzinfo=UTC),
    )
    manifest["objects"][0]["checksum"] = "sha256-wrong"

    result = verify_mirror_inventory(db.mirror_events, config=mirror_config, manifest=manifest)

    assert result["manifest_mismatched"] == 1
    assert result["results"][0]["status"] == "manifest_mismatch"


def test_azure_blob_provider_fake_client_participates_in_inventory_verification() -> None:
    fake_client = _FakeAzureBlobClient()
    mirror_config = _azure_mirror_config()
    provider = AzureBlobAuditMirrorProvider(mirror_config, client=fake_client)
    payload = audit_mirror_payload(_operation(operation_id="azure-inventory-op"))
    checksum = audit_mirror_checksum(payload)
    uri = provider.put_object(
        "workflow-audit/quality.event_create/2026/06/azure-inventory-op.json",
        payload,
        checksum,
    ).uri
    mirror_events = [
        _mirror_event(
            operation_id="azure-inventory-op",
            mirror_mode="object_storage",
            mirror_uri=uri,
            mirror_checksum=checksum,
        )
    ]

    result = verify_mirror_inventory(mirror_events, config=mirror_config, provider=provider)

    assert result["provider"] == "azure_blob"
    assert result["verified"] == 1
    assert result["missing"] == 0
    assert result["mismatched"] == 0
    assert result["results"][0]["computed_checksum"] == checksum


def test_audit_mirror_recovery_drill_compares_db_rows_to_mirror_records(tmp_path: Path) -> None:
    db = _WorkflowAuditDb()
    mirror_config = AuditMirrorConfig(mode="local_filesystem", local_root=tmp_path / "worm")
    append_workflow_operation(
        _operation(operation_id="recovery-mirrored-op"),
        path=tmp_path / "workflow_operations.json",
        db=db,
        object_mirror_config=mirror_config,
    )
    db.add(workflow_operation_to_audit_event(_operation(operation_id="recovery-missing-op")))
    db.flush()

    result = audit_mirror_recovery_drill_summary(db, config=mirror_config)

    assert result["source_deleted"] is False
    assert result["selected_audit_event_count"] == 2
    assert result["successful_mirror_event_count"] == 1
    assert result["missing_mirror_count"] == 1
    assert result["missing_mirror_operation_ids"] == ["recovery-missing-op"]
    assert result["verification"]["verified"] == 1
    assert result["recovery_ready"] is False


def test_audit_mirror_recovery_drill_includes_provider_readiness_summary(tmp_path: Path) -> None:
    db = _WorkflowAuditDb()
    mirror_config = AuditMirrorConfig(mode="local_filesystem", local_root=tmp_path / "worm")
    append_workflow_operation(
        _operation(operation_id="recovery-provider-op"),
        path=tmp_path / "workflow_operations.json",
        db=db,
        object_mirror_config=mirror_config,
    )

    result = audit_mirror_recovery_drill_summary(db, config=mirror_config)

    assert result["provider_readiness"]["provider"] == "local_filesystem"
    assert result["provider_readiness"]["ready"] is True
    assert result["provider_readiness"]["expected_uri_prefix"] == "local-worm://clinical-audit/workflow-audit"
    assert result["provider_readiness"]["capabilities"]["verify_object_checksum"] is True
    assert result["manifest_count"] == 0
    assert result["mirrored_object_count"] == 1


def test_audit_mirror_recovery_drill_includes_signature_verification_status(tmp_path: Path) -> None:
    db = _WorkflowAuditDb()
    mirror_config = AuditMirrorConfig(mode="local_filesystem", local_root=tmp_path / "worm")
    append_workflow_operation(
        _operation(operation_id="recovery-signed-manifest-op"),
        path=tmp_path / "workflow_operations.json",
        db=db,
        object_mirror_config=mirror_config,
    )
    manifest_config = AuditManifestConfig(
        environment="test",
        mirror_mode="local_filesystem",
        signature_required=True,
        signing_mode=SIGNING_MODE_LOCAL_HMAC_SHA256,
        signature_algorithm=ALGORITHM_LOCAL_HMAC_SHA256,
        signature_key_ref="local-dev-hmac-key-v1",
        local_hmac_key="test-only-local-hmac-secret",
    )
    manifest = generate_audit_mirror_manifest(
        db.mirror_events,
        config=manifest_config,
        generated_at=datetime(2026, 6, 13, 13, 0, tzinfo=UTC),
    )

    result = audit_mirror_recovery_drill_summary(
        db,
        config=mirror_config,
        manifest=manifest,
        manifest_signing_config=manifest_config.signing_config(),
    )

    assert result["manifest_signature_verification"]["checksum_status"] == "verified"
    assert result["manifest_signature_verification"]["signature_verification_status"] == "verified"
    assert result["manifest_signature_verification"]["blocking"] is False


def test_audit_mirror_recovery_drill_includes_azure_real_io_state() -> None:
    fake_client = _FakeAzureBlobClient()
    mirror_config = _azure_mirror_config(azure_enable_real_io=True)
    provider = AzureBlobAuditMirrorProvider(mirror_config, client=fake_client)
    operation = _operation(operation_id="azure-recovery-op")
    payload = audit_mirror_payload(operation)
    checksum = audit_mirror_checksum(payload)
    uri = provider.put_object(
        "workflow-audit/quality.event_create/2026/06/azure-recovery-op.json",
        payload,
        checksum,
    ).uri
    db = _WorkflowAuditDb(
        audit_events=[workflow_operation_to_audit_event(operation)],
        mirror_events=[
            _mirror_event(
                operation_id="azure-recovery-op",
                mirror_mode="object_storage",
                mirror_uri=uri,
                mirror_checksum=checksum,
            )
        ],
    )
    db.flush()

    result = audit_mirror_recovery_drill_summary(db, config=mirror_config, provider=provider)

    assert result["provider_readiness"]["provider"] == "azure_blob"
    assert result["provider_readiness"]["real_io_enabled"] is True
    assert result["provider_readiness"]["client_injected"] is True
    assert result["verification"]["provider"] == "azure_blob"
    assert result["verification"]["verified"] == 1
