"""Generate static site data from cached match data."""

import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from data.loader import load_from_cache
from analytics.core import build_all
from analytics.team import team_kpis, sideout_by_category, detect_runs, run_triggers
from analytics.advanced import expected_sideout_by_pass, momentum_data, win_probability_table
from analytics.player import (
    player_season_stats, clutch_comparison, consistency_index,
    season_progression, player_stats_filtered, in_system_efficiency,
)

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

    # Expected sideout by pass quality
    exp_so_df = expected_sideout_by_pass(rallies_df, actions_df)
    expected_sideout = []
    if not exp_so_df.empty:
        for _, row in exp_so_df.iterrows():
            expected_sideout.append({
                "pass_quality": int(row["pass_quality"]),
                "rallies": int(row["rallies"]),
                "sideouts": int(row["sideouts"]),
                "sideout_pct": float(row["sideout_pct"]),
            })

    return {
        "kpis": kpis,
        "progression": progression,
        "attack_by_state": attack_by_state,
        "pass_by_state": pass_by_state,
        "game_results": game_results,
        "sideout_by_phase": sideout_by_phase,
        "expected_sideout": expected_sideout,
    }


def generate_players(dfs):
    """Build players.json with per-player stats, clutch, consistency, progression, game-state splits."""
    actions_df = dfs["actions"]

    all_stats = player_season_stats(actions_df)
    if all_stats.empty:
        return {"players": [], "player_list": []}

    player_list = all_stats["player"].tolist()

    stats_by_player = {}
    for _, row in all_stats.iterrows():
        srv_total = int(row["srv_total"])
        serving_eff = round((int(row["aces"]) - int(row["srv_errors"])) / srv_total, 3) if srv_total > 0 else 0.0
        stats_by_player[row["player"]] = {
            "kills": int(row["kills"]),
            "att_errors": int(row["att_errors"]),
            "att_total": int(row["att_total"]),
            "hitting_eff": float(row["hitting_eff"]),
            "kill_pct": float(row["kill_pct"]),
            "aces": int(row["aces"]),
            "srv_errors": int(row["srv_errors"]),
            "srv_total": srv_total,
            "serving_eff": serving_eff,
            "pass_avg": float(row["pass_avg"]) if row["pass_avg"] is not None else None,
            "pass_total": int(row["pass_total"]),
            "digs": int(row["digs"]),
            "blocks": int(row["blocks"]),
        }

    clutch_df = clutch_comparison(actions_df)
    # Get srv_total per player for clutch and non-clutch
    clutch_stats = player_stats_filtered(actions_df, "is_clutch", True)
    non_clutch_stats = player_stats_filtered(actions_df, "is_clutch", False)
    clutch_srv_total = clutch_stats.set_index("player")["srv_total"] if not clutch_stats.empty else {}
    non_clutch_srv_total = non_clutch_stats.set_index("player")["srv_total"] if not non_clutch_stats.empty else {}

    clutch_by_player = {}
    if not clutch_df.empty:
        for _, row in clutch_df.iterrows():
            p = row["player"]
            clutch_by_player[p] = {}
            for col in ["hitting_eff", "kill_pct", "pass_avg"]:
                c_val = row.get(f"{col}_clutch")
                nc_val = row.get(f"{col}_non_clutch")
                clutch_by_player[p][f"{col}_clutch"] = float(c_val) if c_val is not None and str(c_val) != "nan" else None
                clutch_by_player[p][f"{col}_non_clutch"] = float(nc_val) if nc_val is not None and str(nc_val) != "nan" else None

            # Compute ace% and srv_error% for clutch vs non-clutch
            aces_c = row.get("aces_clutch")
            aces_nc = row.get("aces_non_clutch")
            srv_err_c = row.get("srv_errors_clutch")
            srv_err_nc = row.get("srv_errors_non_clutch")
            srv_tot_c = clutch_srv_total.get(p) if hasattr(clutch_srv_total, "get") else (clutch_srv_total[p] if p in clutch_srv_total else None)
            srv_tot_nc = non_clutch_srv_total.get(p) if hasattr(non_clutch_srv_total, "get") else (non_clutch_srv_total[p] if p in non_clutch_srv_total else None)

            def _safe(num, denom):
                try:
                    if num is None or denom is None or str(num) == "nan" or str(denom) == "nan" or float(denom) == 0:
                        return None
                    return round(float(num) / float(denom) * 100, 2)
                except Exception:
                    return None

            clutch_by_player[p]["ace_pct_clutch"] = _safe(aces_c, srv_tot_c)
            clutch_by_player[p]["ace_pct_non_clutch"] = _safe(aces_nc, srv_tot_nc)
            clutch_by_player[p]["srv_err_pct_clutch"] = _safe(srv_err_c, srv_tot_c)
            clutch_by_player[p]["srv_err_pct_non_clutch"] = _safe(srv_err_nc, srv_tot_nc)

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

        # Serving consistency: per-match serving eff = (aces - errors) / total
        srv_per_match = []
        for vid in match_order.index:
            mdf = pdf[(pdf["video_id"] == vid) & (pdf["action_type"] == "serve")]
            if len(mdf) >= 3:
                aces = (mdf["quality"] == "ace").sum()
                errs = (mdf["quality"] == "error").sum()
                srv_per_match.append((aces - errs) / len(mdf))
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

    # Add rankings to consistency scores per skill
    for skill in ["hitting", "serving", "passing"]:
        scored = [
            (p, data[skill]["score"])
            for p, data in consistency_by_player.items()
            if skill in data
        ]
        scored.sort(key=lambda x: x[1], reverse=True)
        total_ranked = len(scored)
        for rank, (p, _) in enumerate(scored, start=1):
            consistency_by_player[p][skill]["rank"] = rank
            consistency_by_player[p][skill]["total_ranked"] = total_ranked

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
                    serving_eff = round((int(r["aces"]) - int(r["srv_errors"])) / srv_total, 3) if srv_total > 0 else None
                    game_state_by_player[player].append({
                        "situation": sit,
                        "hitting_eff": float(r["hitting_eff"]),
                        "kill_pct": float(r["kill_pct"]),
                        "pass_avg": float(r["pass_avg"]) if r["pass_avg"] is not None else None,
                        "att_total": int(r["att_total"]),
                        "ace_pct": ace_pct,
                        "srv_err_pct": srv_err_pct,
                        "serving_eff": serving_eff,
                        "srv_total": srv_total,
                    })

    # In-system efficiency per player
    is_df = in_system_efficiency(actions_df)
    in_system = {}
    if not is_df.empty:
        for _, row in is_df.iterrows():
            p = row["player"]
            in_system.setdefault(p, {})
            key = "in_system" if row["in_system"] else "out_of_system"
            in_system[p][key] = {
                "kills": int(row["kills"]),
                "errors": int(row["errors"]),
                "attempts": int(row["attempts"]),
                "hitting_eff": float(row["hitting_eff"]),
            }

    return {
        "player_list": player_list,
        "stats": stats_by_player,
        "clutch": clutch_by_player,
        "consistency": consistency_by_player,
        "progression": progression_by_player,
        "game_state": game_state_by_player,
        "in_system": in_system,
    }


def generate_comparison(dfs):
    """Build comparison.json with normalized radar data and trend data."""
    actions_df = dfs["actions"]

    all_stats = player_season_stats(actions_df)
    cons_df = consistency_index(actions_df)
    clutch_df = clutch_comparison(actions_df)

    if all_stats.empty:
        return {"players": [], "radar_metrics": [], "radar_labels": []}

    player_list = all_stats["player"].tolist()

    metrics_map = {}
    for _, row in all_stats.iterrows():
        p = row["player"]
        srv_total = int(row["srv_total"])
        serving_eff = round((int(row["aces"]) - int(row["srv_errors"])) / srv_total, 3) if srv_total > 0 else 0.0
        metrics_map[p] = {
            "hitting_eff": float(row["hitting_eff"]),
            "serving_eff": serving_eff,
            "pass_avg": float(row["pass_avg"]) if row["pass_avg"] is not None else None,
            "digs": int(row["digs"]),
        }

    # Consistency for radar = average of hitting and serving consistency scores
    if not cons_df.empty:
        # cons_df only has hitting consistency; we need serving too
        # Recompute from the players.json consistency data pattern
        import numpy as np
        our_actions = actions_df[actions_df["is_our_team"]].copy()
        match_order = our_actions.groupby("video_id")["match_date"].first().sort_values()

        for _, row in cons_df.iterrows():
            p = row["player"]
            if p not in metrics_map:
                continue
            hitting_score = float(row["consistency_score"])

            # Compute serving consistency for this player
            pdf = our_actions[our_actions["player"] == p]
            srv_per_match = []
            for vid in match_order.index:
                mdf = pdf[(pdf["video_id"] == vid) & (pdf["action_type"] == "serve")]
                if len(mdf) >= 3:
                    aces = (mdf["quality"] == "ace").sum()
                    errs = (mdf["quality"] == "error").sum()
                    srv_per_match.append((aces - errs) / len(mdf))

            if len(srv_per_match) >= 3:
                srv_std = float(np.std(srv_per_match))
                serving_score = round(1 / (1 + srv_std), 3)
                # Blend: average of hitting and serving
                metrics_map[p]["consistency"] = round((hitting_score + serving_score) / 2, 3)
            else:
                # Only hitting data available
                metrics_map[p]["consistency"] = hitting_score

    if not clutch_df.empty:
        for _, row in clutch_df.iterrows():
            p = row["player"]
            if p in metrics_map:
                cr = row.get("clutch_rating")
                metrics_map[p]["clutch_rating"] = float(cr) if cr is not None and str(cr) != "nan" else None

    radar_metrics = ["hitting_eff", "serving_eff", "pass_avg", "digs", "consistency", "clutch_rating"]
    radar_labels = ["Hitting Eff", "Serving Eff", "Pass Avg", "Digs", "Consistency", "Clutch Rating"]

    # Normalize: min-max scale with floor at 0.2 (worst player = 0.2, best = 1.0)
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
                normalized.setdefault(p, {})[metric] = 0.6
            else:
                # Scale to 0.2-1.0 range (floor at 0.2)
                raw_norm = (v - vmin) / (vmax - vmin)
                normalized.setdefault(p, {})[metric] = round(0.2 + raw_norm * 0.8, 3)

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


def generate_runs(dfs):
    """Build runs.json with scoring run analysis."""
    rallies_df = dfs["rallies"]
    actions_df = dfs["actions"]
    matches = dfs["matches"]

    # Get our team name from first match
    our_team_name = matches[0].get("our_team_name", "") if matches else ""

    # Detect runs
    runs_data = detect_runs(rallies_df)
    our_runs = runs_data["our_runs"]
    opp_runs = runs_data["opp_runs"]

    # Summary stats
    our_lengths = [len(r) for r in our_runs]
    opp_lengths = [len(r) for r in opp_runs]
    summary = {
        "our_runs": len(our_runs),
        "opp_runs": len(opp_runs),
        "avg_our_length": round(sum(our_lengths) / len(our_lengths), 2) if our_lengths else 0,
        "avg_opp_length": round(sum(opp_lengths) / len(opp_lengths), 2) if opp_lengths else 0,
        "longest_our": max(our_lengths) if our_lengths else 0,
        "longest_opp": max(opp_lengths) if opp_lengths else 0,
    }

    # Rallies played per player (unique rally IDs from actions)
    our_actions = actions_df[actions_df["is_our_team"]]
    rallies_per_player = (
        our_actions.groupby("player")["rally_id"].nunique().to_dict()
    )

    # Run starters: who triggers our runs
    starters = []
    if our_runs:
        triggers_df = run_triggers(our_runs, actions_df, our_team_name)
        if not triggers_df.empty:
            our_starters = triggers_df[triggers_df["is_our_team"]]
            if not our_starters.empty:
                grp = our_starters.groupby("player")
                for player, g in grp:
                    if not player:
                        continue
                    runs_started = len(g)
                    rp = rallies_per_player.get(player, 0)
                    rate = round(runs_started / rp * 100, 1) if rp > 0 else None
                    breakdown = {}
                    for (act, qual), subg in g.groupby(["action", "quality"]):
                        breakdown[f"{act}_{qual}"] = len(subg)
                    starters.append({
                        "player": player,
                        "runs_started": runs_started,
                        "rallies_played": rp,
                        "start_rate_pct": rate,
                        "breakdown": breakdown,
                    })
                starters.sort(key=lambda x: x["runs_started"], reverse=True)

    # Run killers: who triggers opponent runs (our team errors)
    killers = []
    if opp_runs:
        opp_triggers_df = run_triggers(opp_runs, actions_df, our_team_name)
        if not opp_triggers_df.empty:
            our_errors = opp_triggers_df[
                opp_triggers_df["is_our_team"] &
                opp_triggers_df["quality"].isin(["error"])
            ]
            if not our_errors.empty:
                grp = our_errors.groupby("player")
                for player, g in grp:
                    if not player:
                        continue
                    runs_triggered = len(g)
                    rp = rallies_per_player.get(player, 0)
                    rate = round(runs_triggered / rp * 100, 1) if rp > 0 else None
                    breakdown = {}
                    for (act, qual), subg in g.groupby(["action", "quality"]):
                        breakdown[f"{act}_{qual}"] = len(subg)
                    killers.append({
                        "player": player,
                        "runs_triggered": runs_triggered,
                        "rallies_played": rp,
                        "trigger_rate_pct": rate,
                        "breakdown": breakdown,
                    })
                killers.sort(key=lambda x: x["runs_triggered"], reverse=True)

    # Runs by game phase
    phases = ["early", "middle", "final"]
    runs_by_phase = []
    for phase in phases:
        our_count = sum(1 for r in our_runs if r and r[0].get("game_phase") == phase)
        opp_count = sum(1 for r in opp_runs if r and r[0].get("game_phase") == phase)
        runs_by_phase.append({
            "phase": phase,
            "our_runs": our_count,
            "opp_runs": opp_count,
        })

    # Runs by score situation
    sit_values = ["winning_big", "winning", "close", "losing", "losing_big"]
    runs_by_situation = []
    for sit in sit_values:
        our_count = sum(1 for r in our_runs if r and r[0].get("score_situation") == sit)
        opp_count = sum(1 for r in opp_runs if r and r[0].get("score_situation") == sit)
        runs_by_situation.append({
            "situation": sit,
            "our_runs": our_count,
            "opp_runs": opp_count,
        })

    return {
        "summary": summary,
        "starters": starters,
        "killers": killers,
        "runs_by_phase": runs_by_phase,
        "runs_by_situation": runs_by_situation,
    }


def generate_games(dfs):
    """Build games.json with per-game KPIs, momentum, and win probability."""
    rallies_df = dfs["rallies"]
    actions_df = dfs["actions"]
    matches = dfs["matches"]

    q_map = {"3": 3, "2": 2, "1": 1, "0": 0}

    # Build global win probability lookup
    wp_df = win_probability_table(rallies_df)
    wp_lookup = {}
    if not wp_df.empty:
        for _, row in wp_df.iterrows():
            wp_lookup[(int(row["our_score"]), int(row["opp_score"]))] = float(row["win_pct"])

    game_list = []
    games = {}

    for vid, vgroup in rallies_df.groupby("video_id"):
        first = vgroup.iloc[0]
        game_actions = actions_df[actions_df["video_id"] == vid]

        # Result and sets
        sets_won = int(first["sets_won"])
        sets_lost = int(first["sets_lost"])
        result = "W" if sets_won > sets_lost else "L"

        # Sideout %
        receive = vgroup[vgroup["is_receive"]]
        so_pct = round(receive["is_sideout"].mean() * 100, 1) if len(receive) > 0 else 0

        # Hitting efficiency
        our_attacks = game_actions[
            (game_actions["is_our_team"])
            & (game_actions["action_type"] == "attack")
            & (game_actions["quality"].isin(["kill", "error", "in_play", "block_kill"]))
        ]
        kills = (our_attacks["quality"] == "kill").sum()
        errors = (our_attacks["quality"] == "error").sum()
        att_total = len(our_attacks)
        hitting_eff = round((kills - errors) / att_total, 3) if att_total > 0 else 0

        # Pass average
        receives = game_actions[
            (game_actions["is_our_team"]) & (game_actions["action_type"] == "receive")
        ]
        rq = receives["quality"].map(q_map).dropna()
        pass_avg = round(rq.mean(), 3) if len(rq) > 0 else 0

        game_list.append({
            "video_id": vid,
            "date": first["match_date"],
            "title": first["match_title"],
            "result": result,
            "sets_won": sets_won,
            "sets_lost": sets_lost,
            "sideout_pct": so_pct,
            "hitting_eff": hitting_eff,
            "pass_avg": pass_avg,
        })

        # Momentum data: per-rally data for this match
        mom_df = momentum_data(rallies_df, vid)
        momentum = []
        if not mom_df.empty:
            for _, row in mom_df.iterrows():
                os_ = int(row["our_score_before"]) if "our_score_before" in row else None
                opp_s = int(row["opp_score_before"]) if "opp_score_before" in row else None
                # Use our_score / opp_score from momentum_data output
                os_cur = int(row["our_score"])
                opp_cur = int(row["opp_score"])
                win_prob = wp_lookup.get((os_cur, opp_cur))
                momentum.append({
                    "set_number": int(row["set_number"]),
                    "rally_num": int(row["rally_num"]),
                    "our_score": os_cur,
                    "opp_score": opp_cur,
                    "score_diff": int(row["score_diff"]),
                    "point_winner": row["point_winner"],
                    "game_phase": row["game_phase"],
                    "score_situation": row["score_situation"],
                    "win_prob": win_prob,
                })

        # Per-set box scores
        set_scores = []
        for sn, sgroup in vgroup.groupby("set_number"):
            set_actions = game_actions[game_actions["set_number"] == sn]
            last_rally = sgroup.sort_values("rally_id").iloc[-1]
            our_s = int(last_rally["our_score"])
            opp_s = int(last_rally["opp_score"])

            s_attacks = set_actions[
                (set_actions["is_our_team"])
                & (set_actions["action_type"] == "attack")
                & (set_actions["quality"].isin(["kill", "error", "in_play", "block_kill"]))
            ]
            sk = (s_attacks["quality"] == "kill").sum()
            se = (s_attacks["quality"] == "error").sum()
            st = len(s_attacks)
            s_eff = round((sk - se) / st, 3) if st > 0 else 0

            s_recv = sgroup[sgroup["is_receive"]]
            s_so_pct = round(s_recv["is_sideout"].mean() * 100, 1) if len(s_recv) > 0 else 0

            set_scores.append({
                "set_number": int(sn),
                "our_score": our_s,
                "opp_score": opp_s,
                "won": our_s > opp_s,
                "hitting_eff": s_eff,
                "sideout_pct": s_so_pct,
            })

        # Per-set per-player box scores
        box_scores = {}
        our_game_actions = game_actions[game_actions["is_our_team"]]
        for sn, set_actions in our_game_actions.groupby("set_number"):
            set_rows = []
            for player, pacts in set_actions.groupby("player"):
                if not player:
                    continue
                attacks = pacts[(pacts["action_type"] == "attack") & (pacts["quality"].isin(["kill", "error", "in_play", "block_kill"]))]
                k = int((attacks["quality"] == "kill").sum())
                e = int((attacks["quality"] == "error").sum())
                t = len(attacks)
                eff = round((k - e) / t, 3) if t > 0 else 0
                serves = pacts[pacts["action_type"] == "serve"]
                aces = int((serves["quality"] == "ace").sum())
                digs = int(len(pacts[(pacts["action_type"] == "dig") & (pacts["quality"] != "error")]))
                set_rows.append({
                    "player": player, "kills": k, "errors": e, "attempts": t,
                    "hitting_eff": eff, "aces": aces, "digs": digs,
                })
            set_rows.sort(key=lambda x: x["kills"], reverse=True)
            box_scores[str(int(sn))] = set_rows

        games[vid] = {
            "video_id": vid,
            "date": first["match_date"],
            "title": first["match_title"],
            "result": result,
            "sets_won": sets_won,
            "sets_lost": sets_lost,
            "sideout_pct": so_pct,
            "hitting_eff": hitting_eff,
            "pass_avg": pass_avg,
            "momentum": momentum,
            "set_scores": set_scores,
            "box_scores": box_scores,
        }

    # Sort game list by date
    game_list.sort(key=lambda x: x["date"])

    return {
        "game_list": game_list,
        "games": games,
    }


def generate_zones(dfs):
    """Build zones.json with attack and receive heatmaps by zone."""
    actions_df = dfs["actions"]

    # Attack zones: our team attacks with known src_zone
    attack_actions = actions_df[
        (actions_df["is_our_team"])
        & (actions_df["action_type"] == "attack")
        & (actions_df["quality"].isin(["kill", "error", "in_play", "block_kill"]))
        & (actions_df["src_zone"].notna())
        & (actions_df["src_zone"] != "")
        & (actions_df["src_zone"] != "None")
    ].copy()

    # Receive zones: our team receives with known src_zone
    q_map = {"3": 3, "2": 2, "1": 1, "0": 0}
    receive_actions = actions_df[
        (actions_df["is_our_team"])
        & (actions_df["action_type"] == "receive")
        & (actions_df["src_zone"].notna())
        & (actions_df["src_zone"] != "")
        & (actions_df["src_zone"] != "None")
    ].copy()

    # Team-level attack zones
    attack_zones = []
    for zone, zg in attack_actions.groupby("src_zone"):
        k = (zg["quality"] == "kill").sum()
        e = (zg["quality"] == "error").sum()
        t = len(zg)
        eff = round((k - e) / t, 3) if t > 0 else 0
        # Top player by kills in this zone
        top_player = None
        if not zg.empty:
            player_kills = zg[zg["quality"] == "kill"].groupby("player").size()
            if not player_kills.empty:
                top_player = player_kills.idxmax()
        attack_zones.append({
            "zone": str(zone),
            "kills": int(k),
            "errors": int(e),
            "attempts": int(t),
            "hitting_eff": eff,
            "top_player": top_player,
        })

    # Team-level receive zones
    receive_zones = []
    if not receive_actions.empty:
        receive_actions["pass_quality"] = receive_actions["quality"].map(q_map)
        for zone, zg in receive_actions.groupby("src_zone"):
            rq = zg["pass_quality"].dropna()
            pass_avg = round(rq.mean(), 3) if len(rq) > 0 else None
            t = len(zg)
            # Top receiver by volume
            top_player = None
            player_counts = zg.groupby("player").size()
            if not player_counts.empty:
                top_player = player_counts.idxmax()
            receive_zones.append({
                "zone": str(zone),
                "attempts": int(t),
                "pass_avg": pass_avg,
                "top_player": top_player,
            })

    # Per-player attack zones
    player_attack_zones = {}
    for player, pg in attack_actions.groupby("player"):
        if not player:
            continue
        zones = []
        for zone, zg in pg.groupby("src_zone"):
            k = (zg["quality"] == "kill").sum()
            e = (zg["quality"] == "error").sum()
            t = len(zg)
            eff = round((k - e) / t, 3) if t > 0 else 0
            zones.append({
                "zone": str(zone),
                "kills": int(k),
                "errors": int(e),
                "attempts": int(t),
                "hitting_eff": eff,
            })
        player_attack_zones[player] = zones

    # Per-player receive zones
    player_receive_zones = {}
    if not receive_actions.empty:
        for player, pg in receive_actions.groupby("player"):
            if not player:
                continue
            zones = []
            for zone, zg in pg.groupby("src_zone"):
                rq = zg["pass_quality"].dropna()
                pass_avg = round(rq.mean(), 3) if len(rq) > 0 else None
                zones.append({
                    "zone": str(zone),
                    "attempts": int(len(zg)),
                    "pass_avg": pass_avg,
                })
            player_receive_zones[player] = zones

    return {
        "attack_zones": attack_zones,
        "receive_zones": receive_zones,
        "player_attack_zones": player_attack_zones,
        "player_receive_zones": player_receive_zones,
    }


def filter_matches_by_date(matches, after_date=None):
    """Filter matches to only include those on or after after_date (YYYY-MM-DD string)."""
    if not after_date:
        return matches
    return [m for m in matches if m.get("date", "") >= after_date]


def _generate_all(dfs, output_dir):
    """Generate all JSON files to output_dir."""
    output_dir.mkdir(parents=True, exist_ok=True)

    overview = _sanitize(generate_overview(dfs))
    with open(output_dir / "overview.json", "w") as f:
        json.dump(overview, f, indent=2, default=str)

    players = _sanitize(generate_players(dfs))
    with open(output_dir / "players.json", "w") as f:
        json.dump(players, f, indent=2, default=str)

    comparison = _sanitize(generate_comparison(dfs))
    with open(output_dir / "comparison.json", "w") as f:
        json.dump(comparison, f, indent=2, default=str)

    runs = _sanitize(generate_runs(dfs))
    with open(output_dir / "runs.json", "w") as f:
        json.dump(runs, f, indent=2, default=str)

    games = _sanitize(generate_games(dfs))
    with open(output_dir / "games.json", "w") as f:
        json.dump(games, f, indent=2, default=str)

    zones = _sanitize(generate_zones(dfs))
    with open(output_dir / "zones.json", "w") as f:
        json.dump(zones, f, indent=2, default=str)


def main():
    matches = load_from_cache()
    if not matches:
        print("No cached data found. Run seed_cache.py first.", file=sys.stderr)
        sys.exit(1)

    print(f"Loaded {len(matches)} matches from cache.", file=sys.stderr)

    # Full dataset
    dfs_full = build_all(matches)
    _generate_all(dfs_full, SITE_DATA_DIR / "full")
    print("Generated full dataset", file=sys.stderr)

    # Recent dataset (after Feb 1)
    recent_matches = filter_matches_by_date(matches, "2026-02-01")
    if recent_matches:
        dfs_recent = build_all(recent_matches)
        _generate_all(dfs_recent, SITE_DATA_DIR / "recent")
        print(f"Generated recent dataset ({len(recent_matches)} matches after 2026-02-01)", file=sys.stderr)

    print("Done! Open site/index.html to view.", file=sys.stderr)


if __name__ == "__main__":
    main()
