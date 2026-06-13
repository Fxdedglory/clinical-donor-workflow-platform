import json
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

from app.auth.dependencies import get_current_user
from app.database import get_db
from app.main import app
from app.models import (
    ClinicalReportExport,
    ClinicalReportExportItem,
    ClinicalReportStatusHistory,
    User,
)
from app.services import clinical_workflows
from fastapi.testclient import TestClient


class _PermissionResult:
    def __init__(self, permissions: list[str]) -> None:
        self.permissions = permissions

    def all(self):
        return [(permission,) for permission in self.permissions]


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


class _ClinicalReportsDb:
    def __init__(self, permissions: list[str] | None = None) -> None:
        now = datetime.now(UTC)
        today = date.today()
        self.permissions = permissions or ["reports.read", "reports.export"]
        self.patients = [
            SimpleNamespace(patient_pk=1, patient_id="PT-000001", status="active", created_at=now, updated_at=now),
            SimpleNamespace(patient_pk=2, patient_id="PT-000002", status="deferred", created_at=now, updated_at=now),
        ]
        self.appointments = [
            SimpleNamespace(
                appointment_id=1,
                provider_id=10,
                appointment_type_id=20,
                scheduled_start=now,
                scheduled_end=now + timedelta(minutes=45),
                status="scheduled",
                created_at=now,
            ),
            SimpleNamespace(
                appointment_id=2,
                provider_id=10,
                appointment_type_id=20,
                scheduled_start=now,
                scheduled_end=now + timedelta(minutes=30),
                status="checked_in",
                created_at=now,
            ),
        ]
        self.screening_sessions = [
            SimpleNamespace(
                session_id=1,
                status="completed",
                supervisor_review_required=True,
                started_at=now,
                completed_at=now,
                created_at=now,
            )
        ]
        self.screening_outcomes = [
            SimpleNamespace(
                committed_outcome="eligible",
                proposed_outcome="eligible",
                deferral_type=None,
                supervisor_review_required=False,
                override_outcome=None,
                created_at=now,
            )
        ]
        self.deferrals = [
            SimpleNamespace(
                deferral_number="DEF-1",
                patient_pk=1,
                patient_id="PT-000001",
                deferral_type="temporary",
                status="active",
                reason="Temporary donor hold",
                starts_at=now,
                ends_at=now + timedelta(days=14),
                created_at=now,
            )
        ]
        self.encounters = [
            SimpleNamespace(encounter_id=1, status="completed", started_at=now, created_at=now)
        ]
        self.encounter_notes = [
            SimpleNamespace(note_id=1, status="signed", is_addendum=False, signed_at=now, created_at=now)
        ]
        self.order_results = [
            SimpleNamespace(
                result_id=1,
                order_id=1,
                result_status="final",
                abnormal_flag=True,
                critical_flag=True,
                resulted_at=now,
                created_at=now,
            )
        ]
        self.orders = [
            SimpleNamespace(
                order_id=1,
                status="ordered",
                ordered_at=now,
                created_at=now,
                results=self.order_results,
                has_critical_unacknowledged=True,
            )
        ]
        self.care_plans = [
            SimpleNamespace(care_plan_id=1, status="active", start_date=today, created_at=now, result_flag="critical")
        ]
        self.care_plan_tasks = [
            SimpleNamespace(task_id=1, status="open", due_date=today - timedelta(days=1), created_at=now, priority="stat")
        ]
        self.charges = [
            SimpleNamespace(charge_id=1, status="captured", service_date=today, created_at=now, total_amount=225.0)
        ]
        self.claims = [
            SimpleNamespace(
                claim_id=1,
                status="denied",
                submitted_at=now,
                created_at=now,
                total_amount=225.0,
                balance=125.0,
            )
        ]
        self.payments = [
            SimpleNamespace(payment_id=1, posted_at=now, created_at=now, payment_amount=100.0, adjustment_amount=0.0)
        ]
        self.denials = [
            SimpleNamespace(denial_id=1, status="open", due_date=today, created_at=now)
        ]
        self.quality_events = [
            SimpleNamespace(
                event_id=1,
                severity="high",
                status="open",
                category="documentation",
                due_date=today,
                created_at=now,
                capa_id=1,
            )
        ]
        self.adverse_events = [
            SimpleNamespace(adverse_event_id=1, event_at=now, created_at=now)
        ]
        self.investigations = [
            SimpleNamespace(investigation_id=1, created_at=now)
        ]
        self.compliance_exports = [
            SimpleNamespace(export_id=1, generated_at=now, created_at=now)
        ]
        self.report_exports: list[ClinicalReportExport] = []
        self.committed = False

    def execute(self, statement, *_args, **_kwargs):
        sql = _compiled(statement)
        if "bridge_role_permission" in sql:
            return _PermissionResult(self.permissions)
        table_rows = {
            "clinical_report_exports": self.report_exports,
            "clinical_compliance_exports": self.compliance_exports,
            "clinical_quality_investigations": self.investigations,
            "clinical_quality_events": self.quality_events,
            "clinical_adverse_events": self.adverse_events,
            "clinical_denials": self.denials,
            "clinical_payments": self.payments,
            "clinical_claims": self.claims,
            "clinical_charges": self.charges,
            "clinical_care_plan_tasks": self.care_plan_tasks,
            "clinical_care_plans": self.care_plans,
            "clinical_order_results": self.order_results,
            "clinical_orders": self.orders,
            "clinical_encounter_notes": self.encounter_notes,
            "clinical_encounters": self.encounters,
            "clinical_deferrals": self.deferrals,
            "clinical_screening_outcomes": self.screening_outcomes,
            "clinical_screening_sessions": self.screening_sessions,
            "appointments": self.appointments,
            "patients": self.patients,
        }
        for table_name, rows in table_rows.items():
            if table_name in sql:
                return _Rows(rows)
        return _Rows([])

    def add(self, row):
        if isinstance(row, ClinicalReportExport) and row not in self.report_exports:
            self.report_exports.append(row)

    def flush(self):
        for export_index, export in enumerate(self.report_exports, start=1):
            if export.export_id is None:
                export.export_id = export_index
            for item_index, item in enumerate(export.items, start=1):
                if item.item_id is None:
                    item.item_id = item_index
                item.export_id = export.export_id
            for history_index, history in enumerate(export.status_history, start=1):
                if history.history_id is None:
                    history.history_id = history_index
                history.export_id = export.export_id

    def commit(self):
        self.committed = True

    def refresh(self, _row):
        return None


def _internal_user() -> User:
    return User(
        user_id=1,
        username="reports",
        full_name="Reports User",
        email="reports@example.test",
        role_id=1,
        role="Business Technology Analyst",
        account_type="internal",
        user_type="internal",
        is_internal=True,
        is_external=False,
        external_user_flag=False,
    )


def _external_user() -> User:
    return User(
        user_id=2,
        username="partner",
        full_name="Partner User",
        email="partner@example.test",
        role_id=2,
        role="Partner External User",
        account_type="partner",
        user_type="partner",
        is_internal=False,
        is_external=True,
        external_user_flag=True,
    )


def _override_dependencies(db: _ClinicalReportsDb, user: User) -> None:
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: user


def _clear_overrides() -> None:
    app.dependency_overrides.clear()


def _export_payload() -> dict:
    return {
        "modules": ["patient_throughput", "scheduling_utilization", "audit_activity"],
        "export_format": "json",
        "include_detail": False,
        "reason": "Generate Sprint 11 analytics export",
    }


def test_reports_dashboard_and_module_endpoints_load(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(clinical_workflows, "WORKFLOW_OPERATIONS_PATH", tmp_path / "workflow_operations.json")
    db = _ClinicalReportsDb()
    _override_dependencies(db, _internal_user())
    client = TestClient(app)
    endpoints = [
        "/api/clinical/reports/dashboard",
        "/api/clinical/reports/patient-throughput",
        "/api/clinical/reports/scheduling-utilization",
        "/api/clinical/reports/screening-outcomes",
        "/api/clinical/reports/deferrals",
        "/api/clinical/reports/encounter-volume",
        "/api/clinical/reports/orders-results",
        "/api/clinical/reports/care-plan-aging",
        "/api/clinical/reports/billing-work-queue",
        "/api/clinical/reports/quality-trends",
        "/api/clinical/reports/audit-activity",
    ]
    try:
        responses = {endpoint: client.get(endpoint) for endpoint in endpoints}
    finally:
        _clear_overrides()
    assert all(response.status_code == 200 for response in responses.values())
    assert responses["/api/clinical/reports/dashboard"].json()["module_counts"]["patient_throughput"] == 2
    assert responses["/api/clinical/reports/orders-results"].json()["order_status_counts"]["ordered"] == 1
    assert responses["/api/clinical/reports/billing-work-queue"].json()["balances"]["claim_balance"] == 125.0


def test_reports_export_preview_returns_row_counts(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(clinical_workflows, "WORKFLOW_OPERATIONS_PATH", tmp_path / "workflow_operations.json")
    db = _ClinicalReportsDb()
    _override_dependencies(db, _internal_user())
    try:
        response = TestClient(app).post("/api/clinical/reports/analytics-exports/preview", json=_export_payload())
    finally:
        _clear_overrides()
    assert response.status_code == 200
    payload = response.json()
    assert payload["workflow"] == "reports.analytics_export"
    assert payload["row_counts"]["patient_throughput"] >= 2
    assert payload["commit_required_header"] == "X-Confirm-Generation: true"


def test_reports_export_confirmation_guard_and_audit_file_created(monkeypatch, tmp_path: Path) -> None:
    audit_path = tmp_path / "workflow_operations.json"
    monkeypatch.setattr(clinical_workflows, "WORKFLOW_OPERATIONS_PATH", audit_path)
    db = _ClinicalReportsDb()
    _override_dependencies(db, _internal_user())
    client = TestClient(app)
    try:
        missing = client.post("/api/clinical/reports/analytics-exports", json=_export_payload())
        invalid = client.post(
            "/api/clinical/reports/analytics-exports",
            headers={"X-Confirm-Generation": "false"},
            json=_export_payload(),
        )
        valid = client.post(
            "/api/clinical/reports/analytics-exports",
            headers={"X-Confirm-Generation": "true"},
            json={**_export_payload(), "preview_hash": "reports-hash"},
        )
    finally:
        _clear_overrides()
    assert missing.status_code == 409
    assert invalid.status_code == 409
    assert valid.status_code == 201
    assert audit_path.exists()
    entries = json.loads(audit_path.read_text(encoding="utf-8"))
    assert entries[-1]["workflow"] == "reports.analytics_export"
    assert len(db.report_exports) == 1
    assert isinstance(db.report_exports[0].items[0], ClinicalReportExportItem)
    assert isinstance(db.report_exports[0].status_history[0], ClinicalReportStatusHistory)


def test_reports_export_audit_append_preserves_existing_entries(monkeypatch, tmp_path: Path) -> None:
    audit_path = tmp_path / "workflow_operations.json"
    audit_path.write_text(json.dumps([{"operation_id": "existing", "workflow": "seed"}]), encoding="utf-8")
    monkeypatch.setattr(clinical_workflows, "WORKFLOW_OPERATIONS_PATH", audit_path)
    db = _ClinicalReportsDb()
    _override_dependencies(db, _internal_user())
    try:
        response = TestClient(app).post(
            "/api/clinical/reports/analytics-exports",
            headers={"X-Confirm-Generation": "true"},
            json=_export_payload(),
        )
    finally:
        _clear_overrides()
    assert response.status_code == 201
    entries = json.loads(audit_path.read_text(encoding="utf-8"))
    assert entries[0]["operation_id"] == "existing"
    assert entries[-1]["workflow"] == "reports.analytics_export"


def test_external_partner_cannot_generate_analytics_exports() -> None:
    db = _ClinicalReportsDb(permissions=["partner.portal"])
    _override_dependencies(db, _external_user())
    try:
        response = TestClient(app).post("/api/clinical/reports/analytics-exports/preview", json=_export_payload())
    finally:
        _clear_overrides()
    assert response.status_code == 403
