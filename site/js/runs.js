/* ============================================================
   13-2 Statistical Deep Dive — Scoring Runs Page Logic
   ============================================================ */

const STATE_LABELS_RUNS = {
  winning_big: "Winning Big",
  winning:     "Winning",
  close:       "Close",
  losing:      "Losing",
  losing_big:  "Losing Big",
};
const STATE_ORDER_RUNS = ["winning_big", "winning", "close", "losing", "losing_big"];

const PHASE_LABELS = { early: "Early", middle: "Middle", final: "Final" };
const PHASE_ORDER  = ["early", "middle", "final"];

// ── Initialise ────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", async () => {
  const data = await loadJSON("data/runs.json");
  if (!data) {
    document.querySelector(".main-content").innerHTML =
      '<p style="color:var(--red);padding:2rem">Failed to load runs data.</p>';
    return;
  }

  renderRunsKPIs(data.summary);
  renderStartersTable(data.starters || []);
  renderKillersTable(data.killers || []);
  renderPhaseChart(data.runs_by_phase || []);
  renderSituationChart(data.runs_by_situation || []);
});

// ── KPI Cards ─────────────────────────────────────────────────
function renderRunsKPIs(s) {
  const container = document.getElementById("runs-kpi-row");
  if (!container || !s) return;

  const cards = [
    { label: "Our Runs",       value: s.our_runs,                   color: "green" },
    { label: "Opp Runs",       value: s.opp_runs,                   color: "red"   },
    { label: "Avg Our Length", value: Number(s.avg_our_length).toFixed(1), color: "green" },
    { label: "Avg Opp Length", value: Number(s.avg_opp_length).toFixed(1), color: ""      },
    { label: "Longest Ours",   value: s.longest_our,                color: "gold"  },
    { label: "Longest Theirs", value: s.longest_opp,                color: ""      },
  ];

  container.innerHTML = "";
  cards.forEach(({ label, value, color }) => {
    const div = document.createElement("div");
    div.className = "kpi-card" + (color ? ` ${color}` : "");
    div.innerHTML = `<div class="kpi-value">${value}</div><div class="kpi-label">${label}</div>`;
    container.appendChild(div);
  });
}

// ── Breakdown helper ──────────────────────────────────────────
function fmtBreakdown(bd) {
  if (!bd || typeof bd !== "object") return "—";
  const KEY_LABELS = {
    attack_kill:             "Kill",
    free_ball_kill:          "FB Kill",
    serve_ace:               "Ace",
    attack_error:            "Att Err",
    dig_error:               "Dig Err",
    free_ball_error:         "FB Err",
    free_ball_received_error:"FB Rec Err",
    serve_error:             "Srv Err",
    set_error:               "Set Err",
  };
  return Object.entries(bd)
    .map(([k, v]) => `${KEY_LABELS[k] || k}: ${v}`)
    .join(", ");
}

// ── Sortable table builder ────────────────────────────────────
function buildSortableTable(rows, columns) {
  // columns: [{ key, label, fmt?, cls? }]
  // rows already sorted by caller

  const table = document.createElement("table");
  table.className = "data-table";

  const thead = document.createElement("thead");
  const headerRow = document.createElement("tr");
  columns.forEach(col => {
    const th = document.createElement("th");
    th.textContent = col.label;
    if (col.cls) th.className = col.cls;
    th.style.cursor = "pointer";
    th.dataset.key = col.key;
    headerRow.appendChild(th);
  });
  thead.appendChild(headerRow);
  table.appendChild(thead);

  const tbody = document.createElement("tbody");
  rows.forEach(row => {
    const tr = document.createElement("tr");
    columns.forEach(col => {
      const td = document.createElement("td");
      const raw = row[col.key];
      td.textContent = col.fmt ? col.fmt(raw, row) : (raw ?? "—");
      if (col.cls) td.className = col.cls;
      tr.appendChild(td);
    });
    tbody.appendChild(tr);
  });
  table.appendChild(tbody);

  // Sort on header click
  let sortKey = null;
  let sortAsc = false;

  headerRow.addEventListener("click", e => {
    const th = e.target.closest("th");
    if (!th) return;
    const key = th.dataset.key;
    if (sortKey === key) {
      sortAsc = !sortAsc;
    } else {
      sortKey = key;
      sortAsc = false; // default desc
    }

    // Update header indicators
    headerRow.querySelectorAll("th").forEach(h => h.classList.remove("sort-asc", "sort-desc"));
    th.classList.add(sortAsc ? "sort-asc" : "sort-desc");

    // Re-sort tbody rows
    const trs = Array.from(tbody.querySelectorAll("tr"));
    const colIdx = columns.findIndex(c => c.key === key);
    trs.sort((a, b) => {
      const av = a.cells[colIdx].textContent;
      const bv = b.cells[colIdx].textContent;
      const an = parseFloat(av);
      const bn = parseFloat(bv);
      const cmp = !isNaN(an) && !isNaN(bn) ? an - bn : av.localeCompare(bv);
      return sortAsc ? cmp : -cmp;
    });
    trs.forEach(tr => tbody.appendChild(tr));
  });

  return table;
}

// ── Starters Table ────────────────────────────────────────────
function renderStartersTable(starters) {
  const container = document.getElementById("starters-table");
  if (!container) return;

  const sorted = [...starters].sort((a, b) => b.start_rate_pct - a.start_rate_pct);

  const columns = [
    { key: "player",         label: "Player"        },
    { key: "runs_started",   label: "Runs Started"  },
    { key: "rallies_played", label: "Rallies"       },
    { key: "start_rate_pct", label: "Start Rate %",  fmt: v => Number(v).toFixed(1) + "%" },
    { key: "breakdown",      label: "Breakdown",     fmt: (v) => fmtBreakdown(v) },
  ];

  container.innerHTML = "";
  container.appendChild(buildSortableTable(sorted, columns));
}

// ── Killers Table ─────────────────────────────────────────────
function renderKillersTable(killers) {
  const container = document.getElementById("killers-table");
  if (!container) return;

  const sorted = [...killers].sort((a, b) => b.trigger_rate_pct - a.trigger_rate_pct);

  const columns = [
    { key: "player",           label: "Player"          },
    { key: "runs_triggered",   label: "Runs Triggered"  },
    { key: "rallies_played",   label: "Rallies"         },
    { key: "trigger_rate_pct", label: "Trigger Rate %",  fmt: v => Number(v).toFixed(1) + "%" },
    { key: "breakdown",        label: "Breakdown",       fmt: (v) => fmtBreakdown(v) },
  ];

  container.innerHTML = "";
  container.appendChild(buildSortableTable(sorted, columns));
}

// ── Runs by Phase Chart ───────────────────────────────────────
function renderPhaseChart(phaseData) {
  const el = document.getElementById("runs-by-phase-chart");
  if (!el) return;

  const byPhase = {};
  phaseData.forEach(d => { byPhase[d.phase] = d; });

  const labels   = PHASE_ORDER.map(p => PHASE_LABELS[p] || p);
  const ourRuns  = PHASE_ORDER.map(p => byPhase[p]?.our_runs  ?? 0);
  const oppRuns  = PHASE_ORDER.map(p => byPhase[p]?.opp_runs  ?? 0);

  Plotly.react(el, [
    {
      name: "Our Runs",
      x: labels, y: ourRuns, type: "bar",
      marker: { color: "rgba(74,222,128,0.8)" },
      text: ourRuns.map(String),
      textposition: "auto",
      textfont: { color: "#0f172a", size: 11 },
      hovertemplate: "%{x}<br>Our Runs: %{y}<extra></extra>",
    },
    {
      name: "Opp Runs",
      x: labels, y: oppRuns, type: "bar",
      marker: { color: "rgba(248,113,113,0.8)" },
      text: oppRuns.map(String),
      textposition: "auto",
      textfont: { color: "#0f172a", size: 11 },
      hovertemplate: "%{x}<br>Opp Runs: %{y}<extra></extra>",
    },
  ], darkLayout({
    barmode: "group",
    yaxis: { title: "Number of Runs" },
    height: 300,
    margin: { t: 16, r: 16, b: 48, l: 52 },
    legend: { orientation: "h", y: -0.2 },
  }), PLOTLY_CONFIG);
}

// ── Runs by Situation Chart ───────────────────────────────────
function renderSituationChart(situationData) {
  const el = document.getElementById("runs-by-situation-chart");
  if (!el) return;

  const bySit = {};
  situationData.forEach(d => { bySit[d.situation] = d; });

  const labels  = STATE_ORDER_RUNS.map(k => STATE_LABELS_RUNS[k] || k);
  const ourRuns = STATE_ORDER_RUNS.map(k => bySit[k]?.our_runs  ?? 0);
  const oppRuns = STATE_ORDER_RUNS.map(k => bySit[k]?.opp_runs  ?? 0);

  Plotly.react(el, [
    {
      name: "Our Runs",
      x: labels, y: ourRuns, type: "bar",
      marker: { color: "rgba(74,222,128,0.8)" },
      text: ourRuns.map(String),
      textposition: "auto",
      textfont: { color: "#0f172a", size: 11 },
      hovertemplate: "%{x}<br>Our Runs: %{y}<extra></extra>",
    },
    {
      name: "Opp Runs",
      x: labels, y: oppRuns, type: "bar",
      marker: { color: "rgba(248,113,113,0.8)" },
      text: oppRuns.map(String),
      textposition: "auto",
      textfont: { color: "#0f172a", size: 11 },
      hovertemplate: "%{x}<br>Opp Runs: %{y}<extra></extra>",
    },
  ], darkLayout({
    barmode: "group",
    yaxis: { title: "Number of Runs" },
    height: 300,
    margin: { t: 16, r: 16, b: 48, l: 52 },
    legend: { orientation: "h", y: -0.2 },
  }), PLOTLY_CONFIG);
}
