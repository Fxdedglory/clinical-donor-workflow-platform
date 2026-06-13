import pytest

from app.services.production_security_gates import (
    assert_production_security_gates,
    validate_production_security_gates,
)


def _safe_production_config(**overrides):
    config = {
        "APP_ENV": "prod",
        "SECRET_KEY": "ProdAuthSigningValue1234567890abcdefXYZ",
        "ENCRYPTION_KEY": "ProdFieldCipherValue1234567890abcdefXYZ",
        "COOKIE_SECURE": True,
        "COOKIE_SAMESITE": "lax",
        "CORS_ORIGINS": ["https://clinical.example.com"],
        "DEBUG": False,
        "DATABASE_URL": "postgresql+psycopg://clinical_runtime:secret@db.example.com:5432/clinical?sslmode=require",
        "WORKFLOW_AUDIT_STORAGE": "db_with_json_mirror",
        "WORKFLOW_AUDIT_DB_REQUIRED": True,
        "DEFAULT_ANALYTICS_EXPORT_PROFILE": "aggregate_safe",
        "DEFAULT_COMPLIANCE_EXPORT_PROFILE": "compliance_evidence",
        "DEFAULT_AUDIT_EXPORT_PROFILE": "audit_metadata",
        "PHI_REDACTION_ENABLED": True,
        "ALLOW_GENERIC_FOUNDATION_COMMIT": False,
        "GENERIC_WORKFLOW_COMMIT_ADMIN_ONLY": True,
        "AUTHENTICATION_ENABLED": True,
        "MFA_DEV_BYPASS_CODE": "839471652938",
    }
    config.update(overrides)
    return config


def _failure_codes(config) -> set[str]:
    result = validate_production_security_gates(config)
    return {issue.code for issue in result.failures}


def test_local_dev_mode_returns_warnings_but_does_not_hard_fail() -> None:
    result = validate_production_security_gates({"APP_ENV": "dev"})

    assert result.production_like is False
    assert result.passed is True
    assert not result.failures
    assert result.warnings


def test_production_mode_fails_on_default_secret_key() -> None:
    codes = _failure_codes(_safe_production_config(SECRET_KEY="change-me-for-production-demo-only"))

    assert "secret_key_unsafe" in codes


def test_production_mode_fails_on_debug_true() -> None:
    codes = _failure_codes(_safe_production_config(DEBUG=True))

    assert "debug_enabled" in codes


def test_production_mode_fails_on_wildcard_cors() -> None:
    codes = _failure_codes(_safe_production_config(CORS_ORIGINS=["*"]))

    assert "cors_wildcard" in codes


def test_production_mode_fails_on_missing_database_url() -> None:
    codes = _failure_codes(_safe_production_config(DATABASE_URL=""))

    assert "database_url_missing" in codes


def test_production_mode_fails_on_sqlite_database_url() -> None:
    codes = _failure_codes(_safe_production_config(DATABASE_URL="sqlite:///clinical.db"))

    assert "database_url_sqlite" in codes


def test_production_mode_fails_when_audit_is_json_only() -> None:
    codes = _failure_codes(_safe_production_config(WORKFLOW_AUDIT_STORAGE="json_only"))

    assert "workflow_audit_json_only" in codes


def test_production_mode_fails_when_required_audit_object_mirror_is_disabled() -> None:
    codes = _failure_codes(
        _safe_production_config(
            AUDIT_OBJECT_MIRROR_REQUIRED=True,
            AUDIT_OBJECT_MIRROR_MODE="disabled",
        )
    )

    assert "audit_object_mirror_required_but_disabled" in codes


def test_production_mode_fails_when_required_object_mirror_settings_are_missing() -> None:
    codes = _failure_codes(
        _safe_production_config(
            AUDIT_OBJECT_MIRROR_REQUIRED=True,
            AUDIT_OBJECT_MIRROR_MODE="object_storage",
            AUDIT_OBJECT_MIRROR_PROVIDER="",
            AUDIT_OBJECT_MIRROR_CONTAINER="",
            AUDIT_OBJECT_MIRROR_PREFIX="",
        )
    )

    assert "audit_object_mirror_provider_missing" in codes
    assert "audit_object_mirror_container_missing" in codes
    assert "audit_object_mirror_prefix_missing" in codes


def test_production_mode_fails_when_required_mirror_uses_local_filesystem_without_simulation_flag() -> None:
    codes = _failure_codes(
        _safe_production_config(
            AUDIT_OBJECT_MIRROR_REQUIRED=True,
            AUDIT_OBJECT_MIRROR_MODE="local_filesystem",
            AUDIT_OBJECT_MIRROR_ALLOW_LOCAL_PRODUCTION_SIMULATION=False,
        )
    )

    assert "audit_object_mirror_local_without_simulation_flag" in codes


def test_production_mode_passes_when_required_mirror_is_configured_for_provider_placeholder() -> None:
    result = validate_production_security_gates(
        _safe_production_config(
            AUDIT_OBJECT_MIRROR_REQUIRED=True,
            AUDIT_OBJECT_MIRROR_MODE="object_storage",
            AUDIT_OBJECT_MIRROR_PROVIDER="azure_blob_immutability",
            AUDIT_OBJECT_MIRROR_CONTAINER="clinical-audit-worm",
            AUDIT_OBJECT_MIRROR_PREFIX="workflow-audit",
        )
    )

    assert result.passed is True


def test_production_mode_passes_when_required_local_mirror_is_explicitly_simulation() -> None:
    result = validate_production_security_gates(
        _safe_production_config(
            AUDIT_OBJECT_MIRROR_REQUIRED=True,
            AUDIT_OBJECT_MIRROR_MODE="local_filesystem",
            AUDIT_OBJECT_MIRROR_ALLOW_LOCAL_PRODUCTION_SIMULATION=True,
        )
    )

    assert result.passed is True


def test_production_mode_fails_when_analytics_profile_is_unsafe() -> None:
    codes = _failure_codes(_safe_production_config(DEFAULT_ANALYTICS_EXPORT_PROFILE="internal_detail"))

    assert "unsafe_analytics_export_profile" in codes


def test_production_mode_fails_when_phi_redaction_disabled() -> None:
    codes = _failure_codes(_safe_production_config(PHI_REDACTION_ENABLED=False))

    assert "phi_redaction_disabled" in codes


def test_production_mode_fails_when_generic_commit_broadly_enabled() -> None:
    codes = _failure_codes(_safe_production_config(ALLOW_GENERIC_FOUNDATION_COMMIT=True))

    assert "generic_workflow_commit_enabled" in codes


def test_production_mode_fails_when_authentication_is_disabled() -> None:
    codes = _failure_codes(_safe_production_config(AUTHENTICATION_ENABLED=False))

    assert "authentication_disabled" in codes


def test_production_mode_passes_with_required_safe_settings() -> None:
    result = validate_production_security_gates(_safe_production_config())

    assert result.production_like is True
    assert result.passed is True
    assert not result.failures


def test_assert_production_security_gates_raises_clear_runtime_error() -> None:
    with pytest.raises(RuntimeError, match="Production security gate failed"):
        assert_production_security_gates(_safe_production_config(DEBUG=True))
