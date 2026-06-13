from __future__ import annotations

from copy import deepcopy
from typing import Any

SMALL_CELL_THRESHOLD = 5
SUPPRESSION_REASON = "small_cell"
SUPPRESSION_PROFILES = {"aggregate_safe", "external_safe"}

COUNT_DICT_FIELDS = {
    "status_counts",
    "outcome_counts",
    "type_counts",
    "reason_counts",
    "note_status_counts",
    "order_status_counts",
    "result_status_counts",
    "task_status_counts",
    "priority_counts",
    "claim_status_counts",
    "charge_status_counts",
    "denial_status_counts",
    "severity_counts",
    "category_counts",
    "workflow_counts",
    "actor_counts",
    "entity_type_counts",
    "appointment_type_breakdown",
    "module_counts",
    "row_counts",
}

COUNT_SCALAR_FIELDS = {
    "duplicate_warning_count",
    "supervisor_review_count",
    "override_count",
    "total_operations",
}

SERIES_FIELDS = {"registrations_by_date", "signing_activity"}


def suppression_marker(*, threshold: int = SMALL_CELL_THRESHOLD) -> dict[str, Any]:
    return {
        "value": None,
        "suppressed": True,
        "suppression_reason": SUPPRESSION_REASON,
        "threshold": threshold,
    }


def is_suppressed_cell(value: Any) -> bool:
    return isinstance(value, dict) and value.get("suppressed") is True


def should_suppress_count(value: Any, *, threshold: int = SMALL_CELL_THRESHOLD) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and 0 < value < threshold


def _suppress_count(value: Any, *, threshold: int, paths: list[str], path: str) -> Any:
    if should_suppress_count(value, threshold=threshold):
        paths.append(path)
        return suppression_marker(threshold=threshold)
    return value


def _suppression_metadata(paths: list[str], *, threshold: int) -> dict[str, Any]:
    return {
        "small_cell_suppression": {
            "applied": bool(paths),
            "threshold": threshold,
            "suppression_reason": SUPPRESSION_REASON,
            "suppressed_cells": len(paths),
            "suppressed_paths": paths,
        }
    }


def suppress_report_payload(
    payload: dict[str, Any],
    export_profile: str,
    *,
    threshold: int = SMALL_CELL_THRESHOLD,
) -> tuple[dict[str, Any], dict[str, Any]]:
    if export_profile not in SUPPRESSION_PROFILES:
        redacted = deepcopy(payload)
        metadata = _suppression_metadata([], threshold=threshold)
        redacted["suppression"] = metadata
        return redacted, metadata

    redacted = deepcopy(payload)
    suppressed_paths: list[str] = []

    for metric_index, metric in enumerate(redacted.get("metrics") or []):
        if isinstance(metric, dict) and "value" in metric:
            metric["value"] = _suppress_count(
                metric["value"],
                threshold=threshold,
                paths=suppressed_paths,
                path=f"metrics.{metric_index}.value",
            )

    for field_name in COUNT_DICT_FIELDS:
        value = redacted.get(field_name)
        if not isinstance(value, dict):
            continue
        for key, count_value in list(value.items()):
            value[key] = _suppress_count(
                count_value,
                threshold=threshold,
                paths=suppressed_paths,
                path=f"{field_name}.{key}",
            )

    for field_name in COUNT_SCALAR_FIELDS:
        if field_name in redacted:
            redacted[field_name] = _suppress_count(
                redacted[field_name],
                threshold=threshold,
                paths=suppressed_paths,
                path=field_name,
            )

    for field_name in SERIES_FIELDS:
        for item_index, item in enumerate(redacted.get(field_name) or []):
            if isinstance(item, dict) and "value" in item:
                item["value"] = _suppress_count(
                    item["value"],
                    threshold=threshold,
                    paths=suppressed_paths,
                    path=f"{field_name}.{item_index}.value",
                )

    for row_index, row in enumerate(redacted.get("provider_utilization") or []):
        if not isinstance(row, dict):
            continue
        appointments = row.get("appointments")
        suppressed_appointments = should_suppress_count(appointments, threshold=threshold)
        row["appointments"] = _suppress_count(
            appointments,
            threshold=threshold,
            paths=suppressed_paths,
            path=f"provider_utilization.{row_index}.appointments",
        )
        if suppressed_appointments and isinstance(row.get("scheduled_minutes"), int):
            suppressed_paths.append(f"provider_utilization.{row_index}.scheduled_minutes")
            row["scheduled_minutes"] = suppression_marker(threshold=threshold)

    metadata = _suppression_metadata(suppressed_paths, threshold=threshold)
    redacted["suppression"] = metadata
    return redacted, metadata


def visible_count(value: Any) -> int:
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    return 0
