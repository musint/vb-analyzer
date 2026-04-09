# Volleyball Stat Analyzer — Design Spec

## Overview

A local web dashboard (Dash/Plotly) for analyzing NorCal 13-2 Blue volleyball data from Hudl Balltime. Single-user tool for the head coach. Provides standard stats, clutch performance analysis, player consistency and progression tracking, scoring run detection with trigger analysis, court zone heatmaps, and win probability modeling.

## Data Source

- **Primary**: Balltime API at `backend.balltime.com` via Playwright-based authentication
- **Cache**: JSON file (`data/cache/matches.json`) for instant startup
- **Refresh**: "Refresh from Hudl" button triggers live import (~2 min), saves to cache
- **Dataset**: ~55 matches, ~31,000 individual actions, ~5,100 rallies for the 2025-2026 season
- **Per action**: type, player, team, quality, rally_id, speed_mph, src/dest zones, coordinates, first_ball_side_out, in_system, touch_position

## Tech Stack

- Python 3.12+
- Dash 2.x + Plotly for interactive UI and charts
- Pandas for data processing
- Playwright for Hudl/Balltime authentication
- httpx for Balltime API calls

## Project Structure

```
vb-analyzer/
  app.py                  # Dash app entry, page routing, layout
  data/
    loader.py             # Load from cache or live Balltime, save cache
    balltime.py           # Balltime client + match import (adapted from mcp-hudl)
    cache/                # JSON cache files (gitignored)
  analytics/
    core.py               # Rally reconstruction, running scores, score classification
    player.py             # Player-level stats, clutch, consistency, progression
    team.py               # Team-level: SO%, BP%, scoring runs, run triggers
    rotation.py           # Rotation stats from Balltime generate-multi-video-stats API
    advanced.py           # Expected SO%, serve pressure, win probability, momentum
  pages/
    overview.py           # Season dashboard landing page
    player_detail.py      # Single-player deep dive
    game_detail.py        # Single-game breakdown with momentum chart
    runs.py               # Scoring run visualization & trigger analysis
    zones.py              # Court heatmaps for attack and serve receive
    comparison.py         # Player comparison with radar charts
  components/
    charts.py             # Reusable Plotly figure builders
    tables.py             # Reusable DataTable builders
    filters.py            # Sidebar filter components (player, game, phase, situation)
    court.py              # Court diagram component for heatmaps
  requirements.txt
  .gitignore
```

## Analytics Tiers

### Tier 1: Standard Metrics

- **Hitting efficiency**: (K - E) / TA per player, per game, per situation
- **Kill %**: K / TA
- **Serve stats**: ace %, error %, serve rating
- **Pass stats**: average quality (0-3 scale), distribution by rating
- **Digs, blocks, assists**
- **Sideout % (SO%)**: points won when receiving / total receive rallies
- **Break Point % (BP%)**: points won when serving / total serve rallies
- **Per-game results**: with set scores from Balltime video metadata

### Tier 2: Coach-Specific Metrics

#### Clutch Performance
- **Definition**: "Clutch" = both teams' scores above 20 in sets 1-2, or both above 10 in set 3
- Per-player stats (attack, serve, pass, dig) split into clutch vs non-clutch
- **Clutch Rating**: composite metric = (clutch_hitting_eff - overall_hitting_eff) + adjustments for serve/pass/dig. Positive = player steps up. Negative = player fades.

#### Consistency Index
- Per player, compute standard deviation of per-match hitting efficiency (and pass avg, serve rating)
- **Consistency Score** = 1 / (1 + std_dev). Range 0-1, higher = more consistent.
- Displayed as colored indicator: green (>0.7), yellow (0.4-0.7), red (<0.4)
- Per-game dot plot showing individual match values vs the average

#### Season Progression
- Rolling 5-game averages for hitting eff, pass avg, serve rating
- Trendlines plotted chronologically by match date
- Shows who is improving, declining, or steady

#### Run Initiators
- For every 3+ point run by our team: identify which player scored the first point and how (attack kill, serve ace, block, opponent error forced by whom)
- **Run Starter Leaderboard**: players ranked by run initiation frequency
- **Run Killer Leaderboard**: players whose errors most often start opponent runs
- Both displayed with action type breakdown (kill 39%, opp serve error 25%, etc.)

### Tier 3: Advanced / Professional Metrics

#### Expected Sideout by Pass Quality
- After a 3-pass, what is our sideout %? After a 2-pass? 1-pass? 0-pass?
- Shows conversion efficiency relative to pass quality
- Answers: "are we wasting good passes?"

#### Serve Pressure Index
- Per server: % of serves resulting in opponent error OR 0/1 pass
- Shows who creates real pressure vs who just gets the ball in play

#### In-System vs Out-of-System Attack Efficiency
- Uses the `in_system` flag from Balltime
- Shows which hitters handle bad passes and maintain efficiency out of system

#### Zone Heatmaps
- Court diagram (zones 1-6) colored by attack kill % or efficiency
- Second court for serve receive quality by zone
- Interactive: click zone to drill into players and combos

#### Momentum Tracker
- Per-set running score differential chart
- Color bands highlighting scoring runs (green = ours, red = opponent)
- Shows where momentum swings happen within each set

#### Win Probability Model
- Historical probability of winning a set from each score state (e.g., 18-15)
- Built from all season data (~5,100 rallies)
- Plotted as a curve through each set in the game detail view

## Pages

### Page 1: Season Overview (landing page)
- Record card (W-L), total sets/rallies
- KPI row: SO%, BP%, hitting eff, pass avg, serve rating
- Per-game results table (sortable, set scores, mini sparklines)
- Season trend chart: rolling 5-game SO% and hitting eff
- Sidebar filters: date range, opponent

### Page 2: Player Dashboard
- Player selector dropdown
- Stat card row: kills, eff, aces, pass avg, digs, pts +/-
- Clutch comparison: side-by-side bars (clutch vs non-clutch)
- Consistency gauge: colored indicator + per-game dot plot
- Season progression: rolling 5-game trendlines
- Score situation breakdown: stacked bars across winning big / winning / close / losing / losing big
- Game phase breakdown: early / middle / final stretch stats
- Run initiator stats: starts our runs vs triggers opponent runs

### Page 3: Scoring Runs
- Run timeline: horizontal chart per set with colored run bands, clickable
- Run starter leaderboard table
- Run killer leaderboard table
- Trigger breakdown: bar chart of what starts runs
- Run context: game phase and score situation when runs happen

### Page 4: Game Detail
- Game selector dropdown
- Momentum chart: running score diff per set with run bands
- Set-by-set box score: full player stat table per set
- Win probability curve: historical probability line through match
- Rally-by-rally log: expandable, filterable table

### Page 5: Court Zones
- Interactive court diagram: attack zones colored by kill %/efficiency
- Click zone to see players and combos attacking from there
- Second court: serve receive quality by zone
- Filterable by player, game, situation

### Page 6: Player Comparison
- Select 2-4 players
- Radar chart: overlaid eff, pass avg, serve rating, consistency, clutch rating
- Side-by-side stat tables
- Overlaid progression trendlines

## Data Flow

1. **Startup**: `loader.py` checks for `data/cache/matches.json`. If found, loads instantly.
2. **Refresh**: User clicks "Refresh from Hudl". `balltime.py` launches Playwright, authenticates, calls `library/videos` and `library/actions-export` for each match video, saves to cache.
3. **Processing**: `analytics/core.py` reconstructs rallies, running scores, classifies score situations and game phases. Other analytics modules compute their metrics from these DataFrames.
4. **Rendering**: Each page module queries the analytics objects and builds Plotly figures + DataTables.

## Clutch Definition — Precise

- Sets 1 and 2 (played to 25): clutch = both teams' scores >= 20
- Set 3+ / tiebreak (played to 15): clutch = both teams' scores >= 10
- Applied per-rally: a rally is "clutch" if the scores at that moment meet the threshold

## Score Situation Categories

- **Winning Big**: our lead >= 5
- **Winning**: our lead 2-4
- **Close**: difference -1 to +1
- **Losing**: behind 2-4
- **Losing Big**: behind >= 5

## Game Phase Categories

Based on the higher of the two teams' scores at that moment:
- **Early**: max score 0-9
- **Middle**: max score 10-19
- **Final Stretch**: max score 20+

## Run Detection

- A "run" = 3 or more consecutive points scored by the same team
- Tracked separately for our team and opponent
- Each run records: starting score, ending score, set number, game phase, which player/action initiated it

## Validation

Stats generated by the analytics engine must match the Hudl CSV export (`Export - Stats (1).csv`) for aggregate player totals. This was validated at 100% match in the MCP project.

## Sources

Research that informed the metrics design:
- [Advanced Volleyball Metrics That Drive D3 Success](https://insidehitter.com/2025/03/09/advanced-volleyball-metrics-that-drive-d3-success/)
- [3 Stats that Directly Apply to Team Performance (JVA)](https://jvavolleyball.org/3-stats-that-directly-apply-to-team-performance/)
- [Volleyball Analytics with R: Sideout Efficiency, Serve Pressure, Heatmaps](https://www.r-bloggers.com/2026/01/volleyball-analytics-with-r-the-complete-guide-to-match-data-sideout-efficiency-serve-pressure-heatmaps-and-predictive-models/)
- [Hudl Volleymetrics — Professional Analytics](https://www.hudl.com/products/volleymetrics)
- [Italian Women's League Analytics Toolbox (Springer)](https://link.springer.com/article/10.1186/s40537-025-01284-6)
- [How to Use Stats to Improve Volleyball Rotations](https://www.rotate123.com/how-to-use-stats-to-improve-volleyball-rotations.html)
