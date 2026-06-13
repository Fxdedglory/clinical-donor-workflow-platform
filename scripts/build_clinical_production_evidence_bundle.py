from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.core.config import settings  # noqa: E402
from app.routes.clinical import CLINICAL_MODULES  # noqa: E402
from app.services.clinical_audit_mirror import audit_mirror_config_from_settings  # noqa: E402
from app.services.clinical_audit_signing import (  # noqa: E402
    audit_manifest_signing_config_from_settings,
)
from app.services.clinical_azure_key_vault_live_readiness import (  # noqa: E402
    build_key_vault_live_readiness_report,
    build_key_vault_signing_evidence,
)
from app.services.clinical_azure_worm_evidence import build_validation_evidence  # noqa: E402
from app.services.clinical_azure_worm_live_readiness import (  # noqa: E402
    build_live_readiness_report,
)
from app.services.production_security_gates import validate_production_security_gates  # noqa: E402

EVIDENCE_SCHEMA_VERSION = "clinical.production_evidence_bundle.v1"
DEFAULT_JSON_NAME = "clinical-production-evidence-bundle.json"
DEFAULT_MARKDOWN_NAME = "clinical-production-evidence-summary.md"

DOC_REFERENCES = {
    "api_inventory": "docs/clinical-api-inventory.md",
    "rbac_matrix": "docs/clinical-rbac-matrix.md",
    "migration_runbook": "docs/clinical-migration-runbook.md",
    "production_readiness_runbook": "docs/clinical-production-readiness-runbook.md",
    "production_security_gates": "docs/clinical-production-security-gates.md",
    "security_readiness": "docs/clinical-security-readiness.md",
    "audit_durability_decision": "docs/clinical-audit-durability-decision.md",
    "audit_worm_mirror": "docs/clinical-audit-worm-mirror.md",
    "audit_manifest_signing": "docs/clinical-audit-manifest-signing.md",
    "azure_worm_operator_checklist": "docs/clinical-azure-worm-operator-checklist.md",
    "key_vault_operator_checklist": "docs/clinical-azure-key-vault-operator-checklist.md",
    "key_vault_lifecycle": "docs/clinical-azure-key-vault-key-lifecycle.md",
    "go_live_signoff": "docs/clinical-production-go-live-signoff.md",
    "live_validation_decision_log": "docs/clinical-live-validation-decision-log.md",
    "post_rc_backlog": "docs/clinical-post-rc-backlog.md",
}

VALIDATION_COMMANDS = [
    {
        "command": r".\.venv\Scripts\python.exe scripts\preflight_check.py",
        "required": True,
        "status": "not_run_by_bundle_generator",
    },
    {
        "command": r".\.venv\Scripts\python.exe -m pytest",
        "required": True,
        "status": "not_run_by_bundle_generator",
    },
    {
        "command": "cd frontend; npm run build",
        "required": True,
        "status": "not_run_by_bundle_generator",
    },
    {
        "command": r".\.venv\Scripts\python.exe -m pip check",
        "required": False,
        "status": "not_run_by_bundle_generator",
    },
    {
        "command": "cd frontend; npm audit --audit-level=high",
        "required": False,
        "status": "not_run_by_bundle_generator",
    },
    {
        "command": r".\.venv\Scripts\python.exe scripts\start_app_service.py --check",
        "required": False,
        "status": "not_run_by_bundle_generator",
    },
    {
        "command": r".\.venv\Scripts\python.exe scripts\check_azure_worm_readiness.py --json",
        "required": False,
        "status": "not_run_by_bundle_generator",
    },
    {
        "command": r".\.venv\Scripts\python.exe scripts\check_azure_key_vault_signing_readiness.py --json",
        "required": False,
        "status": "not_run_by_bundle_generator",
    },
    {
        "command": r".\.venv\Scripts\python.exe -m alembic heads",
        "required": False,
        "status": "not_run_by_bundle_generator",
    },
    {
        "command": "git diff --check",
        "required": False,
        "status": "not_run_by_bundle_generator",
    },
]

KNOWN_LIMITATIONS = [
    "Live Azure WORM validation remains skipped by default and requires approved Azure resources.",
    "Live Azure Key Vault signing remains skipped by default and requires approved Key Vault access.",
    "Provider-side immutable retention and legal-hold verification are external approval activities.",
    "Cloud-side key rotation, access-log evidence review, and incident recovery tabletop exercises remain operational tasks.",
    "Snowflake, Power BI, FHIR/HL7, EDI clearinghouse, notification delivery, and approval execution integrations remain post-RC backlog items.",
]

EXTERNAL_APPROVAL_CHECKLIST = [
    {
        "area": "Azure WORM live validation",
        "status": "pending_external_approval",
        "requires": [
            "approved storage account/container",
            "immutability and legal hold evidence",
            "managed/workload identity",
            "dedicated non-production live-test prefix",
            "CLINICAL_RUN_AZURE_WORM_LIVE_TESTS=true only during approved window",
        ],
    },
    {
        "area": "Azure Key Vault live signing",
        "status": "pending_external_approval",
        "requires": [
            "approved Key Vault and signing key/version",
            "least-privilege sign/verify identity",
            "diagnostic/access logging evidence",
            "CLINICAL_RUN_AZURE_KEY_VAULT_LIVE_TESTS=true only during approved window",
        ],
    },
    {
        "area": "Production go-live",
        "status": "pending_product_security_operations_signoff",
        "requires": [
            "Product Owner signoff",
            "Security/Compliance signoff",
            "Operations signoff",
            "migration window and rollback plan",
        ],
    },
]

SENSITIVE_FIELD_TOKENS = (
    "account_key",
    "api_key",
    "client_secret",
    "connection_string",
    "database_url",
    "encryption_key",
    "local_hmac_key",
    "password",
    "private_key",
    "sas_token",
    "secret",
    "signature_key_material",
    "token",
)
SENSITIVE_VALUE_PATTERN = re.compile(
    r"(?i)("
    r"accountkey=|api[_-]?key=|authorization:|bearer\s+|client_secret=|"
    r"password=|secret=|sig=|sharedaccesssignature|token=|"
    r"-----BEGIN [A-Z ]*PRIVATE KEY-----"
    r")"
)
SAFE_FIELD_NAMES = {
    "contains_secret_values",
}

PHI_FIELD_TOKENS = (
    "date_of_birth",
    "dob",
    "first_name",
    "full_name",
    "last_name",
    "medical_record_number",
    "mrn",
    "patient_name",
    "phone",
    "ssn",
)


def utc_timestamp() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _run(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=ROOT, text=True, capture_output=True, check=False)


def _git_commit() -> str | None:
    result = _run(["git", "rev-parse", "HEAD"])
    if result.returncode != 0:
        return None
    return result.stdout.strip() or None


def _git_status_summary() -> dict[str, Any]:
    result = _run(["git", "status", "--short"])
    lines = [line for line in result.stdout.splitlines() if line.strip()]
    protected_dirty = [
        line
        for line in lines
        if line.strip().endswith("backend/app/cli.py") or " backend/app/cli.py" in line
    ]
    return {
        "available": result.returncode == 0,
        "dirty": bool(lines),
        "dirty_file_count": len(lines),
        "protected_dirty_files": protected_dirty,
        "raw_status_included": False,
    }


def _migration_revisions() -> tuple[set[str], set[str]]:
    revisions: set[str] = set()
    down_revisions: set[str] = set()
    for migration in (ROOT / "database" / "migrations" / "versions").glob("*.py"):
        text = migration.read_text(encoding="utf-8", errors="ignore")
        revision_match = re.search(r"^revision:\s*[^=]+=\s*[\"']([^\"']+)[\"']", text, re.MULTILINE)
        if revision_match:
            revisions.add(revision_match.group(1))
        down_match = re.search(r"^down_revision:\s*[^=]+=\s*(.+)$", text, re.MULTILINE)
        if not down_match:
            continue
        down_value = down_match.group(1)
        for value in re.findall(r"[\"']([^\"']+)[\"']", down_value):
            down_revisions.add(value)
    return revisions, down_revisions


def _alembic_heads() -> list[str]:
    revisions, down_revisions = _migration_revisions()
    return sorted(revisions - down_revisions)


def _sensitive_field_name(name: str) -> bool:
    normalized = name.lower().replace("-", "_")
    if normalized in SAFE_FIELD_NAMES:
        return False
    return any(token in normalized for token in SENSITIVE_FIELD_TOKENS)


def _phi_field_name(name: str) -> bool:
    normalized = name.lower().replace("-", "_")
    return any(token in normalized for token in PHI_FIELD_TOKENS)


def _sanitize_scalar(value: str) -> str:
    if SENSITIVE_VALUE_PATTERN.search(value):
        return "[redacted]"
    return value


def sanitize_bundle_payload(value: Any) -> Any:
    if isinstance(value, dict):
        sanitized: dict[str, Any] = {}
        for key, child in value.items():
            key_text = str(key)
            if _sensitive_field_name(key_text) or _phi_field_name(key_text):
                continue
            sanitized[key_text] = sanitize_bundle_payload(child)
        return sanitized
    if isinstance(value, list):
        return [sanitize_bundle_payload(item) for item in value]
    if isinstance(value, str):
        return _sanitize_scalar(value)
    return value


def _module_inventory() -> list[dict[str, Any]]:
    return [module.model_dump(mode="json") for module in CLINICAL_MODULES]


def _security_gate_summary() -> dict[str, Any]:
    result = validate_production_security_gates(settings)
    return {
        "environment": result.environment,
        "production_like": result.production_like,
        "passed": result.passed,
        "failures": [issue.__dict__ for issue in result.failures],
        "warnings": [issue.__dict__ for issue in result.warnings],
    }


def _audit_durability_summary() -> dict[str, Any]:
    config = audit_mirror_config_from_settings(settings)
    return {
        "workflow_audit_storage": getattr(settings, "workflow_audit_storage", "unknown"),
        "workflow_audit_db_required": bool(getattr(settings, "workflow_audit_db_required", False)),
        "json_compatibility_mirror": "metadata/workflow_operations.json",
        "db_append_only_migration": "202606130001_clinical_workflow_audit_events.py",
        "worm_mirror_migration": "202606130002_clinical_audit_worm_mirror.py",
        "manifest_migration": "202606130003_clinical_audit_worm_manifests.py",
        "mirror_mode": config.normalized_mode,
        "mirror_required": config.required,
        "retention_policy_configured": bool(config.retention_policy),
        "legal_hold_reference_configured": bool(config.legal_hold_reference),
    }


def _worm_mirror_readiness_summary() -> dict[str, Any]:
    config = audit_mirror_config_from_settings(settings)
    return {
        "mode": config.normalized_mode,
        "required": config.required,
        "local_filesystem": config.local_filesystem,
        "object_placeholder": config.object_placeholder,
        "provider": config.object_provider or None,
        "container_configured": bool(config.object_container or config.azure_container),
        "prefix_configured": bool(config.object_prefix or config.azure_prefix),
        "azure_real_io_enabled": bool(config.azure_enable_real_io),
        "azure_immutability_required": bool(config.azure_immutability_required),
        "azure_legal_hold_required": bool(config.azure_legal_hold_required),
        "azure_checksum_validation_required": bool(config.azure_checksum_validation_required),
    }


def _azure_worm_dry_run_summary() -> dict[str, Any]:
    config = audit_mirror_config_from_settings(settings)
    signing_config = audit_manifest_signing_config_from_settings(settings)
    report = build_live_readiness_report(config=config, live_write_requested=False)
    report["mode"] = "dry_run"
    evidence = build_validation_evidence(
        report,
        environment_mode=settings.app_env,
        signing_config=signing_config,
    )
    return {
        "report": report,
        "evidence": evidence,
    }


def _key_vault_dry_run_summary() -> dict[str, Any]:
    signing_config = audit_manifest_signing_config_from_settings(settings)
    report = build_key_vault_live_readiness_report(
        config=signing_config,
        live_sign_requested=False,
    )
    evidence = build_key_vault_signing_evidence(report, environment_mode=settings.app_env)
    return {
        "report": report,
        "evidence": evidence,
    }


def build_evidence_bundle(*, generated_at: str | None = None) -> dict[str, Any]:
    key_vault = _key_vault_dry_run_summary()
    bundle = {
        "schema_version": EVIDENCE_SCHEMA_VERSION,
        "generated_at": generated_at or utc_timestamp(),
        "dry_run": True,
        "network_calls_performed": False,
        "live_cloud_tests_performed": False,
        "git": {
            "commit": _git_commit(),
            "status": _git_status_summary(),
        },
        "alembic": {
            "heads": _alembic_heads(),
        },
        "validation_command_checklist": VALIDATION_COMMANDS,
        "clinical_module_inventory": _module_inventory(),
        "documentation_references": DOC_REFERENCES,
        "api_inventory_reference": DOC_REFERENCES["api_inventory"],
        "rbac_matrix_reference": DOC_REFERENCES["rbac_matrix"],
        "migration_runbook_reference": DOC_REFERENCES["migration_runbook"],
        "security_gate_summary": _security_gate_summary(),
        "audit_durability_summary": _audit_durability_summary(),
        "worm_mirror_readiness_summary": _worm_mirror_readiness_summary(),
        "azure_worm_readiness_dry_run_summary": _azure_worm_dry_run_summary(),
        "key_vault_signing_readiness_dry_run_summary": key_vault,
        "key_lifecycle_readiness_summary": key_vault["evidence"].get("lifecycle_summary") or {},
        "known_limitations": KNOWN_LIMITATIONS,
        "external_approval_checklist": EXTERNAL_APPROVAL_CHECKLIST,
        "data_safety_summary": {
            "contains_raw_credentials": False,
            "contains_secret_values": False,
            "contains_phi_ephi": False,
            "sanitization": "whitelisted readiness metadata only; secret-like and PHI-like fields are omitted",
        },
    }
    return sanitize_bundle_payload(bundle)


def markdown_summary(bundle: Mapping[str, Any]) -> str:
    git = bundle.get("git") or {}
    alembic = bundle.get("alembic") or {}
    gate = bundle.get("security_gate_summary") or {}
    modules = bundle.get("clinical_module_inventory") or []
    key_lifecycle = bundle.get("key_lifecycle_readiness_summary") or {}
    lines = [
        "# Clinical Production Evidence Summary",
        "",
        f"Generated at: `{bundle.get('generated_at')}`",
        f"Git commit: `{git.get('commit') or 'unavailable'}`",
        f"Alembic head(s): `{', '.join(alembic.get('heads') or []) or 'unavailable'}`",
        f"Clinical modules: `{len(modules)}`",
        f"Production security gate passed: `{gate.get('passed')}`",
        f"Network calls performed: `{bundle.get('network_calls_performed')}`",
        f"Live cloud tests performed: `{bundle.get('live_cloud_tests_performed')}`",
        "",
        "## Readiness Sections",
        "",
        "- Validation command checklist",
        "- Clinical module inventory",
        "- Security gate summary",
        "- Audit durability summary",
        "- WORM mirror readiness summary",
        "- Azure WORM dry-run readiness summary",
        "- Key Vault signing dry-run readiness summary",
        "- Key lifecycle readiness summary",
        "",
        "## Key Lifecycle",
        "",
        f"- Rotation required: `{key_lifecycle.get('rotation_required')}`",
        f"- Rotation status: `{key_lifecycle.get('rotation_status')}`",
        f"- Access-log review status: `{key_lifecycle.get('access_log_review_status')}`",
        f"- Incident recovery status: `{key_lifecycle.get('incident_recovery_status')}`",
        "",
        "## External Approvals",
        "",
    ]
    for item in bundle.get("external_approval_checklist") or []:
        if isinstance(item, Mapping):
            lines.append(f"- {item.get('area')}: `{item.get('status')}`")
    lines.extend(
        [
            "",
            "## Data Safety",
            "",
            "- Raw credentials included: `false`",
            "- Secret values included: `false`",
            "- PHI/ePHI included: `false`",
            "",
        ]
    )
    return "\n".join(lines)


def write_evidence_bundle(
    out_dir: str | Path,
    bundle: Mapping[str, Any],
    *,
    write_markdown: bool = True,
) -> dict[str, str]:
    target = Path(out_dir)
    target.mkdir(parents=True, exist_ok=True)
    json_path = target / DEFAULT_JSON_NAME
    json_path.write_text(json.dumps(bundle, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    written = {"json": str(json_path)}
    if write_markdown:
        markdown_path = target / DEFAULT_MARKDOWN_NAME
        markdown_path.write_text(markdown_summary(bundle), encoding="utf-8")
        written["markdown"] = str(markdown_path)
    return written


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build a repo-safe clinical production evidence bundle without live cloud calls."
    )
    parser.add_argument(
        "--out",
        required=True,
        help="Output directory for the evidence bundle JSON and markdown summary.",
    )
    parser.add_argument(
        "--generated-at",
        help="Override generated_at timestamp for deterministic test fixtures.",
    )
    parser.add_argument(
        "--no-markdown",
        action="store_true",
        help="Write JSON only.",
    )
    args = parser.parse_args(argv)

    bundle = build_evidence_bundle(generated_at=args.generated_at)
    written = write_evidence_bundle(args.out, bundle, write_markdown=not args.no_markdown)
    print(json.dumps({"status": "written", "dry_run": True, "files": written}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
