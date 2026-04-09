"""Generate static site data from cached match data."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from data.loader import load_from_cache
from analytics.core import build_all
from analytics.team import team_kpis, sideout_by_category

SITE_DATA_DIR = Path(__file__).parent / "site" / "data"


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


def main():
    matches = load_from_cache()
    if not matches:
        print("No cached data found. Run seed_cache.py first.", file=sys.stderr)
        sys.exit(1)

    print(f"Loaded {len(matches)} matches from cache.", file=sys.stderr)
    dfs = build_all(matches)

    SITE_DATA_DIR.mkdir(parents=True, exist_ok=True)

    overview = generate_overview(dfs)
    with open(SITE_DATA_DIR / "overview.json", "w") as f:
        json.dump(overview, f, indent=2, default=str)
    print("Generated overview.json", file=sys.stderr)


if __name__ == "__main__":
    main()
