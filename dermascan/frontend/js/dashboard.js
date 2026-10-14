// ===========================================================
// dashboard.js — used on dashboard.html
// Preserves: requireAuth(), fetch stats, renders stat cards, SVG donut & recent scans
// Updated: Light-theme condition colors, crisp SVG donut track & accessible badges
// ===========================================================
const CONDITION_COLORS = {
  "Actinic Keratosis": "#E9785B",      // Contrasting Coral
  "Basal Cell Carcinoma": "#B83E48",  // Deep Rose
  "Benign Keratosis": "#7C6FC4",      // Lavender Violet
  "Dermatofibroma": "#0E827B",        // Clinical Teal
  "Melanocytic Nevi": "#2C6ECB",      // Medical Blue
  "Vascular Lesion": "#237A57",       // Forest Emerald
  Melanoma: "#DC2626",                // Flagged Red
  Eczema: "#14B8A6",
  Acne: "#D97706",
  Psoriasis: "#8B5CF6"
};

async function loadDashboard() {
  await requireAuth(); // from guard.js — redirects to login if not authed

  try {
    const res = await fetch(`${API_BASE}/api/dashboard/stats`, { credentials: "include" });
    if (!res.ok) throw new Error("Could not load dashboard stats");
    const data = await res.json();
    renderStatCards(data);
    renderDonut(data.condition_counts);
    renderRecentScans(data.recent);
  } catch (err) {
    console.error(err);
    const recentEl = document.getElementById("recentScans");
    if (recentEl) {
      recentEl.innerHTML =
        `<p class="empty-note">Could not reach the backend. Make sure the Flask server is running.</p>`;
    }
  }
}

function renderStatCards(data) {
  const statTotal = document.getElementById("statTotal");
  const statTop = document.getElementById("statTop");
  const statAvgConf = document.getElementById("statAvgConf");
  const statFlagged = document.getElementById("statFlagged");

  if (statTotal) statTotal.textContent = data.total_scans;
  if (statTop) statTop.textContent = data.most_common || "—";
  if (statAvgConf) {
    statAvgConf.textContent = data.total_scans ? `${(data.avg_confidence * 100).toFixed(0)}%` : "—";
  }
  if (statFlagged) statFlagged.textContent = data.melanoma_flags;
}

function renderDonut(counts) {
  const container = document.getElementById("donutContainer");
  if (!container) return;

  const total = Object.values(counts || {}).reduce((a, b) => a + b, 0);

  if (!total) {
    container.innerHTML = `<p class="empty-note">No scans recorded yet. Upload an image in "New scan" to view your personal condition breakdown.</p>`;
    return;
  }

  const size = 160, stroke = 22, radius = (size - stroke) / 2, circumference = 2 * Math.PI * radius;
  let offset = 0;
  let circles = "";
  let legend = "";

  Object.entries(counts).forEach(([label, count]) => {
    if (!count) return;
    const fraction = count / total;
    const dash = fraction * circumference;
    const color = CONDITION_COLORS[label] || "#647773";
    circles += `<circle cx="${size/2}" cy="${size/2}" r="${radius}" fill="none" stroke="${color}"
      stroke-width="${stroke}" stroke-dasharray="${dash} ${circumference - dash}"
      stroke-dashoffset="${-offset}" transform="rotate(-90 ${size/2} ${size/2})" />`;
    offset += dash;
    legend += `
      <div class="legend-row">
        <span class="legend-swatch" style="background:${color}"></span>
        <span>${label}</span>
        <span class="pct">${Math.round(fraction * 100)}%</span>
      </div>`;
  });

  container.innerHTML = `
    <div class="donut-wrap">
      <svg width="${size}" height="${size}" viewBox="0 0 ${size} ${size}">
        <circle cx="${size/2}" cy="${size/2}" r="${radius}" fill="none" stroke="#E4E9E2" stroke-width="${stroke}" />
        ${circles}
      </svg>
      <div class="donut-legend">${legend}</div>
    </div>
  `;
}

function renderRecentScans(scans) {
  const list = document.getElementById("recentScans");
  if (!list) return;

  if (!scans || !scans.length) {
    list.innerHTML = `<p class="empty-note">No scans yet — click "+ New scan" to analyze your first dermal image.</p>`;
    return;
  }

  list.innerHTML = scans.map(scan => {
    const color = CONDITION_COLORS[scan.prediction] || "#647773";
    const initials = (scan.prediction || "SC").substring(0, 2).toUpperCase();
    const date = new Date(scan.created_at).toLocaleString();
    return `
      <div class="scan-row">
        <div class="dot-ic" style="background:${color}18; color:${color}; border:1px solid ${color}33;">${initials}</div>
        <div class="info">
          <div class="cond">${scan.prediction}</div>
          <div class="time">${date}</div>
        </div>
        <div class="conf">${(scan.confidence * 100).toFixed(1)}%</div>
      </div>
    `;
  }).join("");
}

loadDashboard();
