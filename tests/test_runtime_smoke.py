from app.database import get_db
from app.main import app
from app.services.data_producer import CONFORMED_SITES, EXPORT_METADATA_FIELDS, _product_context
from app.services.data_scale_profiles import profile_as_dict, resolve_profile
from fastapi.testclient import TestClient


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
