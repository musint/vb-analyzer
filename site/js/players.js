/* ============================================================
   13-2 Statistical Deep Dive — Players Page Logic
   ============================================================ */

const STATE_LABELS = {
  winning_big: "Winning Big",
  winning: "Winning",
  close: "Close",
  losing: "Losing",
  losing_big: "Losing Big",
};
const STATE_ORDER = ["winning_big", "winning", "close", "losing", "losing_big"];
const STATE_COLORS = {
  winning_big: "#4ade80",
  winning: "#86efac",
  close: "#e2e8f0",
  losing: "#fca5a5",
  losing_big: "#f87171",
};

let playersData = null;

// ── Initialise ────────────────────────────────────────────────
async function initPage() {
  playersData = await loadJSON("players.json");
  if (!playersData) {
    document.querySelector(".main-content").innerHTML =
      '<p style="color:var(--red);padding:2rem">Failed to load player data.</p>';
    return;
  }

  buildDropdown();
  const dropdown = document.getElementById("player-dropdown");
  const selectedPlayer = dropdown ? dropdown.value : playersData.player_list[0];
  if (selectedPlayer) renderPlayer(selectedPlayer);
}

document.addEventListener("DOMContentLoaded", initPage);
window.addEventListener("dataset-changed", initPage);

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
  renderClutchDefinition();
  renderClutch(name);
  renderGameStateHitting(name);
  renderGameStatePassing(name);
  renderGameStateServing(name);
  renderSeasonProgression(name);
  renderConsistency(name);
  renderInSystem(name);
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

// ── Clutch Definition ─────────────────────────────────────────
function renderClutchDefinition() {
  const el = document.getElementById("clutch-definition");
  el.innerHTML = `
    <div class="pill-row" style="margin-bottom:16px">
      <span class="game-state-pill state-close" style="font-size:0.8rem">
        <strong>Clutch</strong> — Sets 1-2: both teams ≥ 20 pts &nbsp;|&nbsp; Set 3: both teams ≥ 10 pts
      </span>
    </div>
    <p style="color:var(--muted);font-size:0.8rem;margin-bottom:16px">
      Clutch moments are the high-pressure rallies at the end of close sets where every point matters most.
      Stats below compare performance in clutch situations vs. all other (normal) rallies.
    </p>`;
}

// ── Clutch Comparison ─────────────────────────────────────────
function renderClutch(name) {
  const container = document.getElementById("clutch-comparison");
  const c = (playersData.clutch || {})[name];

  if (!c) {
    container.innerHTML = '<p style="color:var(--muted);font-size:0.875rem">No clutch data available.</p>';
    return;
  }

  const metrics = [
    ["Hitting Eff", c.hitting_eff_clutch, c.hitting_eff_non_clutch, v => v != null ? Number(v).toFixed(3) : "N/A"],
    ["Kill %",      c.kill_pct_clutch,    c.kill_pct_non_clutch,    v => v != null ? Number(v).toFixed(1) + "%" : "N/A"],
    ["Pass Avg",    c.pass_avg_clutch,    c.pass_avg_non_clutch,    v => v != null ? Number(v).toFixed(2) : "N/A"],
    ["Ace %",       c.ace_pct_clutch,     c.ace_pct_non_clutch,     v => v != null ? v.toFixed(1) + "%" : "N/A"],
    ["Srv Error %", c.srv_err_pct_clutch, c.srv_err_pct_non_clutch, v => v != null ? v.toFixed(1) + "%" : "N/A"],
  ];

  const allVals = metrics.flatMap(([, cv, nv]) => [cv, nv]).filter(v => v != null && !isNaN(v));
  const maxVal = allVals.length ? Math.max(...allVals, 0.001) : 1;

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
  html += `
    <div class="clutch-legend">
      <span><span class="legend-dot clutch"></span>Clutch</span>
      <span><span class="legend-dot normal"></span>Normal</span>
    </div>`;

  container.innerHTML = html;
}

// ── Game State: Hitting ───────────────────────────────────────
function renderGameStateHitting(name) {
  const el = document.getElementById("game-state-hitting");
  const raw = (playersData.game_state || {})[name];

  if (!raw || !raw.length) {
    el.innerHTML = '<p style="color:var(--muted);font-size:0.875rem;padding:1rem">No data.</p>';
    return;
  }

  const byState = {};
  raw.forEach(r => { byState[r.situation] = r; });

  const labels = STATE_ORDER.map(k => STATE_LABELS[k]);
  const colors = STATE_ORDER.map(k => STATE_COLORS[k]);
  const effVals = STATE_ORDER.map(k => byState[k]?.hitting_eff ?? null);
  const attempts = STATE_ORDER.map(k => byState[k]?.att_total ?? 0);

  Plotly.react(el, [{
    x: labels, y: effVals, type: "bar",
    marker: { color: colors },
    text: effVals.map(v => v != null ? v.toFixed(3) : ""),
    textposition: "auto",
    textfont: { color: "#0f172a", size: 11 },
    hovertemplate: "%{x}<br>Eff: %{y:.3f}<br>Attempts: %{customdata}<extra></extra>",
    customdata: attempts,
  }], darkLayout({
    yaxis: { title: "Hitting Efficiency" },
    height: 280,
    margin: { t: 16, r: 16, b: 48, l: 52 },
  }), PLOTLY_CONFIG);
}

// ── Game State: Passing ───────────────────────────────────────
function renderGameStatePassing(name) {
  const el = document.getElementById("game-state-passing");
  const raw = (playersData.game_state || {})[name];

  if (!raw || !raw.length) {
    el.innerHTML = '<p style="color:var(--muted);font-size:0.875rem;padding:1rem">No data.</p>';
    return;
  }

  const byState = {};
  raw.forEach(r => { byState[r.situation] = r; });

  const labels = STATE_ORDER.map(k => STATE_LABELS[k]);
  const colors = STATE_ORDER.map(k => STATE_COLORS[k]);
  const passVals = STATE_ORDER.map(k => byState[k]?.pass_avg ?? null);

  Plotly.react(el, [{
    x: labels, y: passVals, type: "bar",
    marker: { color: colors },
    text: passVals.map(v => v != null ? v.toFixed(2) : ""),
    textposition: "auto",
    textfont: { color: "#0f172a", size: 11 },
    hovertemplate: "%{x}<br>Pass Avg: %{y:.2f}<extra></extra>",
  }], darkLayout({
    yaxis: { title: "Pass Average", range: [0, 3] },
    height: 280,
    margin: { t: 16, r: 16, b: 48, l: 52 },
  }), PLOTLY_CONFIG);
}

// ── Game State: Serving ───────────────────────────────────────
function renderGameStateServing(name) {
  const el = document.getElementById("game-state-serving");
  const raw = (playersData.game_state || {})[name];

  if (!raw || !raw.length) {
    el.innerHTML = '<p style="color:var(--muted);font-size:0.875rem;padding:1rem">No data.</p>';
    return;
  }

  const byState = {};
  raw.forEach(r => { byState[r.situation] = r; });

  const labels = STATE_ORDER.map(k => STATE_LABELS[k]);
  const aceVals = STATE_ORDER.map(k => byState[k]?.ace_pct ?? null);
  const errVals = STATE_ORDER.map(k => byState[k]?.srv_err_pct ?? null);
  const totals = STATE_ORDER.map(k => byState[k]?.srv_total ?? 0);

  Plotly.react(el, [
    {
      name: "Ace %", x: labels, y: aceVals, type: "bar",
      marker: { color: "rgba(74,222,128,0.8)" },
      text: aceVals.map(v => v != null ? v.toFixed(1) + "%" : ""),
      textposition: "auto",
      textfont: { color: "#0f172a", size: 11 },
      hovertemplate: "%{x}<br>Ace%%: %{y:.1f}<br>Serves: %{customdata}<extra></extra>",
      customdata: totals,
    },
    {
      name: "Error %", x: labels, y: errVals, type: "bar",
      marker: { color: "rgba(248,113,113,0.8)" },
      text: errVals.map(v => v != null ? v.toFixed(1) + "%" : ""),
      textposition: "auto",
      textfont: { color: "#0f172a", size: 11 },
      hovertemplate: "%{x}<br>Err%%: %{y:.1f}<br>Serves: %{customdata}<extra></extra>",
      customdata: totals,
    },
  ], darkLayout({
    barmode: "group",
    yaxis: { title: "Percentage" },
    height: 300,
    margin: { t: 16, r: 16, b: 48, l: 52 },
    legend: { orientation: "h", y: -0.2 },
  }), PLOTLY_CONFIG);
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

  Plotly.react(el, [
    {
      name: "Hitting Eff (rolling)",
      x: dates, y: effRolling,
      type: "scatter", mode: "lines+markers", yaxis: "y",
      line: { color: "rgba(34,211,238,0.9)", width: 2 },
      marker: { size: 5 },
      connectgaps: false,
    },
    {
      name: "Pass Avg (rolling)",
      x: dates, y: passRolling,
      type: "scatter", mode: "lines+markers", yaxis: "y2",
      line: { color: "rgba(168,85,247,0.9)", width: 2 },
      marker: { size: 5 },
      connectgaps: false,
    },
  ], darkLayout({
    yaxis: {
      title: "Hitting Eff",
      tickfont: { color: "rgba(34,211,238,0.9)" },
      titlefont: { color: "rgba(34,211,238,0.9)" },
    },
    yaxis2: {
      title: "Pass Avg",
      overlaying: "y", side: "right",
      tickfont: { color: "rgba(168,85,247,0.9)" },
      titlefont: { color: "rgba(168,85,247,0.9)" },
      gridcolor: "rgba(0,0,0,0)",
      zerolinecolor: "rgba(51,65,85,0.5)",
    },
    margin: { t: 24, r: 64, b: 48, l: 52 },
    legend: { orientation: "h", y: -0.2 },
  }), PLOTLY_CONFIG);
}

// ── Consistency Index ─────────────────────────────────────────
function renderConsistency(name) {
  const container = document.getElementById("consistency-index");
  const c = (playersData.consistency || {})[name];

  if (!c) {
    container.innerHTML = '<p style="color:var(--muted);font-size:0.875rem">No consistency data available.</p>';
    return;
  }

  const skills = [
    { key: "hitting",  label: "Hitting",  icon: "Eff" },
    { key: "serving",  label: "Serving",  icon: "Ace%" },
    { key: "passing",  label: "Passing",  icon: "Avg" },
  ];

  let html = '<div style="display:flex;gap:20px;flex-wrap:wrap">';

  skills.forEach(({ key, label, icon }) => {
    const data = c[key];
    if (!data) {
      html += `
        <div style="flex:1;min-width:200px;background:var(--surface2);border-radius:var(--radius);padding:16px">
          <div style="font-weight:600;font-size:0.9rem;margin-bottom:8px">${label}</div>
          <p style="color:var(--muted);font-size:0.8rem">Not enough data</p>
        </div>`;
      return;
    }

    const score = data.score;
    let pillColor = "red";
    if (score >= 0.7) pillColor = "green";
    else if (score >= 0.4) pillColor = "gold";

    const rankText = data.rank ? `#${data.rank} of ${data.total_ranked}` : "";

    html += `
      <div style="flex:1;min-width:200px;background:var(--surface2);border-radius:var(--radius);padding:16px">
        <div style="display:flex;align-items:center;gap:10px;margin-bottom:10px">
          <span style="font-weight:600;font-size:0.9rem">${label}</span>
          <span class="pill ${pillColor}" style="font-size:0.85rem;padding:4px 12px">${score.toFixed(3)}</span>
        </div>
        <div style="display:flex;flex-direction:column;gap:4px;font-size:0.8rem;color:var(--muted)">
          <span>Std Dev: <strong style="color:var(--text)">${data.std_dev.toFixed(4)}</strong></span>
          <span>Avg ${icon}: <strong style="color:var(--text)">${data.avg.toFixed(3)}</strong></span>
          <span>Matches: <strong style="color:var(--text)">${data.matches}</strong></span>
          ${rankText ? `<span>Rank: <strong style="color:var(--accent)">${rankText}</strong></span>` : ""}
        </div>
      </div>`;
  });

  html += '</div>';
  html += '<p style="color:var(--muted);font-size:0.75rem;margin-top:12px">Consistency = 1 / (1 + std_dev). Higher = more consistent match-to-match. Based on per-match stat variance across games with 3+ attempts.</p>';

  container.innerHTML = html;
}

// ── In-System vs Out-of-System Efficiency ─────────────────────
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
    margin: { t: 16, r: 16, b: 48, l: 52 },
  }), PLOTLY_CONFIG);
}
