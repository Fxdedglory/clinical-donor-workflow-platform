from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.core.config import settings
from app.schemas.clinical import WorkflowOperation
from app.services.clinical_audit_mirror import (
    audit_mirror_checksum,
    audit_mirror_config_from_settings,
    audit_mirror_payload,
)
from app.services.clinical_audit_mirror_providers import AzureBlobAuditMirrorProvider
from app.services.clinical_azure_worm_live_readiness import (
    LIVE_TESTS_ENV,
    build_live_readiness_report,
    live_test_prefix,
)

pytestmark = [
    pytest.mark.azure_worm_live,
    pytest.mark.skipif(
        not build_live_readiness_report()["live_tests_enabled"],
        reason=f"Azure WORM live tests require {LIVE_TESTS_ENV}=true.",
    ),
]


def _live_config():
    return audit_mirror_config_from_settings(settings)


def _live_provider() -> AzureBlobAuditMirrorProvider:
    config = _live_config()
    report = build_live_readiness_report(config=config)
    assert not report["blocking_issues"], report
    assert report["provider_readiness"]["ready"] is True, report
    return AzureBlobAuditMirrorProvider(config)


def _operation() -> WorkflowOperation:
    return WorkflowOperation(
        operation_id=f"azure-live-readiness-{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}",
        workflow="audit.azure_worm_live_readiness",
        entity_type="clinical_audit_worm_live_test",
        entity_id="AZURE-WORM-LIVE-READINESS",
        actor="azure-worm-live-readiness",
        timestamp=datetime.now(UTC),
        preview_hash="sha256-live-readiness",
        commit_confirmed=True,
        status_before="planned",
        status_after="validated",
        reason="Validate Azure WORM live integration readiness harness",
        changes={"live_readiness": True, "payload_profile": "audit_metadata"},
    )


def test_live_azure_provider_readiness_requires_explicit_safe_configuration() -> None:
    config = _live_config()
    report = build_live_readiness_report(config=config)

    assert report["live_tests_enabled"] is True
    assert report["real_io_enabled"] is True
    assert report["ready_for_live_validation"] is True
    assert not report["blocking_issues"]
    assert report["provider_readiness"]["provider"] == "azure_blob"


def test_live_azure_provider_can_construct_real_io_client_only_when_enabled() -> None:
    provider = _live_provider()

    client = provider._operation_client()

    assert client is not None


def test_live_azure_put_stat_list_checksum_under_dedicated_test_prefix() -> None:
    provider = _live_provider()
    operation = _operation()
    payload = audit_mirror_payload(operation)
    checksum = audit_mirror_checksum(payload)
    key = f"{live_test_prefix()}/{operation.workflow}/live-readiness/{operation.operation_id}.json"

    written = provider.put_object(key, payload, checksum)
    stat = provider.stat_object(written.uri)
    matches = provider.list_objects(f"{live_test_prefix()}/{operation.workflow}/live-readiness")
    verification = provider.verify_object_checksum(written.uri, checksum)

    assert written.exists is True
    assert stat.exists is True
    assert any(item.uri == written.uri for item in matches)
    assert verification["status"] == "verified"
