/* ============================================================
   13-2 Statistical Deep Dive — Game Detail Page Logic
   ============================================================ */

// ── Module State ─────────────────────────────────────────────
let _gamesData = null;      // Full games.json payload
let _currentGameId = null;  // Currently selected video_id

// ── Entry Point ──────────────────────────────────────────────
async function initPage() {
  _gamesData = await loadJSON("games.json");
  if (!_gamesData || !_gamesData.game_list || !_gamesData.game_list.length) {
    const main = document.querySelector(".main-content");
    if (main) main.innerHTML =
      '<p style="color:var(--red);padding:2rem">Failed to load games data.</p>';
    return;
  }

  renderGameSelector(_gamesData.game_list);
}

document.addEventListener("DOMContentLoaded", initPage);
window.addEventListener("dataset-changed", initPage);

// ── 1. Game Selector ─────────────────────────────────────────
function renderGameSelector(gameList) {
  const container = document.getElementById("game-selector");
  if (!container) return;

  const select = document.createElement("select");
  select.id = "game-dropdown";
  select.className = "dropdown";

  gameList.forEach(g => {
    const opt = document.createElement("option");
    opt.value = g.video_id;
    const score = `${g.sets_won}–${g.sets_lost}`;
    opt.textContent = `${g.date} — ${g.title} (${g.result} ${score})`;
    select.appendChild(opt);
  });

  select.addEventListener("change", () => {
    loadGame(select.value);
  });

  // Clear previous content except the label, then append
  const existingLabel = container.querySelector("label");
  container.innerHTML = "";
  if (existingLabel) container.appendChild(existingLabel);
  container.appendChild(select);

  // Auto-load first game
  if (gameList.length > 0) {
    loadGame(gameList[0].video_id);
  }
}

// ── Load & Render Game ────────────────────────────────────────
function loadGame(videoId) {
  _currentGameId = videoId;
  const gameDetail = _gamesData.games && _gamesData.games[videoId];

  if (!gameDetail) {
    // Game detail not available — render basic KPIs from game_list
    const summary = _gamesData.game_list.find(g => g.video_id === videoId);
    if (summary) renderGameKPIs(summary);
    clearCharts();
    return;
  }

  renderGameKPIs(gameDetail);
  renderMomentumChart(gameDetail.momentum || []);
  renderWinProbChart(gameDetail.momentum || []);
  renderBoxScores(gameDetail.box_scores || {});
}

function clearCharts() {
  ["momentum-chart", "win-prob-chart", "box-scores"].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.innerHTML = '<p style="color:#64748b;padding:1rem">No detail data available for this game.</p>';
  });
}

// ── 2. Game KPIs ─────────────────────────────────────────────
function renderGameKPIs(game) {
  const container = document.getElementById("game-kpis");
  if (!container) return;

  const resultClass = game.result === "W" ? "green" : "red";
  const score = `${game.sets_won}–${game.sets_lost}`;
  const sideoutVal = game.sideout_pct != null ? Number(game.sideout_pct).toFixed(1) + "%" : "—";
  const hittingVal = game.hitting_eff != null ? Number(game.hitting_eff).toFixed(3) : "—";
  const passVal    = game.pass_avg    != null ? Number(game.pass_avg).toFixed(2)    : "—";

  const cards = [
    {
      label: "Result",
      value: `<span class="badge badge-${game.result === "W" ? "win" : "loss"}">${game.result}</span>`,
      colorClass: resultClass,
    },
    { label: "Set Score",   value: score,       colorClass: "" },
    { label: "Sideout %",   value: sideoutVal,  colorClass: "" },
    { label: "Hitting Eff", value: hittingVal,  colorClass: "" },
    { label: "Pass Avg",    value: passVal,      colorClass: "" },
  ];

  container.innerHTML = cards.map(c => `
    <div class="kpi-card${c.colorClass ? " " + c.colorClass : ""}">
      <div class="kpi-value">${c.value}</div>
      <div class="kpi-label">${c.label}</div>
    </div>
  `).join("");
}

// ── 3. Momentum Chart ─────────────────────────────────────────
function renderMomentumChart(momentum) {
  const el = document.getElementById("momentum-chart");
  if (!el) return;

  if (!momentum.length) {
    el.innerHTML = '<p style="color:#64748b;padding:1rem">No momentum data available.</p>';
    return;
  }

  // Group by set
  const sets = groupBySet(momentum);
  const setNums = Object.keys(sets).sort((a, b) => Number(a) - Number(b));
  const numSets = setNums.length;

  const traces = [];
  const shapes = [];
  const annotations = [];

  const SET_COLORS = ["#4ade80", "#38bdf8", "#a78bfa", "#fb923c"];

  setNums.forEach((setNum, idx) => {
    const rallies = sets[setNum];
    const yAxis = idx === 0 ? "y" : `y${idx + 1}`;
    const xAxis = idx === 0 ? "x" : `x${idx + 1}`;

    const x = rallies.map(r => r.rally_num);
    const y = rallies.map(r => r.score_diff);

    const color = SET_COLORS[idx % SET_COLORS.length];

    traces.push({
      x,
      y,
      name: `Set ${setNum}`,
      type: "scatter",
      mode: "lines",
      line: { color, width: 2 },
      xaxis: xAxis,
      yaxis: yAxis,
      hovertemplate:
        `<b>Set ${setNum} — Rally %{x}</b><br>` +
        "Score Diff: %{y}<extra></extra>",
    });

    // Detect 3+ point runs and add shaded rectangles
    const runShapes = detectRuns(rallies);
    runShapes.forEach(s => {
      shapes.push(Object.assign({}, s, { xref: xAxis, yref: yAxis }));
    });

    // Zero line annotation label
    annotations.push({
      xref: "paper",
      yref: yAxis,
      x: 0,
      y: 0,
      text: "Tied",
      showarrow: false,
      font: { color: "#64748b", size: 10 },
      xanchor: "right",
    });
  });

  // Build subplot layout
  const subplotLayout = buildSubplotLayout(numSets, "Score Difference", "momentum");

  const layout = Object.assign({}, subplotLayout, {
    shapes,
    annotations,
    title: { text: "", font: { size: 13, color: "#94a3b8" } },
    showlegend: numSets > 1,
    legend: { orientation: "h", y: 1.05, font: { color: "#94a3b8" }, bgcolor: "rgba(0,0,0,0)" },
  });

  Plotly.newPlot(el, traces, layout, PLOTLY_CONFIG);
}

// ── 4. Win Probability Chart ──────────────────────────────────
function renderWinProbChart(momentum) {
  const el = document.getElementById("win-prob-chart");
  if (!el) return;

  if (!momentum.length) {
    el.innerHTML = '<p style="color:#64748b;padding:1rem">No win probability data available.</p>';
    return;
  }

  const sets = groupBySet(momentum);
  const setNums = Object.keys(sets).sort((a, b) => Number(a) - Number(b));

  const SET_COLORS = ["#4ade80", "#38bdf8", "#a78bfa", "#fb923c"];

  const traces = [];

  setNums.forEach((setNum, idx) => {
    const rallies = sets[setNum];
    const color = SET_COLORS[idx % SET_COLORS.length];

    traces.push({
      x: rallies.map(r => r.rally_num),
      y: rallies.map(r => r.win_prob),
      name: `Set ${setNum}`,
      type: "scatter",
      mode: "lines",
      line: { color, width: 2 },
      hovertemplate:
        `<b>Set ${setNum} — Rally %{x}</b><br>` +
        "Win Prob: %{y:.1f}%<extra></extra>",
    });
  });

  // 50% reference line (uses x-range paper coords)
  const fiftyLine = {
    type: "line",
    xref: "paper",
    yref: "y",
    x0: 0,
    x1: 1,
    y0: 50,
    y1: 50,
    line: { color: "rgba(148,163,184,0.4)", width: 1, dash: "dash" },
  };

  const layout = darkLayout({
    height: 320,
    shapes: [fiftyLine],
    yaxis: {
      title: { text: "Win Probability (%)", font: { size: 11 } },
      ticksuffix: "%",
      range: [0, 100],
    },
    xaxis: {
      title: { text: "Rally Number", font: { size: 11 } },
    },
    showlegend: setNums.length > 1,
    legend: { orientation: "h", y: 1.1, font: { color: "#94a3b8" }, bgcolor: "rgba(0,0,0,0)" },
    margin: { t: 32, r: 16, b: 48, l: 56 },
  });

  Plotly.newPlot(el, traces, layout, PLOTLY_CONFIG);
}

// ── 5. Box Scores ─────────────────────────────────────────────
function renderBoxScores(boxScores) {
  const container = document.getElementById("box-scores");
  if (!container) return;

  const setKeys = Object.keys(boxScores).sort((a, b) => Number(a) - Number(b));

  if (!setKeys.length) {
    container.innerHTML = '<p style="color:#64748b;padding:1rem">No box score data available.</p>';
    return;
  }

  // Build pill buttons
  const pillsHtml = setKeys.map((k, i) => `
    <button
      class="pill-btn${i === 0 ? " active" : ""}"
      onclick="switchBoxTab('${k}')"
      id="box-tab-${k}"
    >Set ${k}</button>
  `).join("");

  // Build tables (one per set)
  const tablesHtml = setKeys.map((k, i) => {
    const players = boxScores[k] || [];
    const rows = players.map(p => `
      <tr>
        <td>${p.player || "—"}</td>
        <td class="num">${p.kills    ?? "—"}</td>
        <td class="num">${p.errors   ?? "—"}</td>
        <td class="num">${p.attempts ?? "—"}</td>
        <td class="num">${p.hitting_eff != null ? Number(p.hitting_eff).toFixed(3) : "—"}</td>
        <td class="num">${p.aces ?? "—"}</td>
        <td class="num">${p.digs ?? "—"}</td>
      </tr>
    `).join("");

    return `
      <div class="box-score-panel" id="box-panel-${k}" style="display:${i === 0 ? "block" : "none"}">
        <table class="data-table">
          <thead>
            <tr>
              <th>Player</th>
              <th class="num">Kills</th>
              <th class="num">Errors</th>
              <th class="num">Attempts</th>
              <th class="num">Hitting Eff</th>
              <th class="num">Aces</th>
              <th class="num">Digs</th>
            </tr>
          </thead>
          <tbody>${rows}</tbody>
        </table>
      </div>
    `;
  }).join("");

  container.innerHTML = `
    <div class="pill-row" style="margin-bottom:1rem">${pillsHtml}</div>
    ${tablesHtml}
  `;
}

// Tab switching — must be globally accessible (called from inline onclick)
function switchBoxTab(setKey) {
  // Hide all panels
  document.querySelectorAll(".box-score-panel").forEach(panel => {
    panel.style.display = "none";
  });
  // Remove active from all tab buttons
  document.querySelectorAll(".pill-btn").forEach(btn => {
    btn.classList.remove("active");
  });

  // Show selected
  const panel = document.getElementById(`box-panel-${setKey}`);
  if (panel) panel.style.display = "block";
  const btn = document.getElementById(`box-tab-${setKey}`);
  if (btn) btn.classList.add("active");
}

// ── Helpers ───────────────────────────────────────────────────

// Group momentum array by set_number
function groupBySet(momentum) {
  const sets = {};
  momentum.forEach(r => {
    const k = String(r.set_number);
    if (!sets[k]) sets[k] = [];
    sets[k].push(r);
  });
  return sets;
}

// Detect 3+ point scoring runs and return Plotly shape objects
// (caller must attach xref/yref)
function detectRuns(rallies) {
  const shapes = [];
  if (!rallies.length) return shapes;

  let runStart = 0;
  let runWinner = rallies[0].point_winner;
  let runLen = 1;

  function pushShape(winner, startIdx, endIdx) {
    if (runLen < 3 || !winner) return;
    const x0 = rallies[startIdx].rally_num - 0.5;
    const x1 = rallies[endIdx].rally_num   + 0.5;
    shapes.push({
      type: "rect",
      x0,
      x1,
      y0: -30,
      y1: 30,
      fillcolor: winner === "us"
        ? "rgba(74,222,128,0.1)"
        : "rgba(248,113,113,0.1)",
      line: { width: 0 },
      layer: "below",
    });
  }

  for (let i = 1; i < rallies.length; i++) {
    const winner = rallies[i].point_winner;
    if (winner === runWinner && winner) {
      runLen++;
    } else {
      pushShape(runWinner, runStart, i - 1);
      runStart  = i;
      runWinner = winner;
      runLen    = 1;
    }
  }
  // Final run
  pushShape(runWinner, runStart, rallies.length - 1);

  return shapes;
}

// Build a stacked-subplot layout for N sets
function buildSubplotLayout(numSets, yAxisLabel, chartType) {
  const gap = 0.08;
  const totalGap = gap * (numSets - 1);
  const panelH = numSets > 0 ? (1 - totalGap) / numSets : 1;

  const baseLayout = {
    paper_bgcolor: "rgba(0,0,0,0)",
    plot_bgcolor:  "rgba(0,0,0,0)",
    font: {
      family: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
      color: "#94a3b8",
      size: 12,
    },
    height: Math.max(300, numSets * 220),
    margin: { t: 32, r: 16, b: 48, l: 56 },
    hoverlabel: {
      bgcolor: "#1e293b",
      bordercolor: "#334155",
      font: { color: "#f1f5f9", size: 13 },
    },
  };

  for (let i = 0; i < numSets; i++) {
    const bottom = 1 - (i + 1) * panelH - i * gap;
    const top    = bottom + panelH;
    const domain = [Math.max(0, bottom), Math.min(1, top)];

    const xKey = i === 0 ? "xaxis"  : `xaxis${i + 1}`;
    const yKey = i === 0 ? "yaxis"  : `yaxis${i + 1}`;
    const anchor = i === 0 ? "y"    : `y${i + 1}`;

    baseLayout[xKey] = {
      gridcolor:    "rgba(51,65,85,0.5)",
      zerolinecolor:"rgba(51,65,85,0.5)",
      tickfont:     { color: "#94a3b8" },
      title:        i === numSets - 1
        ? { text: "Rally Number", font: { size: 11 } }
        : {},
    };
    baseLayout[yKey] = {
      domain,
      title:        { text: `Set ${i + 1}`, font: { size: 10, color: "#94a3b8" } },
      gridcolor:    "rgba(51,65,85,0.5)",
      zerolinecolor:"rgba(148,163,184,0.3)",
      zerolinewidth: 1,
      tickfont:     { color: "#94a3b8" },
      anchor:       "x" + (i === 0 ? "" : String(i + 1)),
    };

    if (i > 0) {
      baseLayout[xKey].anchor = anchor;
    }
  }

  return baseLayout;
}
