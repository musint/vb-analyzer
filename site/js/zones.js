/* ============================================================
   VB Analyzer — Court Zones Page Logic
   ============================================================ */

// Zone layout: [zone_number, x, y, width, height]
const ZONE_COORDS = {
  1: { x: 200, y: 150 },
  2: { x: 200, y: 0 },
  3: { x: 100, y: 0 },
  4: { x: 0,   y: 0 },
  5: { x: 0,   y: 150 },
  6: { x: 100, y: 150 },
};

const ZONE_W = 100;
const ZONE_H = 150;

let zonesData = null;

// ── Entry Point ─────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", async () => {
  zonesData = await loadJSON("data/zones.json");
  if (!zonesData) {
    document.querySelector(".main-content").innerHTML =
      '<p style="color:var(--red);padding:2rem">Failed to load zones data.</p>';
    return;
  }

  buildPlayerFilter();
  renderAll("all");
});

// ── Player Filter ────────────────────────────────────────────
function buildPlayerFilter() {
  const container = document.getElementById("zone-player-filter");
  if (!container) return;

  const players = Object.keys(zonesData.player_attack_zones).sort();

  const select = document.createElement("select");
  select.className = "dropdown";
  select.id = "zone-player-select";

  const defaultOpt = document.createElement("option");
  defaultOpt.value = "all";
  defaultOpt.textContent = "All Players";
  select.appendChild(defaultOpt);

  players.forEach(name => {
    const opt = document.createElement("option");
    opt.value = name;
    opt.textContent = name;
    select.appendChild(opt);
  });

  select.addEventListener("change", () => renderAll(select.value));
  container.appendChild(select);
}

// ── Master render ────────────────────────────────────────────
function renderAll(player) {
  let attackZones, receiveZones;

  if (player === "all") {
    attackZones  = zonesData.attack_zones;
    receiveZones = zonesData.receive_zones;
  } else {
    attackZones  = zonesData.player_attack_zones[player]  || [];
    receiveZones = zonesData.player_receive_zones[player] || [];
  }

  renderAttackCourt(attackZones);
  renderReceiveCourt(receiveZones);
  renderAttackTable(attackZones);
  renderReceiveTable(receiveZones);
}

// ── Color scale helper ────────────────────────────────────────
// Returns rgba string: red (low) → yellow → green (high)
function zoneColor(norm) {
  const clamped = Math.max(0, Math.min(1, norm));
  const R = Math.round(255 * (1 - clamped));
  const G = Math.round(255 * clamped);
  return `rgba(${R},${G},100,0.5)`;
}

// Normalize an array of values to [0,1]; handles all-same case
function normalizeValues(values) {
  const valid = values.filter(v => v != null && !isNaN(v));
  if (valid.length === 0) return values.map(() => 0.5);
  const min = Math.min(...valid);
  const max = Math.max(...valid);
  if (max === min) return values.map(() => 0.5);
  return values.map(v => (v == null || isNaN(v)) ? 0.5 : (v - min) / (max - min));
}

// ── SVG Court Builder ─────────────────────────────────────────
function buildCourtSVG(zoneEntries, metricFn, labelFn, topPlayerFn) {
  // Build a zone -> entry lookup by parsing the "zone" string to int
  const lookup = {};
  (zoneEntries || []).forEach(entry => {
    const zn = parseInt(entry.zone, 10);
    if (!isNaN(zn)) lookup[zn] = entry;
  });

  // Collect all metric values for normalization
  const allMetrics = [1, 2, 3, 4, 5, 6].map(zn => {
    const entry = lookup[zn];
    return entry ? metricFn(entry) : null;
  });
  const norms = normalizeValues(allMetrics);

  const zones = [1, 2, 3, 4, 5, 6];

  const rects = zones.map((zn, i) => {
    const { x, y } = ZONE_COORDS[zn];
    const entry    = lookup[zn];
    const norm     = norms[i];
    const fillClr  = zoneColor(norm);
    const metric   = entry ? metricFn(entry) : null;
    const metricTxt = entry ? labelFn(entry) : "—";
    const topPlayer = entry && topPlayerFn ? topPlayerFn(entry) : null;

    const cx = x + ZONE_W / 2;
    const cy = y + ZONE_H / 2;

    // Zone number label (top-left area of zone)
    const zoneLabelX = x + 8;
    const zoneLabelY = y + 20;

    // Metric value: center of zone
    const metricX = cx;
    const metricY = cy - 8;

    // Top player name: below metric (shortened if long)
    const playerY = cy + 14;
    const shortName = topPlayer
      ? (topPlayer.split(" ").pop() || topPlayer).substring(0, 12)
      : null;

    return `
      <rect x="${x}" y="${y}" width="${ZONE_W}" height="${ZONE_H}"
            fill="${fillClr}" stroke="rgba(148,163,184,0.3)" stroke-width="1"/>
      <text x="${zoneLabelX}" y="${zoneLabelY}"
            fill="rgba(148,163,184,0.8)" font-size="11" font-weight="600"
            font-family="system-ui,sans-serif">${zn}</text>
      <text x="${metricX}" y="${metricY}"
            fill="#f1f5f9" font-size="14" font-weight="700" text-anchor="middle"
            font-family="system-ui,sans-serif">${metricTxt}</text>
      ${shortName ? `
      <text x="${metricX}" y="${playerY}"
            fill="rgba(148,163,184,0.85)" font-size="10" text-anchor="middle"
            font-family="system-ui,sans-serif">${shortName}</text>` : ""}
    `;
  }).join("");

  // Divider lines (vertical: x=100, x=200) and net (y=150)
  const dividers = `
    <line x1="100" y1="0" x2="100" y2="300"
          stroke="rgba(148,163,184,0.25)" stroke-width="1"/>
    <line x1="200" y1="0" x2="200" y2="300"
          stroke="rgba(148,163,184,0.25)" stroke-width="1"/>
    <line x1="0" y1="150" x2="300" y2="150"
          stroke="rgba(148,163,184,0.7)" stroke-width="2"/>
    <text x="150" y="146"
          fill="rgba(148,163,184,0.7)" font-size="10" text-anchor="middle"
          font-family="system-ui,sans-serif" font-weight="600">NET</text>
  `;

  // Court outline
  const outline = `
    <rect x="0" y="0" width="300" height="300"
          fill="none" stroke="rgba(148,163,184,0.5)" stroke-width="2"/>
  `;

  return `<svg viewBox="0 0 300 300" width="100%" style="max-width:360px;display:block;margin:0 auto;">
    ${rects}
    ${outline}
    ${dividers}
  </svg>`;
}

// ── Attack Court ──────────────────────────────────────────────
function renderAttackCourt(attackZones) {
  const el = document.getElementById("attack-court");
  if (!el) return;

  el.innerHTML = buildCourtSVG(
    attackZones,
    entry => entry.hitting_eff,
    entry => {
      const v = entry.hitting_eff;
      return (v == null || isNaN(v)) ? "—" : (v >= 0 ? "+" : "") + v.toFixed(3);
    },
    entry => entry.top_player || null
  );
}

// ── Receive Court ─────────────────────────────────────────────
function renderReceiveCourt(receiveZones) {
  const el = document.getElementById("receive-court");
  if (!el) return;

  el.innerHTML = buildCourtSVG(
    receiveZones,
    entry => entry.pass_avg,
    entry => {
      const v = entry.pass_avg;
      return (v == null || isNaN(v)) ? "—" : Number(v).toFixed(2);
    },
    entry => entry.top_player || null
  );
}

// ── Sortable Table Helpers ────────────────────────────────────
function buildSortableTable(containerId, columns, rows, defaultSortCol) {
  const container = document.getElementById(containerId);
  if (!container) return;

  let workRows = rows.slice();
  let sortState = { col: defaultSortCol, dir: "asc" };

  function sortRows(col, dir) {
    const mult = dir === "asc" ? 1 : -1;
    workRows.sort((a, b) => {
      const va = a[col];
      const vb = b[col];
      if (va == null && vb == null) return 0;
      if (va == null) return mult;
      if (vb == null) return -mult;
      if (typeof va === "string") return mult * va.localeCompare(vb);
      return mult * (va - vb);
    });
  }

  function buildTable() {
    const thead = `<thead><tr>${
      columns.map(c => `<th class="sortable${c.num ? " num" : ""}" data-col="${c.key}">${c.label}</th>`).join("")
    }</tr></thead>`;

    const tbody = "<tbody>" + workRows.map(row => `<tr>${
      columns.map(c => {
        const val = row[c.key];
        const display = c.fmt ? c.fmt(val) : (val == null ? "—" : val);
        return `<td${c.num ? ' class="num"' : ""}>${display}</td>`;
      }).join("")
    }</tr>`).join("") + "</tbody>";

    const table = document.createElement("table");
    table.className = "data-table";
    table.innerHTML = thead + tbody;

    // Mark active sort column
    const activeTh = table.querySelector(`th[data-col="${sortState.col}"]`);
    if (activeTh) activeTh.classList.add(sortState.dir);

    // Sort click handlers
    table.querySelectorAll("th.sortable").forEach(th => {
      th.addEventListener("click", () => {
        const col = th.dataset.col;
        if (sortState.col === col) {
          sortState.dir = sortState.dir === "asc" ? "desc" : "asc";
        } else {
          sortState.col = col;
          sortState.dir = "asc";
        }
        sortRows(sortState.col, sortState.dir);
        container.innerHTML = "";
        container.appendChild(buildTable());
      });
    });

    return table;
  }

  // Initial sort
  sortRows(sortState.col, sortState.dir);
  container.innerHTML = "";
  container.appendChild(buildTable());
}

// ── Attack Detail Table ───────────────────────────────────────
function renderAttackTable(attackZones) {
  const rows = (attackZones || []).map(entry => ({
    zone:       parseInt(entry.zone, 10),
    kills:      entry.kills      != null ? entry.kills      : null,
    errors:     entry.errors     != null ? entry.errors     : null,
    attempts:   entry.attempts   != null ? entry.attempts   : null,
    hitting_eff: entry.hitting_eff != null ? entry.hitting_eff : null,
    top_player: entry.top_player || "—",
  }));

  const columns = [
    { key: "zone",        label: "Zone",       num: true,  fmt: v => v == null ? "—" : v },
    { key: "kills",       label: "Kills",      num: true,  fmt: v => v == null ? "—" : v },
    { key: "errors",      label: "Errors",     num: true,  fmt: v => v == null ? "—" : v },
    { key: "attempts",    label: "Attempts",   num: true,  fmt: v => v == null ? "—" : v },
    { key: "hitting_eff", label: "Eff",        num: true,  fmt: v => v == null ? "—" : (v >= 0 ? "+" : "") + v.toFixed(3) },
    { key: "top_player",  label: "Top Player", num: false, fmt: v => v || "—" },
  ];

  buildSortableTable("attack-detail-table", columns, rows, "zone");
}

// ── Receive Detail Table ──────────────────────────────────────
function renderReceiveTable(receiveZones) {
  const rows = (receiveZones || []).map(entry => ({
    zone:      parseInt(entry.zone, 10),
    pass_avg:  entry.pass_avg  != null ? entry.pass_avg  : null,
    attempts:  entry.attempts  != null ? entry.attempts  : null,
    top_player: entry.top_player || "—",
  }));

  const columns = [
    { key: "zone",      label: "Zone",       num: true,  fmt: v => v == null ? "—" : v },
    { key: "pass_avg",  label: "Pass Avg",   num: true,  fmt: v => v == null ? "—" : Number(v).toFixed(2) },
    { key: "attempts",  label: "Total",      num: true,  fmt: v => v == null ? "—" : v },
    { key: "top_player", label: "Top Player", num: false, fmt: v => v || "—" },
  ];

  buildSortableTable("receive-detail-table", columns, rows, "zone");
}
