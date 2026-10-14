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

// ===========================================================
// Cinematic Signature Hero Visual Telemetry & 3D Tilt Controller
// ===========================================================
(function initHeroVisualInteraction() {
  const heroCard = document.getElementById("heroVisualCard");
  const specimen = document.getElementById("specimenContainer");
  const statusLabel = document.getElementById("heroScanStatus");
  const statusPill = document.getElementById("heroScanStatusPill");

  if (!heroCard) return;

  // 1. Telemetry Stage Status Synchronizer (10s continuous cycle)
  if (statusLabel) {
    const cycleStages = [
      { text: "NEURAL SCAN ACTIVE", time: 0 },
      { text: "SPECTRAL MAPPING", time: 2200 },
      { text: "ABCDE EXTRACTION", time: 4800 },
      { text: "PATTERN VERIFIED", time: 7600 },
      { text: "CYCLE SYNCHRONIZED", time: 9200 }
    ];

    let startTime = performance.now();
    let currentStageIndex = -1;

    function updateScanStage(now) {
      const elapsed = (now - startTime) % 10000;
      let activeIndex = 0;
      for (let i = cycleStages.length - 1; i >= 0; i--) {
        if (elapsed >= cycleStages[i].time) {
          activeIndex = i;
          break;
        }
      }

      if (activeIndex !== currentStageIndex) {
        currentStageIndex = activeIndex;
        statusLabel.style.opacity = "0.4";
        setTimeout(() => {
          statusLabel.textContent = cycleStages[activeIndex].text;
          statusLabel.style.opacity = "1";
        }, 120);
      }

      requestAnimationFrame(updateScanStage);
    }

    // Only run continuous ticker if user hasn't requested reduced motion
    const prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (!prefersReducedMotion) {
      requestAnimationFrame(updateScanStage);
    }
  }

  // 2. Subtle 3D Pointer Parallax Tilt (Desktop / Fine Pointer Only)
  const isFinePointer = window.matchMedia("(pointer: fine)").matches;
  const prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  if (isFinePointer && !prefersReducedMotion) {
    let bounds = null;
    let targetTiltX = 0;
    let targetTiltY = 0;
    let currentTiltX = 0;
    let currentTiltY = 0;
    let isHovering = false;
    let rafId = null;

    function renderParallax() {
      // Smooth interpolation (lerp factor 0.1)
      currentTiltX += (targetTiltX - currentTiltX) * 0.1;
      currentTiltY += (targetTiltY - currentTiltY) * 0.1;

      heroCard.style.transform = `perspective(1000px) rotateX(${currentTiltX.toFixed(2)}deg) rotateY(${currentTiltY.toFixed(2)}deg)`;
      
      if (specimen) {
        // Specimen counter-movement adds organic physical depth
        const specOffsetX = (-currentTiltY * 1.5).toFixed(1);
        const specOffsetY = (currentTiltX * 1.5).toFixed(1);
        specimen.style.transform = `translate3d(${specOffsetX}px, ${specOffsetY}px, 25px)`;
      }

      // Keep animation running smoothly until resting
      if (isHovering || Math.abs(targetTiltX - currentTiltX) > 0.02 || Math.abs(targetTiltY - currentTiltY) > 0.02) {
        rafId = requestAnimationFrame(renderParallax);
      } else {
        heroCard.style.transform = "";
        if (specimen) specimen.style.transform = "";
        rafId = null;
      }
    }

    heroCard.addEventListener("pointerenter", () => {
      bounds = heroCard.getBoundingClientRect();
      isHovering = true;
      if (!rafId) rafId = requestAnimationFrame(renderParallax);
    });

    heroCard.addEventListener("pointermove", (e) => {
      if (!bounds) bounds = heroCard.getBoundingClientRect();
      const mouseX = e.clientX - bounds.left;
      const mouseY = e.clientY - bounds.top;

      const normX = (mouseX / bounds.width) * 2 - 1;
      const normY = (mouseY / bounds.height) * 2 - 1;

      // Restrained max tilt of 5 degrees for sophisticated medical feel
      targetTiltX = -normY * 4.5;
      targetTiltY = normX * 4.5;

      if (!rafId) rafId = requestAnimationFrame(renderParallax);
    });

    heroCard.addEventListener("pointerleave", () => {
      isHovering = false;
      targetTiltX = 0;
      targetTiltY = 0;
      bounds = null;
    });

    window.addEventListener("resize", () => {
      if (heroCard) bounds = heroCard.getBoundingClientRect();
    }, { passive: true });
  }
})();
