"""Core analytics: build DataFrames from match data with all classification columns."""

import pandas as pd


def classify_score_situation(diff: int) -> str:
    if diff >= 5:
        return "winning_big"
    elif diff >= 2:
        return "winning"
    elif diff >= -1:
        return "close"
    elif diff >= -4:
        return "losing"
    else:
        return "losing_big"


def classify_game_phase(max_score: int) -> str:
    if max_score < 10:
        return "early"
    elif max_score < 20:
        return "middle"
    else:
        return "final"


def is_clutch(set_number: int, our_score: int, opp_score: int) -> bool:
    threshold = 20 if set_number <= 2 else 10
    return our_score >= threshold and opp_score >= threshold


def build_rallies_df(matches: list[dict]) -> pd.DataFrame:
    rows = []
    for m in matches:
        for r in m.get("rallies", []):
            our_score = r["our_score_after"]
            opp_score = r["opp_score_after"]
            pw = r["point_winner"]
            if pw == "us":
                our_before, opp_before = our_score - 1, opp_score
            elif pw == "them":
                our_before, opp_before = our_score, opp_score - 1
            else:
                our_before, opp_before = our_score, opp_score
            diff_before = our_before - opp_before
            max_before = max(our_before, opp_before)
            rows.append({
                "video_id": m["video_id"], "match_title": m["title"], "match_date": m["date"],
                "sets_won": m.get("sets_won", 0), "sets_lost": m.get("sets_lost", 0),
                "set_number": r["set_number"], "rally_id": r["rally_id"],
                "our_score": our_score, "opp_score": opp_score,
                "our_score_before": our_before, "opp_score_before": opp_before,
                "point_winner": pw, "serving_team": r["serving_team"],
                "score_diff_before": diff_before,
                "score_situation": classify_score_situation(diff_before),
                "game_phase": classify_game_phase(max_before),
                "is_clutch": is_clutch(r["set_number"], our_before, opp_before),
                "is_sideout": r["serving_team"] == "them" and pw == "us",
                "is_receive": r["serving_team"] == "them",
                "num_actions": len(r.get("actions", [])),
            })
    return pd.DataFrame(rows)


def build_actions_df(matches: list[dict], rallies_df: pd.DataFrame) -> pd.DataFrame:
    rally_ctx = {}
    for _, row in rallies_df.iterrows():
        rally_ctx[(row["video_id"], row["rally_id"])] = row
    rows = []
    for m in matches:
        our_team = m.get("our_team_name", "")
        for r in m.get("rallies", []):
            ctx = rally_ctx.get((m["video_id"], r["rally_id"]))
            if ctx is None:
                continue
            for a in r.get("actions", []):
                player_raw = a.get("player") or ""
                player = player_raw.rsplit(" ", 1)[0] if player_raw and player_raw.split()[-1].isdigit() else player_raw
                rows.append({
                    "video_id": m["video_id"], "match_title": m["title"], "match_date": m["date"],
                    "set_number": r["set_number"], "rally_id": r["rally_id"],
                    "point_winner": ctx["point_winner"], "serving_team": ctx["serving_team"],
                    "score_situation": ctx["score_situation"], "game_phase": ctx["game_phase"],
                    "is_clutch": ctx["is_clutch"],
                    "action_type": str(a.get("action_type") or "").lower(),
                    "team": a.get("team", ""),
                    "is_our_team": a.get("team", "") == our_team,
                    "player": player,
                    "quality": str(a.get("quality") or "").lower(),
                    "first_ball_side_out": a.get("first_ball_side_out"),
                    "in_system": a.get("in_system"),
                    "speed_mph": a.get("speed_mph"),
                    "src_zone": a.get("src_zone"),
                    "dest_zone": a.get("dest_zone"),
                    "touch_position": a.get("touch_position"),
                })
    return pd.DataFrame(rows)


def build_all(matches: list[dict]) -> dict:
    rallies_df = build_rallies_df(matches)
    actions_df = build_actions_df(matches, rallies_df)
    return {"matches": matches, "rallies": rallies_df, "actions": actions_df}
