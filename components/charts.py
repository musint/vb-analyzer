"""Reusable Plotly figure builders."""

import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np


def kpi_card(label: str, value, subtitle: str = "") -> go.Figure:
    """Single KPI indicator card."""
    fig = go.Figure(go.Indicator(
        mode="number",
        value=value if isinstance(value, (int, float)) else 0,
        title={"text": f"<b>{label}</b><br><span style='font-size:0.7em;color:gray'>{subtitle}</span>"},
        number={"suffix": "%" if "pct" in label.lower() or "%" in str(subtitle) else ""},
    ))
    fig.update_layout(height=120, margin=dict(l=10, r=10, t=50, b=10))
    return fig


def bar_comparison(df: pd.DataFrame, x: str, y_cols: list, labels: list, title: str = "") -> go.Figure:
    """Grouped bar chart comparing multiple metrics."""
    fig = go.Figure()
    for col, label in zip(y_cols, labels):
        fig.add_trace(go.Bar(name=label, x=df[x], y=df[col], text=df[col].round(3), textposition="auto"))
    fig.update_layout(title=title, barmode="group", height=400, margin=dict(l=40, r=20, t=50, b=40))
    return fig


def line_trend(df: pd.DataFrame, x: str, y: str, title: str = "", y_label: str = "") -> go.Figure:
    """Line chart for trends."""
    fig = px.line(df, x=x, y=y, title=title, markers=True)
    fig.update_layout(height=350, yaxis_title=y_label, margin=dict(l=40, r=20, t=50, b=40))
    return fig


def dot_plot(values: list, avg: float, title: str = "") -> go.Figure:
    """Dot plot showing individual match values vs average line."""
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=list(range(1, len(values) + 1)), y=values,
        mode="markers", marker=dict(size=8, color="#636EFA"),
        name="Per Match",
    ))
    fig.add_hline(y=avg, line_dash="dash", line_color="red", annotation_text=f"Avg: {avg:.3f}")
    fig.update_layout(title=title, height=250, xaxis_title="Match #", margin=dict(l=40, r=20, t=50, b=40))
    return fig


def radar_chart(players: list[dict], metrics: list[str], labels: list[str], title: str = "") -> go.Figure:
    """Radar chart comparing players across metrics."""
    fig = go.Figure()
    for p in players:
        values = [p.get(m, 0) or 0 for m in metrics]
        values.append(values[0])  # close the polygon
        fig.add_trace(go.Scatterpolar(r=values, theta=labels + [labels[0]], name=p["player"], fill="toself"))
    fig.update_layout(title=title, polar=dict(radialaxis=dict(visible=True)), height=450)
    return fig


def momentum_chart(df: pd.DataFrame, title: str = "") -> go.Figure:
    """Score differential line chart with run bands for one match."""
    fig = go.Figure()
    for sn in sorted(df["set_number"].unique()):
        sdf = df[df["set_number"] == sn]
        fig.add_trace(go.Scatter(
            x=sdf["rally_num"], y=sdf["score_diff"],
            mode="lines+markers", name=f"Set {sn}",
            marker=dict(size=4),
        ))
    fig.add_hline(y=0, line_dash="dash", line_color="gray")
    fig.update_layout(title=title, height=400, xaxis_title="Rally #", yaxis_title="Score Differential",
                      margin=dict(l=40, r=20, t=50, b=40))
    return fig


def game_flow_with_runs(df: pd.DataFrame, our_runs: list, opp_runs: list, title: str = "") -> go.Figure:
    """Momentum chart with colored bands for scoring runs."""
    fig = momentum_chart(df, title)

    # Add run bands as shaded rectangles
    for run in our_runs:
        first_rally = run[0]["rally_num"] if "rally_num" in run[0] else 0
        last_rally = run[-1]["rally_num"] if "rally_num" in run[-1] else 0
        fig.add_vrect(x0=first_rally - 0.5, x1=last_rally + 0.5,
                      fillcolor="green", opacity=0.1, line_width=0)

    for run in opp_runs:
        first_rally = run[0]["rally_num"] if "rally_num" in run[0] else 0
        last_rally = run[-1]["rally_num"] if "rally_num" in run[-1] else 0
        fig.add_vrect(x0=first_rally - 0.5, x1=last_rally + 0.5,
                      fillcolor="red", opacity=0.1, line_width=0)

    return fig
