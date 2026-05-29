from __future__ import annotations

import pandas as pd
import streamlit as st

from components.api import get_json, post_json
from components.ui import dataframe, empty_state, last_updated, page_header


def _metric_grid(row_counts: dict) -> None:
    metrics = [
        ("Donors", row_counts.get("dim_donor", 0)),
        ("Referrals", row_counts.get("fact_donor_screening", 0)),
        ("Partner Submissions", row_counts.get("dim_partner_submission", 0)),
        ("QMS Deviations", row_counts.get("fact_deviation", 0)),
        ("CAPAs", row_counts.get("fact_capa", 0)),
        ("Vendor SLA Events", row_counts.get("fact_vendor_incident", 0)),
        ("Audit Events", row_counts.get("fact_audit_log", 0)),
        ("Workflow Tasks", row_counts.get("fact_workflow_task", 0)),
    ]
    cols = st.columns(4)
    for index, (label, value) in enumerate(metrics):
        cols[index % 4].metric(label, value)


def _operation_panel() -> None:
    st.markdown("<div class='section-title'>Producer Controls</div>", unsafe_allow_html=True)
    st.caption("Write operations require explicit confirmation and use finite cycles by default.")

    seed_tab, incremental_tab, continuous_tab, validation_tab, export_tab = st.tabs(
        ["Seed", "Incremental", "Continuous", "Validation", "Export"]
    )
    with seed_tab:
        with st.form("producer_seed_form"):
            records = st.number_input("Seed records", min_value=500, max_value=5000, value=1200, step=100)
            seed = st.number_input("Deterministic seed", min_value=0, value=42, step=1)
            force = st.checkbox("Clear and reseed existing demo data")
            confirm = st.checkbox("Confirm seed generation")
            submitted = st.form_submit_button("Run Seed Generation")
        if submitted:
            if not confirm:
                st.warning("Confirm seed generation before running.")
            else:
                result = post_json(
                    "/api/generation/seed?confirm=true",
                    {"records": int(records), "seed": int(seed), "force": force},
                )
                if result:
                    st.success(f"Seed generation {result.get('status')}.")

    with incremental_tab:
        with st.form("producer_incremental_form"):
            scale = st.number_input("Activity scale", min_value=1, max_value=25, value=1, step=1)
            seed = st.number_input("Seed", min_value=0, value=42, step=1, key="incremental_seed")
            confirm = st.checkbox("Confirm incremental generation")
            submitted = st.form_submit_button("Generate Incremental Activity")
        if submitted:
            if not confirm:
                st.warning("Confirm incremental generation before running.")
            else:
                result = post_json(
                    "/api/generation/incremental?confirm=true",
                    {"scale": int(scale), "seed": int(seed)},
                )
                if result:
                    st.success(f"Incremental generation {result.get('status')}.")

    with continuous_tab:
        with st.form("producer_continuous_form"):
            interval = st.number_input("Interval seconds", min_value=1, max_value=3600, value=30, step=5)
            cycles = st.number_input("Cycles", min_value=1, max_value=1000, value=3, step=1)
            scale = st.number_input("Scale per cycle", min_value=1, max_value=25, value=1, step=1)
            seed = st.number_input("Seed", min_value=0, value=42, step=1, key="continuous_seed")
            export_each_cycle = st.checkbox("Export after each cycle")
            confirm = st.checkbox("Confirm continuous generation start")
            submitted = st.form_submit_button("Start Continuous Generation")
        stop_col, refresh_col = st.columns(2)
        if submitted:
            if not confirm:
                st.warning("Confirm continuous generation before starting.")
            else:
                result = post_json(
                    "/api/generation/continuous/start?confirm=true",
                    {
                        "interval_seconds": int(interval),
                        "cycles": int(cycles),
                        "scale": int(scale),
                        "seed": int(seed),
                        "export_each_cycle": export_each_cycle,
                        "allow_infinite": False,
                    },
                )
                if result:
                    st.success("Continuous generation started.")
        if stop_col.button("Stop Continuous Generation", width="stretch"):
            result = post_json("/api/generation/continuous/stop?confirm=true", {})
            if result:
                st.info("Stop requested.")
        if refresh_col.button("Refresh Producer Status", width="stretch"):
            st.rerun()

    with validation_tab:
        with st.form("producer_validation_form"):
            confirm = st.checkbox("Confirm validation run")
            submitted = st.form_submit_button("Run Validation")
        if submitted:
            if not confirm:
                st.warning("Confirm validation before running.")
            else:
                result = post_json("/api/generation/validate?confirm=true", {})
                if result:
                    st.success(f"Validation {result.get('status')}.")

    with export_tab:
        with st.form("producer_export_form"):
            batch_id = st.text_input("Batch ID", placeholder="Leave blank for generated batch id")
            confirm = st.checkbox("Confirm export")
            submitted = st.form_submit_button("Export Source Batch")
        if submitted:
            if not confirm:
                st.warning("Confirm export before running.")
            else:
                payload = {"batch_id": batch_id} if batch_id else {}
                result = post_json("/api/generation/export?confirm=true", payload)
                if result:
                    st.success(f"Exported batch {result.get('batch_id')}.")


def render() -> None:
    page_header(
        "Data Producer",
        "Clinical source-system activity for donor referrals, partner portal workflow, QMS, vendor SLA, audit, and exports.",
    )
    payload = get_json("/api/generation/status") or {}
    if not payload:
        st.error("Data producer status is unavailable.")
        return

    last_updated()
    _metric_grid(payload.get("row_counts", {}))

    status = payload.get("continuous", {})
    cols = st.columns(4)
    cols[0].metric("Continuous", "Running" if status.get("running") else "Stopped")
    cols[1].metric("Cycles Complete", status.get("cycles_completed", 0))
    cols[2].metric("Latest Validation", (payload.get("latest_validation") or {}).get("status", "Unknown"))
    cols[3].metric("Latest Export", (payload.get("latest_export_manifest") or {}).get("batch_id", "None"))

    _operation_panel()

    st.markdown("<div class='section-title'>Source Freshness</div>", unsafe_allow_html=True)
    freshness = (payload.get("source_freshness") or {}).get("freshness", [])
    dataframe(freshness, height=260) if freshness else empty_state("No freshness metadata is available yet.")

    left, right = st.columns(2)
    with left:
        st.markdown("<div class='section-title'>Latest Validation</div>", unsafe_allow_html=True)
        validation = payload.get("latest_validation") or {}
        checks = validation.get("checks") or []
        if checks:
            dataframe(checks, height=300)
        else:
            empty_state("No validation run has been recorded.")
    with right:
        st.markdown("<div class='section-title'>Latest Export Manifest</div>", unsafe_allow_html=True)
        manifest = payload.get("latest_export_manifest") or {}
        files = manifest.get("files") or []
        if files:
            dataframe(files, height=300)
        else:
            empty_state("No export manifest has been recorded.")

    st.markdown("<div class='section-title'>Recent Runs</div>", unsafe_allow_html=True)
    runs = get_json("/api/generation/runs?limit=25") or []
    if runs:
        frame = pd.DataFrame(runs)
        keep = [
            "run_type",
            "status",
            "started_at",
            "duration_seconds",
            "extraction_batch_id",
            "warnings",
            "errors",
        ]
        st.dataframe(frame[[column for column in keep if column in frame.columns]], width="stretch", height=320, hide_index=True)
    else:
        empty_state("No producer runs have been recorded.")
