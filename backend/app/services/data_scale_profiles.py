"""Clinical data scale profile definitions."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class DataScaleProfile:
    name: str
    records: int
    incremental_scale: int
    start_date: date
    end_date: date
    expected_rows: str
    runtime_estimate: str
    storage_estimate: str
    export_estimate: str
    azure_suitability: str
    snowflake_suitability: str
    powerbi_suitability: str
    notes: str


DATA_SCALE_PROFILES: dict[str, DataScaleProfile] = {
    "demo": DataScaleProfile(
        "demo",
        500,
        1,
        date(2026, 1, 1),
        date(2026, 5, 29),
        "~5K-15K clinical/QMS/workflow rows",
        "1-3 minutes locally",
        "<100 MB database/export footprint",
        "<100 MB full source export",
        "Safe for current Azure PostgreSQL/App Service footprint.",
        "Good for schema, relationship, and source freshness smoke tests.",
        "Good for operational screen demos.",
        "Minimum deterministic baseline because the existing seed path enforces at least 500 donors.",
    ),
    "small": DataScaleProfile(
        "small",
        1200,
        3,
        date(2025, 7, 1),
        date(2026, 5, 29),
        "~20K-60K clinical/QMS/workflow rows",
        "Several minutes locally",
        "Hundreds of MB possible after exports",
        "Hundreds of MB possible",
        "Feasible for Azure PostgreSQL with monitoring.",
        "Useful for incremental ingestion and EDW conformed-key testing.",
        "Useful for queue, SLA, CAPA, and audit trend demos.",
        "Recommended first non-demo Azure clinical baseline after backup validation.",
    ),
    "medium": DataScaleProfile(
        "medium",
        5000,
        10,
        date(2024, 1, 1),
        date(2026, 5, 29),
        "~100K-300K clinical/QMS/workflow rows",
        "Longer controlled local run",
        "GB-class database/export footprint possible",
        "GB-class full exports possible",
        "Use cautiously; monitor PostgreSQL size and App Service startup.",
        "Good for Snowflake ingestion and dbt L1/L2/L3 rehearsal.",
        "Use through aggregated marts for responsive analytics.",
        "Dry-run locally before Azure.",
    ),
    "large": DataScaleProfile(
        "large",
        20000,
        25,
        date(2021, 1, 1),
        date(2026, 5, 29),
        "Path toward 50K+ referrals and 1M+ workflow events",
        "Long-running controlled batch",
        "Multi-GB database/export footprint",
        "Multi-GB full exports",
        "Requires explicit storage/cost plan.",
        "Good for performance and retention strategy rehearsal.",
        "Use via Snowflake marts only.",
        "Not for current App Service local ad hoc execution.",
    ),
    "enterprise": DataScaleProfile(
        "enterprise",
        50000,
        25,
        date(2019, 1, 1),
        date(2026, 5, 29),
        "Target: 50K+ referrals, 100K+ screenings, 1M+ workflow events, 2M+ audit events",
        "Long-running batch with operator supervision",
        "Multi-GB to tens-of-GB footprint depending on audit/event density",
        "Multi-GB exports",
        "Requires PostgreSQL capacity review and external export storage.",
        "Enterprise-scale clinical EDW and audit-history rehearsal.",
        "Power BI should consume modeled aggregates, not raw event tables.",
        "Planning profile until capacity and retention controls are approved.",
    ),
}


def resolve_profile(
    profile: str,
    *,
    records_override: int | None = None,
    scale_override: int | None = None,
    start_date_override: str | None = None,
    end_date_override: str | None = None,
) -> DataScaleProfile:
    key = profile.lower().strip()
    if key not in DATA_SCALE_PROFILES:
        valid = ", ".join(sorted(DATA_SCALE_PROFILES))
        raise ValueError(f"Unknown data scale profile {profile!r}. Valid profiles: {valid}.")
    base = DATA_SCALE_PROFILES[key]
    return DataScaleProfile(
        base.name,
        records_override or base.records,
        scale_override or base.incremental_scale,
        date.fromisoformat(start_date_override) if start_date_override else base.start_date,
        date.fromisoformat(end_date_override) if end_date_override else base.end_date,
        base.expected_rows,
        base.runtime_estimate,
        base.storage_estimate,
        base.export_estimate,
        base.azure_suitability,
        base.snowflake_suitability,
        base.powerbi_suitability,
        base.notes,
    )


def profile_as_dict(profile: DataScaleProfile) -> dict[str, str | int]:
    return {
        "profile": profile.name,
        "records": profile.records,
        "incremental_scale": profile.incremental_scale,
        "start_date": profile.start_date.isoformat(),
        "end_date": profile.end_date.isoformat(),
        "expected_rows": profile.expected_rows,
        "runtime_estimate": profile.runtime_estimate,
        "storage_estimate": profile.storage_estimate,
        "export_estimate": profile.export_estimate,
        "azure_suitability": profile.azure_suitability,
        "snowflake_suitability": profile.snowflake_suitability,
        "powerbi_suitability": profile.powerbi_suitability,
        "notes": profile.notes,
    }
