from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

REQUIRED_DOCS = [
    "docs/architecture/azure_hosting_readiness_audit.md",
    "docs/architecture/no_docker_no_uv_migration_plan.md",
    "docs/azure/app_service_hosting_plan.md",
    "docs/azure/app_settings_reference.md",
    "docs/azure/final_azure_deployment_execution_plan.md",
    "docs/security/entra_id_future_integration_plan.md",
    "docs/security/external_partner_access_model.md",
    "docs/security/final_security_hardening_backlog.md",
    "docs/runbooks/local_development_runbook.md",
    "docs/runbooks/data_producer_runbook.md",
]

SENSITIVE_PATTERNS = [
    "BEGIN " + "RSA PRIVATE KEY",
    "BEGIN " + "OPENSSH PRIVATE KEY",
    "AK" + "IA",
    "AZURE_CLIENT_" + "SECRET=",
    "SENDGRID_API_" + "KEY=SG.",
    "MAILGUN_API_" + "KEY=key-",
]


def run(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=ROOT, text=True, capture_output=True, check=False)


def main() -> None:
    from app.core.config import settings
    from app.services.production_security_gates import validate_production_security_gates

    checks: list[dict] = []

    def add(name: str, passed: bool, detail: str, severity: str = "error") -> None:
        checks.append({"name": name, "passed": passed, "detail": detail, "severity": severity})

    for doc in REQUIRED_DOCS:
        add(f"required doc {doc}", (ROOT / doc).exists(), doc)

    git_files = run(["git", "ls-files"]).stdout.splitlines()
    generated_tracked = [
        path
        for path in git_files
        if path.startswith(("data/generated/", "data/exports/", "logs/"))
        and not path.endswith(".gitkeep")
    ]
    add("generated bulk data not tracked", not generated_tracked, ", ".join(generated_tracked) or "none")

    large_files = []
    for path_text in git_files:
        path = ROOT / path_text
        if path.exists() and path.is_file() and path.stat().st_size > 10 * 1024 * 1024:
            large_files.append(f"{path_text} ({path.stat().st_size} bytes)")
    add("large tracked files under 10MB", not large_files, ", ".join(large_files) or "none", severity="warning")

    ignore_probe = run(["git", "check-ignore", "data/generated/probe.csv", "data/exports/probe.csv", "logs/probe.log", ".venv/probe.txt"])
    ignored = set(ignore_probe.stdout.splitlines())
    add("generated paths are ignored", "data/generated/probe.csv" in ignored and "data/exports/probe.csv" in ignored, ignore_probe.stdout.strip())
    add("venv and logs are ignored", ".venv/probe.txt" in ignored and "logs/probe.log" in ignored, ignore_probe.stdout.strip())

    tracked_text = "\n".join(
        (ROOT / path).read_text(encoding="utf-8", errors="ignore")
        for path in git_files
        if (ROOT / path).suffix.lower() in {".py", ".md", ".toml", ".txt", ".example", ".yml", ".yaml"}
        and (ROOT / path).is_file()
    )
    found_patterns = [pattern for pattern in SENSITIVE_PATTERNS if pattern in tracked_text]
    add("high-signal secret patterns absent", not found_patterns, ", ".join(found_patterns) or "none")

    docker_files = [path for path in git_files if "Dockerfile" in path or path in {"docker-compose.yml", "docker-compose.prod.yml"}]
    uv_files = [path for path in git_files if path == "uv.lock"]
    pyproject = ROOT / "pyproject.toml"
    if pyproject.exists() and "[tool.uv]" in pyproject.read_text(encoding="utf-8", errors="ignore"):
        uv_files.append("pyproject.toml")
    add("Docker artifacts are legacy only", bool(docker_files), ", ".join(docker_files), severity="warning")
    add("uv artifacts absent", not uv_files, ", ".join(uv_files) or "none")

    gate_result = validate_production_security_gates(settings)
    if gate_result.production_like:
        add(
            "production security gates pass",
            gate_result.passed,
            "; ".join(f"{issue.code}: {issue.message}" for issue in gate_result.failures) or "passed",
        )
    else:
        add(
            "production security gates local warning inventory",
            True,
            f"{len(gate_result.warnings)} production-hardening warning(s) in {gate_result.environment} mode",
            severity="warning",
        )

    failed = [check for check in checks if not check["passed"] and check["severity"] == "error"]
    payload = {
        "status": "passed" if not failed else "failed",
        "checks": checks,
    }
    print(json.dumps(payload, indent=2))
    raise SystemExit(1 if failed else 0)


if __name__ == "__main__":
    main()
