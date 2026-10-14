// ===========================================================
// predict.js — used on predict.html (protected page)
// Preserves: requireAuth(), drag-and-drop, /api/predict POST multipart,
// DOM IDs: dropzone, fileInput, previewWrap, previewImg, analyzeBtn, resetBtn, resultEmpty, resultContent
// ===========================================================
requireAuth(); // from guard.js

const dropzone = document.getElementById("dropzone");
const fileInput = document.getElementById("fileInput");
const previewWrap = document.getElementById("previewWrap");
const previewImg = document.getElementById("previewImg");
const analyzeBtn = document.getElementById("analyzeBtn");
const resetBtn = document.getElementById("resetBtn");
const resultEmpty = document.getElementById("resultEmpty");
const resultContent = document.getElementById("resultContent");

let selectedFile = null;

if (dropzone && fileInput) {
  ["dragenter", "dragover"].forEach(evt =>
    dropzone.addEventListener(evt, e => {
      e.preventDefault();
      dropzone.classList.add("drag-over");
    })
  );
  ["dragleave", "drop"].forEach(evt =>
    dropzone.addEventListener(evt, e => {
      e.preventDefault();
      dropzone.classList.remove("drag-over");
    })
  );
  dropzone.addEventListener("drop", e => {
    const file = e.dataTransfer.files[0];
    if (file) handleFile(file);
  });
  fileInput.addEventListener("change", e => {
    const file = e.target.files[0];
    if (file) handleFile(file);
  });
}

function handleFile(file) {
  if (!file.type.startsWith("image/")) {
    alert("Please upload an image file (JPG or PNG).");
    return;
  }
  selectedFile = file;
  const reader = new FileReader();
  reader.onload = e => {
    previewImg.src = e.target.result;
    previewWrap.style.display = "block";
    analyzeBtn.disabled = false;
  };
  reader.readAsDataURL(file);
}

if (resetBtn) {
  resetBtn.addEventListener("click", () => {
    selectedFile = null;
    fileInput.value = "";
    previewWrap.style.display = "none";
    previewWrap.classList.remove("scanning");
    analyzeBtn.disabled = true;
    resultEmpty.style.display = "flex";
    resultContent.style.display = "none";
    resultContent.innerHTML = "";
  });
}

if (analyzeBtn) {
  analyzeBtn.addEventListener("click", async () => {
    if (!selectedFile) return;

    analyzeBtn.disabled = true;
    analyzeBtn.textContent = "Analyzing scan...";
    previewWrap.classList.add("scanning");

    const formData = new FormData();
    formData.append("image", selectedFile);

    try {
      const res = await fetch(`${API_BASE}/api/predict`, {
        method: "POST",
        credentials: "include", // sends session cookie to save scan to history
        body: formData
      });
      if (res.status === 401) {
        window.location.href = "login.html";
        return;
      }
      if (!res.ok) throw new Error("Prediction request failed");
      const data = await res.json();
      renderResult(data);
    } catch (err) {
      renderError(err);
    } finally {
      previewWrap.classList.remove("scanning");
      analyzeBtn.disabled = false;
      analyzeBtn.textContent = "Analyze image";
    }
  });
}

function renderResult(data) {
  resultEmpty.style.display = "none";
  resultContent.style.display = "block";

  const sorted = Object.entries(data.probabilities || {}).sort((a, b) => b[1] - a[1]);
  const isMelanoma = (data.prediction || "").toLowerCase() === "melanoma";

  let html = `
    <div class="top-result">
      <div>
        <div style="color:var(--ink-secondary); font-size:0.84rem; font-weight:600; margin-bottom:4px; text-transform:uppercase; letter-spacing:0.04em;">Predicted condition</div>
        <div class="label">${data.prediction}</div>
      </div>
      <div class="confidence">${(data.confidence * 100).toFixed(1)}%</div>
    </div>
  `;

  if (isMelanoma) {
    html += `
      <div class="flag-note">
        <span>⚠</span>
        <div><strong>Clinical Attention Flag:</strong> Melanoma indicators were highlighted by the classifier. Please consult a qualified dermatologist for an in-person clinical biopsy and evaluation.</div>
      </div>
    `;
  }

  html += `<div style="margin-bottom:12px; font-size:0.86rem; font-weight:700; color:var(--ink);">Probability Distribution</div>`;

  sorted.forEach(([label, prob]) => {
    const pct = (prob * 100).toFixed(1);
    html += `
      <div class="bar-row">
        <div class="bar-row-head"><span>${label}</span><span>${pct}%</span></div>
        <div class="bar-track"><div class="bar-fill" data-pct="${pct}"></div></div>
      </div>
    `;
  });

  html += `
    <p class="disclaimer">
      <strong>Medical Disclaimer:</strong> DermaScan AI provides automated image analysis for educational and preliminary screening assistance. This is not a definitive diagnosis. Always consult a healthcare professional for clinical decisions.
    </p>
    <div class="saved-note">
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><path d="M20 6L9 17l-5-5"/></svg>
      Saved to your personal dashboard history.
    </div>
  `;

  resultContent.innerHTML = html;

  requestAnimationFrame(() => {
    resultContent.querySelectorAll(".bar-fill").forEach(bar => {
      bar.style.width = bar.dataset.pct + "%";
    });
  });
}

function renderError(err) {
  resultEmpty.style.display = "none";
  resultContent.style.display = "block";
  resultContent.innerHTML = `
    <div class="flag-note">
      <span>⚠</span>
      <div>Could not reach the prediction service. Please ensure the local server is running and try again.</div>
    </div>
  `;
  console.error(err);
}
