from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.core.config import settings  # noqa: E402
from app.schemas.clinical import WorkflowOperation  # noqa: E402
from app.services.clinical_audit_mirror import (  # noqa: E402
    audit_mirror_checksum,
    audit_mirror_config_from_settings,
    audit_mirror_payload,
)
from app.services.clinical_audit_mirror_providers import AzureBlobAuditMirrorProvider  # noqa: E402
from app.services.clinical_azure_worm_evidence import (  # noqa: E402
    build_validation_evidence,
    write_validation_evidence,
)
from app.services.clinical_azure_worm_live_readiness import (  # noqa: E402
    LIVE_TESTS_ENV,
    build_live_readiness_report,
    live_test_prefix,
)


def _operation() -> WorkflowOperation:
    return WorkflowOperation(
        operation_id=f"azure-worm-readiness-{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}",
        workflow="audit.azure_worm_live_readiness",
        entity_type="clinical_audit_worm_live_test",
        entity_id="AZURE-WORM-READINESS",
        actor="azure-worm-readiness-script",
        timestamp=datetime.now(UTC),
        preview_hash="sha256-azure-worm-readiness",
        commit_confirmed=True,
        status_before="planned",
        status_after="validated",
        reason="Manual Azure WORM readiness validation",
        changes={"manual_readiness": True, "payload_profile": "audit_metadata"},
    )


def run_live_write(report: dict[str, Any]) -> dict[str, Any]:
    config = audit_mirror_config_from_settings(settings)
    provider = AzureBlobAuditMirrorProvider(config)
    operation = _operation()
    payload = audit_mirror_payload(operation)
    checksum = audit_mirror_checksum(payload)
    key = f"{live_test_prefix()}/{operation.workflow}/{operation.operation_id}.json"

    written = provider.put_object(key, payload, checksum)
    stat = provider.stat_object(written.uri)
    verification = provider.verify_object_checksum(written.uri, checksum)
    report.update(
        {
            "upload_attempted": True,
            "network_calls_performed": True,
            "live_write": {
                "operation_id": operation.operation_id,
                "uri": written.uri,
                "checksum": checksum,
                "stat_exists": stat.exists,
                "verification_status": verification.get("status"),
            },
        }
    )
    return report


def build_report(*, live_write_requested: bool) -> dict[str, Any]:
    config = audit_mirror_config_from_settings(settings)
    report = build_live_readiness_report(
        config=config,
        live_write_requested=live_write_requested,
    )
    report["mode"] = "live_write" if live_write_requested else "dry_run"
    return report


def _print_human(report: dict[str, Any]) -> None:
    readiness = report["provider_readiness"]
    print("Clinical Azure WORM readiness")
    print(f"mode={report['mode']}")
    print(f"provider={readiness.get('provider')}")
    print(f"provider_ready={readiness.get('ready')}")
    print(f"expected_uri_prefix={readiness.get('expected_uri_prefix')}")
    print(f"real_io_enabled={report['real_io_enabled']}")
    print(f"live_tests_enabled={report['live_tests_enabled']} ({LIVE_TESTS_ENV})")
    print(f"live_test_prefix={report['live_test_prefix'] or '<unset>'}")
    print(f"upload_attempted={report['upload_attempted']}")
    print(f"network_calls_performed={report['network_calls_performed']}")
    if report.get("evidence_out"):
        print(f"evidence_out={report['evidence_out']}")
    if report["blocking_issues"]:
        print("blocking_issues:")
        for issue in report["blocking_issues"]:
            print(f"- {issue['code']}: {issue['message']}")
    if report["warnings"]:
        print("warnings:")
        for issue in report["warnings"]:
            print(f"- {issue['code']}: {issue['message']}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check Azure WORM audit mirror readiness.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    parser.add_argument("--strict", action="store_true", help="Return nonzero when readiness has blocking issues.")
    parser.add_argument(
        "--evidence-out",
        help="Write a sanitized Azure WORM validation evidence JSON artifact to this path.",
    )
    parser.add_argument(
        "--live-write",
        action="store_true",
        help=(
            "Perform one live Azure Blob write/stat/checksum check. Requires "
            f"{LIVE_TESTS_ENV}=true and safe live-test settings."
        ),
    )
    args = parser.parse_args(argv)

    report = build_report(live_write_requested=args.live_write)
    if args.live_write:
        if report["blocking_issues"] or report["provider_readiness"].get("ready") is not True:
            if args.evidence_out:
                evidence = build_validation_evidence(report, environment_mode=settings.app_env)
                evidence_path = write_validation_evidence(args.evidence_out, evidence)
                report["evidence_out"] = str(evidence_path)
            if args.json:
                print(json.dumps(report, indent=2, sort_keys=True, default=str))
            else:
                _print_human(report)
            return 2
        report = run_live_write(report)

    if args.evidence_out:
        evidence = build_validation_evidence(report, environment_mode=settings.app_env)
        evidence_path = write_validation_evidence(args.evidence_out, evidence)
        report["evidence_out"] = str(evidence_path)

    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True, default=str))
    else:
        _print_human(report)

    if args.strict and (report["blocking_issues"] or report["provider_readiness"].get("ready") is not True):
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
