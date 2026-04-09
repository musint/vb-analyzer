"""Team-level analytics: KPIs, sideout, scoring runs, run triggers."""

import pandas as pd
from collections import defaultdict


def team_kpis(rallies_df: pd.DataFrame, actions_df: pd.DataFrame) -> dict:
    """Compute top-level team KPIs."""
    if rallies_df.empty:
        return {}

    valid = rallies_df[rallies_df["point_winner"] != ""]
    total = len(valid)
    won = (valid["point_winner"] == "us").sum()
    receive = valid[valid["is_receive"]]
    sideout = receive["is_sideout"].sum()
    serve = valid[~valid["is_receive"]]
    breakpt = (serve["point_winner"] == "us").sum()

    our_attacks = actions_df[
        (actions_df["is_our_team"]) &
        (actions_df["action_type"] == "attack") &
        (actions_df["quality"].isin(["kill", "error", "in_play", "block_kill"]))
    ]
    kills = (our_attacks["quality"] == "kill").sum()
    errors = (our_attacks["quality"] == "error").sum()
    att_total = len(our_attacks)

    receives = actions_df[
        (actions_df["is_our_team"]) & (actions_df["action_type"] == "receive")
    ]
    q_map = {"3": 3, "2": 2, "1": 1, "0": 0}
    rq = receives["quality"].map(q_map).dropna()

    matches = rallies_df.groupby("video_id").first()
    wins = (matches["sets_won"] > matches["sets_lost"]).sum()
    losses = len(matches) - wins

    return {
        "record": f"{wins}-{losses}",
        "wins": int(wins),
        "losses": int(losses),
        "total_matches": len(matches),
        "total_sets": int(matches["sets_won"].sum() + matches["sets_lost"].sum()),
        "total_rallies": total,
        "point_win_pct": round(won / total * 100, 1) if total > 0 else 0,
        "sideout_pct": round(sideout / len(receive) * 100, 1) if len(receive) > 0 else 0,
        "breakpoint_pct": round(breakpt / len(serve) * 100, 1) if len(serve) > 0 else 0,
        "hitting_eff": round((kills - errors) / att_total, 3) if att_total > 0 else 0,
        "kill_pct": round(kills / att_total * 100, 1) if att_total > 0 else 0,
        "pass_avg": round(rq.mean(), 3) if len(rq) > 0 else 0,
    }


def sideout_by_category(rallies_df: pd.DataFrame, category: str) -> pd.DataFrame:
    """Sideout % grouped by a category column (game_phase, score_situation, is_clutch)."""
    df = rallies_df[(rallies_df["point_winner"] != "") & (rallies_df["is_receive"])]
    if df.empty:
        return pd.DataFrame()
    grouped = df.groupby(category).agg(
        sideouts=("is_sideout", "sum"),
        opportunities=("is_sideout", "count"),
    )
    grouped["sideout_pct"] = (grouped["sideouts"] / grouped["opportunities"] * 100).round(1)
    return grouped.reset_index()


def detect_runs(rallies_df: pd.DataFrame, min_length: int = 3) -> dict:
    """Detect scoring runs. Returns {'our_runs': [...], 'opp_runs': [...]}."""
    df = rallies_df[rallies_df["point_winner"] != ""].copy()
    our_runs = []
    opp_runs = []

    for (vid, sn), group in df.groupby(["video_id", "set_number"]):
        group = group.sort_values("rally_id")
        current_run = []
        current_winner = ""

        for _, row in group.iterrows():
            if row["point_winner"] == current_winner:
                current_run.append(row.to_dict())
            else:
                if len(current_run) >= min_length:
                    target = our_runs if current_winner == "us" else opp_runs
                    target.append(current_run[:])
                current_run = [row.to_dict()]
                current_winner = row["point_winner"]

        if len(current_run) >= min_length:
            target = our_runs if current_winner == "us" else opp_runs
            target.append(current_run[:])

    return {"our_runs": our_runs, "opp_runs": opp_runs}


def run_triggers(runs: list, actions_df: pd.DataFrame, our_team_name: str) -> pd.DataFrame:
    """Analyze what action/player starts each run."""
    triggers = []
    for run in runs:
        first = run[0]
        vid = first["video_id"]
        rid = first["rally_id"]
        rally_actions = actions_df[
            (actions_df["video_id"] == vid) & (actions_df["rally_id"] == rid)
        ]
        terminal = rally_actions[rally_actions["quality"].isin(["kill", "error", "ace", "block_kill"])]
        if not terminal.empty:
            last = terminal.iloc[-1]
            triggers.append({
                "player": last["player"],
                "action": last["action_type"],
                "quality": last["quality"],
                "is_our_team": last["is_our_team"],
                "run_length": len(run),
                "game_phase": first["game_phase"],
                "score_situation": first["score_situation"],
            })
    return pd.DataFrame(triggers)
