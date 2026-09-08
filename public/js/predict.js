// ===========================================================
// predict.js — used on predict.html (protected page)
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

["dragenter", "dragover"].forEach(evt =>
  dropzone.addEventListener(evt, e => { e.preventDefault(); dropzone.classList.add("drag-over"); })
);
["dragleave", "drop"].forEach(evt =>
  dropzone.addEventListener(evt, e => { e.preventDefault(); dropzone.classList.remove("drag-over"); })
);
dropzone.addEventListener("drop", e => {
  const file = e.dataTransfer.files[0];
  if (file) handleFile(file);
});
fileInput.addEventListener("change", e => {
  const file = e.target.files[0];
  if (file) handleFile(file);
});

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

analyzeBtn.addEventListener("click", async () => {
  if (!selectedFile) return;

  analyzeBtn.disabled = true;
  analyzeBtn.textContent = "Analyzing...";
  previewWrap.classList.add("scanning");

  const formData = new FormData();
  formData.append("image", selectedFile);

  try {
    const res = await fetch(`${API_BASE}/api/predict`, {
      method: "POST",
      credentials: "include", // sends the session cookie so the backend can save this scan to your history
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

function renderResult(data) {
  resultEmpty.style.display = "none";
  resultContent.style.display = "block";

  const sorted = Object.entries(data.probabilities).sort((a, b) => b[1] - a[1]);
  const isMelanoma = data.prediction.toLowerCase() === "melanoma";

  let html = `
    <div class="top-result">
      <div>
        <div style="color:var(--text-muted); font-size:0.82rem; margin-bottom:4px;">Predicted condition</div>
        <div class="label">${data.prediction}</div>
      </div>
      <div class="confidence">${(data.confidence * 100).toFixed(1)}%</div>
    </div>
  `;

  if (isMelanoma) {
    html += `<div class="flag-note">⚠ Melanoma indicators detected — please consult a dermatologist for a clinical diagnosis.</div>`;
  }

  sorted.forEach(([label, prob]) => {
    const pct = (prob * 100).toFixed(1);
    html += `
      <div class="bar-row">
        <div class="bar-row-head"><span>${label}</span><span>${pct}%</span></div>
        <div class="bar-track"><div class="bar-fill" data-pct="${pct}"></div></div>
      </div>
    `;
  });

  html += `<p class="disclaimer">This is an AI-generated first read, not a medical diagnosis. Always confirm with a licensed dermatologist.</p>`;
  html += `<p class="saved-note">✓ Saved to your dashboard history.</p>`;

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
      Could not reach the prediction server. Make sure the Flask backend is running, then try again.
    </div>
  `;
  console.error(err);
}
