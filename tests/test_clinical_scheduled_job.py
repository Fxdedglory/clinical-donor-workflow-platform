from __future__ import annotations

from pathlib import Path

import pytest

from scripts import run_clinical_scheduled_job as job


class _FakeSession:
    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False


class _FakePublisher:
    configured = False

    def __init__(self) -> None:
        self.calls = []

    def publish_cycle(self, **kwargs):
        self.calls.append(kwargs)


def _patch_common(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, *, validation_rows: int = 10) -> dict[str, int]:
    calls = {"incremental": 0, "export": 0, "upload": 0}
    monkeypatch.setenv("CLINICAL_JOB_BATCH_ID", "clinical_job_test")
    monkeypatch.setenv("CLINICAL_JOB_LAKE_ROOT", str(tmp_path / "lake"))
    monkeypatch.setenv("CLINICAL_JOB_RESULT_PATH", str(tmp_path / "job_result.json"))
    monkeypatch.setenv("CLINICAL_JOB_ACCEPTED_MANIFEST_PATH", str(tmp_path / "accepted" / "clinical_job_test.json"))
    monkeypatch.setenv("CLINICAL_JOB_UPLOAD_ADLS", "true")
    monkeypatch.setenv("CLINICAL_JOB_ADLS_DRY_RUN", "true")
    monkeypatch.setenv("DATA_LAKE_ACCOUNT_NAME", "stteemailslakewcus")
    monkeypatch.setattr(job, "SessionLocal", lambda: _FakeSession())
    monkeypatch.setattr(job, "MonitorPublisher", _FakePublisher)

    def fake_incremental(*_args, **_kwargs):
        calls["incremental"] += 1
        return {"status": "succeeded", "row_counts": {"dim_donor": 2}}

    def fake_validate(_db):
        return {"status": "passed", "row_counts": {"dim_donor": validation_rows}}

    def fake_export(**kwargs):
        calls["export"] += 1
        lake_root = Path(kwargs["lake_root"])
        manifest_path = lake_root / "manifests" / "source_system=clinical" / "extraction_date=2026-06-04" / "clinical_job_test.json"
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text("{}", encoding="utf-8")
        return {
            "source_system": "clinical",
            "extraction_batch_id": "clinical_job_test",
            "row_count": validation_rows,
            "file_count": 1,
            "manifest_path": str(manifest_path),
            "files": [{"source_table": "dim_donor", "row_count": validation_rows}],
        }

    def fake_parquet_validate(*_args, **_kwargs):
        return {"status": "passed", "issues": []}

    def fake_upload(**_kwargs):
        calls["upload"] += 1
        return {"file_count": 3, "container": "datalake", "account_name": "stteemailslakewcus"}

    monkeypatch.setattr(job, "run_incremental_generation", fake_incremental)
    monkeypatch.setattr(job, "validate_database", fake_validate)
    monkeypatch.setattr(job, "export_to_parquet_lake", fake_export)
    monkeypatch.setattr(job, "validate_parquet_lake", fake_parquet_validate)
    monkeypatch.setattr(job, "upload_parquet_lake_to_adls", fake_upload)
    return calls


def test_export_only_job_does_not_mutate_database(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    calls = _patch_common(monkeypatch, tmp_path)
    monkeypatch.setenv("CLINICAL_JOB_REFRESH_MODE", "export_only")

    result = job.run_job()

    assert result["status"] == "succeeded"
    assert result["refresh_mode"] == "export_only"
    assert result["row_count"] == 10
    assert result["file_count"] == 1
    assert result["adls_upload"]["status"] == "dry_run"
    assert calls["incremental"] == 0
    assert calls["export"] == 1
    assert calls["upload"] == 1
    assert (tmp_path / "accepted" / "clinical_job_test.json").exists()


def test_incremental_demo_refresh_job_runs_bounded_incremental(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    calls = _patch_common(monkeypatch, tmp_path, validation_rows=12)
    monkeypatch.setenv("CLINICAL_JOB_REFRESH_MODE", "incremental_demo_refresh")
    monkeypatch.setenv("CLINICAL_JOB_INCREMENTAL_SCALE", "1")

    result = job.run_job()

    assert result["status"] == "succeeded"
    assert result["refresh_mode"] == "incremental_demo_refresh"
    assert result["row_count"] == 12
    assert calls["incremental"] == 1


def test_full_reseed_is_disabled_for_v2_4f(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    _patch_common(monkeypatch, tmp_path)
    monkeypatch.setenv("CLINICAL_JOB_REFRESH_MODE", "full_reseed")

    with pytest.raises(PermissionError):
        job.run_job()
