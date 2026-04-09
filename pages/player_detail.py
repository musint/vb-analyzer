"""Page 2: Player Detail dashboard with per-player drill-down."""

from dash import html, dcc, callback, Input, Output
import pandas as pd

from analytics.player import (
    player_season_stats, player_stats_filtered, clutch_comparison,
    consistency_index, season_progression, in_system_efficiency,
)
from analytics.advanced import serve_pressure_index
from components.charts import bar_comparison, dot_plot, line_trend
from components.tables import stat_table

# Module-level reference populated by layout(); used by the callback.
_dfs = {}


def _stat_card(label, value):
    """Small styled stat card."""
    return html.Div([
        html.H4(str(value), style={"margin": "0", "fontSize": "28px", "color": "#1a73e8"}),
        html.P(label, style={"margin": "0", "fontSize": "12px", "color": "#666"}),
    ], style={
        "textAlign": "center", "padding": "15px", "backgroundColor": "white",
        "borderRadius": "8px", "boxShadow": "0 1px 3px rgba(0,0,0,0.1)", "flex": "1",
    })


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
    """Return the static page structure. Charts are populated by the callback."""
    global _dfs
    _dfs = dfs

    actions_df = dfs["actions"]
    stats = player_season_stats(actions_df)
    player_options = [{"label": p, "value": p} for p in stats["player"].tolist()] if not stats.empty else []
    default_player = player_options[0]["value"] if player_options else None

    return html.Div([
        html.H2("Player Detail"),

        # Player selector
        html.Div([
            html.Label("Select Player:", style={"fontWeight": "bold", "marginRight": "10px"}),
            dcc.Dropdown(
                id="player-dropdown",
                options=player_options,
                value=default_player,
                clearable=False,
                style={"width": "300px"},
            ),
        ], style={"display": "flex", "alignItems": "center", "marginBottom": "20px"}),

        # Container updated by the callback
        html.Div(id="player-detail-content"),
    ])


def _build_player_content(player, actions_df, rallies_df):
    """Build all chart sections for a given player. Returns a list of Dash components."""
    sections = []

    # --- 1. Stat cards ---
    stats = player_season_stats(actions_df)
    p_row = stats[stats["player"] == player]
    if not p_row.empty:
        p = p_row.iloc[0]
        kills = int(p["kills"])
        hitting_eff = f"{p['hitting_eff']:.3f}"
        aces = int(p["aces"])
        pass_avg = f"{p['pass_avg']:.3f}" if pd.notna(p["pass_avg"]) else "N/A"
        digs = int(p["digs"])
        pts = kills + aces + int(p["blocks"])
    else:
        kills, hitting_eff, aces, pass_avg, digs, pts = 0, ".000", 0, "N/A", 0, 0

    sections.append(
        html.Div([
            _stat_card("Kills", kills),
            _stat_card("Hitting Eff", hitting_eff),
            _stat_card("Aces", aces),
            _stat_card("Pass Avg", pass_avg),
            _stat_card("Digs", digs),
            _stat_card("Points", pts),
        ], style={"display": "flex", "gap": "10px", "marginBottom": "20px"})
    )

    # --- 2. Clutch vs Non-Clutch ---
    clutch_df = clutch_comparison(actions_df)
    if not clutch_df.empty:
        cp = clutch_df[clutch_df["player"] == player]
        if not cp.empty:
            sections.append(_section(
                "Clutch vs Non-Clutch Hitting",
                dcc.Graph(figure=bar_comparison(
                    cp, "player",
                    ["hitting_eff_clutch", "hitting_eff_non_clutch"],
                    ["Clutch", "Non-Clutch"],
                    title=f"{player}: Clutch vs Non-Clutch Hitting Efficiency",
                )),
                html.P(
                    f"Clutch Rating: {cp.iloc[0]['clutch_rating']:.3f}"
                    if pd.notna(cp.iloc[0]["clutch_rating"]) else "Clutch Rating: N/A",
                    style={"fontWeight": "bold", "fontSize": "14px"},
                ),
            ))

    # --- 3. Consistency ---
    cons_df = consistency_index(actions_df)
    if not cons_df.empty:
        cp = cons_df[cons_df["player"] == player]
        if not cp.empty:
            row = cp.iloc[0]
            sections.append(_section(
                "Consistency",
                html.Div([
                    html.Div([
                        dcc.Graph(figure=dot_plot(
                            row["per_match_eff"], row["avg_eff"],
                            title=f"{player}: Per-Match Hitting Efficiency",
                        )),
                    ], style={"flex": "2"}),
                    html.Div([
                        html.P(f"Consistency Score: {row['consistency_score']:.3f}",
                               style={"fontSize": "20px", "fontWeight": "bold", "color": "#1a73e8"}),
                        html.P(f"Std Dev: {row['eff_std_dev']:.4f}", style={"fontSize": "14px"}),
                        html.P(f"Avg Eff: {row['avg_eff']:.3f}", style={"fontSize": "14px"}),
                        html.P(f"Matches: {row['matches_with_attacks']}", style={"fontSize": "14px"}),
                    ], style={"flex": "1", "padding": "20px"}),
                ], style={"display": "flex", "gap": "20px"}),
            ))

    # --- 4. Season Progression ---
    prog = season_progression(actions_df)
    if player in prog:
        pdf = prog[player]
        sections.append(_section(
            "Season Progression (Rolling Hitting Efficiency)",
            dcc.Graph(figure=line_trend(
                pdf, "date", "hitting_eff_rolling",
                title=f"{player}: Rolling Hitting Efficiency",
                y_label="Hitting Efficiency",
            )),
        ))

    # --- 5. Score Situation Breakdown ---
    situations = ["winning_big", "winning", "close", "losing", "losing_big"]
    sit_rows = []
    for sit in situations:
        sit_stats = player_stats_filtered(actions_df, "score_situation", sit)
        if not sit_stats.empty:
            sp = sit_stats[sit_stats["player"] == player]
            if not sp.empty and sp.iloc[0]["att_total"] > 0:
                sit_rows.append({
                    "situation": sit,
                    "hitting_eff": sp.iloc[0]["hitting_eff"],
                    "attempts": sp.iloc[0]["att_total"],
                })
    if sit_rows:
        sit_df = pd.DataFrame(sit_rows)
        sections.append(_section(
            "Hitting Efficiency by Score Situation",
            dcc.Graph(figure=bar_comparison(
                sit_df, "situation", ["hitting_eff"], ["Hitting Eff"],
                title=f"{player}: Efficiency by Score Situation",
            )),
        ))

    # --- 6. Game Phase Breakdown ---
    phases = ["early", "middle", "final"]
    phase_rows = []
    for phase in phases:
        ph_stats = player_stats_filtered(actions_df, "game_phase", phase)
        if not ph_stats.empty:
            pp = ph_stats[ph_stats["player"] == player]
            if not pp.empty and pp.iloc[0]["att_total"] > 0:
                phase_rows.append({
                    "phase": phase,
                    "hitting_eff": pp.iloc[0]["hitting_eff"],
                    "attempts": pp.iloc[0]["att_total"],
                })
    if phase_rows:
        phase_df = pd.DataFrame(phase_rows)
        sections.append(_section(
            "Hitting Efficiency by Game Phase",
            dcc.Graph(figure=bar_comparison(
                phase_df, "phase", ["hitting_eff"], ["Hitting Eff"],
                title=f"{player}: Efficiency by Game Phase",
            )),
        ))

    # --- 7. Serve Pressure Index ---
    spi = serve_pressure_index(actions_df)
    if not spi.empty:
        sp = spi[spi["player"] == player]
        if not sp.empty:
            row = sp.iloc[0]
            sections.append(_section(
                "Serve Pressure Index",
                html.Div([
                    _stat_card("Serves", int(row["serves"])),
                    _stat_card("Aces", int(row["aces"])),
                    _stat_card("Srv Errors", int(row["srv_errors"])),
                    _stat_card("Pressure Serves", int(row["pressure_serves"])),
                    _stat_card("Pressure %", f"{row['pressure_pct']:.1f}%"),
                ], style={"display": "flex", "gap": "10px"}),
            ))

    # --- 8. In-System vs Out-of-System ---
    insys_df = in_system_efficiency(actions_df)
    if not insys_df.empty:
        ip = insys_df[insys_df["player"] == player]
        if not ip.empty and len(ip) == 2:
            # Pivot for comparison
            pivot = ip.copy()
            pivot["label"] = pivot["in_system"].map({True: "In System", False: "Out of System"})
            sections.append(_section(
                "In-System vs Out-of-System Efficiency",
                dcc.Graph(figure=bar_comparison(
                    pivot, "label", ["hitting_eff"], ["Hitting Eff"],
                    title=f"{player}: In-System vs Out-of-System",
                )),
                html.Div([
                    html.Span(
                        f"In System: {pivot[pivot['in_system']].iloc[0]['hitting_eff']:.3f} "
                        f"({int(pivot[pivot['in_system']].iloc[0]['attempts'])} att)  |  "
                        f"Out of System: {pivot[~pivot['in_system']].iloc[0]['hitting_eff']:.3f} "
                        f"({int(pivot[~pivot['in_system']].iloc[0]['attempts'])} att)",
                        style={"fontSize": "13px", "color": "#666"},
                    ),
                ], style={"marginTop": "5px"}),
            ))

    # --- 9. Attack Stats by Game Phase & Score Situation ---
    attack_phase_rows = []
    for phase in ["early", "middle", "final"]:
        ph = player_stats_filtered(actions_df, "game_phase", phase)
        if not ph.empty:
            pp = ph[ph["player"] == player]
            if not pp.empty:
                r = pp.iloc[0]
                attack_phase_rows.append({
                    "Phase": phase.title(),
                    "Kills": int(r["kills"]), "Errors": int(r["att_errors"]),
                    "Attempts": int(r["att_total"]),
                    "Kill%": round(r["kill_pct"], 1),
                    "Eff": r["hitting_eff"],
                })
    if attack_phase_rows:
        sections.append(_section(
            "Attack Stats by Game Phase",
            stat_table(pd.DataFrame(attack_phase_rows), "atk-phase-table", page_size=5),
        ))

    attack_sit_rows = []
    for sit in ["winning_big", "winning", "close", "losing", "losing_big"]:
        s = player_stats_filtered(actions_df, "score_situation", sit)
        if not s.empty:
            sp = s[s["player"] == player]
            if not sp.empty:
                r = sp.iloc[0]
                labels = {"winning_big": "Winning Big (+5+)", "winning": "Winning (+2-4)",
                          "close": "Close (-1 to +1)", "losing": "Losing (-2-4)",
                          "losing_big": "Losing Big (-5+)"}
                attack_sit_rows.append({
                    "Situation": labels[sit],
                    "Kills": int(r["kills"]), "Errors": int(r["att_errors"]),
                    "Attempts": int(r["att_total"]),
                    "Kill%": round(r["kill_pct"], 1),
                    "Eff": r["hitting_eff"],
                })
    if attack_sit_rows:
        sections.append(_section(
            "Attack Stats by Score Situation",
            stat_table(pd.DataFrame(attack_sit_rows), "atk-sit-table", page_size=5),
        ))

    # --- 10. Serve Stats by Game Phase & Score Situation ---
    serve_phase_rows = []
    for phase in ["early", "middle", "final"]:
        ph = player_stats_filtered(actions_df, "game_phase", phase)
        if not ph.empty:
            pp = ph[ph["player"] == player]
            if not pp.empty:
                r = pp.iloc[0]
                total = int(r["srv_total"])
                if total > 0:
                    serve_phase_rows.append({
                        "Phase": phase.title(),
                        "Aces": int(r["aces"]), "Errors": int(r["srv_errors"]),
                        "Total": total,
                        "Ace%": round(r["aces"] / total * 100, 1),
                        "Err%": round(r["srv_errors"] / total * 100, 1),
                    })
    if serve_phase_rows:
        sections.append(_section(
            "Serve Stats by Game Phase",
            stat_table(pd.DataFrame(serve_phase_rows), "srv-phase-table", page_size=5),
        ))

    serve_sit_rows = []
    for sit in ["winning_big", "winning", "close", "losing", "losing_big"]:
        s = player_stats_filtered(actions_df, "score_situation", sit)
        if not s.empty:
            sp = s[s["player"] == player]
            if not sp.empty:
                r = sp.iloc[0]
                total = int(r["srv_total"])
                if total > 0:
                    labels = {"winning_big": "Winning Big (+5+)", "winning": "Winning (+2-4)",
                              "close": "Close (-1 to +1)", "losing": "Losing (-2-4)",
                              "losing_big": "Losing Big (-5+)"}
                    serve_sit_rows.append({
                        "Situation": labels[sit],
                        "Aces": int(r["aces"]), "Errors": int(r["srv_errors"]),
                        "Total": total,
                        "Ace%": round(r["aces"] / total * 100, 1),
                        "Err%": round(r["srv_errors"] / total * 100, 1),
                    })
    if serve_sit_rows:
        sections.append(_section(
            "Serve Stats by Score Situation",
            stat_table(pd.DataFrame(serve_sit_rows), "srv-sit-table", page_size=5),
        ))

    if not sections:
        sections.append(html.P("No data available for this player.", style={"color": "#999"}))

    return sections


# ---------------------------------------------------------------------------
# Callback — registered at module import time so Dash finds the IDs.
# ---------------------------------------------------------------------------

@callback(
    Output("player-detail-content", "children"),
    Input("player-dropdown", "value"),
)
def update_player_detail(player):
    if not player or not _dfs:
        return html.P("Select a player to see details.")
    return _build_player_content(player, _dfs["actions"], _dfs["rallies"])
