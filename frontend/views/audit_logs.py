import pandas as pd
import streamlit as st
from components.api import get_json
from components.ui import dataframe, json_preview, page_header


def render() -> None:
    page_header(
        "Audit Logs",
        "Compliance traceability for record creation, updates, approvals, and rejection decisions.",
    )

    filters = st.columns([1, 1, 2])
    table_name = filters[0].selectbox(
        "Table",
        ["All", "fact_donor_review", "fact_change_control", "fact_vendor_incident"],
    )
    action_type = filters[1].text_input("Action contains")
    limit = filters[2].slider("Rows", 25, 500, 150, 25)

    params = [f"limit={limit}"]
    if table_name != "All":
        params.append(f"table_name={table_name}")
    records = get_json(f"/api/audit-logs?{'&'.join(params)}") or []
    if action_type:
        records = [row for row in records if action_type.upper() in row["action_type"].upper()]

    if records:
        df = pd.DataFrame(records)
        df["old_value"] = df["old_value"].map(json_preview)
        df["new_value"] = df["new_value"].map(json_preview)
        dataframe(df.to_dict("records"), height=560)
    else:
        st.info("No audit records match the current filters.")

