import json
import shutil
import subprocess
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]


def _run_node_privacy_probe() -> dict:
    node = shutil.which("node")
    if not node:
        pytest.skip("Node.js is required for frontend privacy helper checks")

    script = """
import {
  EXPORT_PROFILE_OPTIONS,
  displayClinicalValue,
  exportProfileInfo,
  formatSuppressedCell,
  suppressionSummary,
} from "./frontend/src/pages/clinical/clinicalPrivacyDisplay.js";

const external = { role_name: "Partner External User" };
const internal = { role_name: "Clinical Reviewer", permissions: ["patients.read"] };
const redacted = displayClinicalValue("PT-000001", "patient_id", external);
const internalValue = displayClinicalValue("PT-000001", "patient_id", internal);
const noRole = displayClinicalValue("Jane Donor", "patient_name", null);
const suppressed = formatSuppressedCell({
  value: 3,
  suppressed: true,
  suppression_reason: "small_cell",
  threshold: 5,
});
const profiles = Object.fromEntries(EXPORT_PROFILE_OPTIONS.map((item) => [item.value, exportProfileInfo(item.value)]));
const suppression = suppressionSummary({ small_cell_suppression: { applied: true, threshold: 5, suppressed_cells: 2 } });

console.log(JSON.stringify({ redacted, internalValue, noRole, suppressed, profiles, suppression }));
"""
    completed = subprocess.run(
        [node, "--input-type=module", "-e", script],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(completed.stdout)


def test_clinical_privacy_helper_redacts_external_and_unknown_role_values() -> None:
    data = _run_node_privacy_probe()

    assert data["redacted"]["kind"] == "redacted"
    assert data["redacted"]["label"] == "Redacted"
    assert data["redacted"]["indicator"] == "PHI protected"
    assert "PT-000001" not in json.dumps(data["redacted"])

    assert data["noRole"]["kind"] == "redacted"
    assert data["internalValue"] == {"kind": "value", "value": "PT-000001"}


def test_clinical_privacy_helper_formats_suppressed_cells_without_raw_counts() -> None:
    data = _run_node_privacy_probe()

    assert data["suppressed"]["suppressed"] is True
    assert data["suppressed"]["label"] == "Suppressed"
    assert data["suppressed"]["badge"] == "Small-cell suppression"
    assert data["suppressed"]["threshold"] == 5
    assert "value" not in data["suppressed"]
    assert "3" not in json.dumps(data["suppressed"])


def test_clinical_export_profile_labels_and_suppression_summary() -> None:
    data = _run_node_privacy_probe()

    assert data["profiles"]["aggregate_safe"]["label"] == "Aggregate safe"
    assert data["profiles"]["aggregate_safe"]["redactionActive"] is True
    assert data["profiles"]["aggregate_safe"]["suppressionActive"] is True
    assert data["profiles"]["external_safe"]["redactionActive"] is True
    assert "sensitive details" in data["profiles"]["compliance_evidence"]["warning"]
    assert data["suppression"] == {"applied": True, "threshold": 5, "suppressedCells": 2}


def test_clinical_privacy_component_sources_do_not_render_raw_suppressed_values() -> None:
    suppressed_source = (ROOT / "frontend/src/pages/clinical/ClinicalSuppressedMetric.jsx").read_text(encoding="utf-8")
    redacted_source = (ROOT / "frontend/src/pages/clinical/ClinicalRedactedValue.jsx").read_text(encoding="utf-8")
    app_source = (ROOT / "frontend/src/App.jsx").read_text(encoding="utf-8")

    assert "cell.value" not in suppressed_source
    assert "summary.value" not in suppressed_source
    assert "aria-label={`${summary.label}: ${summary.badge}`}" in suppressed_source
    assert "aria-label={`${label}: ${indicator}`}" in redacted_source
    assert "ClinicalPrivacyIndicator user={user}" in app_source
    assert "ExportProfileIndicator profile=" in app_source
    assert "JSON.stringify({ warnings: preview.warnings" not in app_source


def test_clinical_route_inventory_contains_required_shell_routes() -> None:
    routes_source = (ROOT / "frontend/src/pages/clinical/clinicalRoutes.jsx").read_text(encoding="utf-8")
    required_routes = [
        "/clinical/dashboard",
        "/clinical/patients",
        "/clinical/patients/:id",
        "/clinical/scheduling",
        "/clinical/screening",
        "/clinical/encounters",
        "/clinical/orders",
        "/clinical/care-plans",
        "/clinical/billing",
        "/clinical/quality",
        "/clinical/reports",
        "/clinical/admin",
    ]

    for route in required_routes:
        assert f'route: "{route}"' in routes_source


def test_clinical_identifier_component_keeps_dense_values_scannable() -> None:
    identifier_source = (ROOT / "frontend/src/pages/clinical/ClinicalIdentifier.jsx").read_text(encoding="utf-8")
    app_source = (ROOT / "frontend/src/App.jsx").read_text(encoding="utf-8")

    assert "export function clinicalCellKind" in identifier_source
    assert 'name.includes("email")' in identifier_source
    assert 'name.includes("phone")' in identifier_source
    assert 'return "identifier"' in identifier_source
    assert 'return "token"' in identifier_source
    assert "clinical-id clinical-truncate" in identifier_source
    assert "clinicalCellKind(field, text)" in app_source
    assert "clinicalCellKind(field, Array.isArray(value) ? value.length : value)" in app_source
    assert "density === \"compact\"" in app_source


def test_fe03_frontend_qa_documentation_tracks_routes_modals_and_evidence() -> None:
    doc_path = ROOT / "docs/clinical-fe03-final-frontend-qa.md"
    assert doc_path.exists()
    doc = doc_path.read_text(encoding="utf-8")

    assert "metadata/visual_audit/clinical/fe03_final_frontend_qa/" in doc
    assert "Preview -> Commit" in doc
    assert "Compact Table Regression" in doc
    assert "Route QA" in doc
    for route in [
        "/clinical/dashboard",
        "/clinical/patients",
        "/clinical/patients/:id",
        "/clinical/scheduling",
        "/clinical/screening",
        "/clinical/encounters",
        "/clinical/orders",
        "/clinical/care-plans",
        "/clinical/billing",
        "/clinical/quality",
        "/clinical/reports",
        "/clinical/admin",
    ]:
        assert route in doc


def test_shared_workflow_modal_css_covers_preview_commit_mobile_polish() -> None:
    styles = (ROOT / "frontend/src/styles.css").read_text(encoding="utf-8")

    assert ".preview-panel" in styles
    assert ".modal-actions" in styles
    assert "overscroll-behavior: contain" in styles
    assert "scrollbar-gutter: stable" in styles
    assert "@media (max-width: 620px)" in styles
    assert ".workflow-modal .modal-actions button" in styles
