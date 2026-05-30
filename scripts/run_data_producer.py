from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))


def _print(payload: dict[str, Any] | list[dict[str, Any]]) -> None:
    print(json.dumps(payload, indent=2, default=str))


def _require_confirmation(confirmed: bool, action: str) -> None:
    if not confirmed:
        raise SystemExit(f"{action} requires --confirm.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Clinical data producer utilities")
    parser.add_argument("--metadata-root", default=None, help="Override DATA_PRODUCER_METADATA_ROOT")
    parser.add_argument("--export-root", default=None, help="Override DATA_PRODUCER_EXPORT_ROOT")
    parser.add_argument("--stop-file", default=None, help="Override DATA_PRODUCER_STOP_FILE")
    subparsers = parser.add_subparsers(dest="command", required=True)

    seed_parser = subparsers.add_parser("seed", help="Run deterministic seed generation")
    seed_parser.add_argument("--records", type=int, default=None)
    seed_parser.add_argument("--seed", type=int, default=42)
    seed_parser.add_argument("--profile", choices=["demo", "small", "medium", "large", "enterprise"], default="demo")
    seed_parser.add_argument("--start-date", default=None)
    seed_parser.add_argument("--end-date", default=None)
    seed_parser.add_argument("--force", action="store_true")
    seed_parser.add_argument("--confirm", action="store_true")

    incremental_parser = subparsers.add_parser("incremental", help="Generate row-level incremental activity")
    incremental_parser.add_argument("--seed", type=int, default=42)
    incremental_parser.add_argument("--scale", type=int, default=None)
    incremental_parser.add_argument("--profile", choices=["demo", "small", "medium", "large", "enterprise"], default=None)
    incremental_parser.add_argument("--confirm", action="store_true")

    validate_parser = subparsers.add_parser("validate", help="Validate clinical producer data")
    validate_parser.add_argument("--confirm", action="store_true")

    export_parser = subparsers.add_parser("export", help="Export source-system batch files")
    export_parser.add_argument("--batch-id", default=None)
    export_parser.add_argument("--confirm", action="store_true")

    continuous_parser = subparsers.add_parser("continuous", help="Run continuous generation loop")
    continuous_parser.add_argument("--interval-seconds", type=int, default=30)
    continuous_parser.add_argument("--cycles", type=int, default=1)
    continuous_parser.add_argument("--seed", type=int, default=42)
    continuous_parser.add_argument("--scale", type=int, default=None)
    continuous_parser.add_argument("--profile", choices=["demo", "small", "medium", "large", "enterprise"], default=None)
    continuous_parser.add_argument("--export-each-cycle", action="store_true")
    continuous_parser.add_argument("--allow-infinite", action="store_true")
    continuous_parser.add_argument("--confirm", action="store_true")

    stop_parser = subparsers.add_parser("stop", help="Request continuous generation stop")
    stop_parser.add_argument("--confirm", action="store_true")

    subparsers.add_parser("status", help="Show producer status")
    runs_parser = subparsers.add_parser("runs", help="Show generation run history")
    runs_parser.add_argument("--limit", type=int, default=20)

    args = parser.parse_args()
    if args.metadata_root:
        os.environ["DATA_PRODUCER_METADATA_ROOT"] = args.metadata_root
    if args.export_root:
        os.environ["DATA_PRODUCER_EXPORT_ROOT"] = args.export_root
    if args.stop_file:
        os.environ["DATA_PRODUCER_STOP_FILE"] = args.stop_file

    from app.database import SessionLocal
    from app.services.data_producer import (
        DATA_PRODUCER,
        continuous_state,
        export_database_batch,
        generation_runs,
        generation_status,
        run_incremental_generation,
        run_seed_generation,
        validate_database,
    )

    if args.command == "seed":
        _require_confirmation(args.confirm, "Seed generation")
        _print(
            run_seed_generation(
                records=args.records,
                seed=args.seed,
                force=args.force,
                profile=args.profile,
                start_date=args.start_date,
                end_date=args.end_date,
            )
        )
        return
    if args.command == "incremental":
        _require_confirmation(args.confirm, "Incremental generation")
        scale = args.scale or 1
        if args.profile:
            from app.services.data_scale_profiles import resolve_profile

            scale = resolve_profile(args.profile, scale_override=args.scale).incremental_scale
        with SessionLocal() as db:
            _print(run_incremental_generation(db, seed=args.seed, scale=scale))
        return
    if args.command == "validate":
        _require_confirmation(args.confirm, "Validation")
        with SessionLocal() as db:
            _print(validate_database(db))
        return
    if args.command == "export":
        _require_confirmation(args.confirm, "Export")
        with SessionLocal() as db:
            _print(export_database_batch(db, batch_id=args.batch_id, root=args.export_root))
        return
    if args.command == "continuous":
        _require_confirmation(args.confirm, "Continuous generation")
        scale = args.scale or 1
        if args.profile:
            from app.services.data_scale_profiles import resolve_profile

            scale = resolve_profile(args.profile, scale_override=args.scale).incremental_scale
        cycles = None if args.allow_infinite and args.cycles == 0 else args.cycles
        state = DATA_PRODUCER.start(
            interval_seconds=args.interval_seconds,
            cycles=cycles,
            seed=args.seed,
            scale=scale,
            export_each_cycle=args.export_each_cycle,
            allow_infinite=args.allow_infinite,
        )
        _print(state)
        try:
            while continuous_state().get("running"):
                time.sleep(1)
        except KeyboardInterrupt:
            _print(DATA_PRODUCER.stop())
            raise
        _print(continuous_state())
        return
    if args.command == "stop":
        _require_confirmation(args.confirm, "Stop request")
        _print(DATA_PRODUCER.stop())
        return
    if args.command == "runs":
        _print(generation_runs(limit=args.limit))
        return
    if args.command == "status":
        with SessionLocal() as db:
            _print(generation_status(db))


if __name__ == "__main__":
    main()
