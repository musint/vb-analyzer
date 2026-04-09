# Volleyball Stat Analyzer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a local Dash/Plotly web dashboard for volleyball analytics with 6 interactive pages covering standard stats, clutch performance, consistency, scoring runs, court zones, and player comparison.

**Architecture:** Python Dash multi-page app. Data loaded from cached JSON (exported from Hudl Balltime API) or live via Playwright. Analytics computed in pandas DataFrames. Plotly figures rendered in Dash pages. Single-user, runs locally on `localhost:8050`.

**Tech Stack:** Python 3.12+, Dash 2.x, Plotly, Pandas, Playwright, httpx

---

## File Map

```
vb-analyzer/
  app.py                     # Dash app entry, multi-page routing, sidebar, refresh button
  requirements.txt           # dash, plotly, pandas, playwright, httpx
  .gitignore                 # data/cache/, __pycache__, .env
  .env                       # HUDL_EMAIL, HUDL_PASSWORD
  data/
    __init__.py
    loader.py                # load_data() -> dict of DataFrames; save/load cache
    balltime.py              # BalltimeClient + import_all_matches (adapted from mcp-hudl)
    cache/                   # .gitignored, holds matches.json
  analytics/
    __init__.py
    core.py                  # build_rallies_df(), build_actions_df(), classify helpers
    player.py                # player_season_stats(), clutch_stats(), consistency(), progression()
    team.py                  # team_kpis(), sideout_analysis(), run_detection(), run_triggers()
    advanced.py              # expected_sideout(), serve_pressure(), win_probability(), momentum()
  pages/
    __init__.py
    overview.py              # Page 1: Season dashboard
    player_detail.py         # Page 2: Single-player deep dive
    runs.py                  # Page 3: Scoring run analysis
    game_detail.py           # Page 4: Single-game breakdown
    zones.py                 # Page 5: Court heatmaps
    comparison.py            # Page 6: Player comparison
  components/
    __init__.py
    charts.py                # Reusable Plotly figure builders
    tables.py                # Reusable Dash DataTable builders
    court.py                 # Court diagram SVG + heatmap overlay
    filters.py               # Sidebar filter components
```

---

### Task 1: Project Setup + Data Layer

**Files:**
- Create: `requirements.txt`, `.gitignore`, `.env`, `data/__init__.py`, `data/balltime.py`, `data/loader.py`

This task sets up the project and adapts the Balltime client from the MCP project. The MCP project lives at `C:\Users\SongMu\documents\claudecode\mcp-hudl\src\`. Copy and adapt `balltime_client.py` and `balltime_import.py` into this project as standalone modules (no relative imports from mcp-hudl).

- [ ] **Step 1: Create project files**

`requirements.txt`:
```
dash>=2.17
plotly>=5.22
pandas>=2.2
playwright>=1.44
httpx>=0.27
python-dotenv>=1.0
```

`.gitignore`:
```
data/cache/
__pycache__/
*.pyc
.env
```

`.env`:
```
HUDL_EMAIL=musint@gmail.com
HUDL_PASSWORD=Peace8321.
```

`data/__init__.py`: empty file.

- [ ] **Step 2: Create `data/balltime.py`**

Adapt from `mcp-hudl/src/balltime_client.py` and `mcp-hudl/src/balltime_import.py`. Combine into one file. Key changes:
- Remove relative imports (standalone module)
- Read credentials from environment variables via `python-dotenv`
- Keep `BalltimeClient` class exactly as-is (Playwright auth, httpx calls)
- Keep `MatchData`, `Rally` dataclasses exactly as-is
- Keep `import_all_matches()` exactly as-is
- Keep `process_match()`, `_determine_rally_winner()`, `_determine_serving_team()` exactly as-is
- All `str(x).lower()` fixes for integer quality values must be preserved

The file should be self-contained: running `python data/balltime.py` should authenticate and print match count.

- [ ] **Step 3: Create `data/loader.py`**

```python
"""Load volleyball data from cache or live Balltime API."""

import json
import os
import sys
from pathlib import Path
from dataclasses import asdict

CACHE_DIR = Path(__file__).parent / "cache"
CACHE_FILE = CACHE_DIR / "matches.json"


def load_from_cache():
    """Load cached match data. Returns list of dicts or None if no cache."""
    if not CACHE_FILE.exists():
        return None
    with open(CACHE_FILE, "r") as f:
        return json.load(f)


def save_to_cache(matches):
    """Save match data (list of MatchData) to JSON cache."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    # Convert dataclass instances to dicts
    data = []
    for m in matches:
        d = asdict(m)
        data.append(d)
    with open(CACHE_FILE, "w") as f:
        json.dump(data, f, default=str)
    print(f"Saved {len(data)} matches to cache", file=sys.stderr)


def refresh_from_balltime():
    """Authenticate with Balltime and import all matches. Saves to cache. Returns list of dicts."""
    from dotenv import load_dotenv
    load_dotenv()
    from data.balltime import BalltimeClient, import_all_matches

    email = os.getenv("HUDL_EMAIL", "")
    password = os.getenv("HUDL_PASSWORD", "")
    if not email or not password:
        raise RuntimeError("Set HUDL_EMAIL and HUDL_PASSWORD in .env")

    bt = BalltimeClient()
    result = bt.authenticate(email, password)
    if not result["ok"]:
        raise RuntimeError(f"Balltime auth failed: {result.get('error')}")

    matches = import_all_matches(bt)
    save_to_cache(matches)
    return [asdict(m) for m in matches]


def load_data():
    """Load match data from cache. Returns list of match dicts, or empty list."""
    cached = load_from_cache()
    if cached:
        return cached
    return []
```

- [ ] **Step 4: Install dependencies and verify**

```bash
cd C:\Users\SongMu\documents\claudecode\vb-analyzer
pip install -r requirements.txt
python -c "from data.loader import load_data; print(f'Loaded: {len(load_data())} matches')"
```

Expected: `Loaded: 0 matches` (no cache yet).

- [ ] **Step 5: Seed the cache from the MCP project data**

Write a one-time script `seed_cache.py` that uses the mcp-hudl Balltime client to import all matches and save to this project's cache:

```python
"""One-time script to seed the cache from Hudl Balltime."""
import sys
sys.path.insert(0, r"C:\Users\SongMu\documents\claudecode\mcp-hudl")
from src.balltime_client import BalltimeClient
from src.balltime_import import import_all_matches
from dataclasses import asdict
import json, os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()
bt = BalltimeClient()
bt.authenticate(os.getenv("HUDL_EMAIL"), os.getenv("HUDL_PASSWORD"))
matches = import_all_matches(bt)

cache_dir = Path("data/cache")
cache_dir.mkdir(parents=True, exist_ok=True)
with open(cache_dir / "matches.json", "w") as f:
    json.dump([asdict(m) for m in matches], f, default=str)
print(f"Seeded {len(matches)} matches")
```

Run: `python seed_cache.py`
Expected: ~55 matches imported and saved.

- [ ] **Step 6: Verify cache loads**

```bash
python -c "from data.loader import load_data; d=load_data(); print(f'Loaded: {len(d)} matches, {sum(len(m[\"raw_actions\"]) for m in d)} actions')"
```

Expected: `Loaded: 55 matches, 31005 actions`

- [ ] **Step 7: Commit**

```bash
git init
git add -A
git commit -m "feat: project setup with data layer and Balltime cache"
```

---

### Task 2: Core Analytics Engine

**Files:**
- Create: `analytics/__init__.py`, `analytics/core.py`

The core module builds two master DataFrames (rallies_df and actions_df) from the cached match data, with all the classification columns needed by every page.

- [ ] **Step 1: Create `analytics/__init__.py`** — empty file.

- [ ] **Step 2: Create `analytics/core.py`**

```python
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
    """Clutch = both teams >= 20 in sets 1-2, both >= 10 in set 3+."""
    threshold = 20 if set_number <= 2 else 10
    # Use score BEFORE this point
    return our_score >= threshold and opp_score >= threshold


def build_rallies_df(matches: list[dict]) -> pd.DataFrame:
    """Build a DataFrame with one row per rally, all classification columns."""
    rows = []
    for m in matches:
        for r in m.get("rallies", []):
            our_score = r["our_score_after"]
            opp_score = r["opp_score_after"]
            pw = r["point_winner"]

            # Compute score BEFORE this point
            if pw == "us":
                our_before = our_score - 1
                opp_before = opp_score
            elif pw == "them":
                our_before = our_score
                opp_before = opp_score - 1
            else:
                our_before = our_score
                opp_before = opp_score

            diff_before = our_before - opp_before
            max_before = max(our_before, opp_before)

            rows.append({
                "video_id": m["video_id"],
                "match_title": m["title"],
                "match_date": m["date"],
                "sets_won": m.get("sets_won", 0),
                "sets_lost": m.get("sets_lost", 0),
                "set_number": r["set_number"],
                "rally_id": r["rally_id"],
                "our_score": our_score,
                "opp_score": opp_score,
                "our_score_before": our_before,
                "opp_score_before": opp_before,
                "point_winner": pw,
                "serving_team": r["serving_team"],
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
    """Build a DataFrame with one row per action, joined with rally context."""
    # Build a rally lookup for context columns
    rally_ctx = {}
    for _, row in rallies_df.iterrows():
        key = (row["video_id"], row["rally_id"])
        rally_ctx[key] = row

    rows = []
    for m in matches:
        our_team = m.get("our_team_name", "")
        for r in m.get("rallies", []):
            ctx = rally_ctx.get((m["video_id"], r["rally_id"]))
            if ctx is None:
                continue
            for a in r.get("actions", []):
                player_raw = a.get("player") or ""
                # Strip jersey number suffix: "Emma Lares 14" -> "Emma Lares"
                player = player_raw.rsplit(" ", 1)[0] if player_raw and player_raw.split()[-1].isdigit() else player_raw

                rows.append({
                    "video_id": m["video_id"],
                    "match_title": m["title"],
                    "match_date": m["date"],
                    "set_number": r["set_number"],
                    "rally_id": r["rally_id"],
                    "point_winner": ctx["point_winner"],
                    "serving_team": ctx["serving_team"],
                    "score_situation": ctx["score_situation"],
                    "game_phase": ctx["game_phase"],
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
    """Build all DataFrames. Returns dict with 'rallies', 'actions', 'matches'."""
    rallies_df = build_rallies_df(matches)
    actions_df = build_actions_df(matches, rallies_df)
    return {
        "matches": matches,
        "rallies": rallies_df,
        "actions": actions_df,
    }
```

- [ ] **Step 3: Verify core analytics**

```bash
python -c "
from data.loader import load_data
from analytics.core import build_all
matches = load_data()
dfs = build_all(matches)
print(f'Rallies: {len(dfs[\"rallies\"])}')
print(f'Actions: {len(dfs[\"actions\"])}')
print(f'Clutch rallies: {dfs[\"rallies\"][\"is_clutch\"].sum()}')
print(f'Score situations: {dfs[\"rallies\"][\"score_situation\"].value_counts().to_dict()}')
"
```

Expected: ~5155 rallies, ~31005 actions, clutch rally count > 0, all 5 score situations present.

- [ ] **Step 4: Commit**

```bash
git add analytics/
git commit -m "feat: core analytics engine with rally/action DataFrames"
```

---

### Task 3: Player Analytics Module

**Files:**
- Create: `analytics/player.py`

Implements player_season_stats, clutch comparison, consistency index, season progression, and the stats-by-filter function used by score situation / game phase / clutch breakdowns.

- [ ] **Step 1: Create `analytics/player.py`**

```python
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
```

Add `in_system_efficiency()` to the same file:

```python
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
```

- [ ] **Step 2: Verify player analytics**

```bash
python -c "
from data.loader import load_data
from analytics.core import build_all
from analytics.player import player_season_stats, clutch_comparison, consistency_index
dfs = build_all(load_data())
stats = player_season_stats(dfs['actions'])
print(f'Players: {len(stats)}')
print(stats[['player','kills','hitting_eff','aces','pass_avg']].head(5).to_string())
print()
clutch = clutch_comparison(dfs['actions'])
print(f'Clutch data: {len(clutch)} players')
print()
cons = consistency_index(dfs['actions'])
print(cons[['player','consistency_score','eff_std_dev']].head(5).to_string())
"
```

- [ ] **Step 3: Commit**

```bash
git add analytics/player.py
git commit -m "feat: player analytics — stats, clutch, consistency, progression"
```

---

### Task 4: Team Analytics + Run Detection

**Files:**
- Create: `analytics/team.py`

- [ ] **Step 1: Create `analytics/team.py`**

```python
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
```

- [ ] **Step 2: Verify**

```bash
python -c "
from data.loader import load_data
from analytics.core import build_all
from analytics.team import team_kpis, detect_runs
dfs = build_all(load_data())
kpis = team_kpis(dfs['rallies'], dfs['actions'])
print(f'Record: {kpis[\"record\"]}, SO%: {kpis[\"sideout_pct\"]}, Eff: {kpis[\"hitting_eff\"]}')
runs = detect_runs(dfs['rallies'])
print(f'Our runs: {len(runs[\"our_runs\"])}, Opp runs: {len(runs[\"opp_runs\"])}')
"
```

- [ ] **Step 3: Commit**

```bash
git add analytics/team.py
git commit -m "feat: team analytics — KPIs, sideout, run detection, triggers"
```

---

### Task 5: Advanced Analytics

**Files:**
- Create: `analytics/advanced.py`

- [ ] **Step 1: Create `analytics/advanced.py`**

```python
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
```

- [ ] **Step 2: Verify**

```bash
python -c "
from data.loader import load_data
from analytics.core import build_all
from analytics.advanced import expected_sideout_by_pass, win_probability_table
dfs = build_all(load_data())
esp = expected_sideout_by_pass(dfs['rallies'], dfs['actions'])
print('Expected SO by pass quality:')
print(esp.to_string())
print()
wp = win_probability_table(dfs['rallies'])
print(f'Win prob table: {len(wp)} score states')
print(wp.head(10).to_string())
"
```

- [ ] **Step 3: Commit**

```bash
git add analytics/advanced.py
git commit -m "feat: advanced analytics — expected SO, serve pressure, win probability, momentum"
```

---

### Task 6: Reusable Components

**Files:**
- Create: `components/__init__.py`, `components/charts.py`, `components/tables.py`, `components/court.py`, `components/filters.py`

- [ ] **Step 1: Create all component files**

`components/__init__.py`: empty file.

`components/charts.py`:
```python
"""Reusable Plotly figure builders."""

import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np


def kpi_card(label: str, value, subtitle: str = "") -> go.Figure:
    """Single KPI indicator card."""
    fig = go.Figure(go.Indicator(
        mode="number",
        value=value if isinstance(value, (int, float)) else 0,
        title={"text": f"<b>{label}</b><br><span style='font-size:0.7em;color:gray'>{subtitle}</span>"},
        number={"suffix": "%" if "pct" in label.lower() or "%" in str(subtitle) else ""},
    ))
    fig.update_layout(height=120, margin=dict(l=10, r=10, t=50, b=10))
    return fig


def bar_comparison(df: pd.DataFrame, x: str, y_cols: list, labels: list, title: str = "") -> go.Figure:
    """Grouped bar chart comparing multiple metrics."""
    fig = go.Figure()
    for col, label in zip(y_cols, labels):
        fig.add_trace(go.Bar(name=label, x=df[x], y=df[col], text=df[col].round(3), textposition="auto"))
    fig.update_layout(title=title, barmode="group", height=400, margin=dict(l=40, r=20, t=50, b=40))
    return fig


def line_trend(df: pd.DataFrame, x: str, y: str, title: str = "", y_label: str = "") -> go.Figure:
    """Line chart for trends."""
    fig = px.line(df, x=x, y=y, title=title, markers=True)
    fig.update_layout(height=350, yaxis_title=y_label, margin=dict(l=40, r=20, t=50, b=40))
    return fig


def dot_plot(values: list, avg: float, title: str = "") -> go.Figure:
    """Dot plot showing individual match values vs average line."""
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=list(range(1, len(values) + 1)), y=values,
        mode="markers", marker=dict(size=8, color="#636EFA"),
        name="Per Match",
    ))
    fig.add_hline(y=avg, line_dash="dash", line_color="red", annotation_text=f"Avg: {avg:.3f}")
    fig.update_layout(title=title, height=250, xaxis_title="Match #", margin=dict(l=40, r=20, t=50, b=40))
    return fig


def radar_chart(players: list[dict], metrics: list[str], labels: list[str], title: str = "") -> go.Figure:
    """Radar chart comparing players across metrics."""
    fig = go.Figure()
    for p in players:
        values = [p.get(m, 0) or 0 for m in metrics]
        values.append(values[0])  # close the polygon
        fig.add_trace(go.Scatterpolar(r=values, theta=labels + [labels[0]], name=p["player"], fill="toself"))
    fig.update_layout(title=title, polar=dict(radialaxis=dict(visible=True)), height=450)
    return fig


def momentum_chart(df: pd.DataFrame, title: str = "") -> go.Figure:
    """Score differential line chart with run bands for one match."""
    fig = go.Figure()
    for sn in sorted(df["set_number"].unique()):
        sdf = df[df["set_number"] == sn]
        fig.add_trace(go.Scatter(
            x=sdf["rally_num"], y=sdf["score_diff"],
            mode="lines+markers", name=f"Set {sn}",
            marker=dict(size=4),
        ))
    fig.add_hline(y=0, line_dash="dash", line_color="gray")
    fig.update_layout(title=title, height=400, xaxis_title="Rally #", yaxis_title="Score Differential",
                      margin=dict(l=40, r=20, t=50, b=40))
    return fig


def game_flow_with_runs(df: pd.DataFrame, our_runs: list, opp_runs: list, title: str = "") -> go.Figure:
    """Momentum chart with colored bands for scoring runs."""
    fig = momentum_chart(df, title)

    # Add run bands as shaded rectangles
    for run in our_runs:
        first_rally = run[0]["rally_num"] if "rally_num" in run[0] else 0
        last_rally = run[-1]["rally_num"] if "rally_num" in run[-1] else 0
        fig.add_vrect(x0=first_rally - 0.5, x1=last_rally + 0.5,
                      fillcolor="green", opacity=0.1, line_width=0)

    for run in opp_runs:
        first_rally = run[0]["rally_num"] if "rally_num" in run[0] else 0
        last_rally = run[-1]["rally_num"] if "rally_num" in run[-1] else 0
        fig.add_vrect(x0=first_rally - 0.5, x1=last_rally + 0.5,
                      fillcolor="red", opacity=0.1, line_width=0)

    return fig
```

`components/tables.py`:
```python
"""Reusable Dash DataTable builders."""

from dash import dash_table
import pandas as pd


def stat_table(df: pd.DataFrame, id: str, page_size: int = 15) -> dash_table.DataTable:
    """Standard sortable stat table."""
    return dash_table.DataTable(
        id=id,
        data=df.to_dict("records"),
        columns=[{"name": col, "id": col, "type": "numeric" if df[col].dtype in ["int64", "float64"] else "text"}
                 for col in df.columns],
        sort_action="native",
        filter_action="native",
        page_size=page_size,
        style_table={"overflowX": "auto"},
        style_cell={"textAlign": "left", "padding": "8px", "fontSize": "13px"},
        style_header={"fontWeight": "bold", "backgroundColor": "#f0f0f0"},
        style_data_conditional=[
            {"if": {"row_index": "odd"}, "backgroundColor": "#fafafa"},
        ],
    )
```

`components/court.py`:
```python
"""Court diagram with zone heatmap overlay."""

import plotly.graph_objects as go


# Standard volleyball court zones (1-6) as rectangles
# Zone layout (from our perspective, looking at opponent):
#   4 | 3 | 2
#   5 | 6 | 1
ZONE_COORDS = {
    1: {"x0": 6, "x1": 9, "y0": 0, "y1": 4.5},
    2: {"x0": 6, "x1": 9, "y0": 4.5, "y1": 9},
    3: {"x0": 3, "x1": 6, "y0": 4.5, "y1": 9},
    4: {"x0": 0, "x1": 3, "y0": 4.5, "y1": 9},
    5: {"x0": 0, "x1": 3, "y0": 0, "y1": 4.5},
    6: {"x0": 3, "x1": 6, "y0": 0, "y1": 4.5},
}


def court_heatmap(zone_data: dict, metric: str = "eff", title: str = "") -> go.Figure:
    """Draw volleyball court with zones colored by a metric.
    zone_data: {zone_num: {"eff": 0.15, "kills": 10, "attempts": 50, ...}}
    """
    fig = go.Figure()

    # Draw court outline
    fig.add_shape(type="rect", x0=0, y0=0, x1=9, y1=9, line=dict(color="black", width=2))
    # Net line
    fig.add_shape(type="line", x0=0, y0=4.5, x1=9, y1=4.5, line=dict(color="black", width=3))
    # Zone dividers
    fig.add_shape(type="line", x0=3, y0=0, x1=3, y1=9, line=dict(color="gray", width=1, dash="dot"))
    fig.add_shape(type="line", x0=6, y0=0, x1=6, y1=9, line=dict(color="gray", width=1, dash="dot"))

    # Color zones
    max_val = max((d.get(metric, 0) for d in zone_data.values()), default=1) or 1
    min_val = min((d.get(metric, 0) for d in zone_data.values()), default=0)

    for zone, coords in ZONE_COORDS.items():
        data = zone_data.get(zone, {})
        val = data.get(metric, 0)
        # Normalize to 0-1 for color
        norm = (val - min_val) / (max_val - min_val) if max_val != min_val else 0.5
        r = int(255 * (1 - norm))
        g = int(255 * norm)
        color = f"rgba({r}, {g}, 100, 0.4)"

        fig.add_shape(type="rect", fillcolor=color, line=dict(width=0),
                      **coords)

        # Zone label
        cx = (coords["x0"] + coords["x1"]) / 2
        cy = (coords["y0"] + coords["y1"]) / 2
        label = f"Z{zone}<br>{val:.3f}" if isinstance(val, float) else f"Z{zone}<br>{val}"
        fig.add_annotation(x=cx, y=cy, text=label, showarrow=False,
                          font=dict(size=14, color="black"))

    fig.update_layout(
        title=title, height=500, width=450,
        xaxis=dict(visible=False, range=[-0.5, 9.5]),
        yaxis=dict(visible=False, range=[-0.5, 9.5], scaleanchor="x"),
        margin=dict(l=20, r=20, t=50, b=20),
    )
    return fig
```

`components/filters.py`:
```python
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
```

- [ ] **Step 2: Commit**

```bash
git add components/
git commit -m "feat: reusable components — charts, tables, court diagram, filters"
```

---

### Task 7: App Shell + Overview Page

**Files:**
- Create: `app.py`, `pages/__init__.py`, `pages/overview.py`

- [ ] **Step 1: Create `pages/__init__.py`** — empty file.

- [ ] **Step 2: Create `pages/overview.py`**

```python
"""Page 1: Season Overview dashboard."""

from dash import html, dcc, callback, Input, Output
import plotly.graph_objects as go
from analytics.team import team_kpis, sideout_by_category
from analytics.player import player_season_stats, season_progression
from analytics.advanced import expected_sideout_by_pass
from components.charts import line_trend
from components.tables import stat_table


def layout(dfs):
    kpis = team_kpis(dfs["rallies"], dfs["actions"])
    stats = player_season_stats(dfs["actions"])
    so_by_phase = sideout_by_category(dfs["rallies"], "game_phase")
    so_by_sit = sideout_by_category(dfs["rallies"], "score_situation")
    exp_so = expected_sideout_by_pass(dfs["rallies"], dfs["actions"])

    # Per-game results
    game_results = []
    for vid, group in dfs["rallies"].groupby("video_id"):
        first = group.iloc[0]
        game_results.append({
            "Date": first["match_date"],
            "Opponent": first["match_title"].replace("@ ", "").replace(" - Game", "").replace("vs. ", ""),
            "Result": f"{'W' if first['sets_won'] > first['sets_lost'] else 'L'} {first['sets_won']}-{first['sets_lost']}",
            "SO%": round(group[group["is_receive"]]["is_sideout"].mean() * 100, 1) if group["is_receive"].any() else 0,
            "Pt Win%": round((group["point_winner"] == "us").mean() * 100, 1),
        })
    import pandas as pd
    game_df = pd.DataFrame(game_results).sort_values("Date", ascending=False)

    # KPI cards as simple styled divs
    def kpi_div(label, value):
        return html.Div([
            html.H4(str(value), style={"margin": "0", "fontSize": "28px", "color": "#1a73e8"}),
            html.P(label, style={"margin": "0", "fontSize": "12px", "color": "#666"}),
        ], style={"textAlign": "center", "padding": "15px", "backgroundColor": "white",
                  "borderRadius": "8px", "boxShadow": "0 1px 3px rgba(0,0,0,0.1)", "flex": "1"})

    return html.Div([
        html.H2("Season Overview"),

        # KPI row
        html.Div([
            kpi_div("Record", kpis["record"]),
            kpi_div("Sideout %", f"{kpis['sideout_pct']}%"),
            kpi_div("Break Pt %", f"{kpis['breakpoint_pct']}%"),
            kpi_div("Hitting Eff", f"{kpis['hitting_eff']:.3f}"),
            kpi_div("Pass Avg", f"{kpis['pass_avg']:.3f}"),
            kpi_div("Rallies", f"{kpis['total_rallies']}"),
        ], style={"display": "flex", "gap": "10px", "marginBottom": "20px"}),

        # Sideout by phase and situation + Expected SO by pass quality
        html.Div([
            html.Div([
                html.H4("Sideout % by Game Phase"),
                stat_table(so_by_phase, "so-phase-table", page_size=5),
            ], style={"flex": "1"}),
            html.Div([
                html.H4("Sideout % by Score Situation"),
                stat_table(so_by_sit, "so-sit-table", page_size=5),
            ], style={"flex": "1"}),
            html.Div([
                html.H4("Expected Sideout by Pass Quality"),
                stat_table(exp_so, "exp-so-table", page_size=5),
            ], style={"flex": "1"}),
        ], style={"display": "flex", "gap": "20px", "marginBottom": "20px"}),

        # Game results table
        html.H4("Game Results"),
        stat_table(game_df, "game-results-table"),

        # Player season stats
        html.H4("Player Season Stats", style={"marginTop": "20px"}),
        stat_table(stats, "player-stats-table"),
    ])
```

- [ ] **Step 3: Create `app.py`**

```python
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
```

- [ ] **Step 4: Run the app**

```bash
cd C:\Users\SongMu\documents\claudecode\vb-analyzer
python app.py
```

Open `http://localhost:8050`. The Overview page should show KPI cards, sideout tables, game results, and player stats.

- [ ] **Step 5: Commit**

```bash
git add app.py pages/
git commit -m "feat: app shell with sidebar navigation and overview page"
```

---

### Task 8: Player Detail Page

**Files:**
- Create: `pages/player_detail.py`

- [ ] **Step 1: Create `pages/player_detail.py`**

This page uses Dash callbacks for the player dropdown. It shows: stat cards, clutch comparison bars, consistency gauge + dot plot, season progression trendlines, score situation breakdown, game phase breakdown, and run initiator stats.

Build the full page with a `layout(dfs)` function that returns the static structure, and register callbacks for the player dropdown that update all the charts. Use `player_season_stats`, `clutch_comparison`, `consistency_index`, `season_progression` from `analytics/player.py`, and `detect_runs`, `run_triggers` from `analytics/team.py`.

Key sections:
- Player dropdown at top
- Row of stat cards (kills, eff, aces, pass avg, digs)
- Clutch vs non-clutch grouped bar chart (hitting_eff, kill_pct side by side)
- Consistency dot plot from `consistency_index().per_match_eff`
- Season progression line chart from `season_progression()[player]`
- Score situation bar chart: hitting_eff per situation from `player_stats_filtered()`
- Game phase bar chart: hitting_eff per phase from `player_stats_filtered()`
- Serve pressure index from `advanced.serve_pressure_index()` (for this player)
- In-system vs out-of-system efficiency from `player.in_system_efficiency()`

Use `@callback` with `Input("player-dropdown", "value")` to update all chart `dcc.Graph` components.

- [ ] **Step 2: Test by running app and navigating to /players**

- [ ] **Step 3: Commit**

```bash
git add pages/player_detail.py
git commit -m "feat: player detail page with clutch, consistency, progression"
```

---

### Task 9: Scoring Runs Page

**Files:**
- Create: `pages/runs.py`

- [ ] **Step 1: Create `pages/runs.py`**

Uses `detect_runs()` and `run_triggers()` from `analytics/team.py`. Shows:
- Summary cards: total our runs, opp runs, avg length, longest
- Run starter leaderboard table (from `run_triggers(our_runs)` grouped by player)
- Run killer leaderboard table (from `run_triggers(opp_runs)` grouped by player with `is_our_team == True`)
- Trigger breakdown bar chart (action types that start runs)
- Top 20 longest runs as a table with scores, set, phase, opponent

All static — no callbacks needed. Layout function computes everything from `dfs`.

- [ ] **Step 2: Test and commit**

```bash
git add pages/runs.py
git commit -m "feat: scoring runs page with trigger analysis and leaderboards"
```

---

### Task 10: Game Detail Page

**Files:**
- Create: `pages/game_detail.py`

- [ ] **Step 1: Create `pages/game_detail.py`**

Uses `momentum_data()` from `analytics/advanced.py` and `win_probability_table()`. Shows:
- Game selector dropdown (uses `components/filters.game_dropdown`)
- Momentum chart per set (score diff progression)
- Set-by-set box score table (player stats per set, computed from `actions_df` filtered by video_id and set_number)
- Win probability curve (join momentum data with win_probability_table)

Callback: `@callback(Output("game-charts", "children"), Input("game-selector", "value"))` rebuilds charts for selected game.

- [ ] **Step 2: Test and commit**

```bash
git add pages/game_detail.py
git commit -m "feat: game detail page with momentum chart and win probability"
```

---

### Task 11: Court Zones Page

**Files:**
- Create: `pages/zones.py`

- [ ] **Step 1: Create `pages/zones.py`**

Uses `components/court.court_heatmap()`. Computes attack efficiency per zone from `actions_df`:
```python
attacks = actions_df[(actions_df["is_our_team"]) & (actions_df["action_type"] == "attack") & (actions_df["src_zone"].notna())]
for zone in attacks["src_zone"].unique():
    z = attacks[attacks["src_zone"] == zone]
    kills = (z["quality"] == "kill").sum()
    errors = (z["quality"] == "error").sum()
    total = len(z[z["quality"].isin(["kill", "error", "in_play", "block_kill"])])
    zone_data[zone] = {"eff": (kills-errors)/total, "kills": kills, "attempts": total, ...}
```

Shows two court diagrams side by side:
- Left: Attack efficiency by zone
- Right: Serve receive quality by zone (average pass rating)

Below: table showing per-zone stats with player breakdown.

Optional player filter callback to show one player's zone data.

- [ ] **Step 2: Test and commit**

```bash
git add pages/zones.py
git commit -m "feat: court zones page with attack and receive heatmaps"
```

---

### Task 12: Player Comparison Page

**Files:**
- Create: `pages/comparison.py`

- [ ] **Step 1: Create `pages/comparison.py`**

Multi-select player dropdown (2-4 players). Shows:
- Radar chart using `components/charts.radar_chart()` with metrics: hitting_eff, kill_pct, pass_avg (normalized), serve_pressure (if available), consistency_score, clutch_rating
- Side-by-side stat table
- Overlaid progression trendlines (multiple players on same line chart)

Callback on player multi-select dropdown updates all visuals.

Normalization for radar: each metric scaled to 0-1 range across all players on the team, so the radar is comparative.

- [ ] **Step 2: Test and commit**

```bash
git add pages/comparison.py
git commit -m "feat: player comparison page with radar charts and trendlines"
```

---

### Task 13: Integration Validation

- [ ] **Step 1: Run the full app and verify all pages load**

```bash
python app.py
```

Visit each page: `/`, `/players`, `/runs`, `/game`, `/zones`, `/compare`. Verify no errors in console.

- [ ] **Step 2: Validate stats match CSV export**

```bash
python -c "
from data.loader import load_data
from analytics.core import build_all
from analytics.player import player_season_stats
dfs = build_all(load_data())
stats = player_season_stats(dfs['actions'])
# Compare with known values from Export CSV:
# Ava Nguyen: 236 kills, 785 attack attempts
ava = stats[stats['player'].str.contains('Ava N')]
print(f'Ava N kills: {ava.iloc[0][\"kills\"]} (expected: 236)')
print(f'Ava N att_total: {ava.iloc[0][\"att_total\"]} (expected: 785)')
"
```

- [ ] **Step 3: Final commit**

```bash
git add -A
git commit -m "feat: complete volleyball stat analyzer with all 6 pages"
```

---

## Notes for Implementer

- The data layer (`data/balltime.py`) should be adapted from `C:\Users\SongMu\documents\claudecode\mcp-hudl\src\balltime_client.py` and `C:\Users\SongMu\documents\claudecode\mcp-hudl\src\balltime_import.py`. The key fix: all `quality` field accesses must use `str(x).lower()` because Balltime returns integers (0, 1, 2, 3) for pass ratings.
- The Balltime team ID for NorCal 13-2 Blue is `ac699a8b-d173-50a0-8b26-ebbbd25ceb01` — hardcoded in the import function.
- The `our_team_name` is `"NorCal 13-2 Blue"` — used to distinguish our team from opponent in actions.
- `seed_cache.py` can be deleted after initial cache is created. The "Refresh from Hudl" button in the app does the same thing.
- Dash callbacks use `suppress_callback_exceptions=True` because pages are loaded lazily.
- For the player detail page, since Dash callbacks need component IDs that exist at page load, use a pattern of returning the full page content from the callback rather than individual charts.
