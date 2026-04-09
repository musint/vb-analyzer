"""Player-level analytics: stats, clutch, consistency, progression."""

import pandas as pd
import numpy as np


def player_season_stats(actions_df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate season stats per player. Only our team."""
    df = actions_df[actions_df["is_our_team"]].copy()
    if df.empty:
        return pd.DataFrame()

    rows = []
    for player, pdf in df.groupby("player"):
        if not player:
            continue
        attacks = pdf[pdf["action_type"] == "attack"]
        att_terminal = attacks[attacks["quality"].isin(["kill", "error", "in_play", "block_kill"])]
        kills = (att_terminal["quality"] == "kill").sum()
        att_errors = (att_terminal["quality"] == "error").sum()
        att_total = len(att_terminal)
        eff = (kills - att_errors) / att_total if att_total > 0 else 0

        serves = pdf[pdf["action_type"] == "serve"]
        srv_total = len(serves)
        aces = (serves["quality"] == "ace").sum()
        srv_errors = (serves["quality"] == "error").sum()

        receives = pdf[pdf["action_type"] == "receive"]
        q_map = {"3": 3, "2": 2, "1": 1, "0": 0}
        recv_q = receives["quality"].map(q_map).dropna()
        pass_avg = recv_q.mean() if len(recv_q) > 0 else None
        pass_total = len(recv_q)

        digs = len(pdf[pdf["action_type"] == "dig"])
        blocks = len(pdf[(pdf["action_type"] == "block") & (pdf["quality"].isin(["kill", "block_kill", "solo"]))])

        rows.append({
            "player": player,
            "kills": int(kills), "att_errors": int(att_errors), "att_total": int(att_total),
            "hitting_eff": round(eff, 3),
            "kill_pct": round(kills / att_total * 100, 1) if att_total > 0 else 0,
            "aces": int(aces), "srv_errors": int(srv_errors), "srv_total": int(srv_total),
            "pass_avg": round(pass_avg, 3) if pass_avg is not None else None,
            "pass_total": int(pass_total),
            "digs": int(digs),
            "blocks": int(blocks),
            "total_actions": len(pdf),
        })

    return pd.DataFrame(rows).sort_values("total_actions", ascending=False).reset_index(drop=True)


def player_stats_filtered(actions_df: pd.DataFrame, filter_col: str = None, filter_val=None) -> pd.DataFrame:
    """Player stats filtered by any column (score_situation, game_phase, is_clutch, etc.)."""
    df = actions_df[actions_df["is_our_team"]].copy()
    if filter_col and filter_val is not None:
        df = df[df[filter_col] == filter_val]
    return player_season_stats(df.assign(is_our_team=True))


def clutch_comparison(actions_df: pd.DataFrame) -> pd.DataFrame:
    """Per-player stats in clutch vs non-clutch, with clutch rating."""
    clutch = player_stats_filtered(actions_df, "is_clutch", True)
    non_clutch = player_stats_filtered(actions_df, "is_clutch", False)
    overall = player_season_stats(actions_df)

    if clutch.empty or overall.empty:
        return pd.DataFrame()

    merged = overall[["player"]].copy()
    for col in ["hitting_eff", "kill_pct", "pass_avg", "aces", "srv_errors"]:
        c_vals = clutch.set_index("player")[col] if col in clutch.columns else pd.Series(dtype=float)
        nc_vals = non_clutch.set_index("player")[col] if col in non_clutch.columns else pd.Series(dtype=float)
        merged[f"{col}_clutch"] = merged["player"].map(c_vals)
        merged[f"{col}_non_clutch"] = merged["player"].map(nc_vals)

    # Clutch rating: difference in hitting eff (clutch - overall)
    overall_eff = overall.set_index("player")["hitting_eff"]
    clutch_eff = clutch.set_index("player")["hitting_eff"] if "hitting_eff" in clutch.columns else pd.Series(dtype=float)
    merged["clutch_rating"] = merged["player"].map(clutch_eff) - merged["player"].map(overall_eff)

    return merged


def consistency_index(actions_df: pd.DataFrame) -> pd.DataFrame:
    """Per-player consistency: std dev of per-match hitting eff, consistency score."""
    df = actions_df[actions_df["is_our_team"]].copy()
    if df.empty:
        return pd.DataFrame()

    rows = []
    for player, pdf in df.groupby("player"):
        if not player:
            continue
        per_match = []
        for vid, mdf in pdf.groupby("video_id"):
            attacks = mdf[(mdf["action_type"] == "attack") & (mdf["quality"].isin(["kill", "error", "in_play", "block_kill"]))]
            if len(attacks) >= 3:  # need minimum attempts
                k = (attacks["quality"] == "kill").sum()
                e = (attacks["quality"] == "error").sum()
                per_match.append((k - e) / len(attacks))

        if len(per_match) >= 3:
            std = np.std(per_match)
            score = 1 / (1 + std)
            rows.append({
                "player": player,
                "matches_with_attacks": len(per_match),
                "eff_std_dev": round(std, 4),
                "consistency_score": round(score, 3),
                "per_match_eff": per_match,  # for dot plot
                "avg_eff": round(np.mean(per_match), 3),
            })

    return pd.DataFrame(rows).sort_values("consistency_score", ascending=False).reset_index(drop=True)


def season_progression(actions_df: pd.DataFrame, window: int = 5) -> dict:
    """Per-player rolling averages across the season. Returns dict of player -> DataFrame."""
    df = actions_df[actions_df["is_our_team"]].copy()
    if df.empty:
        return {}

    # Get match order by date
    match_order = df.groupby("video_id")["match_date"].first().sort_values()

    result = {}
    for player, pdf in df.groupby("player"):
        if not player:
            continue
        match_stats = []
        for vid in match_order.index:
            mdf = pdf[pdf["video_id"] == vid]
            if mdf.empty:
                continue
            attacks = mdf[(mdf["action_type"] == "attack") & (mdf["quality"].isin(["kill", "error", "in_play", "block_kill"]))]
            k = (attacks["quality"] == "kill").sum()
            e = (attacks["quality"] == "error").sum()
            eff = (k - e) / len(attacks) if len(attacks) > 0 else None

            receives = mdf[mdf["action_type"] == "receive"]
            q_map = {"3": 3, "2": 2, "1": 1, "0": 0}
            rq = receives["quality"].map(q_map).dropna()
            pavg = rq.mean() if len(rq) > 0 else None

            match_stats.append({
                "date": match_order[vid],
                "match_title": mdf["match_title"].iloc[0],
                "hitting_eff": eff,
                "pass_avg": pavg,
            })

        if len(match_stats) >= window:
            mdf = pd.DataFrame(match_stats)
            mdf["hitting_eff_rolling"] = mdf["hitting_eff"].rolling(window, min_periods=1).mean()
            mdf["pass_avg_rolling"] = mdf["pass_avg"].rolling(window, min_periods=1).mean()
            result[player] = mdf

    return result


def in_system_efficiency(actions_df: pd.DataFrame) -> pd.DataFrame:
    """Attack efficiency in-system vs out-of-system per player."""
    attacks = actions_df[
        (actions_df["is_our_team"]) &
        (actions_df["action_type"] == "attack") &
        (actions_df["quality"].isin(["kill", "error", "in_play", "block_kill"])) &
        (actions_df["in_system"].notna())
    ]
    if attacks.empty:
        return pd.DataFrame()

    rows = []
    for (player, in_sys), g in attacks.groupby(["player", "in_system"]):
        if not player:
            continue
        k = (g["quality"] == "kill").sum()
        e = (g["quality"] == "error").sum()
        t = len(g)
        rows.append({
            "player": player,
            "in_system": bool(in_sys),
            "kills": int(k), "errors": int(e), "attempts": int(t),
            "hitting_eff": round((k - e) / t, 3) if t > 0 else 0,
        })
    return pd.DataFrame(rows)
