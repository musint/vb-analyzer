"""Generate static site data from cached match data."""

import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from data.loader import load_from_cache
from analytics.core import build_all
from analytics.team import team_kpis, sideout_by_category

SITE_DATA_DIR = Path(__file__).parent / "site" / "data"


def _sanitize(obj):
    """Recursively replace NaN/Infinity with None for valid JSON."""
    if isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj)):
        return None
    if isinstance(obj, dict):
        return {k: _sanitize(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_sanitize(v) for v in obj]
    return obj


def generate_overview(dfs):
    """Build overview.json from rallies and actions DataFrames."""
    rallies_df = dfs["rallies"]
    actions_df = dfs["actions"]

    kpis = team_kpis(rallies_df, actions_df)

    # Team progression: per-game KPIs over time
    progression = []
    q_map = {"3": 3, "2": 2, "1": 1, "0": 0}
    for vid, group in rallies_df.groupby("video_id"):
        first = group.iloc[0]
        game_actions = actions_df[actions_df["video_id"] == vid]

        receive = group[group["is_receive"]]
        so_pct = round(receive["is_sideout"].mean() * 100, 1) if len(receive) > 0 else 0

        our_attacks = game_actions[
            (game_actions["is_our_team"])
            & (game_actions["action_type"] == "attack")
            & (game_actions["quality"].isin(["kill", "error", "in_play", "block_kill"]))
        ]
        kills = (our_attacks["quality"] == "kill").sum()
        errors = (our_attacks["quality"] == "error").sum()
        att_total = len(our_attacks)
        hitting_eff = round((kills - errors) / att_total, 3) if att_total > 0 else 0

        receives = game_actions[
            (game_actions["is_our_team"]) & (game_actions["action_type"] == "receive")
        ]
        rq = receives["quality"].map(q_map).dropna()
        pass_avg = round(rq.mean(), 3) if len(rq) > 0 else 0

        progression.append({
            "date": first["match_date"],
            "title": first["match_title"],
            "sideout_pct": so_pct,
            "hitting_eff": hitting_eff,
            "pass_avg": pass_avg,
        })
    progression.sort(key=lambda x: x["date"])

    # Attack stats by game state
    situations = ["winning_big", "winning", "close", "losing", "losing_big"]
    attack_by_state = []
    for sit in situations:
        sit_actions = actions_df[
            (actions_df["is_our_team"])
            & (actions_df["action_type"] == "attack")
            & (actions_df["quality"].isin(["kill", "error", "in_play", "block_kill"]))
            & (actions_df["score_situation"] == sit)
        ]
        k = (sit_actions["quality"] == "kill").sum()
        e = (sit_actions["quality"] == "error").sum()
        t = len(sit_actions)
        attack_by_state.append({
            "situation": sit,
            "hitting_eff": round((k - e) / t, 3) if t > 0 else 0,
            "kills": int(k),
            "errors": int(e),
            "attempts": int(t),
        })

    # Pass stats by game state
    pass_by_state = []
    for sit in situations:
        sit_receives = actions_df[
            (actions_df["is_our_team"])
            & (actions_df["action_type"] == "receive")
            & (actions_df["score_situation"] == sit)
        ]
        rq = sit_receives["quality"].map(q_map).dropna()
        pass_by_state.append({
            "situation": sit,
            "pass_avg": round(rq.mean(), 3) if len(rq) > 0 else 0,
            "total": int(len(rq)),
        })

    # Game results
    game_results = []
    for vid, group in rallies_df.groupby("video_id"):
        first = group.iloc[0]
        game_results.append({
            "date": first["match_date"],
            "opponent": first["match_title"],
            "sets_won": int(first["sets_won"]),
            "sets_lost": int(first["sets_lost"]),
            "result": "W" if first["sets_won"] > first["sets_lost"] else "L",
        })
    game_results.sort(key=lambda x: x["date"], reverse=True)

    # Sideout by game phase
    so_phase = sideout_by_category(rallies_df, "game_phase")
    sideout_by_phase = []
    if not so_phase.empty:
        for _, row in so_phase.iterrows():
            sideout_by_phase.append({
                "phase": row["game_phase"],
                "sideout_pct": float(row["sideout_pct"]),
                "opportunities": int(row["opportunities"]),
            })

    return {
        "kpis": kpis,
        "progression": progression,
        "attack_by_state": attack_by_state,
        "pass_by_state": pass_by_state,
        "game_results": game_results,
        "sideout_by_phase": sideout_by_phase,
    }


def generate_players(dfs):
    """Build players.json with per-player stats, clutch, consistency, progression, game-state splits."""
    actions_df = dfs["actions"]
    from analytics.player import (
        player_season_stats, clutch_comparison, consistency_index,
        season_progression, player_stats_filtered,
    )

    all_stats = player_season_stats(actions_df)
    if all_stats.empty:
        return {"players": [], "player_list": []}

    player_list = all_stats["player"].tolist()

    stats_by_player = {}
    for _, row in all_stats.iterrows():
        stats_by_player[row["player"]] = {
            "kills": int(row["kills"]),
            "att_errors": int(row["att_errors"]),
            "att_total": int(row["att_total"]),
            "hitting_eff": float(row["hitting_eff"]),
            "kill_pct": float(row["kill_pct"]),
            "aces": int(row["aces"]),
            "srv_errors": int(row["srv_errors"]),
            "srv_total": int(row["srv_total"]),
            "pass_avg": float(row["pass_avg"]) if row["pass_avg"] is not None else None,
            "pass_total": int(row["pass_total"]),
            "digs": int(row["digs"]),
            "blocks": int(row["blocks"]),
        }

    clutch_df = clutch_comparison(actions_df)
    clutch_by_player = {}
    if not clutch_df.empty:
        for _, row in clutch_df.iterrows():
            p = row["player"]
            clutch_by_player[p] = {}
            for col in ["hitting_eff", "kill_pct", "pass_avg", "aces", "srv_errors"]:
                c_val = row.get(f"{col}_clutch")
                nc_val = row.get(f"{col}_non_clutch")
                clutch_by_player[p][f"{col}_clutch"] = float(c_val) if c_val is not None and str(c_val) != "nan" else None
                clutch_by_player[p][f"{col}_non_clutch"] = float(nc_val) if nc_val is not None and str(nc_val) != "nan" else None
            cr = row.get("clutch_rating")
            clutch_by_player[p]["clutch_rating"] = float(cr) if cr is not None and str(cr) != "nan" else None

    import numpy as np

    cons_df = consistency_index(actions_df)
    consistency_by_player = {}

    # Hitting consistency from existing module
    if not cons_df.empty:
        for _, row in cons_df.iterrows():
            consistency_by_player[row["player"]] = {
                "hitting": {
                    "score": float(row["consistency_score"]),
                    "std_dev": float(row["eff_std_dev"]),
                    "avg": float(row["avg_eff"]),
                    "matches": int(row["matches_with_attacks"]),
                },
            }

    # Compute serving and passing consistency per player
    our_actions = actions_df[actions_df["is_our_team"]].copy()
    q_map = {"3": 3, "2": 2, "1": 1, "0": 0}
    match_order = our_actions.groupby("video_id")["match_date"].first().sort_values()

    for player, pdf in our_actions.groupby("player"):
        if not player:
            continue
        consistency_by_player.setdefault(player, {})

        # Serving consistency: per-match ace%
        srv_per_match = []
        for vid in match_order.index:
            mdf = pdf[(pdf["video_id"] == vid) & (pdf["action_type"] == "serve")]
            if len(mdf) >= 3:
                aces = (mdf["quality"] == "ace").sum()
                srv_per_match.append(aces / len(mdf))
        if len(srv_per_match) >= 3:
            std = float(np.std(srv_per_match))
            consistency_by_player[player]["serving"] = {
                "score": round(1 / (1 + std), 3),
                "std_dev": round(std, 4),
                "avg": round(float(np.mean(srv_per_match)), 3),
                "matches": len(srv_per_match),
            }

        # Passing consistency: per-match pass avg
        pass_per_match = []
        for vid in match_order.index:
            mdf = pdf[(pdf["video_id"] == vid) & (pdf["action_type"] == "receive")]
            rq = mdf["quality"].map(q_map).dropna()
            if len(rq) >= 3:
                pass_per_match.append(float(rq.mean()))
        if len(pass_per_match) >= 3:
            std = float(np.std(pass_per_match))
            consistency_by_player[player]["passing"] = {
                "score": round(1 / (1 + std), 3),
                "std_dev": round(std, 4),
                "avg": round(float(np.mean(pass_per_match)), 3),
                "matches": len(pass_per_match),
            }

    prog = season_progression(actions_df)
    progression_by_player = {}
    for player, pdf in prog.items():
        progression_by_player[player] = []
        for _, row in pdf.iterrows():
            progression_by_player[player].append({
                "date": str(row["date"]),
                "match_title": row["match_title"],
                "hitting_eff": float(row["hitting_eff"]) if row["hitting_eff"] is not None else None,
                "pass_avg": float(row["pass_avg"]) if row["pass_avg"] is not None else None,
                "hitting_eff_rolling": float(row["hitting_eff_rolling"]) if row["hitting_eff_rolling"] is not None else None,
                "pass_avg_rolling": float(row["pass_avg_rolling"]) if row["pass_avg_rolling"] is not None else None,
            })

    situations = ["winning_big", "winning", "close", "losing", "losing_big"]
    game_state_by_player = {}
    for player in player_list:
        game_state_by_player[player] = []
        for sit in situations:
            sit_stats = player_stats_filtered(actions_df, "score_situation", sit)
            if not sit_stats.empty:
                sp = sit_stats[sit_stats["player"] == player]
                if not sp.empty:
                    r = sp.iloc[0]
                    srv_total = int(r["srv_total"])
                    ace_pct = round(r["aces"] / srv_total * 100, 1) if srv_total > 0 else None
                    srv_err_pct = round(r["srv_errors"] / srv_total * 100, 1) if srv_total > 0 else None
                    game_state_by_player[player].append({
                        "situation": sit,
                        "hitting_eff": float(r["hitting_eff"]),
                        "kill_pct": float(r["kill_pct"]),
                        "pass_avg": float(r["pass_avg"]) if r["pass_avg"] is not None else None,
                        "att_total": int(r["att_total"]),
                        "ace_pct": ace_pct,
                        "srv_err_pct": srv_err_pct,
                        "srv_total": srv_total,
                    })

    return {
        "player_list": player_list,
        "stats": stats_by_player,
        "clutch": clutch_by_player,
        "consistency": consistency_by_player,
        "progression": progression_by_player,
        "game_state": game_state_by_player,
    }


def generate_comparison(dfs):
    """Build comparison.json with normalized radar data and trend data."""
    actions_df = dfs["actions"]
    from analytics.player import player_season_stats, consistency_index

    all_stats = player_season_stats(actions_df)
    cons_df = consistency_index(actions_df)

    if all_stats.empty:
        return {"players": [], "radar_metrics": [], "radar_labels": []}

    player_list = all_stats["player"].tolist()

    metrics_map = {}
    for _, row in all_stats.iterrows():
        metrics_map[row["player"]] = {
            "kills": int(row["kills"]),
            "hitting_eff": float(row["hitting_eff"]),
            "aces": int(row["aces"]),
            "digs": int(row["digs"]),
            "pass_avg": float(row["pass_avg"]) if row["pass_avg"] is not None else None,
        }

    if not cons_df.empty:
        for _, row in cons_df.iterrows():
            p = row["player"]
            if p in metrics_map:
                metrics_map[p]["consistency"] = float(row["consistency_score"])

    radar_metrics = ["kills", "hitting_eff", "aces", "digs", "pass_avg", "consistency"]
    radar_labels = ["Kills", "Hitting Eff", "Aces", "Digs", "Pass Avg", "Consistency"]

    normalized = {}
    for metric in radar_metrics:
        values = [metrics_map[p].get(metric) for p in player_list]
        numeric = [v for v in values if v is not None]
        if not numeric:
            for p in player_list:
                normalized.setdefault(p, {})[metric] = None
            continue
        vmin = min(numeric)
        vmax = max(numeric)
        for i, p in enumerate(player_list):
            v = values[i]
            if v is None:
                normalized.setdefault(p, {})[metric] = None
            elif vmax == vmin:
                normalized.setdefault(p, {})[metric] = 0.5
            else:
                normalized.setdefault(p, {})[metric] = round((v - vmin) / (vmax - vmin), 3)

    colors = ["#38bdf8", "#a78bfa", "#4ade80", "#fbbf24", "#f472b6", "#fb923c", "#f87171", "#34d399"]

    players_data = []
    for i, p in enumerate(player_list):
        players_data.append({
            "name": p,
            "color": colors[i % len(colors)],
            "raw": metrics_map.get(p, {}),
            "normalized": normalized.get(p, {}),
        })

    return {
        "players": players_data,
        "radar_metrics": radar_metrics,
        "radar_labels": radar_labels,
    }


def main():
    matches = load_from_cache()
    if not matches:
        print("No cached data found. Run seed_cache.py first.", file=sys.stderr)
        sys.exit(1)

    print(f"Loaded {len(matches)} matches from cache.", file=sys.stderr)
    dfs = build_all(matches)

    SITE_DATA_DIR.mkdir(parents=True, exist_ok=True)

    overview = _sanitize(generate_overview(dfs))
    with open(SITE_DATA_DIR / "overview.json", "w") as f:
        json.dump(overview, f, indent=2, default=str)
    print("Generated overview.json", file=sys.stderr)

    players = _sanitize(generate_players(dfs))
    with open(SITE_DATA_DIR / "players.json", "w") as f:
        json.dump(players, f, indent=2, default=str)
    print("Generated players.json", file=sys.stderr)

    comparison = _sanitize(generate_comparison(dfs))
    with open(SITE_DATA_DIR / "comparison.json", "w") as f:
        json.dump(comparison, f, indent=2, default=str)
    print("Generated comparison.json", file=sys.stderr)

    print("Done! Open site/index.html to view.", file=sys.stderr)


if __name__ == "__main__":
    main()
