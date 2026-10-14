// ===========================================================
// site.js — public pages (index, about, contact, chatbot)
// Preserves: /api/me check on #authNavLink, /api/contact on #contactForm
// Adds: Mobile nav toggling and accessible micro-interactions
// ===========================================================
const API_BASE = ""; // same origin — Flask serves both site and API

// Swap "Log in" nav link for "Dashboard" if session is already active
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

// Mobile Navigation Toggle
document.addEventListener("DOMContentLoaded", () => {
  const toggleBtn = document.getElementById("mobileToggle");
  const navLinks = document.querySelector(".nav-links");
  if (toggleBtn && navLinks) {
    toggleBtn.addEventListener("click", () => {
      navLinks.classList.toggle("mobile-open");
      const expanded = navLinks.classList.contains("mobile-open");
      toggleBtn.setAttribute("aria-expanded", expanded);
    });
  }
});

// Contact form (public, no auth required)
const contactForm = document.getElementById("contactForm");
if (contactForm) {
  contactForm.addEventListener("submit", async e => {
    e.preventDefault();
    const status = document.getElementById("formStatus");
    const submitBtn = contactForm.querySelector('button[type="submit"]');
    if (submitBtn) {
      submitBtn.disabled = true;
      submitBtn.textContent = "Sending...";
    }
    const payload = {
      name: document.getElementById("name").value.trim(),
      email: document.getElementById("email").value.trim(),
      message: document.getElementById("message").value.trim()
    };
    try {
      await fetch(`${API_BASE}/api/contact`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      if (status) {
        status.textContent = "Message sent successfully — we'll get back to you soon.";
        status.style.display = "block";
      }
      contactForm.reset();
    } catch (err) {
      console.warn("Contact backend not reachable.", err);
      if (status) {
        status.textContent = "Could not reach the server, but your draft is preserved.";
        status.style.display = "block";
      }
    } finally {
      if (submitBtn) {
        submitBtn.disabled = false;
        submitBtn.textContent = "Send message";
      }
    }
  });
}
