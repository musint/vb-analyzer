"""Volleyball Stat Analyzer — Dash App."""

import dash
from dash import html, dcc, callback, Input, Output, State
import sys

from data.loader import load_data, refresh_from_balltime
from analytics.core import build_all

# Load data on startup
print("Loading data...", file=sys.stderr)
matches = load_data()
dfs = build_all(matches) if matches else {"matches": [], "rallies": None, "actions": None}
print(f"Loaded {len(matches)} matches", file=sys.stderr)

# Import ALL page modules at startup so their callbacks register with Dash
import pages.overview
import pages.player_detail
import pages.runs
import pages.game_detail
import pages.zones
import pages.comparison

app = dash.Dash(
    __name__,
    suppress_callback_exceptions=True,
    title="VB Analyzer",
)

# Navigation
NAV_ITEMS = [
    ("Overview", "/"),
    ("Players", "/players"),
    ("Runs", "/runs"),
    ("Game Detail", "/game"),
    ("Zones", "/zones"),
    ("Compare", "/compare"),
]

sidebar = html.Div([
    html.H3("VB Analyzer", style={"color": "white", "marginBottom": "20px"}),
    html.Hr(style={"borderColor": "#444"}),
    *[html.Div(
        dcc.Link(label, href=href, style={"color": "#ccc", "textDecoration": "none", "fontSize": "15px"}),
        style={"padding": "8px 0"},
    ) for label, href in NAV_ITEMS],
    html.Hr(style={"borderColor": "#444"}),
    html.Button("Refresh from Hudl", id="refresh-btn",
                style={"width": "100%", "padding": "10px", "marginTop": "10px",
                       "backgroundColor": "#e74c3c", "color": "white", "border": "none",
                       "borderRadius": "5px", "cursor": "pointer"}),
    html.Div(id="refresh-status", style={"color": "#aaa", "fontSize": "12px", "marginTop": "5px"}),
], style={
    "width": "200px", "position": "fixed", "top": "0", "left": "0", "bottom": "0",
    "backgroundColor": "#2c3e50", "padding": "20px",
})

app.layout = html.Div([
    dcc.Location(id="url", refresh=False),
    sidebar,
    html.Div(id="page-content", style={
        "marginLeft": "240px", "padding": "20px",
        "backgroundColor": "#f5f6fa", "minHeight": "100vh",
    }),
])


@callback(Output("page-content", "children"), Input("url", "pathname"))
def display_page(pathname):
    from pages.overview import layout as overview_layout

    if pathname == "/" or pathname is None:
        return overview_layout(dfs)
    elif pathname == "/players":
        try:
            from pages.player_detail import layout as player_layout
            return player_layout(dfs)
        except ImportError:
            return html.H3("Player Dashboard — Coming Soon")
    elif pathname == "/runs":
        try:
            from pages.runs import layout as runs_layout
            return runs_layout(dfs)
        except ImportError:
            return html.H3("Scoring Runs — Coming Soon")
    elif pathname == "/game":
        try:
            from pages.game_detail import layout as game_layout
            return game_layout(dfs)
        except ImportError:
            return html.H3("Game Detail — Coming Soon")
    elif pathname == "/zones":
        try:
            from pages.zones import layout as zones_layout
            return zones_layout(dfs)
        except ImportError:
            return html.H3("Court Zones — Coming Soon")
    elif pathname == "/compare":
        try:
            from pages.comparison import layout as comparison_layout
            return comparison_layout(dfs)
        except ImportError:
            return html.H3("Player Comparison — Coming Soon")
    return html.H3("Page not found")


@callback(
    Output("refresh-status", "children"),
    Input("refresh-btn", "n_clicks"),
    prevent_initial_call=True,
)
def refresh_data(n_clicks):
    global matches, dfs
    try:
        matches = refresh_from_balltime()
        dfs = build_all(matches)
        return f"Refreshed: {len(matches)} matches loaded"
    except Exception as e:
        return f"Error: {str(e)[:80]}"


if __name__ == "__main__":
    app.run(debug=True, port=8050)
