from __future__ import annotations

import json
from pathlib import Path

from scripts.upload_parquet_lake_to_adls import collect_upload_plan, upload_parquet_lake_to_adls


def _write_minimal_lake(lake_root: Path, source_system: str, batch_id: str) -> None:
    parquet_path = (
        lake_root
        / "bronze"
        / f"source_system={source_system}"
        / "source_table=donor_referrals"
        / "extraction_date=2026-05-30"
        / f"extraction_batch_id={batch_id}"
        / "part-00000.parquet"
    )
    schema_path = lake_root / "_schemas" / f"source_system={source_system}" / "source_table=donor_referrals.json"
    manifest_path = lake_root / "manifests" / f"source_system={source_system}" / "extraction_date=2026-05-30" / f"{batch_id}.json"
    parquet_path.parent.mkdir(parents=True, exist_ok=True)
    schema_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    parquet_path.write_bytes(b"PAR1")
    schema_path.write_text(json.dumps({"source_table": "donor_referrals"}), encoding="utf-8")
    manifest_path.write_text(
        json.dumps(
            {
                "source_system": source_system,
                "extraction_batch_id": batch_id,
                "files": [{"parquet_path": str(parquet_path), "schema_path": str(schema_path), "row_count": 1}],
            }
        ),
        encoding="utf-8",
    )


def test_collect_upload_plan_preserves_lake_layout(tmp_path: Path) -> None:
    lake_root = tmp_path / "datalake"
    _write_minimal_lake(lake_root, "clinical", "clinical_upload_test")

    plan = collect_upload_plan(lake_root, "clinical", "clinical_upload_test")
    blob_names = {item["blob_name"] for item in plan}

    assert blob_names == {
        "bronze/source_system=clinical/source_table=donor_referrals/extraction_date=2026-05-30/extraction_batch_id=clinical_upload_test/part-00000.parquet",
        "_schemas/source_system=clinical/source_table=donor_referrals.json",
        "manifests/source_system=clinical/extraction_date=2026-05-30/clinical_upload_test.json",
    }


def test_upload_dry_run_does_not_require_azure_credentials(tmp_path: Path) -> None:
    lake_root = tmp_path / "datalake"
    _write_minimal_lake(lake_root, "clinical", "clinical_upload_test")

    result = upload_parquet_lake_to_adls(
        lake_root=lake_root,
        source_system="clinical",
        batch_id="clinical_upload_test",
        account_name="example",
        dry_run=True,
    )

    assert result["dry_run"] is True
    assert result["file_count"] == 3
    assert {file["status"] for file in result["files"]} == {"dry_run"}
