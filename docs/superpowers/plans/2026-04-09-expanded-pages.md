# Expanded Pages & Analytics Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add 3 new pages (Runs, Game Detail, Zones) and 3 analytics modules to existing pages. Navigation grows from 3 to 6 tabs.

**Architecture:** Same pattern as existing — `generate_site.py` exports JSON, static HTML/JS pages render with Plotly.js. Existing analytics modules (`analytics/team.py`, `analytics/advanced.py`, `analytics/player.py`) are reused as-is. New generator functions are added to `generate_site.py`.

**Tech Stack:** Python 3 (existing analytics), Plotly.js (CDN), vanilla HTML/CSS/JS.

---

## Task 1: Update Navigation to 6 Tabs

**Files:**
- Modify: `site/index.html`
- Modify: `site/players.html`
- Modify: `site/comparison.html`

Update all 3 existing HTML files to show 6 nav tabs.

- [ ] **Step 1: Update nav in all 3 HTML files**

In each of `site/index.html`, `site/players.html`, and `site/comparison.html`, replace the nav-tabs div:

```html
      <div class="nav-tabs">
        <a href="index.html">Overview</a>
        <a href="players.html">Players</a>
        <a href="comparison.html">Comparison</a>
      </div>
```

with:

```html
      <div class="nav-tabs">
        <a href="index.html">Overview</a>
        <a href="players.html">Players</a>
        <a href="comparison.html">Comparison</a>
        <a href="runs.html">Runs</a>
        <a href="game.html">Game</a>
        <a href="zones.html">Zones</a>
      </div>
```

- [ ] **Step 2: Commit**

```bash
git add site/index.html site/players.html site/comparison.html
git commit -m "feat: update navigation to 6 tabs"
```

---

## Task 2: generate_site.py — Runs Data

**Files:**
- Modify: `generate_site.py`

Add `generate_runs()` function that uses existing `detect_runs()` and `run_triggers()` from `analytics/team.py`.

- [ ] **Step 1: Add imports at top of generate_site.py**

Add to the import section (after existing imports):

```python
from analytics.team import team_kpis, sideout_by_category, detect_runs, run_triggers
```

(Replace the existing `from analytics.team import team_kpis, sideout_by_category` line.)

- [ ] **Step 2: Add generate_runs() function**

Add after the `generate_overview()` function:

```python
def generate_runs(dfs):
    """Build runs.json with run analysis, starters, killers, and context breakdowns."""
    rallies_df = dfs["rallies"]
    actions_df = dfs["actions"]
    matches = dfs["matches"]

    # Get our team name from first match
    our_team_name = matches[0].get("our_team_name", "") if matches else ""

    # Detect runs
    runs = detect_runs(rallies_df)
    our_runs = runs["our_runs"]
    opp_runs = runs["opp_runs"]

    # Summary KPIs
    our_lengths = [len(r) for r in our_runs]
    opp_lengths = [len(r) for r in opp_runs]
    summary = {
        "our_runs": len(our_runs),
        "opp_runs": len(opp_runs),
        "avg_our_length": round(sum(our_lengths) / len(our_lengths), 1) if our_lengths else 0,
        "avg_opp_length": round(sum(opp_lengths) / len(opp_lengths), 1) if opp_lengths else 0,
        "longest_our": max(our_lengths) if our_lengths else 0,
        "longest_opp": max(opp_lengths) if opp_lengths else 0,
    }

    # Rallies played per player (for rate calculations)
    our_actions = actions_df[actions_df["is_our_team"]]
    rallies_per_player = our_actions.groupby("player")["rally_id"].nunique().to_dict()

    # Run starters: use run_triggers on our runs
    starter_df = run_triggers(our_runs, actions_df, our_team_name)
    starters = []
    if not starter_df.empty:
        for player, pgroup in starter_df.groupby("player"):
            if not player:
                continue
            runs_started = len(pgroup)
            rallies_played = rallies_per_player.get(player, 0)
            breakdown = {}
            for _, row in pgroup.iterrows():
                key = row["quality"] if row["quality"] in ("kill", "ace", "block_kill") else "opp_error"
                breakdown[key] = breakdown.get(key, 0) + 1
            starters.append({
                "player": player,
                "runs_started": runs_started,
                "rallies_played": rallies_played,
                "start_rate_pct": round(runs_started / rallies_played * 100, 1) if rallies_played > 0 else 0,
                "breakdown": breakdown,
            })
        starters.sort(key=lambda x: x["start_rate_pct"], reverse=True)

    # Run killers: for opponent runs, find which of our players' errors triggered them
    killer_df = run_triggers(opp_runs, actions_df, our_team_name)
    killers = []
    if not killer_df.empty:
        # Opponent runs are triggered by our errors or opponent kills
        # Filter to actions by our team that are errors
        our_errors = killer_df[killer_df["is_our_team"] & killer_df["quality"].isin(["error"])]
        for player, pgroup in our_errors.groupby("player"):
            if not player:
                continue
            runs_triggered = len(pgroup)
            rallies_played = rallies_per_player.get(player, 0)
            breakdown = {}
            for _, row in pgroup.iterrows():
                key = f"{row['action']}_error"
                breakdown[key] = breakdown.get(key, 0) + 1
            killers.append({
                "player": player,
                "runs_triggered": runs_triggered,
                "rallies_played": rallies_played,
                "trigger_rate_pct": round(runs_triggered / rallies_played * 100, 1) if rallies_played > 0 else 0,
                "breakdown": breakdown,
            })
        killers.sort(key=lambda x: x["trigger_rate_pct"], reverse=True)

    # Runs by game phase
    phases = ["early", "middle", "final"]
    runs_by_phase = []
    for phase in phases:
        our_count = sum(1 for r in our_runs if r[0].get("game_phase") == phase)
        opp_count = sum(1 for r in opp_runs if r[0].get("game_phase") == phase)
        runs_by_phase.append({"phase": phase, "our_runs": our_count, "opp_runs": opp_count})

    # Runs by score situation
    situations = ["winning_big", "winning", "close", "losing", "losing_big"]
    runs_by_situation = []
    for sit in situations:
        our_count = sum(1 for r in our_runs if r[0].get("score_situation") == sit)
        opp_count = sum(1 for r in opp_runs if r[0].get("score_situation") == sit)
        runs_by_situation.append({"situation": sit, "our_runs": our_count, "opp_runs": opp_count})

    return {
        "summary": summary,
        "starters": starters,
        "killers": killers,
        "runs_by_phase": runs_by_phase,
        "runs_by_situation": runs_by_situation,
    }
```

- [ ] **Step 3: Add runs.json to main()**

In `main()`, after the comparison block and before the final print, add:

```python
    runs = _sanitize(generate_runs(dfs))
    with open(SITE_DATA_DIR / "runs.json", "w") as f:
        json.dump(runs, f, indent=2, default=str)
    print("Generated runs.json", file=sys.stderr)
```

- [ ] **Step 4: Run and verify**

Run: `python generate_site.py`
Verify: `python -c "import json; r=json.load(open('site/data/runs.json')); print('Keys:', list(r.keys())); print('Our runs:', r['summary']['our_runs']); print('Starters:', len(r['starters']))"`

- [ ] **Step 5: Commit**

```bash
git add generate_site.py
git commit -m "feat: add runs JSON generation"
```

---

## Task 3: generate_site.py — Games Data

**Files:**
- Modify: `generate_site.py`

Add `generate_games()` function using `momentum_data()` and `win_probability_table()` from `analytics/advanced.py`.

- [ ] **Step 1: Add imports**

Update the imports at the top of `generate_site.py` — add:

```python
from analytics.advanced import expected_sideout_by_pass, serve_pressure_index, momentum_data, win_probability_table
from analytics.player import (
    player_season_stats, clutch_comparison, consistency_index,
    season_progression, player_stats_filtered, in_system_efficiency,
)
```

Move any existing inline imports from `generate_players()` and `generate_comparison()` to the top level (removing the `from analytics.player import ...` lines inside those functions).

- [ ] **Step 2: Add generate_games() function**

Add after `generate_runs()`:

```python
def generate_games(dfs):
    """Build games.json with per-game momentum, win probability, and box scores."""
    rallies_df = dfs["rallies"]
    actions_df = dfs["actions"]
    matches = dfs["matches"]

    # Build global win probability table
    wp_table = win_probability_table(rallies_df)
    wp_lookup = {}
    if not wp_table.empty:
        for _, row in wp_table.iterrows():
            wp_lookup[(int(row["our_score"]), int(row["opp_score"]))] = float(row["win_pct"])

    q_map = {"3": 3, "2": 2, "1": 1, "0": 0}

    game_list = []
    games = {}

    for m in matches:
        vid = m["video_id"]
        game_rallies = rallies_df[rallies_df["video_id"] == vid]
        game_actions = actions_df[actions_df["video_id"] == vid]

        if game_rallies.empty:
            continue

        first = game_rallies.iloc[0]
        sets_won = int(first["sets_won"])
        sets_lost = int(first["sets_lost"])
        result = "W" if sets_won > sets_lost else "L"

        game_list.append({
            "video_id": vid,
            "date": first["match_date"],
            "opponent": first["match_title"],
            "result": result,
            "score": f"{sets_won}-{sets_lost}",
        })

        # Per-game KPIs
        receive = game_rallies[game_rallies["is_receive"]]
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

        our_receives = game_actions[
            (game_actions["is_our_team"]) & (game_actions["action_type"] == "receive")
        ]
        rq = our_receives["quality"].map(q_map).dropna()
        pass_avg = round(rq.mean(), 3) if len(rq) > 0 else 0

        kpis = {
            "result": result,
            "sets_won": sets_won,
            "sets_lost": sets_lost,
            "sideout_pct": so_pct,
            "hitting_eff": hitting_eff,
            "pass_avg": pass_avg,
        }

        # Momentum data
        mom = momentum_data(rallies_df, vid)
        momentum = []
        if not mom.empty:
            for _, row in mom.iterrows():
                momentum.append({
                    "set_number": int(row["set_number"]),
                    "rally_num": int(row["rally_num"]),
                    "our_score": int(row["our_score"]),
                    "opp_score": int(row["opp_score"]),
                    "score_diff": int(row["score_diff"]),
                    "point_winner": row["point_winner"],
                })

        # Win probability per rally
        win_prob = []
        for item in momentum:
            wp = wp_lookup.get((item["our_score"], item["opp_score"]), 50.0)
            win_prob.append({
                "set_number": item["set_number"],
                "rally_num": item["rally_num"],
                "our_score": item["our_score"],
                "opp_score": item["opp_score"],
                "win_pct": wp,
            })

        # Per-set box scores
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

                digs = len(pacts[(pacts["action_type"] == "dig") & (pacts["quality"] != "error")])

                set_rows.append({
                    "player": player,
                    "kills": k,
                    "errors": e,
                    "attempts": t,
                    "hitting_eff": eff,
                    "aces": aces,
                    "digs": int(digs),
                })
            set_rows.sort(key=lambda x: x["kills"], reverse=True)
            box_scores[str(int(sn))] = set_rows

        games[vid] = {
            "kpis": kpis,
            "momentum": momentum,
            "win_probability": win_prob,
            "box_scores": box_scores,
        }

    game_list.sort(key=lambda x: x["date"], reverse=True)
    return {"game_list": game_list, "games": games}
```

- [ ] **Step 3: Add games.json to main()**

In `main()`, add after runs block:

```python
    games_data = _sanitize(generate_games(dfs))
    with open(SITE_DATA_DIR / "games.json", "w") as f:
        json.dump(games_data, f, indent=2, default=str)
    print("Generated games.json", file=sys.stderr)
```

- [ ] **Step 4: Run and verify**

Run: `python generate_site.py`
Verify: `python -c "import json; g=json.load(open('site/data/games.json')); print('Games:', len(g['game_list'])); vid=g['game_list'][0]['video_id']; gd=g['games'][vid]; print('Momentum rallies:', len(gd['momentum'])); print('Box score sets:', list(gd['box_scores'].keys()))"`

- [ ] **Step 5: Commit**

```bash
git add generate_site.py
git commit -m "feat: add games JSON generation with momentum and win probability"
```

---

## Task 4: generate_site.py — Zones Data

**Files:**
- Modify: `generate_site.py`

Add `generate_zones()` that computes attack efficiency and receive quality per zone.

- [ ] **Step 1: Add generate_zones() function**

Add after `generate_games()`:

```python
def generate_zones(dfs):
    """Build zones.json with attack and receive zone data, including per-player breakdowns."""
    actions_df = dfs["actions"]
    our_actions = actions_df[actions_df["is_our_team"]]

    # Attack zones
    attacks = our_actions[
        (our_actions["action_type"] == "attack")
        & (our_actions["quality"].isin(["kill", "error", "in_play", "block_kill"]))
        & (our_actions["src_zone"].notna())
    ]

    attack_zones = {}
    attack_detail = []
    per_player_attack = {}

    if not attacks.empty:
        for zone, grp in attacks.groupby("src_zone"):
            zone_int = int(zone)
            k = int((grp["quality"] == "kill").sum())
            e = int((grp["quality"] == "error").sum())
            t = len(grp)
            eff = round((k - e) / t, 3) if t > 0 else 0

            # Top player by kills
            player_kills = grp[grp["quality"] == "kill"].groupby("player").size()
            top_player = player_kills.idxmax() if not player_kills.empty else ""

            attack_zones[str(zone_int)] = {
                "eff": eff, "kills": k, "errors": e, "attempts": t, "top_player": top_player,
            }
            attack_detail.append({
                "zone": zone_int, "kills": k, "errors": e, "attempts": t, "eff": eff, "top_player": top_player,
            })

        # Per-player attack zones
        for player, pgrp in attacks.groupby("player"):
            if not player:
                continue
            per_player_attack[player] = {}
            for zone, zgrp in pgrp.groupby("src_zone"):
                zone_int = int(zone)
                k = int((zgrp["quality"] == "kill").sum())
                e = int((zgrp["quality"] == "error").sum())
                t = len(zgrp)
                per_player_attack[player][str(zone_int)] = {
                    "eff": round((k - e) / t, 3) if t > 0 else 0,
                    "kills": k, "errors": e, "attempts": t,
                }

    attack_detail.sort(key=lambda x: x["zone"])

    # Receive zones
    q_map = {"3": 3, "2": 2, "1": 1, "0": 0}
    receives = our_actions[
        (our_actions["action_type"] == "receive")
        & (our_actions["src_zone"].notna())
    ]

    receive_zones = {}
    receive_detail = []
    per_player_receive = {}

    if not receives.empty:
        for zone, grp in receives.groupby("src_zone"):
            zone_int = int(zone)
            rq = grp["quality"].map(q_map).dropna()
            avg = round(float(rq.mean()), 3) if len(rq) > 0 else 0
            total = int(len(rq))

            # Top receiver by count
            player_counts = grp.groupby("player").size()
            top_player = player_counts.idxmax() if not player_counts.empty else ""

            receive_zones[str(zone_int)] = {"avg": avg, "total": total, "top_player": top_player}
            receive_detail.append({"zone": zone_int, "avg": avg, "total": total, "top_player": top_player})

        # Per-player receive zones
        for player, pgrp in receives.groupby("player"):
            if not player:
                continue
            per_player_receive[player] = {}
            for zone, zgrp in pgrp.groupby("src_zone"):
                zone_int = int(zone)
                rq = zgrp["quality"].map(q_map).dropna()
                per_player_receive[player][str(zone_int)] = {
                    "avg": round(float(rq.mean()), 3) if len(rq) > 0 else 0,
                    "total": int(len(rq)),
                }

    receive_detail.sort(key=lambda x: x["zone"])

    player_list = sorted(set(list(per_player_attack.keys()) + list(per_player_receive.keys())))

    return {
        "attack_zones": attack_zones,
        "receive_zones": receive_zones,
        "attack_detail": attack_detail,
        "receive_detail": receive_detail,
        "player_list": player_list,
        "per_player_attack": per_player_attack,
        "per_player_receive": per_player_receive,
    }
```

- [ ] **Step 2: Add zones.json to main()**

In `main()`, add after games block:

```python
    zones = _sanitize(generate_zones(dfs))
    with open(SITE_DATA_DIR / "zones.json", "w") as f:
        json.dump(zones, f, indent=2, default=str)
    print("Generated zones.json", file=sys.stderr)
```

- [ ] **Step 3: Run and verify**

Run: `python generate_site.py`
Verify: `python -c "import json; z=json.load(open('site/data/zones.json')); print('Attack zones:', list(z['attack_zones'].keys())); print('Receive zones:', list(z['receive_zones'].keys())); print('Players:', len(z['player_list']))"`

- [ ] **Step 4: Commit**

```bash
git add generate_site.py
git commit -m "feat: add zones JSON generation with per-player breakdowns"
```

---

## Task 5: generate_site.py — Expand Overview and Players Data

**Files:**
- Modify: `generate_site.py`

Add expected sideout by pass to `generate_overview()`, and serve pressure + in-system efficiency to `generate_players()`.

- [ ] **Step 1: Add expected sideout to generate_overview()**

At the end of `generate_overview()`, before the `return` statement, add:

```python
    # Expected sideout by pass quality
    exp_so = expected_sideout_by_pass(rallies_df, actions_df)
    expected_sideout = []
    if not exp_so.empty:
        for _, row in exp_so.iterrows():
            expected_sideout.append({
                "pass_quality": int(row["pass_quality"]),
                "sideout_pct": float(row["sideout_pct"]),
                "rallies": int(row["rallies"]),
            })
```

And add `"expected_sideout": expected_sideout,` to the return dict.

- [ ] **Step 2: Add serve pressure and in-system to generate_players()**

At the end of `generate_players()`, before the `return` statement, add:

```python
    # Serve Pressure Index
    spi_df = serve_pressure_index(actions_df)
    serve_pressure_by_player = {}
    if not spi_df.empty:
        for _, row in spi_df.iterrows():
            serve_pressure_by_player[row["player"]] = {
                "serves": int(row["serves"]),
                "aces": int(row["aces"]),
                "srv_errors": int(row["srv_errors"]),
                "pressure_serves": int(row["pressure_serves"]),
                "pressure_pct": float(row["pressure_pct"]),
            }

    # In-System vs Out-of-System Efficiency
    insys_df = in_system_efficiency(actions_df)
    in_system_by_player = {}
    if not insys_df.empty:
        for player, pgrp in insys_df.groupby("player"):
            if not player:
                continue
            entry = {}
            for _, row in pgrp.iterrows():
                key = "in_system" if row["in_system"] else "out_of_system"
                entry[key] = {
                    "hitting_eff": float(row["hitting_eff"]),
                    "kills": int(row["kills"]),
                    "errors": int(row["errors"]),
                    "attempts": int(row["attempts"]),
                }
            in_system_by_player[player] = entry
```

And add `"serve_pressure": serve_pressure_by_player,` and `"in_system": in_system_by_player,` to the return dict.

- [ ] **Step 3: Run and verify**

Run: `python generate_site.py`
Verify overview: `python -c "import json; o=json.load(open('site/data/overview.json')); print('Expected sideout entries:', len(o.get('expected_sideout', [])))"`
Verify players: `python -c "import json; p=json.load(open('site/data/players.json')); print('Serve pressure players:', len(p.get('serve_pressure', {}))); print('In-system players:', len(p.get('in_system', {})))"`

- [ ] **Step 4: Commit**

```bash
git add generate_site.py
git commit -m "feat: add expected sideout, serve pressure, and in-system data"
```

---

## Task 6: New HTML Pages — Runs, Game, Zones

**Files:**
- Create: `site/runs.html`
- Create: `site/game.html`
- Create: `site/zones.html`

**IMPORTANT:** Use the **frontend-design** skill for this task. Pass it the design context below.

> Create 3 new HTML pages for a volleyball analytics static site matching the existing dark theme in `site/css/style.css`. Reference existing pages (`site/index.html`, `site/players.html`) for the pattern.
>
> All 3 pages share: same nav bar with 6 tabs (Overview, Players, Comparison, Runs, Game, Zones), same Plotly.js CDN, same CSS, app.js, and their own page JS.
>
> **runs.html** — "Scoring Runs" page
> Container IDs: `runs-kpi-row`, `starters-table`, `killers-table`, `runs-by-phase-chart`, `runs-by-situation-chart`
> Layout: KPI row (6 cards), two sortable tables side by side (starters + killers), two charts side by side (phase + situation)
>
> **game.html** — "Game Detail" page
> Container IDs: `game-selector`, `game-kpis`, `momentum-chart`, `win-prob-chart`, `box-scores`
> Layout: Game selector dropdown in a card, KPI row (5 cards), momentum chart (full width, tall), win probability (full width), box score tables area
>
> **zones.html** — "Court Zones" page
> Container IDs: `zone-player-filter`, `attack-court`, `attack-detail-table`, `receive-court`, `receive-detail-table`
> Layout: Player filter dropdown, then two side-by-side sections (attack court + table, receive court + table)

- [ ] **Step 1: Invoke frontend-design skill with the context above**

- [ ] **Step 2: Verify pages load and nav works**

Open each page in browser via `cd site && python -m http.server 8080`. Verify nav shows 6 tabs, container IDs are present.

- [ ] **Step 3: Commit**

```bash
git add site/runs.html site/game.html site/zones.html
git commit -m "feat: add HTML pages for runs, game detail, and zones"
```

---

## Task 7: Runs Page JavaScript

**Files:**
- Create/Replace: `site/js/runs.js`

Loads `data/runs.json` and renders all Runs page sections.

- [ ] **Step 1: Create site/js/runs.js**

```javascript
/* 13-2 Statistical Deep Dive — Runs Page */

const STATE_LABELS = {
  winning_big: "Winning Big", winning: "Winning", close: "Close",
  losing: "Losing", losing_big: "Losing Big",
};

document.addEventListener("DOMContentLoaded", async () => {
  const data = await loadJSON("data/runs.json");
  if (!data) {
    document.querySelector(".main-content").innerHTML =
      '<p style="color:var(--red);padding:2rem">Failed to load runs data.</p>';
    return;
  }
  renderRunKPIs(data.summary);
  renderStartersTable(data.starters);
  renderKillersTable(data.killers);
  renderRunsByPhase(data.runs_by_phase);
  renderRunsBySituation(data.runs_by_situation);
});

function renderRunKPIs(s) {
  const el = document.getElementById("runs-kpi-row");
  const items = [
    { label: "Our Runs", value: s.our_runs, color: "var(--green)" },
    { label: "Opp Runs", value: s.opp_runs, color: "var(--red)" },
    { label: "Avg Our Length", value: s.avg_our_length.toFixed(1), color: "var(--accent)" },
    { label: "Avg Opp Length", value: s.avg_opp_length.toFixed(1), color: "var(--muted)" },
    { label: "Longest Ours", value: s.longest_our, color: "var(--gold)" },
    { label: "Longest Theirs", value: s.longest_opp, color: "var(--muted)" },
  ];
  el.innerHTML = items.map(i => `
    <div class="kpi-card">
      <div class="kpi-value" style="color:${i.color}">${i.value}</div>
      <div class="kpi-label">${i.label}</div>
    </div>`).join("");
}

function renderStartersTable(starters) {
  const el = document.getElementById("starters-table");
  if (!starters.length) { el.innerHTML = '<p class="muted">No run data.</p>'; return; }

  el.innerHTML = `
    <table class="data-table">
      <thead><tr>
        <th>Player</th><th class="num">Runs</th><th class="num">Rallies</th>
        <th class="num sortable">Rate %</th><th>Breakdown</th>
      </tr></thead>
      <tbody>
        ${starters.map(s => `<tr>
          <td>${s.player}</td>
          <td class="num">${s.runs_started}</td>
          <td class="num">${s.rallies_played}</td>
          <td class="num"><strong>${s.start_rate_pct.toFixed(1)}%</strong></td>
          <td class="muted" style="font-size:0.8rem">${Object.entries(s.breakdown).map(([k,v]) => `${k}: ${v}`).join(", ")}</td>
        </tr>`).join("")}
      </tbody>
    </table>`;
}

function renderKillersTable(killers) {
  const el = document.getElementById("killers-table");
  if (!killers.length) { el.innerHTML = '<p class="muted">No killer data.</p>'; return; }

  el.innerHTML = `
    <table class="data-table">
      <thead><tr>
        <th>Player</th><th class="num">Triggered</th><th class="num">Rallies</th>
        <th class="num sortable">Rate %</th><th>Breakdown</th>
      </tr></thead>
      <tbody>
        ${killers.map(k => `<tr>
          <td>${k.player}</td>
          <td class="num">${k.runs_triggered}</td>
          <td class="num">${k.rallies_played}</td>
          <td class="num"><strong>${k.trigger_rate_pct.toFixed(1)}%</strong></td>
          <td class="muted" style="font-size:0.8rem">${Object.entries(k.breakdown).map(([key,v]) => `${key}: ${v}`).join(", ")}</td>
        </tr>`).join("")}
      </tbody>
    </table>`;
}

function renderRunsByPhase(data) {
  const el = document.getElementById("runs-by-phase-chart");
  const labels = { early: "Early (0-9)", middle: "Middle (10-19)", final: "Final (20+)" };
  const order = ["early", "middle", "final"];
  const sorted = [...data].sort((a, b) => order.indexOf(a.phase) - order.indexOf(b.phase));

  Plotly.newPlot(el, [
    { name: "Our Runs", x: sorted.map(d => labels[d.phase] || d.phase), y: sorted.map(d => d.our_runs), type: "bar", marker: { color: "rgba(74,222,128,0.8)" } },
    { name: "Opp Runs", x: sorted.map(d => labels[d.phase] || d.phase), y: sorted.map(d => d.opp_runs), type: "bar", marker: { color: "rgba(248,113,113,0.8)" } },
  ], darkLayout({ barmode: "group", height: 300, legend: { orientation: "h", y: -0.2 } }), PLOTLY_CONFIG);
}

function renderRunsBySituation(data) {
  const el = document.getElementById("runs-by-situation-chart");
  const order = ["winning_big", "winning", "close", "losing", "losing_big"];
  const sorted = [...data].sort((a, b) => order.indexOf(a.situation) - order.indexOf(b.situation));

  Plotly.newPlot(el, [
    { name: "Our Runs", x: sorted.map(d => STATE_LABELS[d.situation] || d.situation), y: sorted.map(d => d.our_runs), type: "bar", marker: { color: "rgba(74,222,128,0.8)" } },
    { name: "Opp Runs", x: sorted.map(d => STATE_LABELS[d.situation] || d.situation), y: sorted.map(d => d.opp_runs), type: "bar", marker: { color: "rgba(248,113,113,0.8)" } },
  ], darkLayout({ barmode: "group", height: 300, legend: { orientation: "h", y: -0.2 } }), PLOTLY_CONFIG);
}
```

- [ ] **Step 2: Verify in browser**

Serve: `cd site && python -m http.server 8080`, open `http://localhost:8080/runs.html`.

- [ ] **Step 3: Commit**

```bash
git add site/js/runs.js
git commit -m "feat: add runs page JavaScript"
```

---

## Task 8: Game Detail Page JavaScript

**Files:**
- Create/Replace: `site/js/game.js`

Loads `data/games.json` and renders game detail with momentum chart, win probability, and box scores.

- [ ] **Step 1: Create site/js/game.js**

```javascript
/* 13-2 Statistical Deep Dive — Game Detail Page */

let gamesData = null;

document.addEventListener("DOMContentLoaded", async () => {
  gamesData = await loadJSON("data/games.json");
  if (!gamesData) {
    document.querySelector(".main-content").innerHTML =
      '<p style="color:var(--red);padding:2rem">Failed to load game data.</p>';
    return;
  }
  buildGameSelector();
  if (gamesData.game_list.length > 0) {
    renderGame(gamesData.game_list[0].video_id);
  }
});

function buildGameSelector() {
  const el = document.getElementById("game-selector");
  const select = document.createElement("select");
  select.id = "game-dropdown";
  select.className = "dropdown";
  gamesData.game_list.forEach(g => {
    const opt = document.createElement("option");
    opt.value = g.video_id;
    opt.textContent = `${g.date} — ${g.opponent} (${g.result} ${g.score})`;
    select.appendChild(opt);
  });
  select.addEventListener("change", () => renderGame(select.value));
  el.appendChild(select);
}

function renderGame(videoId) {
  const g = gamesData.games[videoId];
  if (!g) return;
  renderGameKPIs(g.kpis);
  renderMomentum(g.momentum);
  renderWinProb(g.win_probability);
  renderBoxScores(g.box_scores);
}

function renderGameKPIs(kpis) {
  const el = document.getElementById("game-kpis");
  const items = [
    { label: "Result", value: `<span class="badge badge-${kpis.result === 'W' ? 'win' : 'loss'}">${kpis.result}</span>`, color: "" },
    { label: "Set Score", value: `${kpis.sets_won}-${kpis.sets_lost}`, color: "var(--accent)" },
    { label: "Sideout %", value: kpis.sideout_pct + "%", color: "var(--green)" },
    { label: "Hitting Eff", value: kpis.hitting_eff.toFixed(3), color: "var(--gold)" },
    { label: "Pass Avg", value: kpis.pass_avg.toFixed(3), color: "#a78bfa" },
  ];
  el.innerHTML = items.map(i => `
    <div class="kpi-card">
      <div class="kpi-value" style="color:${i.color}">${i.value}</div>
      <div class="kpi-label">${i.label}</div>
    </div>`).join("");
}

function renderMomentum(momentum) {
  const el = document.getElementById("momentum-chart");
  if (!momentum.length) { el.innerHTML = '<p class="muted">No momentum data.</p>'; return; }

  // Group by set
  const sets = {};
  momentum.forEach(r => {
    if (!sets[r.set_number]) sets[r.set_number] = [];
    sets[r.set_number].push(r);
  });

  const setNums = Object.keys(sets).map(Number).sort();
  const traces = [];
  const shapes = [];

  setNums.forEach((sn, idx) => {
    const rallies = sets[sn];
    const x = rallies.map(r => r.rally_num);
    const y = rallies.map(r => r.score_diff);

    traces.push({
      x, y, type: "scatter", mode: "lines+markers",
      name: `Set ${sn}`,
      line: { width: 2 },
      marker: { size: 4 },
      xaxis: idx === 0 ? "x" : `x${idx + 1}`,
      yaxis: idx === 0 ? "y" : `y${idx + 1}`,
    });

    // Detect runs for shading
    let runStart = null, runWinner = null, runLen = 0;
    rallies.forEach((r, i) => {
      if (r.point_winner === runWinner) {
        runLen++;
      } else {
        if (runLen >= 3 && runStart !== null) {
          shapes.push({
            type: "rect",
            xref: idx === 0 ? "x" : `x${idx + 1}`,
            yref: idx === 0 ? "y" : `y${idx + 1}`,
            x0: rallies[runStart].rally_num - 0.5,
            x1: rallies[i - 1].rally_num + 0.5,
            y0: -30, y1: 30,
            fillcolor: runWinner === "us" ? "rgba(74,222,128,0.1)" : "rgba(248,113,113,0.1)",
            line: { width: 0 },
            layer: "below",
          });
        }
        runStart = i;
        runWinner = r.point_winner;
        runLen = 1;
      }
    });
    if (runLen >= 3 && runStart !== null) {
      shapes.push({
        type: "rect",
        xref: idx === 0 ? "x" : `x${idx + 1}`,
        yref: idx === 0 ? "y" : `y${idx + 1}`,
        x0: rallies[runStart].rally_num - 0.5,
        x1: rallies[rallies.length - 1].rally_num + 0.5,
        y0: -30, y1: 30,
        fillcolor: runWinner === "us" ? "rgba(74,222,128,0.1)" : "rgba(248,113,113,0.1)",
        line: { width: 0 },
        layer: "below",
      });
    }
  });

  // Build subplot layout
  const layout = darkLayout({
    height: 200 * setNums.length + 60,
    shapes,
    showlegend: true,
    legend: { orientation: "h", y: -0.05 },
  });

  // Add subplot axes
  setNums.forEach((sn, idx) => {
    const yKey = idx === 0 ? "yaxis" : `yaxis${idx + 1}`;
    const xKey = idx === 0 ? "xaxis" : `xaxis${idx + 1}`;
    const domain = [1 - (idx + 1) / setNums.length + 0.02, 1 - idx / setNums.length - 0.02];
    layout[yKey] = {
      ...layout.yaxis,
      title: `Set ${sn}`,
      domain,
      zeroline: true, zerolinecolor: "rgba(148,163,184,0.3)", zerolinewidth: 1,
    };
    layout[xKey] = {
      ...layout.xaxis,
      title: idx === setNums.length - 1 ? "Rally" : "",
      anchor: idx === 0 ? "y" : `y${idx + 1}`,
    };
  });

  Plotly.newPlot(el, traces, layout, PLOTLY_CONFIG);
}

function renderWinProb(winProb) {
  const el = document.getElementById("win-prob-chart");
  if (!winProb.length) { el.innerHTML = '<p class="muted">No win probability data.</p>'; return; }

  const sets = {};
  winProb.forEach(r => {
    if (!sets[r.set_number]) sets[r.set_number] = [];
    sets[r.set_number].push(r);
  });

  const setNums = Object.keys(sets).map(Number).sort();
  const traces = setNums.map(sn => {
    const rallies = sets[sn];
    return {
      x: rallies.map((_, i) => i + 1),
      y: rallies.map(r => r.win_pct),
      type: "scatter", mode: "lines",
      name: `Set ${sn}`,
      line: { width: 2 },
    };
  });

  Plotly.newPlot(el, traces, darkLayout({
    height: 300,
    yaxis: { title: "Win Probability %", range: [0, 100] },
    xaxis: { title: "Rally" },
    legend: { orientation: "h", y: -0.2 },
    shapes: [{ type: "line", x0: 0, x1: 1, xref: "paper", y0: 50, y1: 50, line: { color: "rgba(148,163,184,0.3)", dash: "dash", width: 1 } }],
  }), PLOTLY_CONFIG);
}

function renderBoxScores(boxScores) {
  const el = document.getElementById("box-scores");
  const setNums = Object.keys(boxScores).sort();

  if (!setNums.length) { el.innerHTML = '<p class="muted">No box score data.</p>'; return; }

  // Tabs + tables
  let html = '<div class="pill-row" style="margin-bottom:16px">';
  setNums.forEach((sn, i) => {
    html += `<button class="game-state-pill state-close" style="cursor:pointer;${i === 0 ? 'background:var(--accent);color:#0f172a' : ''}" data-set="${sn}" onclick="switchSet('${sn}')"">Set ${sn}</button>`;
  });
  html += '</div>';

  setNums.forEach((sn, i) => {
    const rows = boxScores[sn];
    html += `<div id="box-set-${sn}" style="${i > 0 ? 'display:none' : ''}">
      <table class="data-table">
        <thead><tr>
          <th>Player</th><th class="num">Kills</th><th class="num">Errors</th>
          <th class="num">Att</th><th class="num">Eff</th>
          <th class="num">Aces</th><th class="num">Digs</th>
        </tr></thead>
        <tbody>
          ${rows.map(r => `<tr>
            <td>${r.player}</td>
            <td class="num">${r.kills}</td><td class="num">${r.errors}</td>
            <td class="num">${r.attempts}</td><td class="num">${r.hitting_eff.toFixed(3)}</td>
            <td class="num">${r.aces}</td><td class="num">${r.digs}</td>
          </tr>`).join("")}
        </tbody>
      </table>
    </div>`;
  });

  el.innerHTML = html;
}

// Global function for set tab switching
function switchSet(sn) {
  document.querySelectorAll('[id^="box-set-"]').forEach(d => d.style.display = 'none');
  document.getElementById(`box-set-${sn}`).style.display = '';
  document.querySelectorAll('#box-scores .game-state-pill').forEach(btn => {
    btn.style.background = btn.dataset.set === sn ? 'var(--accent)' : '';
    btn.style.color = btn.dataset.set === sn ? '#0f172a' : '';
  });
}
```

- [ ] **Step 2: Verify in browser**

Serve and open `http://localhost:8080/game.html`. Verify: dropdown lists games, momentum chart shows score diff with run shading, win prob shows 50% line, box scores tab between sets.

- [ ] **Step 3: Commit**

```bash
git add site/js/game.js
git commit -m "feat: add game detail page JavaScript with momentum and win probability"
```

---

## Task 9: Zones Page JavaScript

**Files:**
- Create/Replace: `site/js/zones.js`

Loads `data/zones.json` and renders court heatmaps + detail tables with player filter.

- [ ] **Step 1: Create site/js/zones.js**

```javascript
/* 13-2 Statistical Deep Dive — Zones Page */

// Court zone coordinates (matching components/court.py)
// Zone layout (our perspective): 4|3|2 (front), 5|6|1 (back)
const ZONE_COORDS = {
  1: { x: 200, y: 150, w: 100, h: 150 },  // back right
  2: { x: 200, y: 0,   w: 100, h: 150 },  // front right
  3: { x: 100, y: 0,   w: 100, h: 150 },  // front center
  4: { x: 0,   y: 0,   w: 100, h: 150 },  // front left
  5: { x: 0,   y: 150, w: 100, h: 150 },  // back left
  6: { x: 100, y: 150, w: 100, h: 150 },  // back center
};

let zonesData = null;

document.addEventListener("DOMContentLoaded", async () => {
  zonesData = await loadJSON("data/zones.json");
  if (!zonesData) {
    document.querySelector(".main-content").innerHTML =
      '<p style="color:var(--red);padding:2rem">Failed to load zone data.</p>';
    return;
  }
  buildPlayerFilter();
  renderAll("all");
});

function buildPlayerFilter() {
  const el = document.getElementById("zone-player-filter");
  const select = document.createElement("select");
  select.id = "zone-filter-dropdown";
  select.className = "dropdown";

  const allOpt = document.createElement("option");
  allOpt.value = "all";
  allOpt.textContent = "All Players";
  select.appendChild(allOpt);

  zonesData.player_list.forEach(p => {
    const opt = document.createElement("option");
    opt.value = p;
    opt.textContent = p;
    select.appendChild(opt);
  });

  select.addEventListener("change", () => renderAll(select.value));
  el.appendChild(select);
}

function renderAll(player) {
  const attackData = player === "all" ? zonesData.attack_zones : (zonesData.per_player_attack[player] || {});
  const receiveData = player === "all" ? zonesData.receive_zones : (zonesData.per_player_receive[player] || {});
  const attackDetail = player === "all" ? zonesData.attack_detail : buildDetailFromMap(attackData, "attack");
  const receiveDetail = player === "all" ? zonesData.receive_detail : buildDetailFromMap(receiveData, "receive");

  renderCourt("attack-court", attackData, "eff", "Attack Efficiency");
  renderCourt("receive-court", receiveData, "avg", "Pass Average");
  renderAttackTable(attackDetail);
  renderReceiveTable(receiveDetail);
}

function buildDetailFromMap(zoneMap, type) {
  return Object.entries(zoneMap).map(([zone, data]) => ({
    zone: parseInt(zone),
    ...data,
  })).sort((a, b) => a.zone - b.zone);
}

function getColor(val, min, max) {
  if (max === min) return "rgba(200, 200, 100, 0.5)";
  const norm = (val - min) / (max - min);
  const r = Math.round(255 * (1 - norm));
  const g = Math.round(255 * norm);
  return `rgba(${r}, ${g}, 100, 0.5)`;
}

function renderCourt(containerId, zoneData, metric, title) {
  const el = document.getElementById(containerId);
  const values = Object.values(zoneData).map(d => d[metric] || 0);
  const minVal = values.length ? Math.min(...values) : 0;
  const maxVal = values.length ? Math.max(...values) : 1;

  let svg = `<svg viewBox="-10 -30 320 340" style="width:100%;max-width:320px;margin:0 auto;display:block">`;
  // Court outline
  svg += `<rect x="0" y="0" width="300" height="300" fill="none" stroke="var(--border)" stroke-width="2"/>`;
  // Net line
  svg += `<line x1="0" y1="150" x2="300" y2="150" stroke="var(--muted)" stroke-width="3"/>`;
  svg += `<text x="150" y="-10" text-anchor="middle" fill="var(--muted)" font-size="11">NET</text>`;
  // Zone dividers
  svg += `<line x1="100" y1="0" x2="100" y2="300" stroke="var(--border)" stroke-width="1" stroke-dasharray="4"/>`;
  svg += `<line x1="200" y1="0" x2="200" y2="300" stroke="var(--border)" stroke-width="1" stroke-dasharray="4"/>`;

  for (const [zone, coords] of Object.entries(ZONE_COORDS)) {
    const data = zoneData[zone] || {};
    const val = data[metric] || 0;
    const color = values.length ? getColor(val, minVal, maxVal) : "rgba(100,100,100,0.3)";
    const cx = coords.x + coords.w / 2;
    const cy = coords.y + coords.h / 2;

    svg += `<rect x="${coords.x}" y="${coords.y}" width="${coords.w}" height="${coords.h}" fill="${color}" stroke="var(--border)" stroke-width="0.5"/>`;
    svg += `<text x="${cx}" y="${cy - 8}" text-anchor="middle" fill="var(--text)" font-size="14" font-weight="600">Z${zone}</text>`;

    let valText = "";
    if (metric === "eff") valText = val.toFixed(3);
    else if (metric === "avg") valText = val.toFixed(2);
    else valText = val.toString();
    svg += `<text x="${cx}" y="${cy + 12}" text-anchor="middle" fill="var(--text)" font-size="12">${valText}</text>`;

    if (data.top_player) {
      svg += `<text x="${cx}" y="${cy + 28}" text-anchor="middle" fill="var(--muted)" font-size="9">${data.top_player}</text>`;
    }
  }

  svg += `</svg>`;
  el.innerHTML = svg;
}

function renderAttackTable(detail) {
  const el = document.getElementById("attack-detail-table");
  if (!detail.length) { el.innerHTML = '<p class="muted">No attack zone data.</p>'; return; }

  el.innerHTML = `
    <table class="data-table">
      <thead><tr>
        <th>Zone</th><th class="num">Kills</th><th class="num">Errors</th>
        <th class="num">Att</th><th class="num">Eff</th><th>Top Player</th>
      </tr></thead>
      <tbody>
        ${detail.map(d => `<tr>
          <td>Zone ${d.zone}</td>
          <td class="num">${d.kills || 0}</td><td class="num">${d.errors || 0}</td>
          <td class="num">${d.attempts || 0}</td><td class="num">${(d.eff || 0).toFixed(3)}</td>
          <td class="muted">${d.top_player || "—"}</td>
        </tr>`).join("")}
      </tbody>
    </table>`;
}

function renderReceiveTable(detail) {
  const el = document.getElementById("receive-detail-table");
  if (!detail.length) { el.innerHTML = '<p class="muted">No receive zone data.</p>'; return; }

  el.innerHTML = `
    <table class="data-table">
      <thead><tr>
        <th>Zone</th><th class="num">Pass Avg</th><th class="num">Total</th><th>Top Player</th>
      </tr></thead>
      <tbody>
        ${detail.map(d => `<tr>
          <td>Zone ${d.zone}</td>
          <td class="num">${(d.avg || 0).toFixed(2)}</td>
          <td class="num">${d.total || 0}</td>
          <td class="muted">${d.top_player || "—"}</td>
        </tr>`).join("")}
      </tbody>
    </table>`;
}
```

- [ ] **Step 2: Verify in browser**

Open `http://localhost:8080/zones.html`. Verify: court SVGs render with colored zones, player filter changes data, tables show correct numbers.

- [ ] **Step 3: Commit**

```bash
git add site/js/zones.js
git commit -m "feat: add zones page JavaScript with court heatmaps"
```

---

## Task 10: Enhance Overview — Expected Sideout Chart

**Files:**
- Modify: `site/index.html`
- Modify: `site/js/overview.js`

- [ ] **Step 1: Add container to index.html**

After the sideout-by-phase section (the closing `</section>` of the last `grid-2` section), add:

```html
    <!-- Expected Sideout by Pass Quality -->
    <section class="section">
      <div class="card">
        <h2 class="section-title">Expected Sideout by Pass Quality</h2>
        <div id="expected-sideout-chart" class="chart-container"></div>
      </div>
    </section>
```

- [ ] **Step 2: Add render function to overview.js**

At the end of the DOMContentLoaded handler, add:

```javascript
  if (data.expected_sideout) renderExpectedSideout(data.expected_sideout);
```

Then add the function:

```javascript
function renderExpectedSideout(data) {
  const el = document.getElementById("expected-sideout-chart");
  if (!data.length) { el.innerHTML = '<p class="muted">No data.</p>'; return; }

  const colors = ["#f87171", "#fbbf24", "#86efac", "#4ade80"];
  const trace = {
    x: data.map(d => `Pass ${d.pass_quality}`),
    y: data.map(d => d.sideout_pct),
    type: "bar",
    marker: { color: data.map((_, i) => colors[i] || "#38bdf8") },
    text: data.map(d => d.sideout_pct.toFixed(1) + "%"),
    textposition: "auto",
    textfont: { color: "#0f172a", size: 12 },
    hovertemplate: "Pass %{x}<br>SO%%: %{y:.1f}<br>Rallies: %{customdata}<extra></extra>",
    customdata: data.map(d => d.rallies),
  };

  Plotly.newPlot(el, [trace], darkLayout({
    height: 300,
    yaxis: { title: "Sideout %", range: [0, 100] },
  }), PLOTLY_CONFIG);
}
```

- [ ] **Step 3: Commit**

```bash
git add site/index.html site/js/overview.js
git commit -m "feat: add expected sideout by pass quality to overview"
```

---

## Task 11: Enhance Players — Serve Pressure and In-System

**Files:**
- Modify: `site/players.html`
- Modify: `site/js/players.js`

- [ ] **Step 1: Add containers to players.html**

After the consistency index section, add:

```html
    <!-- Serve Pressure Index -->
    <section class="section">
      <div class="card">
        <h2 class="section-title">Serve Pressure Index</h2>
        <div id="serve-pressure"></div>
      </div>
    </section>

    <!-- In-System vs Out-of-System -->
    <section class="section">
      <div class="card">
        <h2 class="section-title">In-System vs Out-of-System Efficiency</h2>
        <div id="in-system-eff" class="chart-container"></div>
      </div>
    </section>
```

- [ ] **Step 2: Add render functions to players.js**

In the `renderPlayer()` function, add two new calls:

```javascript
  renderServePressure(name);
  renderInSystem(name);
```

Then add the two functions:

```javascript
function renderServePressure(name) {
  const el = document.getElementById("serve-pressure");
  const sp = (playersData.serve_pressure || {})[name];

  if (!sp) {
    el.innerHTML = '<p style="color:var(--muted);font-size:0.875rem">No serve pressure data.</p>';
    return;
  }

  const items = [
    { label: "Total Serves", value: sp.serves, color: "var(--accent)" },
    { label: "Aces", value: sp.aces, color: "var(--green)" },
    { label: "Serve Errors", value: sp.srv_errors, color: "var(--red)" },
    { label: "Pressure Serves", value: sp.pressure_serves, color: "var(--gold)" },
    { label: "Pressure %", value: sp.pressure_pct.toFixed(1) + "%", color: "var(--gold)" },
  ];

  el.innerHTML = '<div class="kpi-row">' + items.map(i => `
    <div class="kpi-card">
      <div class="kpi-value" style="color:${i.color}">${i.value}</div>
      <div class="kpi-label">${i.label}</div>
    </div>`).join("") + '</div>' +
    '<p style="color:var(--muted);font-size:0.75rem;margin-top:8px">Pressure = aces + serves causing opponent 0 or 1 pass</p>';
}

function renderInSystem(name) {
  const el = document.getElementById("in-system-eff");
  const data = (playersData.in_system || {})[name];

  if (!data || (!data.in_system && !data.out_of_system)) {
    el.innerHTML = '<p style="color:var(--muted);font-size:0.875rem">No in-system data available.</p>';
    return;
  }

  const inSys = data.in_system || { hitting_eff: 0, attempts: 0 };
  const outSys = data.out_of_system || { hitting_eff: 0, attempts: 0 };

  Plotly.react(el, [{
    x: ["In System", "Out of System"],
    y: [inSys.hitting_eff, outSys.hitting_eff],
    type: "bar",
    marker: { color: ["rgba(74,222,128,0.8)", "rgba(248,113,113,0.8)"] },
    text: [inSys.hitting_eff.toFixed(3), outSys.hitting_eff.toFixed(3)],
    textposition: "auto",
    textfont: { color: "#0f172a", size: 12 },
    hovertemplate: "%{x}<br>Eff: %{y:.3f}<br>Attempts: %{customdata}<extra></extra>",
    customdata: [inSys.attempts, outSys.attempts],
  }], darkLayout({
    height: 280,
    yaxis: { title: "Hitting Efficiency" },
  }), PLOTLY_CONFIG);
}
```

- [ ] **Step 3: Commit**

```bash
git add site/players.html site/js/players.js
git commit -m "feat: add serve pressure and in-system efficiency to players page"
```

---

## Task 12: End-to-End Verification

**Files:**
- Possibly tweak: any file with issues found during verification

- [ ] **Step 1: Clean build**

```bash
cd C:\Users\SongMu\documents\claudecode\vba\vb-analyzer
rm -rf site/data/
python generate_site.py
```

Expected: all 6 JSON files generated (overview, players, comparison, runs, games, zones).

- [ ] **Step 2: Verify all 6 pages**

```bash
cd site && python -m http.server 8080
```

Walk through each page:
1. **Overview** — all existing sections plus expected sideout chart at bottom
2. **Players** — all existing sections plus serve pressure KPIs and in-system bar chart
3. **Comparison** — unchanged, still works
4. **Runs** — KPIs, starter/killer tables, phase/situation charts
5. **Game** — game dropdown, KPIs update, momentum chart with run shading, win probability, set tabs for box scores
6. **Zones** — court SVGs with colored zones, player filter changes both courts and tables

- [ ] **Step 3: Verify navigation**

Click through all 6 nav tabs from each page. Active tab should highlight. All links work.

- [ ] **Step 4: Check for console errors**

Open browser dev tools on each page. No JavaScript errors in console.

- [ ] **Step 5: Fix any issues found**

If any CSS classes are missing, container IDs don't match, or data doesn't render — fix and commit.

- [ ] **Step 6: Final commit**

```bash
git add -A site/
git commit -m "feat: complete expanded pages with all 6 pages working"
```
