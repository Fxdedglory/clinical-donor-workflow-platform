from __future__ import annotations

import csv
from pathlib import Path

from scripts.export_to_parquet_lake import export_to_parquet_lake
from scripts.validate_parquet_lake import validate_parquet_lake


def test_clinical_parquet_lake_fixture_export_and_validation(tmp_path: Path) -> None:
    fixture_root = tmp_path / "fixture"
    fixture_root.mkdir()
    fixture_path = fixture_root / "dim_donor.csv"
    with fixture_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["donor_id", "created_at", "updated_at"])
        writer.writeheader()
        writer.writerow(
            {
                "donor_id": "DNR-TEST-001",
                "created_at": "2026-05-01T10:00:00Z",
                "updated_at": "2026-05-02T10:00:00Z",
            }
        )

    lake_root = tmp_path / "datalake"
    manifest = export_to_parquet_lake(
        fixture_root=fixture_root,
        lake_root=lake_root,
        batch_id="clinical_parquet_test",
        source_system="clinical",
    )
    validation = validate_parquet_lake(lake_root, source_system="clinical", batch_id="clinical_parquet_test")

    assert manifest["mode"] == "fixture"
    assert manifest["row_count"] == 1
    assert validation["status"] == "passed"
