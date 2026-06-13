from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.core.config import settings  # noqa: E402
from app.services.clinical_audit_signing import (  # noqa: E402
    audit_manifest_signing_config_from_settings,
    sign_manifest_checksum,
    verify_manifest_signature,
)
from app.services.clinical_azure_key_vault_live_readiness import (  # noqa: E402
    LIVE_TESTS_ENV,
    build_key_vault_live_readiness_report,
    build_key_vault_signing_evidence,
    write_key_vault_signing_evidence,
)

LIVE_VALIDATION_MANIFEST_CHECKSUM = "sha256-azure-key-vault-live-validation"


def run_live_sign(report: dict[str, Any]) -> dict[str, Any]:
    config = audit_manifest_signing_config_from_settings(settings)
    report.update(
        {
            "signing_attempted": True,
            "network_calls_performed": True,
        }
    )
    signature = sign_manifest_checksum(LIVE_VALIDATION_MANIFEST_CHECKSUM, config)
    report["signature_status"] = signature.status
    report["signature_reason"] = signature.reason
    if not signature.signature:
        report["verification_attempted"] = False
        report["blocking_issues"] = [
            *report.get("blocking_issues", []),
            {
                "code": "azure_key_vault_live_signature_missing",
                "message": signature.reason or "Azure Key Vault live signing did not return a signature.",
                "severity": "error",
            },
        ]
        return report
    report["verification_attempted"] = True
    verification = verify_manifest_signature(
        manifest_checksum=LIVE_VALIDATION_MANIFEST_CHECKSUM,
        signature=signature.signature,
        config=config,
    )
    report["verification_status"] = verification.get("signature_verification_status")
    report["verification_reason"] = verification.get("reason")
    if verification.get("verified") is not True:
        report["blocking_issues"] = [
            *report.get("blocking_issues", []),
            {
                "code": "azure_key_vault_live_verification_failed",
                "message": verification.get("reason") or "Azure Key Vault live signature verification failed.",
                "severity": "error",
            },
        ]
    return report


def build_report(*, live_sign_requested: bool) -> dict[str, Any]:
    config = audit_manifest_signing_config_from_settings(settings)
    return build_key_vault_live_readiness_report(
        config=config,
        live_sign_requested=live_sign_requested,
    )


def _print_human(report: dict[str, Any]) -> None:
    readiness = report.get("signing_readiness") or {}
    print("Clinical Azure Key Vault signing readiness")
    print(f"mode={report['mode']}")
    print(f"signing_mode={report.get('signing_mode')}")
    print(f"signing_required={report.get('signing_required')}")
    print(f"algorithm={report.get('signature_algorithm')}")
    print(f"real_io_enabled={report.get('real_io_enabled')}")
    print(f"live_tests_enabled={report.get('live_tests_enabled')} ({LIVE_TESTS_ENV})")
    print(f"live_sign_requested={report.get('live_sign_requested')}")
    print(f"signing_attempted={report.get('signing_attempted')}")
    print(f"verification_attempted={report.get('verification_attempted')}")
    print(f"network_calls_performed={report.get('network_calls_performed')}")
    print(f"vault_url_configured={readiness.get('vault_url_configured')}")
    print(f"key_name={readiness.get('key_name') or '<unset>'}")
    print(f"key_version={readiness.get('key_version') or '<unset>'}")
    print(f"sdk_available={readiness.get('sdk_available')}")
    print(f"real_io_ready={readiness.get('real_io_ready')}")
    if report.get("verification_status"):
        print(f"verification_status={report['verification_status']}")
    if report.get("evidence_out"):
        print(f"evidence_out={report['evidence_out']}")
    if report.get("blocking_issues"):
        print("blocking_issues:")
        for issue in report["blocking_issues"]:
            print(f"- {issue['code']}: {issue['message']}")
    if report.get("warnings"):
        print("warnings:")
        for issue in report["warnings"]:
            print(f"- {issue['code']}: {issue['message']}")


def _write_evidence_if_requested(report: dict[str, Any], evidence_out: str | None) -> dict[str, Any]:
    if not evidence_out:
        return report
    evidence = build_key_vault_signing_evidence(report, environment_mode=settings.app_env)
    evidence_path = write_key_vault_signing_evidence(evidence_out, evidence)
    report["evidence_out"] = str(evidence_path)
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check Azure Key Vault manifest signing readiness.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    parser.add_argument("--strict", action="store_true", help="Return nonzero when readiness has blocking issues.")
    parser.add_argument(
        "--evidence-out",
        help="Write a sanitized Azure Key Vault signing evidence JSON artifact to this path.",
    )
    parser.add_argument(
        "--live-sign",
        action="store_true",
        help=(
            "Perform one live Azure Key Vault sign/verify check. Requires "
            f"{LIVE_TESTS_ENV}=true and safe live Key Vault settings."
        ),
    )
    args = parser.parse_args(argv)

    report = build_report(live_sign_requested=args.live_sign)
    if args.live_sign:
        if report["blocking_issues"] or report["signing_readiness"].get("real_io_ready") is not True:
            report = _write_evidence_if_requested(report, args.evidence_out)
            if args.json:
                print(json.dumps(report, indent=2, sort_keys=True, default=str))
            else:
                _print_human(report)
            return 2
        report = run_live_sign(report)

    report = _write_evidence_if_requested(report, args.evidence_out)

    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True, default=str))
    else:
        _print_human(report)

    if args.strict and report.get("blocking_issues"):
        return 2
    if args.live_sign and report.get("verification_status") != "verified":
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
