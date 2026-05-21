from __future__ import annotations

import json
from datetime import datetime
from typing import Any

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

RISK_COLORS = {
    "Low": "#178a6f",
    "Moderate": "#b7791f",
    "High": "#c05621",
    "Critical": "#c53030",
}

STATUS_COLORS = {
    "Draft Intake": "#64748b",
    "Pending Intake Validation": "#2b6cb0",
    "Pending Clinical Review": "#6b46c1",
    "Clinical Review In Progress": "#4c51bf",
    "Pending Additional Information": "#b7791f",
    "High Risk Escalation": "#c05621",
    "QA Investigation": "#7b341e",
    "CAPA Investigation": "#9b2c2c",
    "Clinical Re-Review": "#805ad5",
    "Operations Escalation": "#c53030",
    "Approved": "#178a6f",
    "Released": "#178a6f",
    "Released for Clinical Use": "#178a6f",
    "Released for Research Use": "#178a6f",
    "Release Approved": "#178a6f",
    "Recovery Authorized": "#178a6f",
    "Resolved": "#178a6f",
    "Eligible": "#178a6f",
    "Pending": "#b7791f",
    "Conditional": "#b7791f",
    "Needs Review": "#b7791f",
    "Pending Administrative Screen": "#b7791f",
    "Pending Medical Social History Review": "#b7791f",
    "Pending Infectious Disease Review": "#b7791f",
    "Pending Tissue Suitability Review": "#b7791f",
    "Pending Recovery Suitability Review": "#b7791f",
    "Pending Medical Director Review": "#b7791f",
    "Pending QA Review": "#b7791f",
    "Pending Processing Release": "#b7791f",
    "Awaiting Lab Results": "#b7791f",
    "Awaiting Signatures": "#b7791f",
    "Awaiting External Review": "#b7791f",
    "Awaiting Medical Director Review": "#b7791f",
    "Escalated": "#c05621",
    "High Priority": "#c05621",
    "SLA Risk": "#c05621",
    "Processing Hold": "#c05621",
    "Release Hold": "#c05621",
    "Hold": "#c05621",
    "Rejected": "#c53030",
    "Critical": "#c53030",
    "Blocked": "#c53030",
    "Overdue": "#c53030",
    "Destroyed": "#c53030",
    "Quarantine": "#c53030",
    "Closed": "#2f855a",
    "Archived": "#64748b",
    "Inactive": "#64748b",
    "Open": "#c05621",
}


def apply_theme(compact_sidebar: bool = False) -> None:
    sidebar_width = "6.4rem" if compact_sidebar else "18rem"
    sidebar_padding = "0.45rem" if compact_sidebar else "1rem"
    sidebar_css = f"""
        section[data-testid="stSidebar"] {{
            display: block !important;
            visibility: visible !important;
            opacity: 1 !important;
            min-width: {sidebar_width} !important;
            max-width: {sidebar_width} !important;
            width: {sidebar_width} !important;
            transform: translateX(0) !important;
            left: 0 !important;
            background: #0b2738 !important;
            border-right: 1px solid rgba(255,255,255,0.08) !important;
            z-index: 999991 !important;
        }}

        section[data-testid="stSidebar"] > div,
        section[data-testid="stSidebar"] div[data-testid="stSidebarContent"] {{
            display: block !important;
            visibility: visible !important;
            opacity: 1 !important;
            min-height: 100vh;
            background: #0b2738 !important;
        }}

        section[data-testid="stSidebar"] div[data-testid="stSidebarContent"] {{
            padding-left: {sidebar_padding};
            padding-right: {sidebar_padding};
        }}
    """
    st.markdown(
        """
        <style>
        :root {
            --clinical-teal: #127c75;
            --clinical-teal-dark: #0f5f5a;
            --clinical-slate: #243141;
            --clinical-muted: #657282;
            --clinical-border: #d9e1e8;
            --clinical-surface: #ffffff;
            --clinical-bg: #f7f9fb;
            --clinical-success: #178a6f;
            --clinical-warning: #b7791f;
            --clinical-orange: #c05621;
            --clinical-danger: #c53030;
            --clinical-gray: #64748b;
        }

        .stApp {
            background: var(--clinical-bg);
            color: var(--clinical-slate);
        }

        #MainMenu,
        footer,
        div[data-testid="stToolbar"] {
            visibility: hidden;
        }

        header[data-testid="stHeader"] {
            background: transparent;
        }

        section[data-testid="stSidebar"] h1,
        section[data-testid="stSidebar"] h2,
        section[data-testid="stSidebar"] h3 {
            color: #f8fbfc;
        }

        section[data-testid="stSidebar"] p,
        section[data-testid="stSidebar"] span,
        section[data-testid="stSidebar"] label {
            color: #e7f1f4;
        }

        section[data-testid="stSidebar"] div[data-testid="stCaptionContainer"] p {
            color: #aec3cc;
        }

        .sidebar-notice {
            background: rgba(255,255,255,0.10);
            border: 1px solid rgba(255,255,255,0.18);
            border-radius: 8px;
            padding: 12px 14px;
            margin: 12px 0 16px;
            color: #f8fbfc;
        }

        .sidebar-notice div {
            color: #c7dbe2;
            font-size: 0.82rem;
            margin-bottom: 0.25rem;
        }

        .sidebar-notice strong {
            color: #ffffff;
            display: block;
            font-size: 1.45rem;
            line-height: 1.2;
        }

        .workspace-card {
            background: rgba(255,255,255,0.10);
            border: 1px solid rgba(255,255,255,0.18);
            border-radius: 8px;
            padding: 12px 14px;
            margin: 12px 0 16px;
        }

        .workspace-card div {
            color: #c7dbe2;
            font-size: 0.78rem;
            margin-bottom: 0.35rem;
        }

        .workspace-card strong {
            color: #ffffff;
            display: block;
            font-size: 0.95rem;
            line-height: 1.35;
        }

        section[data-testid="stSidebar"] div.stButton button p,
        section[data-testid="stSidebar"] div.stButton button span {
            color: #0b2738 !important;
        }

        section[data-testid="stSidebar"] div.stButton button {
            border-radius: 7px;
            border: 1px solid rgba(255,255,255,0.12);
            background: rgba(255,255,255,0.92);
            min-height: 2.4rem;
            font-size: 0.88rem;
            font-weight: 600;
            box-shadow: none;
        }

        section[data-testid="stSidebar"] div.stButton button:hover {
            border-color: #8dd3ca;
            background: #ffffff;
        }

        section[data-testid="stSidebar"] hr {
            border-color: rgba(255,255,255,0.16);
        }

        .block-container {
            padding-top: 1.05rem;
            padding-bottom: 2rem;
            max-width: 1440px;
        }

        .app-topbar {
            background: #ffffff;
            border: 1px solid var(--clinical-border);
            border-radius: 8px;
            padding: 10px 12px;
            margin-bottom: 12px;
            box-shadow: 0 1px 2px rgba(36,49,65,0.04);
            position: relative;
            z-index: 20;
            overflow: visible;
        }

        div[data-testid="stHorizontalBlock"] {
            overflow: visible;
        }

        .app-topbar div[data-testid="stVerticalBlock"],
        .app-topbar div[data-testid="column"] {
            overflow: visible;
            align-items: stretch;
        }

        div.stButton > button,
        div[data-testid="stPopover"] > button,
        div[data-testid="stFormSubmitButton"] > button {
            min-height: 42px;
            height: 42px;
            line-height: 1;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            padding-top: 0;
            padding-bottom: 0;
            position: relative;
            z-index: 30;
        }

        div[data-testid="stTextInput"] input {
            min-height: 42px;
            line-height: 42px;
        }

        div[data-testid="stPopover"] {
            position: relative;
            z-index: 40;
        }

        .system-notice {
            background: #fff8ed;
            border: 1px solid #f0d29d;
            border-left: 4px solid var(--clinical-orange);
            border-radius: 8px;
            color: #5f3d07;
            padding: 10px 14px;
            margin: 0 0 14px;
            font-size: 0.92rem;
        }

        .operational-card {
            background: #ffffff;
            border: 1px solid var(--clinical-border);
            border-radius: 8px;
            padding: 14px 16px;
            margin-bottom: 14px;
            box-shadow: 0 1px 2px rgba(36,49,65,0.04);
        }

        .operational-card h3 {
            margin: 0 0 8px;
            font-size: 1rem;
            color: var(--clinical-slate);
        }

        .muted-small {
            color: var(--clinical-muted);
            font-size: 0.78rem;
        }

        div[data-testid="stMetric"] {
            background: #ffffff;
            border: 1px solid var(--clinical-border);
            border-radius: 8px;
            padding: 14px 16px;
            box-shadow: 0 1px 2px rgba(36,49,65,0.04);
        }

        div[data-testid="stMetricLabel"] p {
            color: var(--clinical-muted);
            font-size: 0.78rem;
            letter-spacing: 0;
        }

        div[data-testid="stMetricValue"] {
            color: var(--clinical-slate);
            font-size: 1.55rem;
        }

        div[data-testid="stDataFrame"] {
            border: 1px solid var(--clinical-border);
            border-radius: 8px;
            overflow: hidden;
        }

        .clinical-panel {
            background: #ffffff;
            border: 1px solid var(--clinical-border);
            border-radius: 8px;
            padding: 16px 18px;
            margin-bottom: 16px;
        }

        .clinical-kicker {
            color: var(--clinical-muted);
            font-size: 0.82rem;
            margin-top: -0.45rem;
            margin-bottom: 1.1rem;
        }

        .status-chip {
            display: inline-block;
            border-radius: 6px;
            padding: 4px 8px;
            font-size: 0.78rem;
            font-weight: 600;
            color: #ffffff;
        }

        .soft-chip {
            display: inline-block;
            border-radius: 6px;
            padding: 3px 7px;
            font-size: 0.76rem;
            font-weight: 650;
            color: var(--clinical-slate);
            background: #eef3f7;
            border: 1px solid #d9e1e8;
        }

        .section-title {
            font-weight: 700;
            color: var(--clinical-slate);
            margin-bottom: 0.35rem;
        }

        .empty-state {
            background: #ffffff;
            border: 1px dashed var(--clinical-border);
            border-radius: 8px;
            padding: 18px;
            color: var(--clinical-muted);
            text-align: center;
            margin-bottom: 14px;
        }

        """
        + sidebar_css
        + """
        </style>
        """,
        unsafe_allow_html=True,
    )


def page_header(title: str, subtitle: str) -> None:
    st.title(title)
    st.markdown(f"<div class='clinical-kicker'>{subtitle}</div>", unsafe_allow_html=True)


def last_updated(label: str | None = None) -> None:
    value = label or datetime.now().strftime("%I:%M %p").lstrip("0")
    st.markdown(f"<div class='muted-small'>Last Updated: {value}</div>", unsafe_allow_html=True)


def status_chip(label: str, palette: dict[str, str] | None = None) -> str:
    colors = palette or STATUS_COLORS
    color = colors.get(label, "#657282")
    return f"<span class='status-chip' style='background:{color}'>{label}</span>"


def soft_chip(label: str) -> str:
    return f"<span class='soft-chip'>{label}</span>"


def empty_state(message: str) -> None:
    st.markdown(f"<div class='empty-state'>{message}</div>", unsafe_allow_html=True)


def dataframe(records: list[dict[str, Any]], columns: list[str] | None = None, height: int = 420) -> None:
    if not records:
        empty_state("No records match the current filters.")
        return
    df = pd.DataFrame(records)
    if columns:
        df = df[[col for col in columns if col in df.columns]]
    df = df.rename(columns=lambda col: str(col).replace("_", " ").title())
    st.dataframe(df, width="stretch", height=height, hide_index=True)


def json_preview(value: Any, max_chars: int = 140) -> str:
    if value is None:
        return ""
    text = json.dumps(value, default=str)
    return text if len(text) <= max_chars else f"{text[:max_chars]}..."


def empty_figure(title: str) -> go.Figure:
    fig = go.Figure()
    fig.update_layout(
        title=title,
        height=320,
        margin=dict(l=20, r=20, t=50, b=20),
        paper_bgcolor="#ffffff",
        plot_bgcolor="#ffffff",
        annotations=[
            dict(
                text="No data available",
                x=0.5,
                y=0.5,
                xref="paper",
                yref="paper",
                showarrow=False,
                font=dict(color="#657282"),
            )
        ],
    )
    return fig
