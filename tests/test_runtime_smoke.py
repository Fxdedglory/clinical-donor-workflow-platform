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
