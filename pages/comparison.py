"""Page: Player Comparison with radar charts, stat tables, and trendlines."""

from dash import html, dcc, callback, Input, Output
import pandas as pd
import plotly.graph_objects as go

from analytics.player import (
    player_season_stats, consistency_index, clutch_comparison, season_progression,
)
from components.charts import radar_chart, line_trend
from components.tables import stat_table

# Module-level reference populated by layout(); used by the callback.
_dfs = {}


def _section(title, *children):
    """Wrap a section with a title and card-like styling."""
    return html.Div([
        html.H4(title, style={"marginBottom": "10px"}),
        *children,
    ], style={
        "backgroundColor": "white", "padding": "15px", "borderRadius": "8px",
        "boxShadow": "0 1px 3px rgba(0,0,0,0.1)", "marginBottom": "20px",
    })


def layout(dfs):
    """Return the static page structure. Content is populated by the callback."""
    global _dfs
    _dfs = dfs

    actions_df = dfs["actions"]
    stats = player_season_stats(actions_df)
    player_options = (
        [{"label": p, "value": p} for p in stats["player"].tolist()]
        if not stats.empty else []
    )
    default_players = [o["value"] for o in player_options[:2]]

    return html.Div([
        html.H2("Player Comparison"),

        # Multi-select player dropdown
        html.Div([
            html.Label("Select Players (2-4):",
                       style={"fontWeight": "bold", "marginRight": "10px"}),
            dcc.Dropdown(
                id="compare-players",
                options=player_options,
                value=default_players,
                multi=True,
                placeholder="Select 2-4 players to compare...",
                style={"width": "600px"},
            ),
        ], style={"display": "flex", "alignItems": "center", "marginBottom": "20px"}),

        # Container updated by the callback
        html.Div(id="compare-content"),
    ])


def _normalize(values):
    """Min-max normalize a list of values to 0-1, skipping None."""
    numeric = [v for v in values if v is not None]
    if not numeric:
        return values
    vmin = min(numeric)
    vmax = max(numeric)
    if vmax == vmin:
        return [0.5 if v is not None else None for v in values]
    return [(v - vmin) / (vmax - vmin) if v is not None else None for v in values]


def _build_comparison(selected_players, actions_df):
    """Build all comparison sections for the selected players."""
    sections = []

    # --- Gather all team data for normalization ---
    all_stats = player_season_stats(actions_df)
    all_consistency = consistency_index(actions_df)
    all_clutch = clutch_comparison(actions_df)

    if all_stats.empty:
        return [html.P("No player data available.", style={"color": "#999"})]

    # Build a combined metrics dict for all players (for normalization)
    metrics_map = {}  # player -> {metric: value}
    for _, row in all_stats.iterrows():
        p = row["player"]
        metrics_map[p] = {
            "hitting_eff": row["hitting_eff"],
            "kill_pct": row["kill_pct"],
            "pass_avg": row["pass_avg"],  # may be None
        }

    # Add consistency scores
    if not all_consistency.empty:
        for _, row in all_consistency.iterrows():
            p = row["player"]
            if p in metrics_map:
                metrics_map[p]["consistency_score"] = row["consistency_score"]

    # Add clutch ratings
    if not all_clutch.empty:
        for _, row in all_clutch.iterrows():
            p = row["player"]
            if p in metrics_map and pd.notna(row.get("clutch_rating")):
                metrics_map[p]["clutch_rating"] = row["clutch_rating"]

    # --- Compute normalized values across ALL team players ---
    radar_metrics = ["hitting_eff", "kill_pct", "pass_avg", "consistency_score", "clutch_rating"]
    radar_labels = ["Hitting Eff", "Kill %", "Pass Avg", "Consistency", "Clutch Rating"]

    # Collect raw values per metric across all players
    all_raw = {m: [] for m in radar_metrics}
    for p, mdict in metrics_map.items():
        for m in radar_metrics:
            val = mdict.get(m)
            all_raw[m].append(val)

    # Normalize each metric
    all_norm = {m: _normalize(vals) for m, vals in all_raw.items()}

    # Map normalized values back to players
    all_players_list = list(metrics_map.keys())
    norm_map = {}  # player -> {metric: normalized_value}
    for i, p in enumerate(all_players_list):
        norm_map[p] = {}
        for m in radar_metrics:
            norm_map[p][m] = all_norm[m][i]

    # --- 1. Radar Chart ---
    # Filter to only metrics that have data for at least one selected player
    active_metrics = []
    active_labels = []
    for m, label in zip(radar_metrics, radar_labels):
        if any(norm_map.get(p, {}).get(m) is not None for p in selected_players):
            active_metrics.append(m)
            active_labels.append(label)

    if active_metrics:
        radar_players = []
        for p in selected_players:
            entry = {"player": p}
            for m in active_metrics:
                entry[m] = norm_map.get(p, {}).get(m, 0) or 0
            radar_players.append(entry)

        sections.append(_section(
            "Player Comparison Radar",
            dcc.Graph(figure=radar_chart(
                radar_players, active_metrics, active_labels,
                title="Normalized Player Comparison (0-1 scale)",
            )),
        ))

    # --- 2. Side-by-side stat table ---
    selected_stats = all_stats[all_stats["player"].isin(selected_players)].copy()
    if not selected_stats.empty:
        display_cols = [
            "player", "kills", "att_total", "hitting_eff", "kill_pct",
            "aces", "srv_total", "pass_avg", "digs", "blocks", "total_actions",
        ]
        display_cols = [c for c in display_cols if c in selected_stats.columns]
        sections.append(_section(
            "Season Stats Comparison",
            stat_table(selected_stats[display_cols], "compare-stat-table"),
        ))

    # --- 3. Overlaid progression trendlines ---
    prog = season_progression(actions_df)
    prog_players = [p for p in selected_players if p in prog]
    if prog_players:
        fig = go.Figure()
        for p in prog_players:
            pdf = prog[p]
            fig.add_trace(go.Scatter(
                x=pdf["date"], y=pdf["hitting_eff_rolling"],
                mode="lines+markers", name=p, marker=dict(size=5),
            ))
        fig.update_layout(
            title="Rolling Hitting Efficiency (Season Progression)",
            height=400,
            xaxis_title="Date",
            yaxis_title="Hitting Efficiency (Rolling)",
            margin=dict(l=40, r=20, t=50, b=40),
        )
        sections.append(_section(
            "Season Progression Comparison",
            dcc.Graph(figure=fig),
        ))

    if not sections:
        sections.append(html.P("No comparison data available for the selected players.",
                               style={"color": "#999"}))

    return sections


# ---------------------------------------------------------------------------
# Callback
# ---------------------------------------------------------------------------

@callback(
    Output("compare-content", "children"),
    Input("compare-players", "value"),
)
def update_comparison(selected_players):
    if not selected_players or len(selected_players) < 2 or not _dfs:
        return html.P("Select at least 2 players to compare.",
                      style={"color": "#999", "fontStyle": "italic"})
    if len(selected_players) > 4:
        return html.P("Please select at most 4 players.",
                      style={"color": "#e74c3c", "fontStyle": "italic"})
    return _build_comparison(selected_players, _dfs["actions"])
