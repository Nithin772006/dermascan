// ===========================================================
// dashboard.js — used on dashboard.html
// ===========================================================
const CONDITION_COLORS = {
  "Actinic Keratosis": "#f97316",
  "Basal Cell Carcinoma": "#e11d48",
  "Benign Keratosis": "#8b5cf6",
  "Dermatofibroma": "#06b6d4",
  "Melanocytic Nevi": "#3b82f6",
  "Vascular Lesion": "#10b981",
  Melanoma: "#fb7185",
  Eczema: "#4fe8c9",
  Acne: "#ffb970",
  Psoriasis: "#a78bfa"
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
    document.getElementById("recentScans").innerHTML =
      `<p class="empty-note">Could not reach the backend. Make sure the Flask server is running.</p>`;
  }
}

function renderStatCards(data) {
  document.getElementById("statTotal").textContent = data.total_scans;
  document.getElementById("statTop").textContent = data.most_common || "—";
  document.getElementById("statAvgConf").textContent =
    data.total_scans ? `${(data.avg_confidence * 100).toFixed(0)}%` : "—";
  document.getElementById("statFlagged").textContent = data.melanoma_flags;
}

function renderDonut(counts) {
  const container = document.getElementById("donutContainer");
  const total = Object.values(counts).reduce((a, b) => a + b, 0);

  if (!total) {
    container.innerHTML = `<p class="empty-note">No scans yet — run your first analysis to see a breakdown here.</p>`;
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
    const color = CONDITION_COLORS[label] || "#8d9bb5";
    circles += `<circle cx="${size/2}" cy="${size/2}" r="${radius}" fill="none" stroke="${color}"
      stroke-width="${stroke}" stroke-dasharray="${dash} ${circumference - dash}"
      stroke-dashoffset="${-offset}" transform="rotate(-90 ${size/2} ${size/2})" />`;
    offset += dash;
    legend += `<div class="legend-row"><span class="legend-swatch" style="background:${color}"></span>
      ${label} <span class="pct">${Math.round(fraction * 100)}%</span></div>`;
  });

  container.innerHTML = `
    <div class="donut-wrap">
      <svg width="${size}" height="${size}" viewBox="0 0 ${size} ${size}">
        <circle cx="${size/2}" cy="${size/2}" r="${radius}" fill="none" stroke="#182339" stroke-width="${stroke}" />
        ${circles}
      </svg>
      <div class="donut-legend">${legend}</div>
    </div>
  `;
}

function renderRecentScans(scans) {
  const list = document.getElementById("recentScans");
  if (!scans || !scans.length) {
    list.innerHTML = `<p class="empty-note">No scans yet — click "New scan" to analyze your first image.</p>`;
    return;
  }

  list.innerHTML = scans.map(scan => {
    const color = CONDITION_COLORS[scan.prediction] || "#8d9bb5";
    const initials = scan.prediction.substring(0, 2).toUpperCase();
    const date = new Date(scan.created_at).toLocaleString();
    return `
      <div class="scan-row">
        <div class="dot-ic" style="background:${color}22; color:${color};">${initials}</div>
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
