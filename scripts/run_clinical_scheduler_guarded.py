from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))


def main() -> None:
    from app.services.clinical_scheduler_guardrails import (
        DESTRUCTIVE_CONFIRMATION_PHRASE,
        run_clinical_scheduler_refresh,
    )

    parser = argparse.ArgumentParser(description="Guarded Clinical external scheduler runner")
    parser.add_argument("--refresh-mode", choices=["export_only", "incremental_demo_refresh", "full_reseed"], default="incremental_demo_refresh")
    parser.add_argument("--batch-id", default=None)
    parser.add_argument("--execute", action="store_true", help="Execute the guarded job. Omit for dry-run.")
    parser.add_argument("--force", action="store_true", help="Required with destructive refresh modes.")
    parser.add_argument("--confirm", default="", help=f"Required for destructive refresh: {DESTRUCTIVE_CONFIRMATION_PHRASE}")
    parser.add_argument("--backup-evidence-file", default=None, help="JSON file containing PostgreSQL backup evidence for destructive refresh.")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--scale", type=int, default=1)
    parser.add_argument("--export-root", default=None)
    args = parser.parse_args()

    backup_evidence = None
    if args.backup_evidence_file:
        backup_evidence = json.loads(Path(args.backup_evidence_file).read_text(encoding="utf-8"))

    result = run_clinical_scheduler_refresh(
        refresh_mode=args.refresh_mode,
        batch_id=args.batch_id,
        dry_run=not args.execute,
        force=args.force,
        confirm=args.confirm,
        backup_evidence=backup_evidence,
        seed=args.seed,
        scale=args.scale,
        export_root=args.export_root,
    )
    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
