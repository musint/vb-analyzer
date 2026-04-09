/* ============================================================
   13-2 Statistical Deep Dive — Shared Application Logic
   ============================================================ */

// Highlight active nav tab based on current page
document.addEventListener("DOMContentLoaded", () => {
  const path = window.location.pathname.split("/").pop() || "index.html";
  document.querySelectorAll("nav a").forEach(a => {
    const href = a.getAttribute("href");
    if (href === path || (path === "" && href === "index.html")) {
      a.classList.add("active");
    }
  });

  // Staggered animation for cards and KPI items
  document.querySelectorAll(".card, .kpi-card").forEach((el, i) => {
    el.classList.add("animate-in");
    el.style.animationDelay = `${0.05 + i * 0.05}s`;
  });
});

// Shared data loading utility
async function loadJSON(path) {
  try {
    const response = await fetch(path);
    if (!response.ok) throw new Error(`Failed to load ${path}`);
    return await response.json();
  } catch (e) {
    console.error(e);
    return null;
  }
}

// Shared Plotly layout defaults for dark theme
const PLOTLY_DARK_LAYOUT = {
  paper_bgcolor: "rgba(0,0,0,0)",
  plot_bgcolor: "rgba(0,0,0,0)",
  font: {
    family: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
    color: "#94a3b8",
    size: 12,
  },
  margin: { t: 32, r: 16, b: 40, l: 48 },
  xaxis: {
    gridcolor: "rgba(51,65,85,0.5)",
    zerolinecolor: "rgba(51,65,85,0.5)",
    tickfont: { color: "#94a3b8" },
  },
  yaxis: {
    gridcolor: "rgba(51,65,85,0.5)",
    zerolinecolor: "rgba(51,65,85,0.5)",
    tickfont: { color: "#94a3b8" },
  },
  legend: {
    font: { color: "#94a3b8" },
    bgcolor: "rgba(0,0,0,0)",
  },
  hoverlabel: {
    bgcolor: "#1e293b",
    bordercolor: "#334155",
    font: { color: "#f1f5f9", size: 13 },
  },
};

// Shared Plotly config
const PLOTLY_CONFIG = {
  responsive: true,
  displaylogo: false,
  modeBarButtonsToRemove: [
    "select2d", "lasso2d", "autoScale2d",
    "hoverClosestCartesian", "hoverCompareCartesian",
    "toggleSpikelines",
  ],
};

// Helper: merge custom layout with dark defaults
function darkLayout(overrides = {}) {
  return Object.assign({}, PLOTLY_DARK_LAYOUT, overrides, {
    xaxis: Object.assign({}, PLOTLY_DARK_LAYOUT.xaxis, overrides.xaxis || {}),
    yaxis: Object.assign({}, PLOTLY_DARK_LAYOUT.yaxis, overrides.yaxis || {}),
    legend: Object.assign({}, PLOTLY_DARK_LAYOUT.legend, overrides.legend || {}),
  });
}

// Helper: format percentage
function fmtPct(val, decimals = 1) {
  if (val == null || isNaN(val)) return "—";
  return (val * 100).toFixed(decimals) + "%";
}

// Helper: format number
function fmtNum(val, decimals = 1) {
  if (val == null || isNaN(val)) return "—";
  return Number(val).toFixed(decimals);
}
