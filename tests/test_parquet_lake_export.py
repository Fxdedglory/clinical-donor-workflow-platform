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


def test_clinical_parquet_lake_excludes_sensitive_columns(tmp_path: Path) -> None:
    import pyarrow.parquet as pq

    fixture_root = tmp_path / "fixture"
    fixture_root.mkdir()
    fixture_path = fixture_root / "dim_user.csv"
    with fixture_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "user_id",
                "email",
                "hashed_password",
                "password_reset_token",
                "mfa_enabled",
                "donor_identifier_hash",
            ],
        )
        writer.writeheader()
        writer.writerow(
            {
                "user_id": "1",
                "email": "demo@example.test",
                "hashed_password": "not-exported",
                "password_reset_token": "not-exported",
                "mfa_enabled": "true",
                "donor_identifier_hash": "not-exported",
            }
        )

    lake_root = tmp_path / "datalake"
    manifest = export_to_parquet_lake(
        fixture_root=fixture_root,
        lake_root=lake_root,
        batch_id="clinical_sensitive_column_test",
        source_system="clinical",
    )
    parquet_path = Path(manifest["files"][0]["parquet_path"])
    exported = pq.ParquetFile(parquet_path).read()

    assert "user_id" in exported.column_names
    assert "email" in exported.column_names
    assert "hashed_password" not in exported.column_names
    assert "password_reset_token" not in exported.column_names
    assert "mfa_enabled" not in exported.column_names
    assert "donor_identifier_hash" not in exported.column_names
