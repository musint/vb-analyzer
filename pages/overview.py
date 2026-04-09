"""Page 1: Season Overview dashboard."""

from dash import html, dcc, callback, Input, Output
import plotly.graph_objects as go
from analytics.team import team_kpis, sideout_by_category
from analytics.player import player_season_stats, season_progression
from analytics.advanced import expected_sideout_by_pass
from components.charts import line_trend
from components.tables import stat_table


def layout(dfs):
    kpis = team_kpis(dfs["rallies"], dfs["actions"])
    stats = player_season_stats(dfs["actions"])
    so_by_phase = sideout_by_category(dfs["rallies"], "game_phase")
    so_by_sit = sideout_by_category(dfs["rallies"], "score_situation")
    exp_so = expected_sideout_by_pass(dfs["rallies"], dfs["actions"])

    # Per-game results
    game_results = []
    for vid, group in dfs["rallies"].groupby("video_id"):
        first = group.iloc[0]
        game_results.append({
            "Date": first["match_date"],
            "Opponent": first["match_title"].replace("@ ", "").replace(" - Game", "").replace("vs. ", ""),
            "Result": f"{'W' if first['sets_won'] > first['sets_lost'] else 'L'} {first['sets_won']}-{first['sets_lost']}",
            "SO%": round(group[group["is_receive"]]["is_sideout"].mean() * 100, 1) if group["is_receive"].any() else 0,
            "Pt Win%": round((group["point_winner"] == "us").mean() * 100, 1),
        })

    import pandas as pd
    game_df = pd.DataFrame(game_results).sort_values("Date", ascending=False)

    # KPI cards as simple styled divs
    def kpi_div(label, value):
        return html.Div([
            html.H4(str(value), style={"margin": "0", "fontSize": "28px", "color": "#1a73e8"}),
            html.P(label, style={"margin": "0", "fontSize": "12px", "color": "#666"}),
        ], style={"textAlign": "center", "padding": "15px", "backgroundColor": "white",
                  "borderRadius": "8px", "boxShadow": "0 1px 3px rgba(0,0,0,0.1)", "flex": "1"})

    return html.Div([
        html.H2("Season Overview"),

        # KPI row
        html.Div([
            kpi_div("Record", kpis["record"]),
            kpi_div("Sideout %", f"{kpis['sideout_pct']}%"),
            kpi_div("Break Pt %", f"{kpis['breakpoint_pct']}%"),
            kpi_div("Hitting Eff", f"{kpis['hitting_eff']:.3f}"),
            kpi_div("Pass Avg", f"{kpis['pass_avg']:.3f}"),
            kpi_div("Rallies", f"{kpis['total_rallies']}"),
        ], style={"display": "flex", "gap": "10px", "marginBottom": "20px"}),

        # Sideout by phase and situation + Expected SO by pass quality
        html.Div([
            html.Div([
                html.H4("Sideout % by Game Phase"),
                stat_table(so_by_phase, "so-phase-table", page_size=5),
            ], style={"flex": "1"}),
            html.Div([
                html.H4("Sideout % by Score Situation"),
                stat_table(so_by_sit, "so-sit-table", page_size=5),
            ], style={"flex": "1"}),
            html.Div([
                html.H4("Expected Sideout by Pass Quality"),
                stat_table(exp_so, "exp-so-table", page_size=5),
            ], style={"flex": "1"}),
        ], style={"display": "flex", "gap": "20px", "marginBottom": "20px"}),

        # Game results table
        html.H4("Game Results"),
        stat_table(game_df, "game-results-table"),

        # Player season stats
        html.H4("Player Season Stats", style={"marginTop": "20px"}),
        stat_table(stats, "player-stats-table"),
    ])
