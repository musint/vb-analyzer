"""Sidebar filter components."""

from dash import dcc, html


def player_dropdown(players: list[str], id: str = "player-filter", multi: bool = False) -> html.Div:
    return html.Div([
        html.Label("Player", style={"fontWeight": "bold"}),
        dcc.Dropdown(
            id=id,
            options=[{"label": p, "value": p} for p in sorted(players)],
            multi=multi,
            placeholder="All players",
        ),
    ], style={"marginBottom": "15px"})


def game_dropdown(matches: list[dict], id: str = "game-filter") -> html.Div:
    options = [
        {"label": f"{m['title'][:30]} ({m['date'][:10]})", "value": m["video_id"]}
        for m in sorted(matches, key=lambda x: x.get("date", ""), reverse=True)
    ]
    return html.Div([
        html.Label("Game", style={"fontWeight": "bold"}),
        dcc.Dropdown(id=id, options=options, placeholder="All games"),
    ], style={"marginBottom": "15px"})


def phase_dropdown(id: str = "phase-filter") -> html.Div:
    return html.Div([
        html.Label("Game Phase", style={"fontWeight": "bold"}),
        dcc.Dropdown(
            id=id,
            options=[
                {"label": "Early (0-9)", "value": "early"},
                {"label": "Middle (10-19)", "value": "middle"},
                {"label": "Final (20+)", "value": "final"},
            ],
            placeholder="All phases",
        ),
    ], style={"marginBottom": "15px"})


def situation_dropdown(id: str = "situation-filter") -> html.Div:
    return html.Div([
        html.Label("Score Situation", style={"fontWeight": "bold"}),
        dcc.Dropdown(
            id=id,
            options=[
                {"label": "Winning Big (+5+)", "value": "winning_big"},
                {"label": "Winning (+2-4)", "value": "winning"},
                {"label": "Close (-1 to +1)", "value": "close"},
                {"label": "Losing (-2-4)", "value": "losing"},
                {"label": "Losing Big (-5+)", "value": "losing_big"},
            ],
            placeholder="All situations",
        ),
    ], style={"marginBottom": "15px"})
