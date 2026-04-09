"""Page 4: Game Detail — per-game momentum, box score, win probability, rally log."""

from dash import html, dcc, callback, Input, Output
import pandas as pd
import plotly.graph_objects as go

from analytics.advanced import momentum_data, win_probability_table
from analytics.player import player_stats_filtered
from analytics.team import detect_runs
from components.charts import momentum_chart
from components.tables import stat_table
from components.filters import game_dropdown

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


def _format_set_scores(match):
    """Build a set-scores string like 'W 2-1: 25-20, 23-25, 15-12'."""
    sets_won = match.get("sets_won", 0)
    sets_lost = match.get("sets_lost", 0)
    result = "W" if sets_won > sets_lost else "L"
    set_scores = match.get("set_scores", [])
    score_parts = [f"{s['a']}-{s['b']}" for s in set_scores]
    return f"{result} {sets_won}-{sets_lost}: {', '.join(score_parts)}" if score_parts else f"{result} {sets_won}-{sets_lost}"


def _build_game_content(video_id, matches, rallies_df, actions_df):
    """Build all sections for a selected game. Returns a list of Dash components."""
    # Find the match dict
    match = next((m for m in matches if m["video_id"] == video_id), None)
    if match is None:
        return [html.P("Game not found.", style={"color": "#999"})]

    sections = []

    # --- 1. Set Scores Display ---
    score_text = _format_set_scores(match)
    opponent = match.get("title", "Unknown")
    game_date = match.get("date", "")[:10]
    sections.append(
        html.Div([
            html.H3(f"{opponent}", style={"margin": "0", "color": "#2c3e50"}),
            html.P(f"{game_date}  |  {score_text}",
                   style={"fontSize": "18px", "color": "#1a73e8", "fontWeight": "bold", "margin": "5px 0 0 0"}),
        ], style={
            "backgroundColor": "white", "padding": "15px", "borderRadius": "8px",
            "boxShadow": "0 1px 3px rgba(0,0,0,0.1)", "marginBottom": "20px",
        })
    )

    # --- 2. Momentum Chart ---
    mom_df = momentum_data(rallies_df, video_id)
    if not mom_df.empty:
        fig = momentum_chart(mom_df, title="Score Differential by Set")
        sections.append(_section("Momentum", dcc.Graph(figure=fig)))

    # --- 3. Box Score (Player Stats) ---
    box_score = player_stats_filtered(actions_df, "video_id", video_id)
    if not box_score.empty:
        sections.append(_section(
            "Box Score",
            stat_table(box_score, "game-box-score-table"),
        ))

    # --- 4. Win Probability Curve ---
    game_rallies = rallies_df[rallies_df["video_id"] == video_id].sort_values(
        ["set_number", "rally_id"]
    )
    if not game_rallies.empty:
        wp_table = win_probability_table(rallies_df)
        if not wp_table.empty:
            # Merge win_pct onto each rally by (our_score_before, opp_score_before)
            game_wp = game_rallies[["set_number", "rally_id", "our_score_before", "opp_score_before"]].copy()
            game_wp = game_wp.merge(
                wp_table[["our_score", "opp_score", "win_pct"]],
                left_on=["our_score_before", "opp_score_before"],
                right_on=["our_score", "opp_score"],
                how="left",
            )
            game_wp["rally_seq"] = range(1, len(game_wp) + 1)

            fig_wp = go.Figure()
            for sn in sorted(game_wp["set_number"].unique()):
                sdf = game_wp[game_wp["set_number"] == sn]
                fig_wp.add_trace(go.Scatter(
                    x=sdf["rally_seq"], y=sdf["win_pct"],
                    mode="lines+markers", name=f"Set {sn}",
                    marker=dict(size=4),
                ))
            fig_wp.add_hline(y=50, line_dash="dash", line_color="gray")
            fig_wp.update_layout(
                title="Win Probability by Rally",
                height=400,
                xaxis_title="Rally #",
                yaxis_title="Win Probability (%)",
                margin=dict(l=40, r=20, t=50, b=40),
            )
            sections.append(_section("Win Probability", dcc.Graph(figure=fig_wp)))

    # --- 5. Rally Log ---
    if not game_rallies.empty:
        log_cols = ["rally_id", "set_number", "our_score", "opp_score", "point_winner", "serving_team"]
        available_cols = [c for c in log_cols if c in game_rallies.columns]
        rally_log = game_rallies[available_cols].copy()
        sections.append(_section(
            "Rally Log",
            stat_table(rally_log, "game-rally-log-table", page_size=20),
        ))

    if not sections:
        sections.append(html.P("No data available for this game.", style={"color": "#999"}))

    return sections


def layout(dfs):
    """Return the static page structure. Content is populated by the callback."""
    global _dfs
    _dfs = dfs

    matches = dfs["matches"]

    # Sort matches by date descending for the dropdown
    sorted_matches = sorted(matches, key=lambda m: m.get("date", ""), reverse=True)
    default_vid = sorted_matches[0]["video_id"] if sorted_matches else None

    # Build dropdown options with "opponent (date)" label
    options = []
    for m in sorted_matches:
        label = f"{m['title']} ({m['date'][:10]})"
        options.append({"label": label, "value": m["video_id"]})

    return html.Div([
        html.H2("Game Detail"),

        # Game selector
        html.Div([
            html.Label("Select Game:", style={"fontWeight": "bold", "marginRight": "10px"}),
            dcc.Dropdown(
                id="game-selector",
                options=options,
                value=default_vid,
                clearable=False,
                style={"width": "500px"},
            ),
        ], style={"display": "flex", "alignItems": "center", "marginBottom": "20px"}),

        # Container updated by the callback
        html.Div(id="game-detail-content"),
    ])


# ---------------------------------------------------------------------------
# Callback -- registered at module import time so Dash finds the IDs.
# ---------------------------------------------------------------------------

@callback(
    Output("game-detail-content", "children"),
    Input("game-selector", "value"),
)
def update_game_detail(video_id):
    if not video_id or not _dfs:
        return html.P("Select a game to see details.")
    return _build_game_content(
        video_id, _dfs["matches"], _dfs["rallies"], _dfs["actions"]
    )
