from app.main import app
from app.services.data_producer import CONFORMED_SITES, EXPORT_METADATA_FIELDS, _product_context
from fastapi.testclient import TestClient


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
