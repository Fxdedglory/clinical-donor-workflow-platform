from pathlib import Path

import pytest
from app import main as clinical_main
from app.database import get_db
from app.main import app
from app.services.adls_historical import run_clinical_historical_adls_upload
from app.services.adls_smoke import (
    CONFIRMATION_PHRASE,
    create_tiny_adls_smoke_batch,
    run_adls_smoke_upload,
)
from app.services.data_producer import CONFORMED_SITES, EXPORT_METADATA_FIELDS, _product_context
from app.services.data_scale_profiles import profile_as_dict, resolve_profile
from fastapi.testclient import TestClient


def test_app_service_startup_uses_packaged_dependencies_without_runtime_install() -> None:
    startup_script = Path("scripts/start_app_service.py").read_text(encoding="utf-8")

    assert "python_packages" in startup_script
    assert "pip install" not in startup_script
    assert "--check" in startup_script


class _ScalarResult:
    def scalar_one_or_none(self):
        return None


class _FakeSession:
    def __init__(self) -> None:
        self.added = []
        self.committed = False

    def execute(self, *_args, **_kwargs):
        return _ScalarResult()

    def add(self, value):
        self.added.append(value)

    def flush(self) -> None:
        return None

    def commit(self) -> None:
        self.committed = True


def _override_db(fake_session):
    def _dependency():
        yield fake_session

    return _dependency


def test_api_health_returns_runtime_metadata() -> None:
    response = TestClient(app).get("/api/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["startup_mode"] == "fastapi_react"
    assert payload["version"]


def test_api_health_includes_timing_headers() -> None:
    response = TestClient(app).get("/api/health")

    assert response.status_code == 200
    assert response.headers["x-request-id"]
    assert float(response.headers["x-response-time-ms"]) >= 0
    assert response.headers["server-timing"].startswith("app;dur=")


def test_auth_experience_routes_serve_frontend_shell() -> None:
    client = TestClient(app)

    for path in [
        "/dashboard",
        "/referrals",
        "/screening",
        "/clinical-review",
        "/eligibility",
        "/recovery-cases",
        "/partner-portal",
        "/qms",
        "/capa",
        "/vendor-sla",
        "/documents",
        "/audit",
        "/data-producer",
        "/health",
        "/login",
        "/logout",
        "/forgot-password",
        "/reset-password",
        "/request-access",
        "/profile",
        "/preferences",
    ]:
        response = client.get(path, headers={"accept": "text/html"})
        assert response.status_code == 200, path
        assert "text/html" in response.headers.get("content-type", ""), path


def test_public_access_request_accepts_partner_supplier_only_and_audits() -> None:
    fake_session = _FakeSession()
    app.dependency_overrides[get_db] = _override_db(fake_session)
    client = TestClient(app)
    try:
        response = client.post(
            "/api/auth/access-request",
            json={
                "full_name": "ADLS Smoke Partner",
                "email": "adls.smoke.partner@example.com",
                "organization_name": "Example Recovery Partner",
                "request_type": "Supplier",
                "requested_role": "Operations Manager",
                "business_reason": "Partner portal qualification review",
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "access_request_received"
    assert "supplier access request" in payload["message"]
    assert fake_session.committed is True
    event = fake_session.added[-1]
    assert event.event_type == "ACCESS_REQUEST_SUBMITTED"
    assert event.route == "/api/auth/access-request"
    assert event.details["request_type"] == "Supplier"
    assert event.details["auto_assigned_role"] == "Supplier External User"
    assert event.details["requested_role_ignored"] == "Operations Manager"


def test_prefixed_access_request_api_accepts_post() -> None:
    fake_session = _FakeSession()
    app.dependency_overrides[get_db] = _override_db(fake_session)
    try:
        response = TestClient(app).post(
            "/Clinical/api/auth/access-request",
            json={
                "full_name": "Prefixed Partner",
                "email": "prefixed.partner@example.com",
                "organization_name": "Prefixed Partner Org",
                "request_type": "Partner",
                "business_reason": "Direct prefixed route smoke",
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["status"] == "access_request_received"


def test_public_access_request_rejects_internal_request_type() -> None:
    response = TestClient(app).post(
        "/api/auth/access-request",
        json={
            "full_name": "Internal Request",
            "email": "internal.request@example.com",
            "organization_name": "Internal",
            "request_type": "Clinical Reviewer",
            "business_reason": "Should be admin assigned",
        },
    )

    assert response.status_code == 422


def test_forgot_password_response_is_enumeration_safe() -> None:
    fake_session = _FakeSession()
    app.dependency_overrides[get_db] = _override_db(fake_session)
    try:
        response = TestClient(app).post(
            "/api/auth/password-reset/request",
            json={"email": "not-a-real-clinical-user@example.com"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["status"] == "If the email matches an account in our system, a reset link will be sent."


def test_standard_monitoring_endpoints_return_required_fields() -> None:
    client = TestClient(app)
    required_fields = {
        "/api/monitoring/health": {
            "app_name",
            "environment",
            "status",
            "version",
            "build_sha",
            "timestamp_utc",
            "storage_backend",
            "database_status",
            "database_role",
            "database_ssl_status",
        },
        "/api/monitoring/source-freshness": {
            "app_name",
            "source_systems",
            "latest_generated_at",
            "latest_extraction_batch_id",
            "latest_validation_at",
            "latest_export_at",
            "freshness_status",
            "stale_threshold_minutes",
        },
        "/api/monitoring/validation": {
            "app_name",
            "latest_validation_status",
            "latest_validation_at",
            "errors_count",
            "warnings_count",
            "validation_summary",
        },
        "/api/monitoring/export-manifest": {
            "app_name",
            "latest_export_batch_id",
            "latest_export_at",
            "export_file_count",
            "export_row_count",
            "export_status",
        },
        "/api/monitoring/run-history": {"recent_generation_runs", "recent_validation_runs", "recent_export_runs"},
        "/api/monitoring/security-events": {"app_name", "events", "schema_fields"},
        "/api/monitoring/user-access": {"app_name", "events", "schema_fields"},
    }

    for path, fields in required_fields.items():
        response = client.get(path)
        assert response.status_code == 200, path
        payload = response.json()
        assert fields.issubset(payload), path


def test_monitoring_endpoints_do_not_expose_secret_values() -> None:
    client = TestClient(app)
    secret_markers = ["password", "secret_key", "connection_string", "database_url", "smtp_password"]

    for path in [
        "/api/monitoring/health",
        "/api/monitoring/source-freshness",
        "/api/monitoring/validation",
        "/api/monitoring/export-manifest",
        "/api/monitoring/run-history",
        "/api/monitoring/security-events",
        "/api/monitoring/user-access",
    ]:
        response = client.get(path)
        assert response.status_code == 200, path
        body = response.text.lower()
        assert not any(marker in body for marker in secret_markers), path


def test_enterprise_export_metadata_and_product_alignment() -> None:
    assert {site["site_id"] for site in CONFORMED_SITES} == {
        "SITE-ALACHUA",
        "SITE-WLAF",
        "SITE-EP",
        "SITE-GLENCOE",
        "SITE-NEUNK",
        "SITE-GLASGOW",
        "SITE-MARTON",
    }
    assert "source_record_id" in EXPORT_METADATA_FIELDS
    assert "source_table" in EXPORT_METADATA_FIELDS
    assert "generated_at" in EXPORT_METADATA_FIELDS
    assert _product_context("Dermal Matrix")["erp_material_family"] == "Allograft"


def test_clinical_data_scale_profiles_are_defined() -> None:
    demo = profile_as_dict(resolve_profile("demo"))
    enterprise = profile_as_dict(resolve_profile("enterprise"))

    assert demo["records"] == 500
    assert demo["incremental_scale"] == 1
    assert enterprise["records"] == 50000
    assert enterprise["incremental_scale"] == 25


def test_adls_smoke_upload_requires_confirmation() -> None:
    response = TestClient(app).post("/api/operations/adls-smoke-upload", json={})

    assert response.status_code == 409
    assert response.json()["detail"]["status"] == "confirmation_required"


def test_adls_smoke_batch_uses_expected_layout(tmp_path: Path) -> None:
    batch = create_tiny_adls_smoke_batch(
        tmp_path,
        source_system="clinical",
        batch_id="clinical_smoke_test",
    )

    assert batch["row_count"] == 1
    assert set(batch["uploaded_paths"]) == {
        "bronze/source_system=clinical/source_table=adls_smoke/"
        "extraction_date="
        + batch["extraction_date"]
        + "/extraction_batch_id=clinical_smoke_test/part-00000.parquet",
        "manifests/source_system=clinical/extraction_date="
        + batch["extraction_date"]
        + "/clinical_smoke_test.json",
        "_schemas/source_system=clinical/adls_smoke.json",
    }


def test_adls_smoke_endpoint_returns_schema(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(*, source_system: str) -> dict[str, object]:
        return {
            "source_system": source_system,
            "status": "uploaded",
            "file_count": 3,
            "row_count": 1,
            "uploaded_paths": ["bronze/source_system=clinical/source_table=adls_smoke/x.parquet"],
            "batch_id": "clinical_smoke_test",
            "auth_mode": "managed_identity",
            "account_name": "stteemailslakewcus",
            "container": "datalake",
            "error": None,
        }

    monkeypatch.setattr(clinical_main, "run_adls_smoke_upload", fake_run)
    response = TestClient(app).post(
        "/api/operations/adls-smoke-upload",
        json={"confirm": CONFIRMATION_PHRASE},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["source_system"] == "clinical"
    assert payload["auth_mode"] == "managed_identity"
    assert payload["file_count"] == 3
    assert payload["row_count"] == 1


def test_adls_smoke_runner_accepts_fake_uploader(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATA_LAKE_ACCOUNT_NAME", "stteemailslakewcus")

    def fake_upload(plan, account_name, container, auth_mode):
        assert account_name == "stteemailslakewcus"
        assert container == "datalake"
        assert auth_mode == "managed_identity"
        return [{"path": item["blob_name"], "status": "uploaded"} for item in plan]

    result = run_adls_smoke_upload(source_system="clinical", uploader=fake_upload)

    assert result["status"] == "uploaded"
    assert result["file_count"] == 3
    assert result["row_count"] == 1


def test_clinical_historical_adls_upload_uses_managed_identity(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("DATA_LAKE_ACCOUNT_NAME", "stteemailslakewcus")
    monkeypatch.setenv("DATA_LAKE_CONTAINER", "datalake")
    monkeypatch.setenv("DATA_LAKE_AUTH_MODE", "managed_identity")

    def fake_export(**kwargs):
        return {
            "manifest_path": str(tmp_path / "manifest.json"),
            "row_count": 2,
            "files": [
                {"source_table": "dim_donor", "row_count": 1, "extraction_date": "2026-05-30"},
                {"source_table": "fact_donor_screening", "row_count": 1, "extraction_date": "2026-05-30"},
            ],
        }

    def fake_upload(**kwargs):
        assert kwargs["auth_mode"] == "managed_identity"
        assert kwargs["account_name"] == "stteemailslakewcus"
        assert kwargs["container"] == "datalake"
        return {
            "file_count": 3,
            "files": [
                {
                    "blob_name": "bronze/source_system=clinical/source_table=dim_donor/"
                    "extraction_date=2026-05-30/extraction_batch_id=clinical_small_test/part-00000.parquet",
                    "status": "uploaded",
                },
                {
                    "blob_name": "bronze/source_system=clinical/source_table=fact_donor_screening/"
                    "extraction_date=2026-05-30/extraction_batch_id=clinical_small_test/part-00000.parquet",
                    "status": "uploaded",
                },
                {
                    "blob_name": "manifests/source_system=clinical/extraction_date=2026-05-30/clinical_small_test.json",
                    "status": "uploaded",
                },
            ],
        }

    result = run_clinical_historical_adls_upload(
        batch_id="clinical_small_test",
        lake_root=tmp_path,
        export_fn=fake_export,
        upload_fn=fake_upload,
    )

    assert result["status"] == "uploaded"
    assert result["auth_mode"] == "managed_identity"
    assert result["source_system"] == "clinical"
    assert result["batch_id"] == "clinical_small_test"
    assert result["row_count"] == 2
    assert result["file_count"] == 3
    assert result["source_table_count"] == 2
    assert any("source_table=dim_donor" in path for path in result["uploaded_paths"])
