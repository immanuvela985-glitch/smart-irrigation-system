"""Shared Streamlit theme, layout helpers, and Plotly charts."""

from __future__ import annotations

from typing import Any

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.config import APP_SUBTITLE, APP_TITLE, BLUE, GREEN, NAVY
from src.state import format_timestamp, init_state, source_banner_text, sync_hardware_from_settings

CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&display=swap');

html, body, [class*="css"] {{
  font-family: "DM Sans", "Segoe UI", sans-serif;
}}

.stApp {{
  background: linear-gradient(180deg, #EEF3F8 0%, { '#F3F6FB' } 40%, #EAF3EE 100%);
}}

section[data-testid="stSidebar"] {{
  background: linear-gradient(180deg, {NAVY} 0%, #10233F 58%, #0E3328 130%);
}}
section[data-testid="stSidebar"] * {{
  color: #E7EEF8 !important;
}}
section[data-testid="stSidebar"] .stSelectbox label,
section[data-testid="stSidebar"] .stRadio label {{
  color: #D5E2F3 !important;
}}

.brand-mark {{
  display: flex;
  gap: 12px;
  align-items: center;
  padding: 8px 4px 18px 4px;
  border-bottom: 1px solid rgba(255,255,255,0.12);
  margin-bottom: 10px;
}}
.brand-logo {{
  width: 42px;
  height: 42px;
  border-radius: 12px;
  background: linear-gradient(135deg, {GREEN}, {BLUE});
  display: grid;
  place-items: center;
  font-weight: 700;
  font-size: 18px;
}}
.brand-title {{ font-size: 15px; font-weight: 700; line-height: 1.25; }}
.brand-sub {{ font-size: 12px; opacity: 0.75; }}

.page-kicker {{
  color: {BLUE};
  font-size: 12px;
  letter-spacing: 0.14em;
  font-weight: 700;
  text-transform: uppercase;
  margin-bottom: 4px;
}}
.page-title {{
  font-size: 30px;
  font-weight: 700;
  color: {NAVY};
  margin: 0;
}}
.page-help {{
  color: #4B5D78;
  margin: 6px 0 18px 0;
}}

.metric-card {{
  background: #FFFFFF;
  border: 1px solid #E3EAF3;
  border-radius: 18px;
  padding: 16px 18px 14px 18px;
  box-shadow: 0 10px 28px rgba(11, 29, 54, 0.06);
  min-height: 118px;
}}
.metric-label {{
  font-size: 12px;
  color: #5B6B82;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  font-weight: 600;
}}
.metric-value {{
  font-size: 28px;
  font-weight: 700;
  color: {NAVY};
  margin: 8px 0 4px 0;
}}
.metric-hint {{ color: #6B7C93; font-size: 13px; }}
.metric-card.accent-green {{ border-top: 4px solid {GREEN}; }}
.metric-card.accent-blue {{ border-top: 4px solid {BLUE}; }}
.metric-card.accent-navy {{ border-top: 4px solid {NAVY}; }}
.metric-card.accent-amber {{ border-top: 4px solid #D39B2A; }}

.banner {{
  border-radius: 14px;
  padding: 12px 16px;
  margin: 0 0 16px 0;
  border: 1px solid transparent;
}}
.banner-demo {{ background: #E8F4EE; border-color: #B7DCC6; color: #145C32; }}
.banner-warn {{ background: #FFF6E5; border-color: #F0D29A; color: #7A4B00; }}
.banner-error {{ background: #FDECEC; border-color: #F3C0C0; color: #8A1F1F; }}
.banner-info {{ background: #E7F1FB; border-color: #B9D4F0; color: #1A4E86; }}
.banner b {{ font-weight: 700; }}

.status-pill {{
  display: inline-block;
  border-radius: 999px;
  padding: 4px 10px;
  font-size: 12px;
  font-weight: 700;
}}
.pill-on {{ background: #E5F7EB; color: #157A3A; }}
.pill-off {{ background: #EEF2F6; color: #4E5D70; }}
.pill-req {{ background: #FFF3D6; color: #8A5A00; }}
.pill-ok {{ background: #E5F0FB; color: #1D6FBF; }}

.empty-state {{
  background: white;
  border: 1px dashed #C9D6E5;
  border-radius: 16px;
  padding: 28px 20px;
  text-align: center;
  color: #5C6E86;
}}

div[data-testid="stExpander"] {{
  background: white;
  border-radius: 14px;
  border: 1px solid #E3EAF3;
}}
</style>
"""


def configure_page(page_title: str) -> None:
    st.set_page_config(
        page_title=f"{page_title} · Smart Irrigation",
        page_icon="🌿",
        layout="wide",
        initial_sidebar_state="expanded",
    )


def apply_theme() -> None:
    init_state()
    sync_hardware_from_settings()
    st.markdown(CSS, unsafe_allow_html=True)
    with st.sidebar:
        st.markdown(
            """
            <div class="brand-mark">
              <div class="brand-logo">AI</div>
              <div>
                <div class="brand-title">Smart Irrigation</div>
                <div class="brand-sub">ML + IoT dashboard</div>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        kind, detail = source_banner_text()
        st.caption(f"{kind}")
        st.caption(detail)


def page_header(kicker: str, title: str, help_text: str) -> None:
    st.markdown(f'<div class="page-kicker">{kicker}</div>', unsafe_allow_html=True)
    st.markdown(f'<h1 class="page-title">{title}</h1>', unsafe_allow_html=True)
    st.markdown(f'<p class="page-help">{help_text}</p>', unsafe_allow_html=True)


def metric_card(label: str, value: str, hint: str, accent: str = "green") -> None:
    st.markdown(
        f"""
        <div class="metric-card accent-{accent}">
          <div class="metric-label">{label}</div>
          <div class="metric-value">{value}</div>
          <div class="metric-hint">{hint}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def banner(kind: str, title: str, body: str) -> None:
    st.markdown(
        f'<div class="banner banner-{kind}"><b>{title}</b><br>{body}</div>',
        unsafe_allow_html=True,
    )


def empty_state(title: str, body: str) -> None:
    st.markdown(
        f'<div class="empty-state"><b>{title}</b><p>{body}</p></div>',
        unsafe_allow_html=True,
    )


def moisture_chart(frame: pd.DataFrame, title: str = "Soil moisture history") -> go.Figure:
    fig = go.Figure()
    if frame is None or frame.empty or "soil_moisture" not in frame.columns:
        fig.update_layout(title="No moisture history yet")
        return fig
    x = frame["timestamp"] if "timestamp" in frame.columns else frame.index
    fig.add_trace(
        go.Scatter(
            x=x,
            y=frame["soil_moisture"],
            mode="lines",
            name="Soil moisture (%)",
            line=dict(color=GREEN, width=3),
            fill="tozeroy",
            fillcolor="rgba(31,138,76,0.12)",
        )
    )
    threshold = float(st.session_state.get("moisture_threshold", 35))
    fig.add_hline(
        y=threshold,
        line_dash="dash",
        line_color=BLUE,
        annotation_text=f"Threshold {threshold:.0f}%",
        annotation_position="top left",
    )
    fig.update_layout(
        title=title,
        height=360,
        margin=dict(l=10, r=10, t=50, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="white",
        xaxis_title="Time",
        yaxis_title="Moisture (%)",
        yaxis=dict(range=[0, 100]),
        font=dict(color="#12233D", family="DM Sans, Segoe UI, sans-serif"),
        hovermode="x unified",
    )
    return fig


def comparison_chart(results: list[dict[str, Any]]) -> go.Figure:
    names = [item["name"] for item in results]
    fig = go.Figure()
    palette = { "accuracy": GREEN, "precision": BLUE, "recall": "#0B1D36", "f1": "#D39B2A" }
    for metric in ("accuracy", "precision", "recall", "f1"):
        fig.add_trace(
            go.Bar(
                x=names,
                y=[item[metric] for item in results],
                name=metric.upper() if metric == "f1" else metric.title(),
                marker_color=palette[metric],
            )
        )
    fig.update_layout(
        barmode="group",
        height=380,
        yaxis=dict(range=[0, 1], title="Score"),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="white",
        legend=dict(orientation="h", y=1.12),
        margin=dict(l=10, r=10, t=30, b=10),
        font=dict(color="#12233D"),
    )
    return fig


def confusion_heatmap(matrix: list[list[int]], title: str) -> go.Figure:
    fig = go.Figure(
        data=go.Heatmap(
            z=matrix,
            x=["Pred 0", "Pred 1"],
            y=["True 0", "True 1"],
            colorscale=[[0, "#EAF3EE"], [1, GREEN]],
            text=matrix,
            texttemplate="%{text}",
            showscale=False,
        )
    )
    fig.update_layout(title=title, height=280, margin=dict(l=10, r=10, t=40, b=10))
    return fig


def status_row() -> None:
    hardware = st.session_state.hardware
    info = hardware.connection_info()
    last = format_timestamp(st.session_state.last_update)
    pump = "ON" if hardware.pump_on else "OFF"
    kind, _ = source_banner_text()
    c1, c2, c3 = st.columns(3)
    with c1:
        metric_card("System status", kind, info.detail, "navy")
    with c2:
        metric_card("Pump", pump, hardware.last_command_reason, "amber" if hardware.pump_on else "blue")
    with c3:
        metric_card("Last update", last, APP_SUBTITLE, "green")
