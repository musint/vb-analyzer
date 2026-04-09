# Static Site Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convert vb-analyzer from a Dash server app to a polished static site on GitHub Pages — Python generates JSON data, separate HTML/CSS/JS frontend renders with Plotly.js.

**Architecture:** `generate_site.py` imports existing analytics modules, computes page-specific aggregations, and writes JSON to `site/data/`. The `site/` folder contains 3 HTML pages (Overview, Players, Comparison) with a shared CSS dark theme and per-page JS files that load JSON and render Plotly.js charts. No build tools. No frameworks.

**Tech Stack:** Python 3 (existing analytics), Plotly.js (CDN), vanilla HTML/CSS/JS, CSS variables for theming.

---

## Task 1: generate_site.py — Overview Data

**Files:**
- Create: `generate_site.py`
- Create: `site/data/` (directory)
- Read: `data/loader.py`, `analytics/core.py`, `analytics/team.py`, `analytics/player.py`

This task builds the Python script that generates `site/data/overview.json`. It reuses existing analytics modules.

- [ ] **Step 1: Create generate_site.py with overview JSON export**

```python
"""Generate static site data from cached match data."""

import json
import os
import sys
from pathlib import Path

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from data.loader import load_from_cache
from analytics.core import build_all
from analytics.team import team_kpis, sideout_by_category
from analytics.player import player_season_stats, player_stats_filtered

SITE_DATA_DIR = Path(__file__).parent / "site" / "data"


def generate_overview(dfs):
    """Build overview.json from rallies and actions DataFrames."""
    rallies_df = dfs["rallies"]
    actions_df = dfs["actions"]

    # KPIs
    kpis = team_kpis(rallies_df, actions_df)

    # Team progression: per-game KPIs over time
    progression = []
    for vid, group in rallies_df.groupby("video_id"):
        first = group.iloc[0]
        game_actions = actions_df[actions_df["video_id"] == vid]

        # Sideout %
        receive = group[group["is_receive"]]
        so_pct = round(receive["is_sideout"].mean() * 100, 1) if len(receive) > 0 else 0

        # Hitting eff
        our_attacks = game_actions[
            (game_actions["is_our_team"])
            & (game_actions["action_type"] == "attack")
            & (game_actions["quality"].isin(["kill", "error", "in_play", "block_kill"]))
        ]
        kills = (our_attacks["quality"] == "kill").sum()
        errors = (our_attacks["quality"] == "error").sum()
        att_total = len(our_attacks)
        hitting_eff = round((kills - errors) / att_total, 3) if att_total > 0 else 0

        # Pass avg
        receives = game_actions[
            (game_actions["is_our_team"]) & (game_actions["action_type"] == "receive")
        ]
        q_map = {"3": 3, "2": 2, "1": 1, "0": 0}
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

    # Overview
    overview = generate_overview(dfs)
    with open(SITE_DATA_DIR / "overview.json", "w") as f:
        json.dump(overview, f, indent=2, default=str)
    print("Generated overview.json", file=sys.stderr)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run generate_site.py and verify overview.json**

Run: `cd C:\Users\SongMu\documents\claudecode\vba\vb-analyzer && python generate_site.py`

Expected output:
```
Loaded 55 matches from cache.
Generated overview.json
```

Verify: `python -c "import json; d=json.load(open('site/data/overview.json')); print(list(d.keys())); print(f'KPIs: {d[\"kpis\"][\"record\"]}'); print(f'Games: {len(d[\"game_results\"])}'); print(f'Progression points: {len(d[\"progression\"])}')"

Expected: All keys present, record matches actual data, 55 game results, 55 progression points.

- [ ] **Step 3: Commit**

```bash
git add generate_site.py
git commit -m "feat: add generate_site.py with overview JSON export"
```

Note: Do NOT commit `site/data/*.json` — these are generated files and will be gitignored in Task 7.

---

## Task 2: generate_site.py — Players and Comparison Data

**Files:**
- Modify: `generate_site.py`
- Read: `analytics/player.py`

Add `generate_players()` and `generate_comparison()` functions to export the remaining two JSON files.

- [ ] **Step 1: Add generate_players() to generate_site.py**

Add this function after `generate_overview()`:

```python
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

    # Season stats per player
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

    # Clutch comparison
    clutch_df = clutch_comparison(actions_df)
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
            cr = row.get("clutch_rating")
            clutch_by_player[p]["clutch_rating"] = float(cr) if cr is not None and str(cr) != "nan" else None

    # Consistency
    cons_df = consistency_index(actions_df)
    consistency_by_player = {}
    if not cons_df.empty:
        for _, row in cons_df.iterrows():
            consistency_by_player[row["player"]] = {
                "consistency_score": float(row["consistency_score"]),
                "eff_std_dev": float(row["eff_std_dev"]),
                "avg_eff": float(row["avg_eff"]),
                "matches_with_attacks": int(row["matches_with_attacks"]),
            }

    # Season progression
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

    # Stats by game state per player
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
                    game_state_by_player[player].append({
                        "situation": sit,
                        "hitting_eff": float(r["hitting_eff"]),
                        "kill_pct": float(r["kill_pct"]),
                        "pass_avg": float(r["pass_avg"]) if r["pass_avg"] is not None else None,
                        "att_total": int(r["att_total"]),
                    })

    return {
        "player_list": player_list,
        "stats": stats_by_player,
        "clutch": clutch_by_player,
        "consistency": consistency_by_player,
        "progression": progression_by_player,
        "game_state": game_state_by_player,
    }
```

- [ ] **Step 2: Add generate_comparison() to generate_site.py**

Add this function after `generate_players()`:

```python
def generate_comparison(dfs):
    """Build comparison.json with normalized radar data and trend data."""
    actions_df = dfs["actions"]
    from analytics.player import player_season_stats, consistency_index

    all_stats = player_season_stats(actions_df)
    cons_df = consistency_index(actions_df)

    if all_stats.empty:
        return {"players": [], "radar_metrics": [], "radar_labels": []}

    player_list = all_stats["player"].tolist()

    # Build raw metrics per player
    metrics_map = {}
    for _, row in all_stats.iterrows():
        metrics_map[row["player"]] = {
            "kills": int(row["kills"]),
            "hitting_eff": float(row["hitting_eff"]),
            "aces": int(row["aces"]),
            "digs": int(row["digs"]),
            "pass_avg": float(row["pass_avg"]) if row["pass_avg"] is not None else None,
        }

    # Add consistency
    if not cons_df.empty:
        for _, row in cons_df.iterrows():
            p = row["player"]
            if p in metrics_map:
                metrics_map[p]["consistency"] = float(row["consistency_score"])

    # Normalize each metric to 0-1 across all players
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

    # Player colors (fixed palette)
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
```

- [ ] **Step 3: Update main() to call all generators**

Replace the `main()` function:

```python
def main():
    matches = load_from_cache()
    if not matches:
        print("No cached data found. Run seed_cache.py first.", file=sys.stderr)
        sys.exit(1)

    print(f"Loaded {len(matches)} matches from cache.", file=sys.stderr)
    dfs = build_all(matches)

    SITE_DATA_DIR.mkdir(parents=True, exist_ok=True)

    # Overview
    overview = generate_overview(dfs)
    with open(SITE_DATA_DIR / "overview.json", "w") as f:
        json.dump(overview, f, indent=2, default=str)
    print("Generated overview.json", file=sys.stderr)

    # Players
    players = generate_players(dfs)
    with open(SITE_DATA_DIR / "players.json", "w") as f:
        json.dump(players, f, indent=2, default=str)
    print("Generated players.json", file=sys.stderr)

    # Comparison
    comparison = generate_comparison(dfs)
    with open(SITE_DATA_DIR / "comparison.json", "w") as f:
        json.dump(comparison, f, indent=2, default=str)
    print("Generated comparison.json", file=sys.stderr)

    print("Done! Open site/index.html to view.", file=sys.stderr)
```

- [ ] **Step 4: Run and verify all JSON files**

Run: `cd C:\Users\SongMu\documents\claudecode\vba\vb-analyzer && python generate_site.py`

Expected:
```
Loaded 55 matches from cache.
Generated overview.json
Generated players.json
Generated comparison.json
Done! Open site/index.html to view.
```

Verify: `python -c "import json; p=json.load(open('site/data/players.json')); print(f'Players: {len(p[\"player_list\"])}'); c=json.load(open('site/data/comparison.json')); print(f'Comparison players: {len(c[\"players\"])}')"

- [ ] **Step 5: Commit**

```bash
git add generate_site.py
git commit -m "feat: add players and comparison JSON generation"
```

---

## Task 3: Frontend Foundation — HTML Shell, CSS Theme, Navigation

**Files:**
- Create: `site/index.html`
- Create: `site/players.html`
- Create: `site/comparison.html`
- Create: `site/css/style.css`
- Create: `site/js/app.js`

**IMPORTANT:** Use the **frontend-design** skill for this task. The skill should create all 3 HTML files, the CSS file, and the shared JS. Pass it the following context:

> Build the HTML/CSS/JS foundation for a volleyball analytics static site. Dark theme dashboard.
>
> **Pages:** 3 HTML files — `site/index.html` (Overview), `site/players.html` (Players), `site/comparison.html` (Comparison).
>
> **Design reference:** NCVA Power League Dashboard style — dark navy background, polished typography, micro-interactions, CSS variables. The brainstorming mockups are in `.superpowers/brainstorm/18192-1775760145/content/overview-mockup.html` and `players-comparison-mockup.html`.
>
> **CSS (`site/css/style.css`):** Dark theme with CSS variables. Root variables: `--bg: #0f172a`, `--surface: #1e293b`, `--surface2: #273549`, `--border: #334155`, `--text: #f1f5f9`, `--muted: #94a3b8`, `--accent: #38bdf8`, `--green: #4ade80`, `--red: #f87171`, `--gold: #fbbf24`, `--radius: 8px`. System font stack. Card styles, KPI card styles, table styles with hover/striping, pill badges, nav bar with gradient, game state color-coded pills, W/L badges. Hover states with 0.15s transitions. Mobile breakpoint at 768px.
>
> **Navigation:** Horizontal top nav bar with gradient background. Logo "VB Analyzer" on left, tabs on right. Active tab gets accent color underline. Standard `<a>` links.
>
> **Shared JS (`site/js/app.js`):** Helper to highlight active nav tab based on current page. Utility function `async function loadJSON(path)` that fetches and returns parsed JSON.
>
> **Each HTML page** must include: Plotly.js CDN (`<script src="https://cdn.plot.ly/plotly-2.35.0.min.js"></script>`), `css/style.css`, `js/app.js`, and its own page-specific JS file (`js/overview.js`, `js/players.js`, or `js/comparison.js`). Each page has empty container divs with IDs that the page JS will populate (e.g., `<div id="kpi-row"></div>`, `<div id="progression-chart"></div>`, etc.).
>
> **Container IDs for index.html:** `kpi-row`, `progression-chart`, `attack-by-state-chart`, `pass-by-state-chart`, `game-state-definitions`, `game-results-table`, `sideout-by-phase-chart`
>
> **Container IDs for players.html:** `player-selector`, `player-kpis`, `clutch-comparison`, `player-game-state-chart`, `season-progression-chart`, `consistency-index`
>
> **Container IDs for comparison.html:** `player-multi-select`, `radar-chart`, `trend-chart`, `comparison-table`

- [ ] **Step 1: Invoke frontend-design skill with the context above**

The skill generates all HTML, CSS, and JS files.

- [ ] **Step 2: Verify the pages load in a browser**

Open `site/index.html` in a browser. Verify:
- Dark theme renders correctly
- Navigation bar shows all 3 tabs
- Links between pages work
- Container divs are present (empty is OK — JS not connected yet)

- [ ] **Step 3: Commit**

```bash
git add site/index.html site/players.html site/comparison.html site/css/style.css site/js/app.js
git commit -m "feat: add frontend shell with dark theme CSS and navigation"
```

---

## Task 4: Overview Page JavaScript

**Files:**
- Create: `site/js/overview.js`

This JS file loads `data/overview.json` and renders all Overview page content.

- [ ] **Step 1: Create site/js/overview.js**

```javascript
/* Overview page: load overview.json, render KPIs, charts, tables. */

document.addEventListener("DOMContentLoaded", async () => {
  const data = await loadJSON("data/overview.json");
  if (!data) return;

  renderKPIs(data.kpis);
  renderProgression(data.progression);
  renderAttackByState(data.attack_by_state);
  renderPassByState(data.pass_by_state);
  renderGameStateDefinitions();
  renderGameResults(data.game_results);
  renderSideoutByPhase(data.sideout_by_phase);
});

const PLOTLY_DARK = {
  paper_bgcolor: "transparent",
  plot_bgcolor: "transparent",
  font: { color: "#94a3b8", family: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif' },
  xaxis: { gridcolor: "#334155", zerolinecolor: "#334155" },
  yaxis: { gridcolor: "#334155", zerolinecolor: "#334155" },
  margin: { l: 50, r: 20, t: 40, b: 40 },
};

function renderKPIs(kpis) {
  const el = document.getElementById("kpi-row");
  const items = [
    { label: "Record", value: kpis.record, color: "var(--accent)" },
    { label: "Sideout %", value: kpis.sideout_pct + "%", color: "var(--green)" },
    { label: "Break Pt %", value: kpis.breakpoint_pct + "%", color: "var(--gold)" },
    { label: "Hitting Eff", value: kpis.hitting_eff.toFixed(3), color: "#f472b6" },
    { label: "Pass Avg", value: kpis.pass_avg.toFixed(3), color: "#a78bfa" },
  ];
  el.innerHTML = items.map(i => `
    <div class="kpi-card">
      <div class="kpi-value" style="color:${i.color}">${i.value}</div>
      <div class="kpi-label">${i.label}</div>
    </div>
  `).join("");
}

function renderProgression(progression) {
  const el = document.getElementById("progression-chart");
  const dates = progression.map(p => p.date);
  const traces = [
    { x: dates, y: progression.map(p => p.sideout_pct), name: "Sideout %", line: { color: "#4ade80" } },
    { x: dates, y: progression.map(p => p.hitting_eff), name: "Hitting Eff", yaxis: "y2", line: { color: "#38bdf8" } },
    { x: dates, y: progression.map(p => p.pass_avg), name: "Pass Avg", yaxis: "y3", line: { color: "#a78bfa" } },
  ];
  const layout = {
    ...PLOTLY_DARK,
    title: "Team Progression Over Season",
    height: 350,
    yaxis: { ...PLOTLY_DARK.yaxis, title: "Sideout %" },
    yaxis2: { title: "Hitting Eff", overlaying: "y", side: "right", gridcolor: "transparent", font: { color: "#38bdf8" } },
    yaxis3: { title: "Pass Avg", overlaying: "y", side: "right", position: 0.95, gridcolor: "transparent", font: { color: "#a78bfa" } },
    legend: { orientation: "h", y: -0.15 },
  };
  Plotly.newPlot(el, traces, layout, { responsive: true, displayModeBar: false });
}

const STATE_LABELS = {
  winning_big: "Winning Big",
  winning: "Winning",
  close: "Close",
  losing: "Losing",
  losing_big: "Losing Big",
};
const STATE_COLORS = {
  winning_big: "#4ade80",
  winning: "#86efac",
  close: "#e2e8f0",
  losing: "#fca5a5",
  losing_big: "#f87171",
};

function renderAttackByState(data) {
  const el = document.getElementById("attack-by-state-chart");
  const trace = {
    x: data.map(d => STATE_LABELS[d.situation]),
    y: data.map(d => d.hitting_eff),
    type: "bar",
    marker: { color: data.map(d => STATE_COLORS[d.situation]) },
    text: data.map(d => d.hitting_eff.toFixed(3)),
    textposition: "auto",
    textfont: { color: "#0f172a", size: 12 },
    hovertemplate: "%{x}<br>Eff: %{y:.3f}<br>Attempts: %{customdata}<extra></extra>",
    customdata: data.map(d => d.attempts),
  };
  Plotly.newPlot(el, [trace], {
    ...PLOTLY_DARK,
    title: "Attack Efficiency by Game State",
    height: 300,
    yaxis: { ...PLOTLY_DARK.yaxis, title: "Hitting Efficiency" },
  }, { responsive: true, displayModeBar: false });
}

function renderPassByState(data) {
  const el = document.getElementById("pass-by-state-chart");
  const trace = {
    x: data.map(d => STATE_LABELS[d.situation]),
    y: data.map(d => d.pass_avg),
    type: "bar",
    marker: { color: data.map(d => STATE_COLORS[d.situation]) },
    text: data.map(d => d.pass_avg.toFixed(3)),
    textposition: "auto",
    textfont: { color: "#0f172a", size: 12 },
    hovertemplate: "%{x}<br>Pass Avg: %{y:.3f}<br>Passes: %{customdata}<extra></extra>",
    customdata: data.map(d => d.total),
  };
  Plotly.newPlot(el, [trace], {
    ...PLOTLY_DARK,
    title: "Pass Average by Game State",
    height: 300,
    yaxis: { ...PLOTLY_DARK.yaxis, title: "Pass Average" },
  }, { responsive: true, displayModeBar: false });
}

function renderGameStateDefinitions() {
  const el = document.getElementById("game-state-definitions");
  const states = [
    { name: "Winning Big", desc: "leading by 5+", cls: "state-winning-big" },
    { name: "Winning", desc: "leading by 2-4", cls: "state-winning" },
    { name: "Close", desc: "within 1 point", cls: "state-close" },
    { name: "Losing", desc: "trailing by 2-4", cls: "state-losing" },
    { name: "Losing Big", desc: "trailing by 5+", cls: "state-losing-big" },
  ];
  el.innerHTML = `<div class="card"><h3 class="section-title">Game State Definitions</h3><div class="pill-row">` +
    states.map(s => `<span class="game-state-pill ${s.cls}"><strong>${s.name}</strong> — ${s.desc}</span>`).join("") +
    `</div></div>`;
}

function renderGameResults(results) {
  const el = document.getElementById("game-results-table");
  const sortState = { col: null, asc: true };

  function render(data) {
    el.innerHTML = `
      <table class="data-table">
        <thead>
          <tr>
            <th data-col="date" class="sortable">Date</th>
            <th data-col="opponent" class="sortable">Opponent</th>
            <th data-col="score" class="sortable">Score</th>
            <th data-col="result" class="sortable">Result</th>
          </tr>
        </thead>
        <tbody>
          ${data.map(r => `
            <tr>
              <td class="muted">${r.date}</td>
              <td>${r.opponent}</td>
              <td class="num">${r.sets_won}-${r.sets_lost}</td>
              <td><span class="badge badge-${r.result === 'W' ? 'win' : 'loss'}">${r.result}</span></td>
            </tr>
          `).join("")}
        </tbody>
      </table>`;

    el.querySelectorAll("th.sortable").forEach(th => {
      th.addEventListener("click", () => {
        const col = th.dataset.col;
        if (sortState.col === col) sortState.asc = !sortState.asc;
        else { sortState.col = col; sortState.asc = true; }
        const sorted = [...data].sort((a, b) => {
          let va, vb;
          if (col === "date") { va = a.date; vb = b.date; }
          else if (col === "opponent") { va = a.opponent; vb = b.opponent; }
          else if (col === "score") { va = a.sets_won; vb = b.sets_won; }
          else if (col === "result") { va = a.result; vb = b.result; }
          if (va < vb) return sortState.asc ? -1 : 1;
          if (va > vb) return sortState.asc ? 1 : -1;
          return 0;
        });
        render(sorted);
      });
    });
  }
  render(results);
}

function renderSideoutByPhase(data) {
  const el = document.getElementById("sideout-by-phase-chart");
  const order = ["early", "middle", "final"];
  const sorted = [...data].sort((a, b) => order.indexOf(a.phase) - order.indexOf(b.phase));
  const labels = { early: "Early (0-9)", middle: "Middle (10-19)", final: "Final (20+)" };
  const trace = {
    x: sorted.map(d => labels[d.phase] || d.phase),
    y: sorted.map(d => d.sideout_pct),
    type: "bar",
    marker: { color: ["#38bdf8", "#a78bfa", "#f472b6"] },
    text: sorted.map(d => d.sideout_pct.toFixed(1) + "%"),
    textposition: "auto",
    textfont: { color: "#0f172a", size: 12 },
    hovertemplate: "%{x}<br>SO%%: %{y:.1f}<br>Opps: %{customdata}<extra></extra>",
    customdata: sorted.map(d => d.opportunities),
  };
  Plotly.newPlot(el, [trace], {
    ...PLOTLY_DARK,
    title: "Sideout % by Game Phase",
    height: 300,
    yaxis: { ...PLOTLY_DARK.yaxis, title: "Sideout %" },
  }, { responsive: true, displayModeBar: false });
}
```

- [ ] **Step 2: Verify overview page renders in browser**

Open `site/index.html`. Verify: KPI cards display with values, progression chart shows lines, attack/pass by game state bar charts render, game results table is sortable, sideout by phase chart shows 3 bars, game state definitions display as pills.

Note: This needs to be served via a local HTTP server since `fetch()` won't work with `file://` protocol. Run: `cd site && python -m http.server 8080` then open `http://localhost:8080`.

- [ ] **Step 3: Commit**

```bash
git add site/js/overview.js
git commit -m "feat: add overview page JavaScript with all charts and tables"
```

---

## Task 5: Players Page JavaScript

**Files:**
- Create: `site/js/players.js`

- [ ] **Step 1: Create site/js/players.js**

```javascript
/* Players page: load players.json, render per-player stats with dropdown. */

let playersData = null;

document.addEventListener("DOMContentLoaded", async () => {
  playersData = await loadJSON("data/players.json");
  if (!playersData) return;

  renderPlayerSelector(playersData.player_list);
  if (playersData.player_list.length > 0) {
    renderPlayer(playersData.player_list[0]);
  }
});

const PLOTLY_DARK = {
  paper_bgcolor: "transparent",
  plot_bgcolor: "transparent",
  font: { color: "#94a3b8", family: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif' },
  xaxis: { gridcolor: "#334155", zerolinecolor: "#334155" },
  yaxis: { gridcolor: "#334155", zerolinecolor: "#334155" },
  margin: { l: 50, r: 20, t: 40, b: 40 },
};

const STATE_LABELS = {
  winning_big: "Winning Big", winning: "Winning", close: "Close",
  losing: "Losing", losing_big: "Losing Big",
};
const STATE_COLORS = {
  winning_big: "#4ade80", winning: "#86efac", close: "#e2e8f0",
  losing: "#fca5a5", losing_big: "#f87171",
};

function renderPlayerSelector(playerList) {
  const el = document.getElementById("player-selector");
  el.innerHTML = `
    <label class="section-label">Select Player</label>
    <select id="player-dropdown" class="dropdown">
      ${playerList.map(p => `<option value="${p}">${p}</option>`).join("")}
    </select>`;
  document.getElementById("player-dropdown").addEventListener("change", (e) => {
    renderPlayer(e.target.value);
  });
}

function renderPlayer(player) {
  const stats = playersData.stats[player];
  if (!stats) return;

  renderPlayerKPIs(player, stats);
  renderClutchComparison(player);
  renderPlayerGameState(player);
  renderSeasonProgression(player);
  renderConsistencyIndex(player);
}

function renderPlayerKPIs(player, stats) {
  const el = document.getElementById("player-kpis");
  const items = [
    { label: "Kills", value: stats.kills, color: "var(--accent)" },
    { label: "Hitting Eff", value: stats.hitting_eff.toFixed(3), color: "var(--green)" },
    { label: "Aces", value: stats.aces, color: "var(--gold)" },
    { label: "Digs", value: stats.digs, color: "#a78bfa" },
    { label: "Pass Avg", value: stats.pass_avg !== null ? stats.pass_avg.toFixed(3) : "N/A", color: "#f472b6" },
    { label: "Errors", value: stats.att_errors + stats.srv_errors, color: "var(--red)" },
  ];
  el.innerHTML = items.map(i => `
    <div class="kpi-card">
      <div class="kpi-value" style="color:${i.color}">${i.value}</div>
      <div class="kpi-label">${i.label}</div>
    </div>
  `).join("");
}

function renderClutchComparison(player) {
  const el = document.getElementById("clutch-comparison");
  const clutch = playersData.clutch[player];
  if (!clutch) { el.innerHTML = ""; return; }

  const metrics = [
    { label: "Hitting Eff", clutch: clutch.hitting_eff_clutch, normal: clutch.hitting_eff_non_clutch },
    { label: "Kill %", clutch: clutch.kill_pct_clutch, normal: clutch.kill_pct_non_clutch },
    { label: "Pass Avg", clutch: clutch.pass_avg_clutch, normal: clutch.pass_avg_non_clutch },
  ].filter(m => m.clutch !== null && m.normal !== null);

  if (metrics.length === 0) { el.innerHTML = ""; return; }

  el.innerHTML = `<div class="card">
    <h3 class="section-title">Clutch Performance</h3>
    <p class="section-subtitle">How they play when it matters most</p>
    <div class="clutch-bars">
      ${metrics.map(m => `
        <div class="clutch-metric">
          <div class="clutch-label">${m.label}</div>
          <div class="clutch-bar-row">
            <div class="clutch-bar clutch" style="flex:${Math.max(m.clutch, 0.01)}">${typeof m.clutch === "number" ? m.clutch.toFixed(3) : m.clutch}</div>
            <div class="clutch-bar normal" style="flex:${Math.max(m.normal, 0.01)}">${typeof m.normal === "number" ? m.normal.toFixed(3) : m.normal}</div>
          </div>
        </div>
      `).join("")}
      <div class="clutch-legend">
        <span><span class="legend-dot" style="background:var(--gold)"></span>Clutch</span>
        <span><span class="legend-dot" style="background:#475569"></span>Normal</span>
      </div>
    </div>
  </div>`;
}

function renderPlayerGameState(player) {
  const el = document.getElementById("player-game-state-chart");
  const states = playersData.game_state[player];
  if (!states || states.length === 0) { el.innerHTML = ""; return; }

  const traces = [
    {
      x: states.map(s => STATE_LABELS[s.situation]),
      y: states.map(s => s.hitting_eff),
      name: "Hitting Eff",
      type: "bar",
      marker: { color: "#38bdf8" },
      text: states.map(s => s.hitting_eff.toFixed(3)),
      textposition: "auto",
      textfont: { color: "#0f172a", size: 11 },
    },
    {
      x: states.map(s => STATE_LABELS[s.situation]),
      y: states.filter(s => s.pass_avg !== null).map(s => s.pass_avg),
      name: "Pass Avg",
      type: "bar",
      marker: { color: "#a78bfa" },
      text: states.filter(s => s.pass_avg !== null).map(s => s.pass_avg.toFixed(3)),
      textposition: "auto",
      textfont: { color: "#0f172a", size: 11 },
    },
  ];
  el.innerHTML = `<div class="card"><h3 class="section-title">Stats by Game State</h3><div id="player-game-state-plotly"></div></div>`;
  Plotly.newPlot("player-game-state-plotly", traces, {
    ...PLOTLY_DARK,
    barmode: "group",
    height: 300,
    legend: { orientation: "h", y: -0.15 },
  }, { responsive: true, displayModeBar: false });
}

function renderSeasonProgression(player) {
  const el = document.getElementById("season-progression-chart");
  const prog = playersData.progression[player];
  if (!prog || prog.length === 0) { el.innerHTML = ""; return; }

  const traces = [
    {
      x: prog.map(p => p.date), y: prog.map(p => p.hitting_eff_rolling),
      name: "Hitting Eff (Rolling)", mode: "lines+markers",
      line: { color: "#38bdf8" }, marker: { size: 5 },
    },
    {
      x: prog.map(p => p.date), y: prog.map(p => p.pass_avg_rolling),
      name: "Pass Avg (Rolling)", mode: "lines+markers", yaxis: "y2",
      line: { color: "#a78bfa" }, marker: { size: 5 },
    },
  ];
  el.innerHTML = `<div class="card"><h3 class="section-title">Season Progression</h3><div id="season-prog-plotly"></div></div>`;
  Plotly.newPlot("season-prog-plotly", traces, {
    ...PLOTLY_DARK,
    height: 350,
    yaxis: { ...PLOTLY_DARK.yaxis, title: "Hitting Eff" },
    yaxis2: { title: "Pass Avg", overlaying: "y", side: "right", gridcolor: "transparent" },
    legend: { orientation: "h", y: -0.15 },
  }, { responsive: true, displayModeBar: false });
}

function renderConsistencyIndex(player) {
  const el = document.getElementById("consistency-index");
  const cons = playersData.consistency[player];
  if (!cons) { el.innerHTML = ""; return; }

  const score = cons.consistency_score;
  const color = score >= 0.7 ? "var(--green)" : score >= 0.4 ? "var(--gold)" : "var(--red)";

  el.innerHTML = `<div class="card">
    <div style="display:flex;align-items:center;gap:12px;margin-bottom:8px">
      <h3 class="section-title" style="margin:0">Consistency Index</h3>
      <span class="pill" style="background:${color};color:#0f172a;font-weight:700">${score.toFixed(3)}</span>
    </div>
    <p class="muted" style="font-size:0.85rem">
      Std Dev: ${cons.eff_std_dev.toFixed(4)} · Avg Eff: ${cons.avg_eff.toFixed(3)} · Matches: ${cons.matches_with_attacks}
    </p>
  </div>`;
}
```

- [ ] **Step 2: Verify players page in browser**

Serve: `cd site && python -m http.server 8080`, open `http://localhost:8080/players.html`.

Verify: player dropdown works, KPI cards update on selection, clutch bars render, game state grouped bar chart shows, season progression chart shows, consistency badge appears.

- [ ] **Step 3: Commit**

```bash
git add site/js/players.js
git commit -m "feat: add players page JavaScript with all charts and interactivity"
```

---

## Task 6: Comparison Page JavaScript

**Files:**
- Create: `site/js/comparison.js`

- [ ] **Step 1: Create site/js/comparison.js**

```javascript
/* Comparison page: radar charts, trend comparison, stat table. */

let compData = null;
let playersData = null;
let selectedPlayers = [];

document.addEventListener("DOMContentLoaded", async () => {
  compData = await loadJSON("data/comparison.json");
  playersData = await loadJSON("data/players.json");
  if (!compData) return;

  renderMultiSelect();
  // Default: first 2 players
  if (compData.players.length >= 2) {
    selectedPlayers = compData.players.slice(0, 2).map(p => p.name);
    updateSelection();
  }
});

const PLOTLY_DARK = {
  paper_bgcolor: "transparent",
  plot_bgcolor: "transparent",
  font: { color: "#94a3b8", family: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif' },
  margin: { l: 50, r: 50, t: 40, b: 40 },
};

function renderMultiSelect() {
  const el = document.getElementById("player-multi-select");
  el.innerHTML = `
    <label class="section-label">Compare Players</label>
    <div id="player-pills" class="pill-row"></div>
    <select id="add-player-dropdown" class="dropdown" style="margin-top:8px">
      <option value="">+ Add player...</option>
      ${compData.players.map(p => `<option value="${p.name}">${p.name}</option>`).join("")}
    </select>`;

  document.getElementById("add-player-dropdown").addEventListener("change", (e) => {
    const name = e.target.value;
    if (name && !selectedPlayers.includes(name) && selectedPlayers.length < 6) {
      selectedPlayers.push(name);
      updateSelection();
    }
    e.target.value = "";
  });
}

function updateSelection() {
  // Render pills
  const pillsEl = document.getElementById("player-pills");
  pillsEl.innerHTML = selectedPlayers.map(name => {
    const p = compData.players.find(pl => pl.name === name);
    return `<span class="player-pill" style="border-color:${p.color};color:${p.color}">
      ${name} <span class="pill-remove" data-name="${name}">✕</span>
    </span>`;
  }).join("");

  pillsEl.querySelectorAll(".pill-remove").forEach(btn => {
    btn.addEventListener("click", () => {
      selectedPlayers = selectedPlayers.filter(n => n !== btn.dataset.name);
      updateSelection();
    });
  });

  if (selectedPlayers.length >= 2) {
    renderRadarChart();
    renderTrendChart();
    renderComparisonTable();
  } else {
    document.getElementById("radar-chart").innerHTML = '<p class="muted" style="padding:20px">Select at least 2 players to compare.</p>';
    document.getElementById("trend-chart").innerHTML = "";
    document.getElementById("comparison-table").innerHTML = "";
  }
}

function renderRadarChart() {
  const el = document.getElementById("radar-chart");
  const metrics = compData.radar_metrics;
  const labels = compData.radar_labels;

  const traces = selectedPlayers.map(name => {
    const p = compData.players.find(pl => pl.name === name);
    const values = metrics.map(m => p.normalized[m] || 0);
    // Close the polygon
    return {
      type: "scatterpolar",
      r: [...values, values[0]],
      theta: [...labels, labels[0]],
      fill: "toself",
      fillcolor: p.color + "20",
      line: { color: p.color, width: 2 },
      name: name,
    };
  });

  el.innerHTML = `<div class="card"><h3 class="section-title">Player Comparison Radar</h3><div id="radar-plotly"></div></div>`;
  Plotly.newPlot("radar-plotly", traces, {
    ...PLOTLY_DARK,
    polar: {
      bgcolor: "transparent",
      radialaxis: { visible: true, range: [0, 1], gridcolor: "#334155", linecolor: "#334155", tickfont: { color: "#94a3b8" } },
      angularaxis: { gridcolor: "#334155", linecolor: "#334155", tickfont: { color: "#94a3b8" } },
    },
    height: 450,
    legend: { orientation: "h", y: -0.1 },
    showlegend: true,
  }, { responsive: true, displayModeBar: false });
}

function renderTrendChart() {
  const el = document.getElementById("trend-chart");
  if (!playersData) { el.innerHTML = ""; return; }

  const traces = [];
  selectedPlayers.forEach(name => {
    const p = compData.players.find(pl => pl.name === name);
    const prog = playersData.progression[name];
    if (!prog) return;
    traces.push({
      x: prog.map(d => d.date),
      y: prog.map(d => d.hitting_eff_rolling),
      mode: "lines+markers",
      name: name,
      line: { color: p.color, width: 2 },
      marker: { size: 5 },
    });
  });

  if (traces.length === 0) { el.innerHTML = ""; return; }

  el.innerHTML = `<div class="card"><h3 class="section-title">Trend Comparison</h3><div id="trend-plotly"></div></div>`;
  Plotly.newPlot("trend-plotly", traces, {
    ...PLOTLY_DARK,
    height: 350,
    yaxis: { ...{ gridcolor: "#334155", zerolinecolor: "#334155" }, title: "Rolling Hitting Eff" },
    xaxis: { gridcolor: "#334155", zerolinecolor: "#334155" },
    legend: { orientation: "h", y: -0.15 },
  }, { responsive: true, displayModeBar: false });
}

function renderComparisonTable() {
  const el = document.getElementById("comparison-table");
  const metrics = [
    { key: "kills", label: "Kills", fmt: v => v },
    { key: "hitting_eff", label: "Hitting Eff", fmt: v => v !== null ? v.toFixed(3) : "N/A" },
    { key: "aces", label: "Aces", fmt: v => v },
    { key: "digs", label: "Digs", fmt: v => v },
    { key: "pass_avg", label: "Pass Avg", fmt: v => v !== null ? v.toFixed(3) : "N/A" },
  ];

  // Add consistency if available
  if (playersData) {
    metrics.push({
      key: "consistency",
      label: "Consistency",
      fmt: v => v !== null ? v.toFixed(3) : "N/A",
    });
  }

  // Get raw values
  const playerValues = {};
  selectedPlayers.forEach(name => {
    const p = compData.players.find(pl => pl.name === name);
    playerValues[name] = { ...p.raw };
    if (playersData && playersData.consistency[name]) {
      playerValues[name].consistency = playersData.consistency[name].consistency_score;
    }
  });

  // Find best per metric
  const best = {};
  metrics.forEach(m => {
    let bestVal = -Infinity;
    let bestPlayer = null;
    selectedPlayers.forEach(name => {
      const v = playerValues[name]?.[m.key];
      if (v !== null && v !== undefined && v > bestVal) {
        bestVal = v;
        bestPlayer = name;
      }
    });
    best[m.key] = bestPlayer;
  });

  const headerColors = selectedPlayers.map(name => {
    const p = compData.players.find(pl => pl.name === name);
    return p.color;
  });

  el.innerHTML = `<div class="card">
    <h3 class="section-title">Detailed Comparison</h3>
    <table class="data-table">
      <thead>
        <tr>
          <th>Metric</th>
          ${selectedPlayers.map((name, i) => `<th style="color:${headerColors[i]}">${name}</th>`).join("")}
        </tr>
      </thead>
      <tbody>
        ${metrics.map(m => `
          <tr>
            <td class="muted">${m.label}</td>
            ${selectedPlayers.map(name => {
              const v = playerValues[name]?.[m.key];
              const isBest = best[m.key] === name;
              return `<td class="num ${isBest ? 'best-value' : ''}">${m.fmt(v)}</td>`;
            }).join("")}
          </tr>
        `).join("")}
      </tbody>
    </table>
    <p class="muted" style="font-size:0.75rem;margin-top:8px">Best-in-class highlighted in <span style="color:var(--gold);font-weight:600">gold</span></p>
  </div>`;
}
```

- [ ] **Step 2: Verify comparison page in browser**

Serve: `cd site && python -m http.server 8080`, open `http://localhost:8080/comparison.html`.

Verify: multi-select dropdown works, player pills render with colors and ✕ removal, radar chart renders with overlapping polygons, trend chart shows multi-line comparison, stat table highlights best values in gold.

- [ ] **Step 3: Commit**

```bash
git add site/js/comparison.js
git commit -m "feat: add comparison page JavaScript with radar charts and stat table"
```

---

## Task 7: Add site/data/ to .gitignore and Update Existing .gitignore

**Files:**
- Modify: `.gitignore`

The generated JSON in `site/data/` should not be committed (it's derived from cached match data). Also add `.superpowers/` to gitignore.

- [ ] **Step 1: Update .gitignore**

Append these lines to the existing `.gitignore`:

```
# Generated static site data
site/data/

# Superpowers brainstorm sessions
.superpowers/
```

- [ ] **Step 2: Remove tracked generated files if any**

Run: `git rm -r --cached site/data/ 2>/dev/null; echo "done"`

This un-tracks the generated JSON files without deleting them locally.

- [ ] **Step 3: Commit**

```bash
git add .gitignore
git commit -m "chore: gitignore generated site data and superpowers sessions"
```

---

## Task 8: End-to-End Verification and Polish

**Files:**
- Possibly tweak: `site/css/style.css` (if any CSS classes referenced in JS are missing)

This task is a final integration check. No new code — just verifying the full flow.

- [ ] **Step 1: Clean build from scratch**

```bash
cd C:\Users\SongMu\documents\claudecode\vba\vb-analyzer
rm -rf site/data/
python generate_site.py
```

Expected: all 3 JSON files regenerated.

- [ ] **Step 2: Serve and verify all 3 pages**

```bash
cd site && python -m http.server 8080
```

Walk through:
1. **Overview** (`http://localhost:8080/`) — KPIs, progression chart, attack/pass by state, game state pills, game results (click headers to sort), sideout by phase
2. **Players** (`http://localhost:8080/players.html`) — switch players via dropdown, verify all sections update
3. **Comparison** (`http://localhost:8080/comparison.html`) — add/remove players, radar chart updates, trend lines update, table highlights best

- [ ] **Step 3: Fix any missing CSS classes**

If any JS-generated HTML references CSS classes not in `style.css`, add them. Common ones to check:
- `.kpi-card`, `.kpi-value`, `.kpi-label`
- `.card`, `.section-title`, `.section-subtitle`
- `.data-table`, `.sortable`, `.num`, `.muted`
- `.badge`, `.badge-win`, `.badge-loss`
- `.game-state-pill`, `.state-winning-big`, `.state-winning`, `.state-close`, `.state-losing`, `.state-losing-big`
- `.pill-row`, `.pill`
- `.dropdown`
- `.clutch-bars`, `.clutch-metric`, `.clutch-label`, `.clutch-bar-row`, `.clutch-bar.clutch`, `.clutch-bar.normal`, `.clutch-legend`, `.legend-dot`
- `.player-pill`, `.pill-remove`
- `.best-value`
- `.section-label`

- [ ] **Step 4: Verify GitHub Pages readiness**

The `site/` folder must work when served from a subdirectory. All paths in HTML/JS must be relative (not absolute). Check:
- CSS link: `css/style.css` (relative ✓)
- JS sources: `js/app.js`, `js/overview.js` etc. (relative ✓)
- JSON fetch: `data/overview.json` (relative ✓)
- Nav links: `index.html`, `players.html`, `comparison.html` (relative ✓)

- [ ] **Step 5: Final commit**

```bash
git add -A site/
git commit -m "feat: complete static site with all 3 pages ready for GitHub Pages"
```
