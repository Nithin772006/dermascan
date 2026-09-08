// ===========================================================
// auth.js — used on login.html and signup.html
// ===========================================================
const API_BASE = "";

function showAuthError(message) {
  const el = document.getElementById("authError");
  el.textContent = message;
  el.style.display = "block";
}

const loginForm = document.getElementById("loginForm");
if (loginForm) {
  loginForm.addEventListener("submit", async e => {
    e.preventDefault();
    const btn = document.getElementById("loginBtn");
    btn.disabled = true;
    btn.textContent = "Logging in...";

    const payload = {
      email: document.getElementById("email").value.trim(),
      password: document.getElementById("password").value
    };

    try {
      const res = await fetch(`${API_BASE}/api/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify(payload)
      });
      let data;
      const ct = res.headers.get("content-type") || "";
      if (ct.includes("application/json")) {
        data = await res.json();
      } else {
        const text = await res.text();
        if (text.includes("Vercel") && text.includes("Login")) {
          throw new Error("Vercel Deployment Protection is active. Please turn off 'Vercel Authentication' in Vercel Project Settings -> Deployment Protection.");
        }
        throw new Error(res.status === 404 ? "API route /api/login not found (404)." : `Server returned non-JSON (${res.status})`);
      }
      if (!res.ok) throw new Error(data.error || "Login failed");
      window.location.href = "dashboard.html";
    } catch (err) {
      showAuthError(err.message);
      btn.disabled = false;
      btn.textContent = "Log in";
    }
  });
}

const signupForm = document.getElementById("signupForm");
if (signupForm) {
  signupForm.addEventListener("submit", async e => {
    e.preventDefault();
    const btn = document.getElementById("signupBtn");

    const password = document.getElementById("password").value;
    const confirmPassword = document.getElementById("confirmPassword").value;
    if (password !== confirmPassword) {
      showAuthError("Passwords don't match.");
      return;
    }

    btn.disabled = true;
    btn.textContent = "Creating account...";

    const payload = {
      name: document.getElementById("name").value.trim(),
      email: document.getElementById("email").value.trim(),
      password
    };

    try {
      const res = await fetch(`${API_BASE}/api/signup`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify(payload)
      });
      let data;
      const ct = res.headers.get("content-type") || "";
      if (ct.includes("application/json")) {
        data = await res.json();
      } else {
        const text = await res.text();
        if (text.includes("Vercel") && text.includes("Login")) {
          throw new Error("Vercel Deployment Protection is active. Please turn off 'Vercel Authentication' in Vercel Project Settings -> Deployment Protection.");
        }
        throw new Error(res.status === 404 ? "API route /api/signup not found (404)." : `Server returned non-JSON (${res.status})`);
      }
      if (!res.ok) throw new Error(data.error || "Sign up failed");
      window.location.href = "dashboard.html";
    } catch (err) {
      showAuthError(err.message);
      btn.disabled = false;
      btn.textContent = "Create account";
    }
  });
}
