/* ============================================================
   VB Analyzer — Comparison Page Logic
   ============================================================ */

const MAX_PLAYERS = 6;
const MIN_PLAYERS = 2;

let compData    = null;   // comparison.json
let playersData = null;   // players.json

// Names of currently selected players
let selectedNames = [];

// ── Init ──────────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", async () => {
  [compData, playersData] = await Promise.all([
    loadJSON("data/comparison.json"),
    loadJSON("data/players.json"),
  ]);

  if (!compData || !playersData) {
    document.querySelector(".main-content").innerHTML =
      '<p style="color:var(--red);padding:2rem">Failed to load comparison data.</p>';
    return;
  }

  // Filter out "None" entries and players without a name
  compData.players = compData.players.filter(p => p.name && p.name !== "None");

  // Default: first 2 players
  selectedNames = compData.players.slice(0, MIN_PLAYERS).map(p => p.name);

  buildMultiSelect();
  renderAll();
});

// ── Helpers ───────────────────────────────────────────────────
function getPlayerObj(name) {
  return compData.players.find(p => p.name === name);
}

function renderAll() {
  renderRadar();
  renderTrends();
  renderTable();
}

// ── Multi-Player Select ───────────────────────────────────────
function buildMultiSelect() {
  const container = document.getElementById("player-multi-select");
  container.innerHTML = "";

  // Row: dropdown + label
  const controlRow = document.createElement("div");
  controlRow.style.cssText = "display:flex;align-items:center;gap:12px;margin-bottom:12px;flex-wrap:wrap;";

  const label = document.createElement("span");
  label.textContent = "Add player:";
  label.style.cssText = "font-size:0.875rem;color:var(--muted);white-space:nowrap;";

  const select = document.createElement("select");
  select.id   = "player-add-dropdown";
  select.className = "dropdown";

  // Placeholder
  const placeholder = document.createElement("option");
  placeholder.value = "";
  placeholder.textContent = "— choose a player —";
  placeholder.disabled = true;
  placeholder.selected = true;
  select.appendChild(placeholder);

  compData.players.forEach(p => {
    const opt = document.createElement("option");
    opt.value = p.name;
    opt.textContent = p.name;
    select.appendChild(opt);
  });

  select.addEventListener("change", () => {
    const name = select.value;
    if (!name) return;
    if (selectedNames.includes(name)) {
      select.value = "";
      return;
    }
    if (selectedNames.length >= MAX_PLAYERS) {
      select.value = "";
      return;
    }
    selectedNames.push(name);
    select.value = "";
    refreshPills();
    renderAll();
  });

  controlRow.appendChild(label);
  controlRow.appendChild(select);

  const maxNote = document.createElement("span");
  maxNote.style.cssText = "font-size:0.75rem;color:var(--muted);";
  maxNote.textContent = `Max ${MAX_PLAYERS} players`;
  controlRow.appendChild(maxNote);

  container.appendChild(controlRow);

  // Pill row
  const pillRow = document.createElement("div");
  pillRow.id = "pill-row";
  pillRow.className = "pill-row";
  container.appendChild(pillRow);

  refreshPills();
}

function refreshPills() {
  const pillRow = document.getElementById("pill-row");
  if (!pillRow) return;
  pillRow.innerHTML = "";

  selectedNames.forEach(name => {
    const player = getPlayerObj(name);
    const color  = player ? player.color : "#94a3b8";

    const pill = document.createElement("span");
    pill.className = "player-pill";
    pill.style.cssText = `
      border-color: ${color};
      background: ${color}1a;
      color: ${color};
    `;

    const nameSpan = document.createElement("span");
    nameSpan.textContent = name;

    const removeBtn = document.createElement("button");
    removeBtn.className = "pill-remove";
    removeBtn.innerHTML = "&#x2715;";
    removeBtn.title = `Remove ${name}`;
    removeBtn.style.cssText = `
      background: ${color}26;
      color: ${color};
    `;
    removeBtn.addEventListener("click", () => {
      if (selectedNames.length <= MIN_PLAYERS) return; // keep minimum
      selectedNames = selectedNames.filter(n => n !== name);
      refreshPills();
      renderAll();
    });

    pill.appendChild(nameSpan);
    pill.appendChild(removeBtn);
    pillRow.appendChild(pill);
  });

  // Min-players hint
  if (selectedNames.length <= MIN_PLAYERS) {
    const hint = document.createElement("span");
    hint.style.cssText = "font-size:0.75rem;color:var(--muted);align-self:center;";
    hint.textContent = `Minimum ${MIN_PLAYERS} players required`;
    pillRow.appendChild(hint);
  }
}

// ── Radar Chart ───────────────────────────────────────────────
function renderRadar() {
  const el = document.getElementById("radar-chart");

  if (selectedNames.length < MIN_PLAYERS) {
    el.innerHTML = '<p style="color:var(--muted);padding:2rem;text-align:center;">Select at least 2 players</p>';
    return;
  }

  const metrics = compData.radar_metrics;
  const labels  = compData.radar_labels;

  // Close polygon: append first element to end
  const thetaClosed = [...labels, labels[0]];

  const traces = selectedNames.map(name => {
    const player = getPlayerObj(name);
    if (!player) return null;

    const rValues = metrics.map(m => {
      const v = player.normalized[m];
      return (v == null || isNaN(v)) ? 0 : v;
    });
    const rClosed = [...rValues, rValues[0]];

    return {
      type:      "scatterpolar",
      name:      name,
      r:         rClosed,
      theta:     thetaClosed,
      fill:      "toself",
      fillcolor: player.color + "20",
      line: {
        color: player.color,
        width: 2,
      },
      hovertemplate: "<b>%{fullData.name}</b><br>%{theta}: %{r:.3f}<extra></extra>",
    };
  }).filter(Boolean);

  const layout = Object.assign(darkLayout({
    margin: { t: 40, r: 60, b: 40, l: 60 },
  }), {
    polar: {
      bgcolor: "transparent",
      angularaxis: {
        tickfont:  { color: "#94a3b8", size: 11 },
        linecolor: "rgba(51,65,85,0.6)",
        gridcolor: "rgba(51,65,85,0.5)",
      },
      radialaxis: {
        range:     [0, 1],
        gridcolor: "rgba(51,65,85,0.5)",
        linecolor: "rgba(51,65,85,0.5)",
        tickfont:  { color: "#94a3b8", size: 9 },
        tickformat: ".1f",
        tickvals:  [0.25, 0.5, 0.75, 1.0],
      },
    },
    showlegend: true,
    legend: {
      font:    { color: "#94a3b8" },
      bgcolor: "rgba(0,0,0,0)",
      x: 1.05,
      y: 0.5,
    },
  });

  Plotly.react(el, traces, layout, PLOTLY_CONFIG);
}

// ── Trend Chart ───────────────────────────────────────────────
function renderTrends() {
  const el = document.getElementById("trend-chart");

  if (selectedNames.length < MIN_PLAYERS) {
    el.innerHTML = '<p style="color:var(--muted);padding:2rem;text-align:center;">Select at least 2 players</p>';
    return;
  }

  const progression = playersData.progression || {};
  const traces = [];

  selectedNames.forEach(name => {
    const player = getPlayerObj(name);
    const series = progression[name];
    if (!series || !series.length) return;

    const dates = series.map(d => d.date);
    const effs  = series.map(d => {
      const v = d.hitting_eff_rolling;
      return (v == null || isNaN(v)) ? null : v;
    });

    traces.push({
      type:           "scatter",
      mode:           "lines+markers",
      name:           name,
      x:              dates,
      y:              effs,
      connectgaps:    false,
      line: {
        color: player ? player.color : "#94a3b8",
        width: 2,
        shape: "spline",
      },
      marker: {
        color: player ? player.color : "#94a3b8",
        size:  5,
      },
      hovertemplate: "<b>%{fullData.name}</b><br>%{x}<br>Eff: %{y:.3f}<extra></extra>",
    });
  });

  if (!traces.length) {
    el.innerHTML = '<p style="color:var(--muted);padding:2rem;text-align:center;">No trend data available for selected players</p>';
    return;
  }

  const layout = darkLayout({
    title: {
      text:  "Hitting Efficiency (Rolling Average)",
      font:  { color: "#94a3b8", size: 13 },
      x: 0.5,
      xanchor: "center",
    },
    xaxis: {
      title:      { text: "Date", font: { color: "#94a3b8" } },
      tickformat: "%b %d",
      type:       "date",
    },
    yaxis: {
      title:      { text: "Hitting Eff (rolling)", font: { color: "#94a3b8" } },
      tickformat: ".3f",
      zeroline:   true,
      zerolinecolor: "rgba(148,163,184,0.3)",
    },
    margin:     { t: 50, r: 16, b: 50, l: 60 },
    showlegend: true,
  });

  Plotly.react(el, traces, layout, PLOTLY_CONFIG);
}

// ── Comparison Table ──────────────────────────────────────────
const TABLE_ROWS = [
  { label: "Kills",       key: "kills",       fmt: v => (v == null || isNaN(v)) ? "—" : Math.round(v).toString() },
  { label: "Hitting Eff", key: "hitting_eff",  fmt: v => (v == null || isNaN(v)) ? "—" : Number(v).toFixed(3) },
  { label: "Aces",        key: "aces",         fmt: v => (v == null || isNaN(v)) ? "—" : Math.round(v).toString() },
  { label: "Digs",        key: "digs",         fmt: v => (v == null || isNaN(v)) ? "—" : Math.round(v).toString() },
  { label: "Pass Avg",    key: "pass_avg",     fmt: v => (v == null || isNaN(v)) ? "—" : Number(v).toFixed(3) },
  { label: "Consistency", key: "consistency",  fmt: v => (v == null || isNaN(v)) ? "—" : Number(v).toFixed(3) },
];

function renderTable() {
  const wrap = document.getElementById("comparison-table");

  if (selectedNames.length < MIN_PLAYERS) {
    wrap.innerHTML = '<p style="color:var(--muted);padding:2rem;text-align:center;">Select at least 2 players</p>';
    return;
  }

  const players = selectedNames.map(n => getPlayerObj(n)).filter(Boolean);

  // Build table
  const table = document.createElement("table");
  table.className = "data-table";

  // Header
  const thead  = document.createElement("thead");
  const headTr = document.createElement("tr");

  const metricTh = document.createElement("th");
  metricTh.textContent = "Metric";
  headTr.appendChild(metricTh);

  players.forEach(p => {
    const th = document.createElement("th");
    th.className = "num";
    th.style.color = p.color;
    th.textContent = p.name;
    headTr.appendChild(th);
  });

  thead.appendChild(headTr);
  table.appendChild(thead);

  // Body
  const tbody = document.createElement("tbody");

  TABLE_ROWS.forEach(row => {
    const tr = document.createElement("tr");

    const labelTd = document.createElement("td");
    labelTd.textContent = row.label;
    tr.appendChild(labelTd);

    // Gather raw numeric values to find the best
    const rawVals = players.map(p => {
      const v = p.raw[row.key];
      return (v == null || isNaN(v)) ? null : v;
    });
    const validVals = rawVals.filter(v => v !== null);
    const bestVal   = validVals.length ? Math.max(...validVals) : null;

    players.forEach((p, i) => {
      const td = document.createElement("td");
      td.className = "num";
      const raw = p.raw[row.key];
      td.textContent = row.fmt(raw);

      if (bestVal !== null && raw !== null && !isNaN(raw) && raw === bestVal) {
        td.classList.add("best-value");
      }
      tr.appendChild(td);
    });

    tbody.appendChild(tr);
  });

  table.appendChild(tbody);

  // Footer
  const tfoot = document.createElement("tfoot");
  const footTr = document.createElement("tr");
  const footTd = document.createElement("td");
  footTd.colSpan = players.length + 1;
  footTd.style.cssText = "font-size:0.75rem;color:var(--muted);padding-top:10px;text-align:left;";
  footTd.textContent = "Best-in-class highlighted in gold";
  footTr.appendChild(footTd);
  tfoot.appendChild(footTr);
  table.appendChild(tfoot);

  wrap.innerHTML = "";
  wrap.appendChild(table);
}
