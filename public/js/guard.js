// ===========================================================
// guard.js — protects dashboard.html and predict.html
// Redirects to login.html if there's no active session, and
// fills in the sidebar user card once auth is confirmed.
// ===========================================================
const API_BASE = "";
let CURRENT_USER = null;

async function requireAuth() {
  try {
    const res = await fetch(`${API_BASE}/api/me`, { credentials: "include" });
    if (!res.ok) throw new Error("not logged in");
    const data = await res.json();
    CURRENT_USER = data.user;
    renderUserCard(data.user);
    return data.user;
  } catch (e) {
    window.location.href = "login.html";
    return null;
  }
}

function renderUserCard(user) {
  const nameEl = document.getElementById("userName");
  const emailEl = document.getElementById("userEmail");
  const avatarEl = document.getElementById("userAvatar");
  const greetingEl = document.getElementById("greeting");
  if (nameEl) nameEl.textContent = user.name;
  if (emailEl) emailEl.textContent = user.email;
  if (avatarEl) avatarEl.textContent = user.name.charAt(0).toUpperCase();
  if (greetingEl) greetingEl.textContent = `Welcome back, ${user.name.split(" ")[0]}`;
}

const logoutBtn = document.getElementById("logoutBtn");
if (logoutBtn) {
  logoutBtn.addEventListener("click", async () => {
    await fetch(`${API_BASE}/api/logout`, { method: "POST", credentials: "include" });
    window.location.href = "login.html";
  });
}

// Run immediately on every protected page that includes this script
requireAuth();
