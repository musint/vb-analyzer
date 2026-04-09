/* ============================================================
   VB Analyzer — Players Page Logic
   ============================================================ */

const STATE_LABELS = {
  winning_big: "Winning Big",
  winning: "Winning",
  close: "Close",
  losing: "Losing",
  losing_big: "Losing Big",
};

// State ordering for game-state chart
const STATE_ORDER = ["winning_big", "winning", "close", "losing", "losing_big"];

let playersData = null;

// ── Initialise ────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", async () => {
  playersData = await loadJSON("data/players.json");
  if (!playersData) {
    document.querySelector(".main-content").innerHTML =
      '<p style="color:var(--red);padding:2rem">Failed to load player data.</p>';
    return;
  }

  buildDropdown();
  const firstPlayer = playersData.player_list[0];
  if (firstPlayer) renderPlayer(firstPlayer);
});

// ── Dropdown ──────────────────────────────────────────────────
function buildDropdown() {
  const container = document.getElementById("player-selector");
  const select = document.createElement("select");
  select.id = "player-dropdown";
  select.className = "dropdown";

  playersData.player_list.forEach(name => {
    const opt = document.createElement("option");
    opt.value = name;
    opt.textContent = name;
    select.appendChild(opt);
  });

  select.addEventListener("change", () => renderPlayer(select.value));
  container.appendChild(select);
}

// ── Master render dispatcher ──────────────────────────────────
function renderPlayer(name) {
  renderKPIs(name);
  renderClutch(name);
  renderGameStateChart(name);
  renderSeasonProgression(name);
  renderConsistency(name);
}

// ── KPI Cards ─────────────────────────────────────────────────
function renderKPIs(name) {
  const s = (playersData.stats || {})[name];
  const container = document.getElementById("player-kpis");
  container.innerHTML = "";

  if (!s) {
    container.innerHTML = '<p style="color:var(--muted)">No stats found.</p>';
    return;
  }

  const totalErrors = (s.att_errors || 0) + (s.srv_errors || 0);
  const passDisplay = (s.pass_total > 0 && s.pass_avg != null)
    ? Number(s.pass_avg).toFixed(3)
    : "N/A";

  const cards = [
    { label: "Kills",       value: s.kills ?? "—",                      color: "green" },
    { label: "Hitting Eff", value: Number(s.hitting_eff).toFixed(3),    color: s.hitting_eff >= 0.2 ? "green" : s.hitting_eff >= 0.1 ? "gold" : "red" },
    { label: "Aces",        value: s.aces ?? "—",                       color: "gold" },
    { label: "Digs",        value: s.digs ?? "—",                       color: "" },
    { label: "Pass Avg",    value: passDisplay,                         color: "" },
    { label: "Errors",      value: totalErrors,                         color: totalErrors > 20 ? "red" : "" },
  ];

  cards.forEach(({ label, value, color }) => {
    const div = document.createElement("div");
    div.className = "kpi-card" + (color ? ` ${color}` : "");
    div.innerHTML = `<div class="kpi-value">${value}</div><div class="kpi-label">${label}</div>`;
    container.appendChild(div);
  });
}

// ── Clutch Comparison ─────────────────────────────────────────
function renderClutch(name) {
  const container = document.getElementById("clutch-comparison");
  const c = (playersData.clutch || {})[name];

  if (!c) {
    container.innerHTML = '<p style="color:var(--muted);font-size:0.875rem">No clutch data available.</p>';
    return;
  }

  // Metrics to display: [label, clutch_val, normal_val, formatter]
  const metrics = [
    ["Hitting Eff", c.hitting_eff_clutch, c.hitting_eff_non_clutch, v => v != null ? Number(v).toFixed(3) : "N/A"],
    ["Kill %",      c.kill_pct_clutch,    c.kill_pct_non_clutch,    v => v != null ? Number(v).toFixed(1) + "%" : "N/A"],
    ["Pass Avg",    c.pass_avg_clutch,    c.pass_avg_non_clutch,    v => v != null ? Number(v).toFixed(2) : "N/A"],
  ];

  // Find absolute max across all values for bar scaling
  const allVals = metrics.flatMap(([, cv, nv]) => [cv, nv]).filter(v => v != null && !isNaN(v));
  const maxVal = allVals.length ? Math.max(...allVals) : 1;

  let html = '<div class="clutch-bars">';

  metrics.forEach(([label, cv, nv, fmt]) => {
    const clutchPct = cv != null && !isNaN(cv) ? Math.max(0, (cv / maxVal) * 100) : 0;
    const normalPct = nv != null && !isNaN(nv) ? Math.max(0, (nv / maxVal) * 100) : 0;

    html += `
      <div class="clutch-metric">
        <div class="clutch-label">${label}</div>
        <div class="clutch-bar-row">
          <div class="clutch-bar clutch" style="width:${clutchPct}%">${fmt(cv)}</div>
        </div>
        <div class="clutch-bar-row">
          <div class="clutch-bar normal" style="width:${normalPct}%">${fmt(nv)}</div>
        </div>
      </div>`;
  });

  html += "</div>";

  // Legend
  html += `
    <div class="clutch-legend">
      <span><span class="legend-dot clutch"></span>Clutch</span>
      <span><span class="legend-dot normal"></span>Normal</span>
    </div>`;

  container.innerHTML = html;
}

// ── Performance by Game State ─────────────────────────────────
function renderGameStateChart(name) {
  const el = document.getElementById("player-game-state-chart");
  const raw = (playersData.game_state || {})[name];

  if (!raw || !raw.length) {
    el.innerHTML = '<p style="color:var(--muted);font-size:0.875rem;padding:1rem">No game-state data available.</p>';
    return;
  }

  // Index by situation key
  const byState = {};
  raw.forEach(r => { byState[r.situation] = r; });

  const labels = STATE_ORDER.map(k => STATE_LABELS[k] || k);
  const effVals = STATE_ORDER.map(k => {
    const v = byState[k]?.hitting_eff;
    return (v != null && !isNaN(v)) ? +v.toFixed(3) : null;
  });
  const passVals = STATE_ORDER.map(k => {
    const v = byState[k]?.pass_avg;
    return (v != null && !isNaN(v)) ? +v.toFixed(3) : null;
  });

  const traces = [
    {
      name: "Hitting Eff",
      x: labels,
      y: effVals,
      type: "bar",
      marker: { color: "rgba(34,211,238,0.8)" },
    },
    {
      name: "Pass Avg",
      x: labels,
      y: passVals,
      type: "bar",
      marker: { color: "rgba(168,85,247,0.8)" },
    },
  ];

  const layout = darkLayout({
    barmode: "group",
    yaxis: { title: "Value" },
    margin: { t: 24, r: 16, b: 48, l: 52 },
  });

  Plotly.react(el, traces, layout, PLOTLY_CONFIG);
}

// ── Season Progression ────────────────────────────────────────
function renderSeasonProgression(name) {
  const el = document.getElementById("season-progression-chart");
  const raw = (playersData.progression || {})[name];

  if (!raw || !raw.length) {
    el.innerHTML = '<p style="color:var(--muted);font-size:0.875rem;padding:1rem">No progression data available.</p>';
    return;
  }

  const dates = raw.map(r => r.date);
  const effRolling  = raw.map(r => {
    const v = r.hitting_eff_rolling;
    return (v != null && !isNaN(v)) ? +Number(v).toFixed(3) : null;
  });
  const passRolling = raw.map(r => {
    const v = r.pass_avg_rolling;
    return (v != null && !isNaN(v)) ? +Number(v).toFixed(3) : null;
  });

  const traces = [
    {
      name: "Hitting Eff (rolling)",
      x: dates,
      y: effRolling,
      type: "scatter",
      mode: "lines+markers",
      yaxis: "y",
      line: { color: "rgba(34,211,238,0.9)", width: 2 },
      marker: { color: "rgba(34,211,238,0.9)", size: 5 },
      connectgaps: false,
    },
    {
      name: "Pass Avg (rolling)",
      x: dates,
      y: passRolling,
      type: "scatter",
      mode: "lines+markers",
      yaxis: "y2",
      line: { color: "rgba(168,85,247,0.9)", width: 2 },
      marker: { color: "rgba(168,85,247,0.9)", size: 5 },
      connectgaps: false,
    },
  ];

  const layout = darkLayout({
    yaxis: {
      title: "Hitting Eff",
      tickfont: { color: "rgba(34,211,238,0.9)" },
      titlefont: { color: "rgba(34,211,238,0.9)" },
    },
    yaxis2: {
      title: "Pass Avg",
      overlaying: "y",
      side: "right",
      tickfont: { color: "rgba(168,85,247,0.9)" },
      titlefont: { color: "rgba(168,85,247,0.9)" },
      gridcolor: "rgba(0,0,0,0)",
      zerolinecolor: "rgba(51,65,85,0.5)",
    },
    margin: { t: 24, r: 64, b: 48, l: 52 },
    legend: { orientation: "h", y: -0.2 },
  });

  Plotly.react(el, traces, layout, PLOTLY_CONFIG);
}

// ── Consistency Index ─────────────────────────────────────────
function renderConsistency(name) {
  const container = document.getElementById("consistency-index");
  const c = (playersData.consistency || {})[name];

  if (!c) {
    container.innerHTML = '<p style="color:var(--muted);font-size:0.875rem">No consistency data available.</p>';
    return;
  }

  const score = c.consistency_score;
  let pillColor = "red";
  if (score >= 0.7) pillColor = "green";
  else if (score >= 0.4) pillColor = "gold";

  const scoreDisplay = score != null ? (score * 100).toFixed(1) + "%" : "—";
  const stdDev       = c.eff_std_dev    != null ? Number(c.eff_std_dev).toFixed(4) : "—";
  const avgEff       = c.avg_eff        != null ? Number(c.avg_eff).toFixed(3)     : "—";
  const matches      = c.matches_with_attacks ?? "—";

  container.innerHTML = `
    <div style="display:flex;align-items:center;gap:16px;flex-wrap:wrap">
      <span class="pill ${pillColor}" style="font-size:1.25rem;padding:8px 20px">${scoreDisplay}</span>
      <div style="display:flex;flex-direction:column;gap:6px;font-size:0.85rem;color:var(--muted)">
        <span>Std Dev (Eff): <strong style="color:var(--text)">${stdDev}</strong></span>
        <span>Avg Hitting Eff: <strong style="color:var(--text)">${avgEff}</strong></span>
        <span>Matches with attacks: <strong style="color:var(--text)">${matches}</strong></span>
      </div>
    </div>`;
}
