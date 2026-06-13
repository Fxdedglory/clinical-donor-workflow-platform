from pathlib import Path

from app.main import app

ROOT = Path(__file__).resolve().parents[1]

CLINICAL_PREFIX = "/api/clinical"


def _clinical_routes() -> set[tuple[str, str]]:
    routes: set[tuple[str, str]] = set()
    for route in app.routes:
        path = getattr(route, "path", "")
        if not path.startswith(CLINICAL_PREFIX):
            continue
        for method in getattr(route, "methods", set()) or set():
            if method in {"HEAD", "OPTIONS"}:
                continue
            routes.add((method, path))
    return routes


def _classify(method: str, path: str) -> set[str]:
    categories: set[str] = set()
    if path in {"/api/clinical/status", "/api/clinical/modules"}:
        categories.add("public_or_health")
    elif path == "/api/clinical/workflows/preview":
        categories.add("public_or_health")
    elif path == "/api/clinical/workflows/commit":
        categories.update({"generic_foundation_restricted", "external_partner_denied"})
    elif path.startswith("/api/clinical/admin"):
        categories.update({"clinical_admin", "external_partner_denied"})
    elif path.startswith("/api/clinical/reports/analytics-exports") and method == "POST":
        categories.update({"analytics_export", "external_partner_denied"})
    elif path.startswith("/api/clinical/reports"):
        categories.add("internal_read")
        if "audit-activity" in path:
            categories.add("audit_evidence")
    elif path.startswith("/api/clinical/quality/audit-evidence"):
        categories.update({"audit_evidence", "compliance_export", "external_partner_denied"})
    elif path.startswith("/api/clinical/quality/compliance-exports"):
        categories.update({"compliance_export", "external_partner_denied"})
    elif method == "GET":
        categories.add("internal_read")
    elif method in {"POST", "PATCH", "PUT", "DELETE"}:
        categories.update({"internal_mutation", "external_partner_denied"})
    return categories or {"unclassified"}


def _sensitive_route(method: str, path: str) -> bool:
    return (
        method in {"POST", "PATCH", "PUT", "DELETE"}
        or path.startswith("/api/clinical/admin")
        or "exports" in path
        or "audit" in path
        or path == "/api/clinical/workflows/commit"
    )


def test_all_sensitive_clinical_routes_are_documented_and_classified() -> None:
    api_inventory = (ROOT / "docs/clinical-api-inventory.md").read_text(encoding="utf-8")
    unclassified: list[tuple[str, str]] = []
    undocumented: list[tuple[str, str]] = []

    for method, path in sorted(_clinical_routes()):
        if not _sensitive_route(method, path):
            continue
        if "unclassified" in _classify(method, path):
            unclassified.append((method, path))
        if f"`{path}`" not in api_inventory:
            undocumented.append((method, path))

    assert unclassified == []
    assert undocumented == []


def test_all_clinical_mutation_routes_carry_internal_or_admin_classification() -> None:
    mutation_routes = [
        (method, path)
        for method, path in sorted(_clinical_routes())
        if method in {"POST", "PATCH", "PUT", "DELETE"} and not path.endswith("/preview")
    ]

    assert mutation_routes
    for method, path in mutation_routes:
        categories = _classify(method, path)
        assert categories & {"internal_mutation", "clinical_admin", "analytics_export", "compliance_export", "generic_foundation_restricted"}
        assert "external_partner_denied" in categories


def test_export_and_audit_routes_have_specific_classifications() -> None:
    route_categories = {(method, path): _classify(method, path) for method, path in _clinical_routes()}

    assert "analytics_export" in route_categories[("POST", "/api/clinical/reports/analytics-exports/preview")]
    assert "analytics_export" in route_categories[("POST", "/api/clinical/reports/analytics-exports")]
    assert "compliance_export" in route_categories[("GET", "/api/clinical/quality/audit-evidence")]
    assert "compliance_export" in route_categories[("POST", "/api/clinical/quality/compliance-exports/preview")]
    assert "compliance_export" in route_categories[("POST", "/api/clinical/quality/compliance-exports")]
    assert "audit_evidence" in route_categories[("GET", "/api/clinical/quality/audit-evidence")]
    assert "audit_evidence" in route_categories[("GET", "/api/clinical/reports/audit-activity")]


def test_admin_and_generic_foundation_routes_do_not_drift() -> None:
    admin_routes = {(method, path) for method, path in _clinical_routes() if path.startswith("/api/clinical/admin")}
    assert admin_routes
    assert all("clinical_admin" in _classify(method, path) for method, path in admin_routes)
    assert "generic_foundation_restricted" in _classify("POST", "/api/clinical/workflows/commit")


def test_route_permission_docs_include_required_categories() -> None:
    api_inventory = (ROOT / "docs/clinical-api-inventory.md").read_text(encoding="utf-8")
    rbac_matrix = (ROOT / "docs/clinical-rbac-matrix.md").read_text(encoding="utf-8")

    for token in [
        "public_or_health",
        "internal_read",
        "internal_mutation",
        "clinical_admin",
        "compliance_export",
        "analytics_export",
        "audit_evidence",
        "external_partner_denied",
        "generic_foundation_restricted",
    ]:
        assert token in api_inventory
        assert token in rbac_matrix
