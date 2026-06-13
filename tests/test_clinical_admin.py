import json
import re
from datetime import UTC, datetime, time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.auth.dependencies import get_current_user
from app.database import get_db
from app.main import app
from app.models import (
    AppointmentType,
    ClinicalAdminApprovalPath,
    ClinicalAdminApprovalStep,
    ClinicalAdminConfigVersion,
    ClinicalAdminStatusHistory,
    ClinicalBillingCodeCatalog,
    ClinicalDeferralRuleVersion,
    ClinicalEligibilityRuleVersion,
    ClinicalNoteTemplate,
    ClinicalNotificationTemplate,
    ClinicalOrderCatalogItem,
    ClinicalProvider,
    ClinicalProviderScheduleTemplate,
    ClinicalQualityCategory,
    ClinicalScreeningTemplateVersion,
    Role,
    RolePermission,
    User,
)
from app.services import clinical_workflows


class _PermissionResult:
    def __init__(self, permissions: list[str]) -> None:
        self.permissions = permissions

    def all(self):
        return [(permission,) for permission in self.permissions]


class _Rows:
    def __init__(self, rows: list[object]) -> None:
        self.rows = rows

    def scalar_one_or_none(self):
        return self.rows[0] if self.rows else None

    def scalars(self):
        return self

    def all(self):
        return self.rows


def _compiled(statement) -> str:
    try:
        return str(statement.compile(compile_kwargs={"literal_binds": True}))
    except Exception:
        return str(statement)


def _id_filter(rows: list[object], attr: str, sql: str) -> list[object]:
    match = re.search(rf"{attr}\s*=\s*(\d+)", sql)
    if not match:
        return rows
    value = int(match.group(1))
    return [row for row in rows if getattr(row, attr, None) == value]


class _ClinicalAdminDb:
    def __init__(self, permissions: list[str] | None = None) -> None:
        self.permissions = permissions or ["clinical_admin.read", "clinical_admin.manage"]
        self.roles = [
            Role(role_id=1, role_name="System Administrator", description=""),
            Role(role_id=2, role_name="Partner External User", description=""),
        ]
        self.role_permissions = [
            RolePermission(role_id=1, permission_name="clinical_admin.read"),
            RolePermission(role_id=1, permission_name="clinical_admin.manage"),
            RolePermission(role_id=2, permission_name="partner.portal"),
        ]
        self.providers = [
            ClinicalProvider(provider_id=1, provider_code="PROV-1", full_name="Alex Clinician", role="Clinician", status="active")
        ]
        self.appointment_types: list[AppointmentType] = []
        self.provider_schedules: list[ClinicalProviderScheduleTemplate] = []
        self.screening_templates: list[ClinicalScreeningTemplateVersion] = []
        self.eligibility_rules: list[ClinicalEligibilityRuleVersion] = []
        self.deferral_rules: list[ClinicalDeferralRuleVersion] = []
        self.note_templates: list[ClinicalNoteTemplate] = []
        self.order_catalog: list[ClinicalOrderCatalogItem] = []
        self.billing_codes: list[ClinicalBillingCodeCatalog] = []
        self.quality_categories: list[ClinicalQualityCategory] = []
        self.approval_paths: list[ClinicalAdminApprovalPath] = []
        self.notification_templates: list[ClinicalNotificationTemplate] = []
        self.config_versions: list[ClinicalAdminConfigVersion] = []
        self.status_history: list[ClinicalAdminStatusHistory] = []
        self.committed = False

    def execute(self, statement, *_args, **_kwargs):
        sql = _compiled(statement)
        if "bridge_role_permission" in sql and "permission_name" in sql and "role_id" not in sql.split("FROM")[0]:
            return _PermissionResult(self.permissions)
        if "bridge_role_permission" in sql:
            return _Rows(self.role_permissions)
        if "dim_role" in sql:
            return _Rows(self.roles)
        if "clinical_admin_config_versions" in sql:
            return _Rows(self.config_versions)
        if "clinical_admin_status_history" in sql:
            return _Rows(self.status_history)
        if "appointment_types" in sql:
            return _Rows(_id_filter(self.appointment_types, "appointment_type_id", sql))
        if "clinical_provider_schedule_templates" in sql:
            return _Rows(_id_filter(self.provider_schedules, "schedule_template_id", sql))
        if "clinical_providers" in sql:
            return _Rows(_id_filter(self.providers, "provider_id", sql))
        if "clinical_screening_template_versions" in sql:
            return _Rows(self.screening_templates)
        if "clinical_eligibility_rule_versions" in sql:
            return _Rows(self.eligibility_rules)
        if "clinical_deferral_rule_versions" in sql:
            return _Rows(self.deferral_rules)
        if "clinical_note_templates" in sql:
            return _Rows(_id_filter(self.note_templates, "template_id", sql))
        if "clinical_order_catalog_items" in sql:
            return _Rows(_id_filter(self.order_catalog, "catalog_item_id", sql))
        if "clinical_billing_code_catalog" in sql:
            return _Rows(_id_filter(self.billing_codes, "code_id", sql))
        if "clinical_quality_categories" in sql:
            return _Rows(_id_filter(self.quality_categories, "category_id", sql))
        if "clinical_admin_approval_paths" in sql:
            return _Rows(_id_filter(self.approval_paths, "path_id", sql))
        if "clinical_notification_templates" in sql:
            return _Rows(_id_filter(self.notification_templates, "notification_template_id", sql))
        return _Rows([])

    def get(self, model, row_id):
        mapping = {
            AppointmentType: (self.appointment_types, "appointment_type_id"),
            ClinicalProvider: (self.providers, "provider_id"),
            ClinicalProviderScheduleTemplate: (self.provider_schedules, "schedule_template_id"),
            ClinicalNoteTemplate: (self.note_templates, "template_id"),
            ClinicalOrderCatalogItem: (self.order_catalog, "catalog_item_id"),
            ClinicalBillingCodeCatalog: (self.billing_codes, "code_id"),
            ClinicalQualityCategory: (self.quality_categories, "category_id"),
            ClinicalAdminApprovalPath: (self.approval_paths, "path_id"),
            ClinicalNotificationTemplate: (self.notification_templates, "notification_template_id"),
        }
        rows, attr = mapping.get(model, ([], ""))
        return next((row for row in rows if getattr(row, attr, None) == row_id), None)

    def add(self, row):
        target = self._target_for(row)
        if target is not None and row not in target:
            target.append(row)

    def flush(self):
        assignments = [
            (self.appointment_types, "appointment_type_id"),
            (self.provider_schedules, "schedule_template_id"),
            (self.screening_templates, "template_version_id"),
            (self.eligibility_rules, "rule_version_id"),
            (self.deferral_rules, "rule_version_id"),
            (self.note_templates, "template_id"),
            (self.order_catalog, "catalog_item_id"),
            (self.billing_codes, "code_id"),
            (self.quality_categories, "category_id"),
            (self.approval_paths, "path_id"),
            (self.notification_templates, "notification_template_id"),
            (self.config_versions, "version_id"),
            (self.status_history, "history_id"),
        ]
        for rows, attr in assignments:
            for index, row in enumerate(rows, start=1):
                if getattr(row, attr, None) is None:
                    setattr(row, attr, index)
                    if attr == "path_id":
                        for step_index, step in enumerate(row.steps, start=1):
                            if step.step_id is None:
                                step.step_id = step_index
                            step.path_id = row.path_id

    def commit(self):
        self.committed = True

    def refresh(self, _row):
        return None

    def _target_for(self, row):
        if isinstance(row, AppointmentType):
            return self.appointment_types
        if isinstance(row, ClinicalProviderScheduleTemplate):
            return self.provider_schedules
        if isinstance(row, ClinicalScreeningTemplateVersion):
            return self.screening_templates
        if isinstance(row, ClinicalEligibilityRuleVersion):
            return self.eligibility_rules
        if isinstance(row, ClinicalDeferralRuleVersion):
            return self.deferral_rules
        if isinstance(row, ClinicalNoteTemplate):
            return self.note_templates
        if isinstance(row, ClinicalOrderCatalogItem):
            return self.order_catalog
        if isinstance(row, ClinicalBillingCodeCatalog):
            return self.billing_codes
        if isinstance(row, ClinicalQualityCategory):
            return self.quality_categories
        if isinstance(row, ClinicalAdminApprovalPath):
            return self.approval_paths
        if isinstance(row, ClinicalNotificationTemplate):
            return self.notification_templates
        if isinstance(row, ClinicalAdminConfigVersion):
            return self.config_versions
        if isinstance(row, ClinicalAdminStatusHistory):
            return self.status_history
        return None


def _internal_user() -> User:
    return User(
        user_id=1,
        username="admin",
        full_name="Admin User",
        email="admin@example.test",
        role_id=1,
        role="System Administrator",
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


def _override_dependencies(db: _ClinicalAdminDb, user: User) -> None:
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: user


def _clear_overrides() -> None:
    app.dependency_overrides.clear()


def _payloads() -> list[tuple[str, str, dict, str]]:
    return [
        (
            "/api/clinical/admin/appointment-types",
            "appointment_type",
            {"type_code": "SCREEN", "name": "Screening Visit", "duration_minutes": 45, "category": "screening", "description": "Donor screening", "active": True},
            "admin.appointment_type_upsert",
        ),
        (
            "/api/clinical/admin/provider-schedules",
            "provider_schedule",
            {"provider_id": 1, "weekday": 1, "date_pattern": "weekly", "start_time": "08:00", "end_time": "16:00", "location": "Clinic", "active": True},
            "admin.provider_schedule_upsert",
        ),
        (
            "/api/clinical/admin/screening-templates",
            "screening_template",
            {"template_key": "adult-screen", "template_name": "Adult Screening", "required_questions": [{"key": "travel", "required": True}], "active": True},
            "admin.screening_template_version",
        ),
        (
            "/api/clinical/admin/eligibility-rules",
            "eligibility_rule",
            {"rule_key": "age-rule", "rule_name": "Age Rule", "rule_type": "eligibility", "severity": "high", "criteria": {"min_age": 18}, "expression": "age >= 18", "active": True},
            "admin.eligibility_rule_version",
        ),
        (
            "/api/clinical/admin/deferral-rules",
            "deferral_rule",
            {"rule_key": "travel-deferral", "rule_name": "Travel Deferral", "rule_type": "deferral", "severity": "medium", "criteria": {"travel": True}, "expression": "travel == true", "active": True},
            "admin.deferral_rule_version",
        ),
        (
            "/api/clinical/admin/note-templates",
            "note_template",
            {"template_key": "screen-note", "name": "Screening Note", "note_type": "screening", "body": "Assessment", "sections": [{"title": "Assessment"}], "active": True},
            "admin.note_template_upsert",
        ),
        (
            "/api/clinical/admin/order-catalog",
            "order_catalog",
            {"code": "CBC", "name": "CBC", "order_type": "laboratory", "description": "Complete blood count", "default_priority": "routine", "active": True},
            "admin.order_catalog_upsert",
        ),
        (
            "/api/clinical/admin/billing-codes",
            "billing_code",
            {"code": "99201", "code_type": "cpt", "description": "Initial visit", "default_amount": 100, "active": True},
            "admin.billing_code_upsert",
        ),
        (
            "/api/clinical/admin/quality-categories",
            "quality_category",
            {"category_key": "documentation", "category": "Documentation", "severity_mapping": {"default": "medium"}, "closure_required": True, "approval_required": True, "active": True},
            "admin.quality_category_upsert",
        ),
        (
            "/api/clinical/admin/approval-paths",
            "approval_path",
            {"workflow": "quality.event_close", "path_name": "Quality Closure", "steps": [{"step_order": 1, "role": "Quality Assurance Specialist", "permission": "quality.close", "required": True, "active": True}], "active": True},
            "admin.approval_path_upsert",
        ),
        (
            "/api/clinical/admin/notification-templates",
            "notification_template",
            {"workflow": "quality.event_close", "channel": "in_app", "subject": "Quality event closed", "body": "Event closed", "active": True},
            "admin.notification_template_upsert",
        ),
    ]


def test_admin_commit_rejects_missing_invalid_and_accepts_valid_confirmation(monkeypatch, tmp_path: Path) -> None:
    audit_path = tmp_path / "workflow_operations.json"
    monkeypatch.setattr(clinical_workflows, "WORKFLOW_OPERATIONS_PATH", audit_path)
    db = _ClinicalAdminDb()
    _override_dependencies(db, _internal_user())
    payload = _payloads()[0][2]
    try:
        missing = TestClient(app).post("/api/clinical/admin/appointment-types", json=payload)
        invalid = TestClient(app).post("/api/clinical/admin/appointment-types", headers={"X-Confirm-Generation": "false"}, json=payload)
        valid = TestClient(app).post("/api/clinical/admin/appointment-types", headers={"X-Confirm-Generation": "true"}, json={**payload, "preview_hash": "appointment-hash"})
    finally:
        _clear_overrides()
    assert missing.status_code == 409
    assert invalid.status_code == 409
    assert valid.status_code == 201
    assert audit_path.exists()
    entries = json.loads(audit_path.read_text(encoding="utf-8"))
    assert entries[-1]["workflow"] == "admin.appointment_type_upsert"
    assert len(db.config_versions) == 1


@pytest.mark.parametrize(("endpoint", "workflow_type", "payload", "expected_workflow"), _payloads())
def test_admin_preview_commit_and_audit_for_each_workflow(monkeypatch, tmp_path: Path, endpoint: str, workflow_type: str, payload: dict, expected_workflow: str) -> None:
    audit_path = tmp_path / f"{workflow_type}.json"
    monkeypatch.setattr(clinical_workflows, "WORKFLOW_OPERATIONS_PATH", audit_path)
    db = _ClinicalAdminDb()
    _override_dependencies(db, _internal_user())
    try:
        preview = TestClient(app).post(f"{endpoint}/preview", json=payload)
        commit = TestClient(app).post(endpoint, headers={"X-Confirm-Generation": "true"}, json={**payload, "preview_hash": "admin-hash"})
    finally:
        _clear_overrides()
    assert preview.status_code == 200
    assert preview.json()["workflow"] == expected_workflow
    assert commit.status_code == 201
    assert db.config_versions[-1].config_type == workflow_type
    entries = json.loads(audit_path.read_text(encoding="utf-8"))
    assert entries[-1]["workflow"] == expected_workflow


def test_admin_audit_append_preserves_existing_entries(monkeypatch, tmp_path: Path) -> None:
    audit_path = tmp_path / "workflow_operations.json"
    audit_path.write_text(json.dumps([{"operation_id": "existing", "workflow": "seed"}]), encoding="utf-8")
    monkeypatch.setattr(clinical_workflows, "WORKFLOW_OPERATIONS_PATH", audit_path)
    db = _ClinicalAdminDb()
    _override_dependencies(db, _internal_user())
    try:
        response = TestClient(app).post("/api/clinical/admin/billing-codes", headers={"X-Confirm-Generation": "true"}, json=_payloads()[7][2])
    finally:
        _clear_overrides()
    assert response.status_code == 201
    entries = json.loads(audit_path.read_text(encoding="utf-8"))
    assert entries[0]["operation_id"] == "existing"
    assert entries[-1]["workflow"] == "admin.billing_code_upsert"


def test_admin_versioned_records_preserve_prior_versions(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(clinical_workflows, "WORKFLOW_OPERATIONS_PATH", tmp_path / "workflow_operations.json")
    db = _ClinicalAdminDb()
    db.screening_templates.append(
        ClinicalScreeningTemplateVersion(template_version_id=1, template_key="adult-screen", template_name="Adult Screening", version=1, required_questions=[], active=True, created_at=datetime.now(UTC))
    )
    db.eligibility_rules.append(
        ClinicalEligibilityRuleVersion(rule_version_id=1, rule_key="age-rule", rule_name="Age Rule", rule_type="eligibility", severity="medium", criteria={}, active=True, version=1, created_at=datetime.now(UTC))
    )
    db.deferral_rules.append(
        ClinicalDeferralRuleVersion(rule_version_id=1, rule_key="travel-deferral", rule_name="Travel Deferral", rule_type="deferral", severity="medium", criteria={}, active=True, version=1, created_at=datetime.now(UTC))
    )
    _override_dependencies(db, _internal_user())
    try:
        screening = TestClient(app).post("/api/clinical/admin/screening-templates", headers={"X-Confirm-Generation": "true"}, json=_payloads()[2][2])
        eligibility = TestClient(app).post("/api/clinical/admin/eligibility-rules", headers={"X-Confirm-Generation": "true"}, json=_payloads()[3][2])
        deferral = TestClient(app).post("/api/clinical/admin/deferral-rules", headers={"X-Confirm-Generation": "true"}, json=_payloads()[4][2])
    finally:
        _clear_overrides()
    assert screening.status_code == 201
    assert eligibility.status_code == 201
    assert deferral.status_code == 201
    assert [row.version for row in db.screening_templates] == [1, 2]
    assert [row.version for row in db.eligibility_rules] == [1, 2]
    assert [row.version for row in db.deferral_rules] == [1, 2]
    assert db.screening_templates[0].active is False
    assert db.eligibility_rules[0].active is False
    assert db.deferral_rules[0].active is False


def test_admin_dashboard_config_history_and_rbac_load(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(clinical_workflows, "WORKFLOW_OPERATIONS_PATH", tmp_path / "workflow_operations.json")
    db = _ClinicalAdminDb()
    _override_dependencies(db, _internal_user())
    try:
        commit = TestClient(app).post("/api/clinical/admin/quality-categories", headers={"X-Confirm-Generation": "true"}, json=_payloads()[8][2])
        dashboard = TestClient(app).get("/api/clinical/admin/dashboard")
        versions = TestClient(app).get("/api/clinical/admin/config-versions")
        rbac = TestClient(app).get("/api/clinical/admin/rbac")
    finally:
        _clear_overrides()
    assert commit.status_code == 201
    assert dashboard.status_code == 200
    assert dashboard.json()["total_config_versions"] == 1
    assert versions.status_code == 200
    assert versions.json()[0]["config_type"] == "quality_category"
    assert rbac.status_code == 200
    assert any(role["role"] == "System Administrator" and role["can_manage_admin"] for role in rbac.json()["roles"])


def test_external_partner_admin_mutation_is_rejected() -> None:
    db = _ClinicalAdminDb(permissions=["partner.portal"])
    _override_dependencies(db, _external_user())
    try:
        response = TestClient(app).post("/api/clinical/admin/appointment-types/preview", json=_payloads()[0][2])
    finally:
        _clear_overrides()
    assert response.status_code == 403
