"""Page: Court Zones — attack efficiency and serve receive quality by zone."""

from dash import html, dcc
import pandas as pd
from components.court import court_heatmap
from components.tables import stat_table


def layout(dfs):
    actions_df = dfs["actions"]

    # --- Attack Efficiency by Zone ---
    attacks = actions_df[
        (actions_df["is_our_team"])
        & (actions_df["action_type"] == "attack")
        & (actions_df["src_zone"].notna())
    ].copy()

    attack_zone_data = {}
    attack_detail_rows = []

    for zone, grp in attacks.groupby("src_zone"):
        zone_int = int(zone)
        qualified = grp[grp["quality"].isin(["kill", "error", "in_play", "block_kill"])]
        kills = (qualified["quality"] == "kill").sum()
        errors = (qualified["quality"].isin(["error", "block_kill"])).sum()
        attempts = len(qualified)
        eff = (kills - errors) / attempts if attempts > 0 else 0.0

        attack_zone_data[zone_int] = {
            "eff": eff,
            "kills": kills,
            "errors": errors,
            "attempts": attempts,
        }

        # Top attacker in this zone (by kills)
        kill_actions = qualified[qualified["quality"] == "kill"]
        if not kill_actions.empty:
            top_attacker = kill_actions.groupby("player").size().idxmax()
        elif not qualified.empty:
            top_attacker = qualified.groupby("player").size().idxmax()
        else:
            top_attacker = ""

        kill_pct = round(kills / attempts * 100, 1) if attempts > 0 else 0.0

        attack_detail_rows.append({
            "Zone": zone_int,
            "Attempts": attempts,
            "Kills": kills,
            "Errors": errors,
            "Kill%": kill_pct,
            "Eff": round(eff, 3),
            "Top Attacker": top_attacker,
        })

    attack_fig = court_heatmap(attack_zone_data, metric="eff", title="Attack Efficiency by Zone")
    attack_detail_df = pd.DataFrame(attack_detail_rows).sort_values("Zone") if attack_detail_rows else pd.DataFrame(
        columns=["Zone", "Attempts", "Kills", "Errors", "Kill%", "Eff", "Top Attacker"]
    )

    # --- Serve Receive Quality by Zone ---
    receives = actions_df[
        (actions_df["is_our_team"])
        & (actions_df["action_type"] == "receive")
        & (actions_df["src_zone"].notna())
    ].copy()

    quality_map = {"3": 3, "2": 2, "1": 1, "0": 0}

    receive_zone_data = {}
    receive_detail_rows = []

    for zone, grp in receives.groupby("src_zone"):
        zone_int = int(zone)
        mapped = grp["quality"].map(quality_map).dropna()
        avg_quality = mapped.mean() if len(mapped) > 0 else 0.0
        count = len(mapped)

        receive_zone_data[zone_int] = {
            "avg": round(avg_quality, 2),
            "count": count,
        }

        # Top receiver in this zone (by count)
        if not grp.empty:
            top_receiver = grp.groupby("player").size().idxmax()
        else:
            top_receiver = ""

        receive_detail_rows.append({
            "Zone": zone_int,
            "Passes": count,
            "Avg Quality": round(avg_quality, 2),
            "Top Receiver": top_receiver,
        })

    receive_fig = court_heatmap(receive_zone_data, metric="avg", title="Serve Receive Quality by Zone")
    receive_detail_df = pd.DataFrame(receive_detail_rows).sort_values("Zone") if receive_detail_rows else pd.DataFrame(
        columns=["Zone", "Passes", "Avg Quality", "Top Receiver"]
    )

    # --- Layout ---
    return html.Div([
        html.H2("Court Zones"),

        # Side-by-side court heatmaps
        html.Div([
            html.Div([dcc.Graph(figure=attack_fig)], style={"flex": "1"}),
            html.Div([dcc.Graph(figure=receive_fig)], style={"flex": "1"}),
        ], style={"display": "flex", "gap": "20px", "marginBottom": "20px"}),

        # Attack zone detail table
        html.H4("Attack Zone Detail"),
        stat_table(attack_detail_df, "attack-zone-table"),

        # Receive zone detail table
        html.H4("Receive Zone Detail", style={"marginTop": "20px"}),
        stat_table(receive_detail_df, "receive-zone-table"),
    ])
