"""Page: Scoring Runs analysis with trigger breakdowns and leaderboards."""

from dash import html, dcc
import pandas as pd
import plotly.graph_objects as go

from analytics.team import detect_runs, run_triggers
from components.tables import stat_table
from components.charts import bar_comparison


OUR_TEAM_NAME = "NorCal 13-2 Blue"


def _trigger_label(row):
    """Build a human-readable label combining team context + action + quality."""
    prefix = "Our" if row["is_our_team"] else "Opp"
    return f"{prefix} {row['action']} {row['quality']}"


def _kpi_div(label, value):
    return html.Div([
        html.H4(str(value), style={"margin": "0", "fontSize": "28px", "color": "#1a73e8"}),
        html.P(label, style={"margin": "0", "fontSize": "12px", "color": "#666"}),
    ], style={
        "textAlign": "center", "padding": "15px", "backgroundColor": "white",
        "borderRadius": "8px", "boxShadow": "0 1px 3px rgba(0,0,0,0.1)", "flex": "1",
    })


def _build_runs_table(runs):
    """Build a DataFrame of the top 20 longest runs for display."""
    records = []
    for run in runs:
        first = run[0]
        last = run[-1]
        records.append({
            "Length": len(run),
            "Score Start": f"{first['our_score']}-{first['opp_score']}",
            "Score End": f"{last['our_score']}-{last['opp_score']}",
            "Set": first["set_number"],
            "Phase": first["game_phase"],
            "Opponent": first["match_title"],
            "Date": first["match_date"],
        })
    df = pd.DataFrame(records)
    if df.empty:
        return df
    return df.sort_values("Length", ascending=False).head(20).reset_index(drop=True)


def _build_starter_leaderboard(triggers_df):
    """Group triggers by player to show who starts our runs most often."""
    if triggers_df.empty:
        return pd.DataFrame(columns=["Player", "Run Starts", "Most Common Action"])
    grouped = triggers_df.groupby("player").agg(
        run_starts=("player", "count"),
        most_common_action=("trigger_label", lambda x: x.mode().iloc[0] if len(x) > 0 else ""),
    ).reset_index()
    grouped.columns = ["Player", "Run Starts", "Most Common Action"]
    return grouped.sort_values("Run Starts", ascending=False).reset_index(drop=True)


def _build_killer_leaderboard(opp_triggers_df):
    """From opponent run triggers, find our players whose errors start opponent runs."""
    if opp_triggers_df.empty:
        return pd.DataFrame(columns=["Player", "Opp Runs Started", "Most Common Error"])
    # Filter to our team errors (our mistakes that start opponent runs)
    our_errors = opp_triggers_df[opp_triggers_df["is_our_team"] == True].copy()
    if our_errors.empty:
        return pd.DataFrame(columns=["Player", "Opp Runs Started", "Most Common Error"])
    grouped = our_errors.groupby("player").agg(
        opp_runs_started=("player", "count"),
        most_common_error=("trigger_label", lambda x: x.mode().iloc[0] if len(x) > 0 else ""),
    ).reset_index()
    grouped.columns = ["Player", "Opp Runs Started", "Most Common Error"]
    return grouped.sort_values("Opp Runs Started", ascending=False).reset_index(drop=True)


def _trigger_breakdown_chart(triggers_df, title):
    """Bar chart showing action type distribution that starts runs."""
    if triggers_df.empty:
        fig = go.Figure()
        fig.update_layout(title=title, height=400)
        return fig
    counts = triggers_df["trigger_label"].value_counts()
    total = counts.sum()
    df = pd.DataFrame({
        "Action": counts.index,
        "Count": counts.values,
        "Pct": (counts.values / total * 100).round(1),
    })
    fig = go.Figure(go.Bar(
        x=df["Pct"],
        y=df["Action"],
        orientation="h",
        text=df.apply(lambda r: f"{r['Pct']}% ({int(r['Count'])})", axis=1),
        textposition="auto",
        marker_color="#1a73e8",
    ))
    fig.update_layout(
        title=title,
        height=max(300, len(df) * 35 + 100),
        xaxis_title="Percentage",
        yaxis=dict(autorange="reversed"),
        margin=dict(l=200, r=20, t=50, b=40),
    )
    return fig


def layout(dfs):
    rallies_df = dfs["rallies"]
    actions_df = dfs["actions"]

    # Detect runs
    runs = detect_runs(rallies_df, min_length=3)
    our_runs = runs["our_runs"]
    opp_runs = runs["opp_runs"]

    # Get triggers
    our_triggers = run_triggers(our_runs, actions_df, OUR_TEAM_NAME)
    opp_triggers = run_triggers(opp_runs, actions_df, OUR_TEAM_NAME)

    # Add trigger labels
    if not our_triggers.empty:
        our_triggers["trigger_label"] = our_triggers.apply(_trigger_label, axis=1)
    if not opp_triggers.empty:
        opp_triggers["trigger_label"] = opp_triggers.apply(_trigger_label, axis=1)

    # Section 1: Summary cards
    our_count = len(our_runs)
    opp_count = len(opp_runs)
    avg_our_len = round(sum(len(r) for r in our_runs) / our_count, 1) if our_count > 0 else 0
    longest_our = max((len(r) for r in our_runs), default=0)

    summary_row = html.Div([
        _kpi_div("Our Runs", our_count),
        _kpi_div("Opp Runs", opp_count),
        _kpi_div("Avg Our Run Length", avg_our_len),
        _kpi_div("Longest Our Run", longest_our),
    ], style={"display": "flex", "gap": "10px", "marginBottom": "20px"})

    # Section 2: Top 20 longest OUR runs table
    runs_table_df = _build_runs_table(our_runs)

    # Section 3: Run Starter Leaderboard
    starter_lb = _build_starter_leaderboard(our_triggers)

    # Section 4: Run Killer Leaderboard
    killer_lb = _build_killer_leaderboard(opp_triggers)

    # Section 5: Trigger breakdown - what starts our runs
    our_trigger_chart = _trigger_breakdown_chart(our_triggers, "What Starts Our Runs")

    # Section 6: What starts opponent runs
    opp_trigger_chart = _trigger_breakdown_chart(opp_triggers, "What Starts Opponent Runs")

    return html.Div([
        html.H2("Scoring Runs"),

        # Summary cards
        summary_row,

        # Top 20 longest our runs
        html.H4("Top 20 Longest Our Runs"),
        stat_table(runs_table_df, "runs-top20-table") if not runs_table_df.empty else html.P("No runs found."),

        # Leaderboards side by side
        html.Div([
            html.Div([
                html.H4("Run Starter Leaderboard"),
                html.P("Players whose actions start our scoring runs",
                       style={"fontSize": "12px", "color": "#666", "marginTop": "-10px"}),
                stat_table(starter_lb, "run-starter-lb") if not starter_lb.empty else html.P("No data."),
            ], style={"flex": "1"}),
            html.Div([
                html.H4("Run Killer Leaderboard"),
                html.P("Our players whose errors start opponent scoring runs",
                       style={"fontSize": "12px", "color": "#666", "marginTop": "-10px"}),
                stat_table(killer_lb, "run-killer-lb") if not killer_lb.empty else html.P("No data."),
            ], style={"flex": "1"}),
        ], style={"display": "flex", "gap": "20px", "marginTop": "20px", "marginBottom": "20px"}),

        # Trigger breakdown charts side by side
        html.Div([
            html.Div([
                dcc.Graph(figure=our_trigger_chart),
            ], style={"flex": "1"}),
            html.Div([
                dcc.Graph(figure=opp_trigger_chart),
            ], style={"flex": "1"}),
        ], style={"display": "flex", "gap": "20px", "marginBottom": "20px"}),
    ])
