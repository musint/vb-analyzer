/* ============================================================
   VB Analyzer — Overview Page Logic
   ============================================================ */

const STATE_LABELS = {
  winning_big: "Winning Big",
  winning:     "Winning",
  close:       "Close",
  losing:      "Losing",
  losing_big:  "Losing Big",
};

const STATE_COLORS = {
  winning_big: "#4ade80",
  winning:     "#86efac",
  close:       "#e2e8f0",
  losing:      "#fca5a5",
  losing_big:  "#f87171",
};

// ── Entry Point ─────────────────────────────────────────────
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
  if (data.expected_sideout) renderExpectedSideout(data.expected_sideout);
});

// ── 1. KPI Row ───────────────────────────────────────────────
function renderKPIs(kpis) {
  const container = document.getElementById("kpi-row");
  if (!container) return;

  const cards = [
    { label: "Record",       value: kpis.record,                          colorClass: "" },
    { label: "Sideout %",    value: fmtNum(kpis.sideout_pct, 1) + "%",   colorClass: "green" },
    { label: "Break Pt %",   value: fmtNum(kpis.breakpoint_pct, 1) + "%", colorClass: "gold" },
    { label: "Hitting Eff",  value: fmtNum(kpis.hitting_eff, 3),          colorClass: "" },
    { label: "Pass Avg",     value: fmtNum(kpis.pass_avg, 2),             colorClass: "" },
  ];

  container.innerHTML = cards.map(c => `
    <div class="kpi-card${c.colorClass ? " " + c.colorClass : ""}">
      <div class="kpi-value">${c.value}</div>
      <div class="kpi-label">${c.label}</div>
    </div>
  `).join("");
}

// ── 2. Team Progression Chart ─────────────────────────────────
function renderProgression(progression) {
  const el = document.getElementById("progression-chart");
  if (!el || !progression || !progression.length) return;

  // Build x labels: combine date + short title
  const x = progression.map(d => {
    const date = d.date || "";
    const shortTitle = (d.title || "").replace(/ - Game$/, "").substring(0, 20);
    return `${date}<br>${shortTitle}`;
  });

  const traceSideout = {
    x,
    y: progression.map(d => d.sideout_pct),
    name: "Sideout %",
    type: "scatter",
    mode: "lines+markers",
    line: { color: "#4ade80", width: 2 },
    marker: { color: "#4ade80", size: 5 },
    hovertemplate: "<b>%{text}</b><br>Sideout: %{y:.1f}%<extra></extra>",
    text: progression.map(d => d.title || ""),
  };

  const traceHitting = {
    x,
    y: progression.map(d => d.hitting_eff),
    name: "Hitting Eff",
    type: "scatter",
    mode: "lines+markers",
    yaxis: "y2",
    line: { color: "#38bdf8", width: 2 },
    marker: { color: "#38bdf8", size: 5 },
    hovertemplate: "<b>%{text}</b><br>Hitting Eff: %{y:.3f}<extra></extra>",
    text: progression.map(d => d.title || ""),
  };

  const tracePass = {
    x,
    y: progression.map(d => d.pass_avg),
    name: "Pass Avg",
    type: "scatter",
    mode: "lines+markers",
    yaxis: "y2",
    line: { color: "#a78bfa", width: 2 },
    marker: { color: "#a78bfa", size: 5 },
    hovertemplate: "<b>%{text}</b><br>Pass Avg: %{y:.2f}<extra></extra>",
    text: progression.map(d => d.title || ""),
  };

  const layout = darkLayout({
    xaxis: {
      tickangle: -45,
      tickfont: { size: 10 },
    },
    yaxis: {
      title: { text: "Sideout %", font: { color: "#4ade80", size: 11 } },
      ticksuffix: "%",
      range: [0, 100],
    },
    yaxis2: {
      title: { text: "Hitting Eff / Pass Avg", font: { color: "#94a3b8", size: 11 } },
      overlaying: "y",
      side: "right",
      gridcolor: "rgba(51,65,85,0.2)",
      tickfont: { color: "#94a3b8" },
    },
    legend: { orientation: "h", x: 0, y: 1.12 },
    margin: { t: 40, r: 60, b: 80, l: 56 },
  });

  Plotly.newPlot(el, [traceSideout, traceHitting, tracePass], layout, PLOTLY_CONFIG);
}

// ── 3. Attack by Game State Chart ─────────────────────────────
function renderAttackByState(attackByState) {
  const el = document.getElementById("attack-by-state-chart");
  if (!el || !attackByState || !attackByState.length) return;

  const x = attackByState.map(d => STATE_LABELS[d.situation] || d.situation);
  const y = attackByState.map(d => d.hitting_eff);
  const colors = attackByState.map(d => STATE_COLORS[d.situation] || "#94a3b8");

  const trace = {
    x,
    y,
    type: "bar",
    marker: { color: colors, opacity: 0.85 },
    hovertemplate: "<b>%{x}</b><br>Hitting Eff: %{y:.3f}<extra></extra>",
  };

  const layout = darkLayout({
    yaxis: {
      title: { text: "Hitting Efficiency", font: { size: 11 } },
      zeroline: true,
      zerolinecolor: "rgba(148,163,184,0.4)",
      zerolinewidth: 1,
    },
    xaxis: { tickfont: { size: 11 } },
    margin: { t: 24, r: 16, b: 48, l: 56 },
  });

  Plotly.newPlot(el, [trace], layout, PLOTLY_CONFIG);
}

// ── 4. Pass by Game State Chart ───────────────────────────────
function renderPassByState(passByState) {
  const el = document.getElementById("pass-by-state-chart");
  if (!el || !passByState || !passByState.length) return;

  const x = passByState.map(d => STATE_LABELS[d.situation] || d.situation);
  const y = passByState.map(d => d.pass_avg);
  const colors = passByState.map(d => STATE_COLORS[d.situation] || "#94a3b8");

  const trace = {
    x,
    y,
    type: "bar",
    marker: { color: colors, opacity: 0.85 },
    hovertemplate: "<b>%{x}</b><br>Pass Avg: %{y:.2f}<extra></extra>",
  };

  const layout = darkLayout({
    yaxis: {
      title: { text: "Pass Average", font: { size: 11 } },
      range: [0, 3],
    },
    xaxis: { tickfont: { size: 11 } },
    margin: { t: 24, r: 16, b: 48, l: 56 },
  });

  Plotly.newPlot(el, [trace], layout, PLOTLY_CONFIG);
}

// ── 5. Game State Definitions ─────────────────────────────────
function renderGameStateDefinitions() {
  const container = document.getElementById("game-state-definitions");
  if (!container) return;

  const states = [
    { key: "winning_big", cssClass: "state-winning-big", label: "Winning Big", desc: "Leading 5+" },
    { key: "winning",     cssClass: "state-winning",     label: "Winning",     desc: "Leading 2-4" },
    { key: "close",       cssClass: "state-close",       label: "Close",       desc: "Within 1 pt" },
    { key: "losing",      cssClass: "state-losing",      label: "Losing",      desc: "Trailing 2-4" },
    { key: "losing_big",  cssClass: "state-losing-big",  label: "Losing Big",  desc: "Trailing 5+" },
  ];

  container.innerHTML = `
    <div class="pill-row">
      ${states.map(s => `
        <span class="game-state-pill ${s.cssClass}">
          ${s.label} <span style="opacity:0.7;font-weight:400;margin-left:4px;">(${s.desc})</span>
        </span>
      `).join("")}
    </div>
  `;
}

// ── 6. Game Results Table (sortable) ──────────────────────────
function renderGameResults(gameResults) {
  const container = document.getElementById("game-results-table");
  if (!container || !gameResults || !gameResults.length) return;

  // Working copy we can re-sort
  let rows = gameResults.map((g, i) => ({ ...g, _orig: i }));

  // Sort state: { col, dir }  dir = "asc" | "desc"
  let sortState = { col: null, dir: "asc" };

  function buildTable() {
    const thead = `
      <thead>
        <tr>
          <th class="sortable" data-col="date">Date</th>
          <th class="sortable" data-col="opponent">Opponent</th>
          <th class="sortable num" data-col="score">Score</th>
          <th class="sortable" data-col="result">Result</th>
        </tr>
      </thead>
    `;

    const tbody = "<tbody>" + rows.map(g => {
      const scoreTxt = (g.sets_won === 0 && g.sets_lost === 0)
        ? "—"
        : `${g.sets_won}–${g.sets_lost}`;
      const badgeClass = g.result === "W" ? "badge-win" : "badge-loss";
      return `
        <tr>
          <td>${g.date}</td>
          <td>${g.opponent}</td>
          <td class="num">${scoreTxt}</td>
          <td><span class="badge ${badgeClass}">${g.result}</span></td>
        </tr>
      `;
    }).join("") + "</tbody>";

    const table = document.createElement("table");
    table.className = "data-table";
    table.innerHTML = thead + tbody;

    // Apply active sort indicator
    if (sortState.col) {
      const th = table.querySelector(`th[data-col="${sortState.col}"]`);
      if (th) th.classList.add(sortState.dir);
    }

    // Click handler for sorting
    table.querySelectorAll("th.sortable").forEach(th => {
      th.addEventListener("click", () => {
        const col = th.dataset.col;
        if (sortState.col === col) {
          sortState.dir = sortState.dir === "asc" ? "desc" : "asc";
        } else {
          sortState.col = col;
          sortState.dir = "asc";
        }
        sortRows(col, sortState.dir);
        container.innerHTML = "";
        container.appendChild(buildTable());
      });
    });

    return table;
  }

  function sortRows(col, dir) {
    const mult = dir === "asc" ? 1 : -1;
    rows.sort((a, b) => {
      let va, vb;
      if (col === "date") {
        va = a.date; vb = b.date;
        return mult * va.localeCompare(vb);
      }
      if (col === "opponent") {
        va = a.opponent.toLowerCase(); vb = b.opponent.toLowerCase();
        return mult * va.localeCompare(vb);
      }
      if (col === "score") {
        va = a.sets_won - a.sets_lost; vb = b.sets_won - b.sets_lost;
        return mult * (va - vb);
      }
      if (col === "result") {
        va = a.result; vb = b.result;
        return mult * va.localeCompare(vb);
      }
      return 0;
    });
  }

  container.appendChild(buildTable());
}

// ── 7. Sideout by Phase Chart ─────────────────────────────────
function renderSideoutByPhase(sideoutByPhase) {
  const el = document.getElementById("sideout-by-phase-chart");
  if (!el || !sideoutByPhase || !sideoutByPhase.length) return;

  // Canonical order: early → middle → final
  const phaseOrder = ["early", "middle", "final"];
  const phaseLabels = { early: "Early (0–9)", middle: "Middle (10–19)", final: "Final (20+)" };
  const phaseColors = { early: "#38bdf8", middle: "#a78bfa", final: "#4ade80" };

  const sorted = phaseOrder
    .map(p => sideoutByPhase.find(d => d.phase === p))
    .filter(Boolean);

  const x = sorted.map(d => phaseLabels[d.phase] || d.phase);
  const y = sorted.map(d => d.sideout_pct);
  const colors = sorted.map(d => phaseColors[d.phase] || "#94a3b8");

  const trace = {
    x,
    y,
    type: "bar",
    marker: { color: colors, opacity: 0.85 },
    text: sorted.map(d => `${d.sideout_pct.toFixed(1)}%`),
    textposition: "outside",
    textfont: { color: "#94a3b8", size: 12 },
    hovertemplate: "<b>%{x}</b><br>Sideout: %{y:.1f}%<br>Opportunities: %{customdata}<extra></extra>",
    customdata: sorted.map(d => d.opportunities),
  };

  const layout = darkLayout({
    yaxis: {
      title: { text: "Sideout %", font: { size: 11 } },
      ticksuffix: "%",
      range: [0, 100],
    },
    xaxis: { tickfont: { size: 12 } },
    margin: { t: 36, r: 16, b: 48, l: 56 },
  });

  Plotly.newPlot(el, [trace], layout, PLOTLY_CONFIG);
}

// ── 8. Expected Sideout by Pass Quality ─────────────────────
function renderExpectedSideout(data) {
  const el = document.getElementById("expected-sideout-chart");
  if (!el || !data || !data.length) return;

  const colors = ["#f87171", "#fbbf24", "#86efac", "#4ade80"];
  const trace = {
    x: data.map(d => `Pass ${d.pass_quality}`),
    y: data.map(d => d.sideout_pct),
    type: "bar",
    marker: { color: data.map((_, i) => colors[i] || "#38bdf8") },
    text: data.map(d => d.sideout_pct.toFixed(1) + "%"),
    textposition: "auto",
    textfont: { color: "#0f172a", size: 12 },
    hovertemplate: "%{x}<br>SO%%: %{y:.1f}<br>Rallies: %{customdata}<extra></extra>",
    customdata: data.map(d => d.rallies),
  };

  Plotly.newPlot(el, [trace], darkLayout({
    height: 300,
    yaxis: { title: "Sideout %", range: [0, 100], ticksuffix: "%" },
    margin: { t: 24, r: 16, b: 48, l: 56 },
  }), PLOTLY_CONFIG);
}
