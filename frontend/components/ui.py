from __future__ import annotations

import json
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
    "Pending": "#2b6cb0",
    "Under Review": "#6b46c1",
    "Approved": "#178a6f",
    "Rejected": "#c53030",
    "Deferred": "#b7791f",
    "Open": "#c05621",
    "Resolved": "#178a6f",
}


def apply_theme() -> None:
    st.markdown(
        """
        <style>
        :root {
            --clinical-teal: #127c75;
            --clinical-slate: #243141;
            --clinical-muted: #657282;
            --clinical-border: #d9e1e8;
            --clinical-surface: #ffffff;
            --clinical-bg: #f7f9fb;
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

        section[data-testid="stSidebar"] {
            background: linear-gradient(180deg, #063548 0%, #082638 100%);
            border-right: 1px solid rgba(255,255,255,0.08);
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

        section[data-testid="stSidebar"] hr {
            border-color: rgba(255,255,255,0.16);
        }

        .block-container {
            padding-top: 1.8rem;
            padding-bottom: 2rem;
            max-width: 1440px;
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

        .section-title {
            font-weight: 700;
            color: var(--clinical-slate);
            margin-bottom: 0.35rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def page_header(title: str, subtitle: str) -> None:
    st.title(title)
    st.markdown(f"<div class='clinical-kicker'>{subtitle}</div>", unsafe_allow_html=True)


def status_chip(label: str, palette: dict[str, str] | None = None) -> str:
    colors = palette or STATUS_COLORS
    color = colors.get(label, "#657282")
    return f"<span class='status-chip' style='background:{color}'>{label}</span>"


def dataframe(records: list[dict[str, Any]], columns: list[str] | None = None, height: int = 420) -> None:
    if not records:
        st.info("No records match the current filters.")
        return
    df = pd.DataFrame(records)
    if columns:
        df = df[[col for col in columns if col in df.columns]]
    df = df.rename(columns=lambda col: str(col).replace("_", " ").title())
    st.dataframe(df, use_container_width=True, height=height, hide_index=True)


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
