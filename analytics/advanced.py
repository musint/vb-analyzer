"""Advanced analytics: expected sideout, serve pressure, win probability, momentum."""

import pandas as pd
import numpy as np


def expected_sideout_by_pass(rallies_df: pd.DataFrame, actions_df: pd.DataFrame) -> pd.DataFrame:
    """Sideout % grouped by pass quality (0, 1, 2, 3)."""
    receives = actions_df[
        (actions_df["is_our_team"]) & (actions_df["action_type"] == "receive")
    ].copy()
    q_map = {"3": 3, "2": 2, "1": 1, "0": 0}
    receives["pass_quality"] = receives["quality"].map(q_map)
    receives = receives[receives["pass_quality"].notna()]

    # Join with rally outcome
    rally_outcomes = rallies_df[["video_id", "rally_id", "point_winner"]].drop_duplicates()
    merged = receives.merge(rally_outcomes, on=["video_id", "rally_id"], how="left", suffixes=("", "_rally"))
    pw = merged.get("point_winner_rally", merged.get("point_winner"))
    merged["won"] = pw == "us"

    return merged.groupby("pass_quality").agg(
        rallies=("won", "count"),
        sideouts=("won", "sum"),
    ).assign(
        sideout_pct=lambda x: (x["sideouts"] / x["rallies"] * 100).round(1)
    ).reset_index()


def serve_pressure_index(actions_df: pd.DataFrame) -> pd.DataFrame:
    """Per server: % of serves creating pressure (opponent error or 0/1 pass on next touch)."""
    serves = actions_df[
        (actions_df["is_our_team"]) & (actions_df["action_type"] == "serve")
    ].copy()
    if serves.empty:
        return pd.DataFrame()

    # A serve creates pressure if quality is "ace" or "error" (opponent's)
    # or the next receive by opponent is quality 0 or 1
    # Simplified: serve result "ace" = max pressure, "error" on serve = 0 pressure
    # For non-terminal serves, check if rally's first receive was 0 or 1
    rows = []
    for player, pdf in serves.groupby("player"):
        if not player:
            continue
        total = len(pdf)
        aces = (pdf["quality"] == "ace").sum()
        errors = (pdf["quality"] == "error").sum()
        # Pressure = aces + serves where opponent passed 0 or 1
        # We approximate: total - errors - aces = in_play serves
        # For in_play serves, check opponent receive quality in same rally
        in_play_vids = pdf[(pdf["quality"] != "ace") & (pdf["quality"] != "error")]
        pressure_from_pass = 0
        for _, srv in in_play_vids.iterrows():
            opp_recv = actions_df[
                (actions_df["video_id"] == srv["video_id"]) &
                (actions_df["rally_id"] == srv["rally_id"]) &
                (~actions_df["is_our_team"]) &
                (actions_df["action_type"] == "receive")
            ]
            if not opp_recv.empty:
                q = opp_recv.iloc[0]["quality"]
                if q in ("0", "1", "error"):
                    pressure_from_pass += 1

        pressure_total = int(aces) + pressure_from_pass
        rows.append({
            "player": player,
            "serves": total,
            "aces": int(aces),
            "srv_errors": int(errors),
            "pressure_serves": pressure_total,
            "pressure_pct": round(pressure_total / total * 100, 1) if total > 0 else 0,
        })

    return pd.DataFrame(rows).sort_values("serves", ascending=False).reset_index(drop=True)


def win_probability_table(rallies_df: pd.DataFrame) -> pd.DataFrame:
    """Build historical win probability for each score state.
    Returns DataFrame: set_number, our_score, opp_score, win_pct, sample_size."""
    rows = []
    # For each rally, compute: from this score state, did we eventually win the set?
    for (vid, sn), group in rallies_df.groupby(["video_id", "set_number"]):
        group = group.sort_values("rally_id")
        if group.empty:
            continue
        final = group.iloc[-1]
        set_winner = "us" if final["our_score"] > final["opp_score"] else "them"

        for _, r in group.iterrows():
            rows.append({
                "our_score": r["our_score_before"],
                "opp_score": r["opp_score_before"],
                "set_winner": set_winner,
            })

    df = pd.DataFrame(rows)
    if df.empty:
        return pd.DataFrame()

    grouped = df.groupby(["our_score", "opp_score"]).agg(
        total=("set_winner", "count"),
        wins=("set_winner", lambda x: (x == "us").sum()),
    )
    grouped["win_pct"] = (grouped["wins"] / grouped["total"] * 100).round(1)
    return grouped.reset_index()


def momentum_data(rallies_df: pd.DataFrame, video_id: str) -> pd.DataFrame:
    """Build per-rally momentum data for a specific match.
    Score differential progression for each set."""
    df = rallies_df[rallies_df["video_id"] == video_id].sort_values(["set_number", "rally_id"])
    if df.empty:
        return pd.DataFrame()

    df = df.copy()
    df["score_diff"] = df["our_score"] - df["opp_score"]
    df["rally_num"] = df.groupby("set_number").cumcount() + 1
    return df[["set_number", "rally_num", "our_score", "opp_score", "score_diff",
               "point_winner", "game_phase", "score_situation"]]
