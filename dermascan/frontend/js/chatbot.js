// ===========================================================
// chatbot.js — simple rule-based AI Bot (no API key needed)
// Matches keywords in the question to a canned, informative answer.
// ===========================================================
const KNOWLEDGE_BASE = [
  {
    keywords: ["eczema"],
    answer: "Eczema (atopic dermatitis) causes dry, itchy, inflamed patches of skin, often in skin folds like elbows and knees. It's a chronic condition often linked to allergies or a sensitive skin barrier. DermaScan can flag it from an image, but a dermatologist should confirm and guide treatment."
  },
  {
    keywords: ["melanoma", "cancer", "warning sign", "abcde"],
    answer: "Melanoma is the most serious type of skin cancer. Common warning signs follow the 'ABCDE' rule: Asymmetry, Border irregularity, Color variation, Diameter over 6mm, and Evolving size/shape. If DermaScan flags melanoma, please see a dermatologist promptly — early detection matters a lot here."
  },
  {
    keywords: ["acne"],
    answer: "Acne happens when hair follicles get clogged with oil and dead skin cells, causing pimples, blackheads or cysts — most common on the face, chest and back. It's usually manageable with topical treatments; a dermatologist can help with persistent or severe cases."
  },
  {
    keywords: ["psoriasis"],
    answer: "Psoriasis is a chronic autoimmune condition that speeds up skin cell turnover, causing thick, scaly, red or silvery patches — often on the scalp, elbows and knees. It tends to flare and settle over time and is managed rather than cured."
  },
  {
    keywords: ["actinic keratosis", "akiec"],
    answer: "Actinic Keratosis is a rough, scaly patch on sun-damaged skin considered a precancerous lesion. It can potentially develop into squamous cell carcinoma if left untreated, so dermatological evaluation is recommended."
  },
  {
    keywords: ["basal cell", "bcc", "carcinoma"],
    answer: "Basal Cell Carcinoma is the most common form of skin cancer. It frequently appears as a slightly transparent or pearly bump, often on sun-exposed areas like the face or neck. It rarely metastasizes but requires medical excision or treatment."
  },
  {
    keywords: ["benign keratosis", "seborrheic", "bkl"],
    answer: "Benign Keratosis (such as seborrheic keratosis or solar lentigines) are non-cancerous skin growths that often appear waxy, scaly, or slightly elevated. While harmless, a dermatologist can help confirm they are benign."
  },
  {
    keywords: ["dermatofibroma", "df"],
    answer: "Dermatofibroma is a harmless, common benign skin nodule usually found on the arms or legs, often feeling like a small, firm pea under the skin with a brownish or pinkish hue."
  },
  {
    keywords: ["nevi", "nevus", "mole", "melanocytic"],
    answer: "Melanocytic Nevi (common moles) are benign proliferations of pigment-producing melanocytes. Routine monitoring of mole size, shape, and color using the ABCDE rule is best practice."
  },
  {
    keywords: ["vascular lesion", "angioma", "vasc"],
    answer: "Vascular lesions include cherry angiomas, hemangiomas, and pyogenic granulomas, caused by abnormal clusters of blood vessels in the skin. They are typically benign."
  },
  {
    keywords: ["how does the model work", "model work", "architecture", "cnn", "how it works"],
    answer: "DermaScan uses a Convolutional Neural Network built on MobileNetV2 (transfer learning with ImageNet weights). An uploaded image is preprocessed and resized to 224x224, passed through the MobileNetV2 feature extractor, and classified across the 7 HAM10000 clinical lesion categories."
  },
  {
    keywords: ["accurate", "accuracy", "how good", "reliable"],
    answer: "Accuracy depends on the training data and how many epochs the model was trained for — the MobileNetV2 transfer learning model achieves strong generalization on the balanced HAM10000 benchmark. DermaScan is meant as an assistive clinical triage tool, not a replacement for a dermatologist's formal diagnosis."
  },
  {
    keywords: ["dataset", "ham10000", "training data"],
    answer: "The model is trained on the HAM10000 dataset ('Human Against Machine with 10,000 training images'), a premier medical dermatology benchmark containing 10,015 dermatoscopic images across 7 diagnostic categories."
  },
  {
    keywords: ["dashboard", "history", "scans", "track"],
    answer: "Once you sign up and log in, every scan you run on the Diagnose page is saved automatically. Your Dashboard shows total scans, a condition breakdown, average confidence, and your most recent results."
  },
  {
    keywords: ["login", "signup", "account", "sign up"],
    answer: "You can create a free account from the Sign up page — it just needs your name, email and a password. Once logged in, your scan history is tracked on your personal Dashboard."
  },
  {
    keywords: ["team", "who made", "bug slayers", "college", "rec"],
    answer: "This project was built by team Bug Slayers, AIDS department, Rajalakshmi Engineering College, Chennai, as an internship project."
  },
  {
    keywords: ["hi", "hello", "hey"],
    answer: "Hey! Ask me anything about eczema, melanoma, acne, psoriasis, or how DermaScan AI works."
  }
];

const FALLBACK_ANSWER = "I don't have a specific answer for that yet — try asking about eczema, melanoma, acne, psoriasis, the model, the dataset, or your dashboard. For anything about your own skin, please consult a dermatologist.";

function findAnswer(question) {
  const q = question.toLowerCase();
  for (const entry of KNOWLEDGE_BASE) {
    if (entry.keywords.some(k => q.includes(k))) {
      return entry.answer;
    }
  }
  return FALLBACK_ANSWER;
}

const chatWindow = document.getElementById("chatWindow");
const chatInput = document.getElementById("chatInput");
const sendBtn = document.getElementById("sendBtn");

function addMessage(text, sender) {
  const div = document.createElement("div");
  div.className = `chat-msg ${sender}`;
  div.textContent = text;
  chatWindow.appendChild(div);
  chatWindow.scrollTop = chatWindow.scrollHeight;
}

function handleSend(question) {
  const text = (question || chatInput.value).trim();
  if (!text) return;
  addMessage(text, "user");
  chatInput.value = "";
  setTimeout(() => {
    addMessage(findAnswer(text), "bot");
  }, 400); // small delay so it feels like it's "thinking"
}

sendBtn.addEventListener("click", () => handleSend());
chatInput.addEventListener("keydown", e => {
  if (e.key === "Enter") handleSend();
});
document.querySelectorAll(".chat-chip").forEach(chip => {
  chip.addEventListener("click", () => handleSend(chip.dataset.q));
});
