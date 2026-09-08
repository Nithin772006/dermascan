// ===========================================================
// site.js — used on public pages (index, about, contact)
// ===========================================================
const API_BASE = ""; // same origin — Flask serves both the site and the API

// Swap "Log in" nav link for "Dashboard" if a session is already active
(async function checkAuthForNav() {
  const link = document.getElementById("authNavLink");
  if (!link) return;
  try {
    const res = await fetch(`${API_BASE}/api/me`, { credentials: "include" });
    if (res.ok) {
      link.textContent = "Dashboard";
      link.href = "dashboard.html";
    }
  } catch (e) {
    // backend not reachable yet — leave default "Log in" link
  }
})();

// Contact form (public, no auth required)
const contactForm = document.getElementById("contactForm");
if (contactForm) {
  contactForm.addEventListener("submit", async e => {
    e.preventDefault();
    const payload = {
      name: document.getElementById("name").value,
      email: document.getElementById("email").value,
      message: document.getElementById("message").value
    };
    const status = document.getElementById("formStatus");
    try {
      await fetch(`${API_BASE}/api/contact`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
    } catch (err) {
      console.warn("Contact backend not reachable.", err);
    }
    status.style.display = "block";
    contactForm.reset();
  });
}
