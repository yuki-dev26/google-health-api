const qaEl = document.getElementById("qa");
const qaEmptyEl = document.getElementById("qa-empty");
const formEl = document.getElementById("form");
const inputEl = document.getElementById("input");
const sendBtn = document.getElementById("send-btn");
const bannerEl = document.getElementById("banner");
const healthDataEl = document.getElementById("health-data");
const dataStatusEl = document.getElementById("data-status");
const dateStartEl = document.getElementById("date-start");
const dateEndEl = document.getElementById("date-end");
const dateApplyBtn = document.getElementById("date-apply");
const aiIconFileEl = document.getElementById("ai-icon-file");
const aiAvatarLargeEl = document.getElementById("ai-avatar-large");

let aiIconDataUrl = null;
let ready = false;

function fa(name) {
  return `<i class="fa-solid fa-${name} icon" aria-hidden="true"></i>`;
}

function shortDate(dateStr) {
  const m = dateStr?.match(/(\d{4})-(\d{2})-(\d{2})/);
  if (m) return `${Number(m[2])}/${Number(m[3])}`;
  const m2 = dateStr?.match(/(\d{4})\/(\d{2})\/(\d{2})/);
  if (m2) return `${Number(m2[2])}/${Number(m2[3])}`;
  return dateStr || "—";
}

function shortDateTime(dateStr) {
  const m = dateStr?.match(/(\d{4})\/(\d{2})\/(\d{2})\s+(\d{2}:\d{2})/);
  if (m) return `${Number(m[2])}/${Number(m[3])} ${m[4]}`;
  return dateStr || "—";
}

function renderAiAvatar(el) {
  el.innerHTML = "";
  el.classList.add("ai-avatar-btn");
  if (!el.getAttribute("title")) {
    el.setAttribute("title", "クリックでアイコン画像を設定");
  }

  if (aiIconDataUrl) {
    const img = document.createElement("img");
    img.src = aiIconDataUrl;
    img.alt = "AI";
    el.appendChild(img);
    return;
  }

  const icon = document.createElement("i");
  icon.className = "fa-solid fa-robot icon";
  icon.setAttribute("aria-hidden", "true");
  el.appendChild(icon);
}

function bindAvatarUpload(el) {
  if (el.tagName === "BUTTON") {
    el.onclick = () => aiIconFileEl.click();
  } else {
    el.addEventListener("click", () => aiIconFileEl.click());
  }
}

function applyAiIconEverywhere() {
  if (aiAvatarLargeEl) {
    renderAiAvatar(aiAvatarLargeEl);
    bindAvatarUpload(aiAvatarLargeEl);
  }
  document.querySelectorAll(".qa-avatar").forEach((el) => {
    renderAiAvatar(el);
    bindAvatarUpload(el);
  });
}

aiIconFileEl.addEventListener("change", () => {
  const file = aiIconFileEl.files?.[0];
  if (!file) return;
  const reader = new FileReader();
  reader.onload = () => {
    aiIconDataUrl = reader.result;
    applyAiIconEverywhere();
  };
  reader.readAsDataURL(file);
  aiIconFileEl.value = "";
});

function setLoading(on) {
  sendBtn.disabled = on || !ready;
  inputEl.disabled = !ready;
  dateApplyBtn.disabled = on;
}

function renderMetricList(items, valueFn, emptyLabel) {
  if (!items.length) {
    return `<p class="empty-inline">${emptyLabel}</p>`;
  }
  return `<ul class="metric-list">${items
    .map(
      (item) =>
        `<li class="metric-row"><span class="metric-date">${escapeHtml(shortDate(item.date))}</span><span class="metric-value">${escapeHtml(valueFn(item))}</span></li>`,
    )
    .join("")}</ul>`;
}

function renderSleepList(sessions) {
  if (!sessions.length) {
    return '<p class="empty-inline">なし</p>';
  }
  return `<ul class="sleep-list">${sessions
    .map(
      (s) => `
    <li class="sleep-card">
      <div class="sleep-duration">${escapeHtml(s.sleep_duration || "—")}</div>
      <div class="sleep-meta">
        <span>${fa("moon")} ${escapeHtml(shortDateTime(s.bedtime_jst))}</span>
        <span>${fa("sun")} ${escapeHtml(shortDateTime(s.wake_jst))}</span>
      </div>
    </li>`,
    )
    .join("")}</ul>`;
}

function renderHealthData(data) {
  if (!data) {
    healthDataEl.innerHTML = '<p class="empty-note">データ未取得</p>';
    dataStatusEl.textContent = "—";
    dataStatusEl.className = "pill";
    return;
  }

  const period = data.period
    ? `${shortDate(data.period.start)} 〜 ${shortDate(data.period.end)}`
    : "—";
  dataStatusEl.textContent = period;
  dataStatusEl.className = "pill ok";

  healthDataEl.innerHTML = `
    <div class="data-block">
      <h3>${fa("user")} プロフィール</h3>
      <p class="profile-line">年齢 <strong>${escapeHtml(String(data.profile?.age ?? "—"))}</strong> 歳</p>
    </div>
    <div class="data-block">
      <h3>${fa("shoe-prints")} 歩数</h3>
      ${renderMetricList(data.daily_steps || [], (d) => `${d.steps ?? "—"} 歩`, "なし")}
    </div>
    <div class="data-block">
      <h3>${fa("route")} 距離</h3>
      ${renderMetricList(data.daily_distance_km || [], (d) => `${d.distance_km ?? "—"} km`, "なし")}
    </div>
    <div class="data-block">
      <h3>${fa("bed")} 睡眠</h3>
      ${renderSleepList(data.sleep_sessions || [])}
    </div>`;
}

function showQa(question, answer, loading = false) {
  qaEmptyEl?.remove();
  qaEl.innerHTML = "";

  const wrap = document.createElement("div");
  wrap.className = "qa-pair";

  const q = document.createElement("div");
  q.className = "qa-item user";
  q.innerHTML = `<div class="qa-label">${fa("comment")} 質問</div><div class="qa-text">${escapeHtml(question)}</div>`;

  const a = document.createElement("div");
  a.className = "qa-item assistant";
  const avatar = document.createElement("button");
  avatar.type = "button";
  avatar.className = "ai-avatar qa-avatar ai-avatar-btn";
  renderAiAvatar(avatar);
  bindAvatarUpload(avatar);
  const body = document.createElement("div");
  body.className = "qa-body";
  body.innerHTML = `<div class="qa-label">${fa("wand-magic-sparkles")} 回答</div><div class="qa-text ${loading ? "loading" : ""}">${loading ? "考え中…" : escapeHtml(answer)}</div>`;
  a.append(avatar, body);

  wrap.append(q, a);
  qaEl.appendChild(wrap);
}

function escapeHtml(text) {
  return String(text)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

function apiErrorDetail(data, fallback) {
  if (Array.isArray(data.detail)) return data.detail[0]?.msg || fallback;
  return data.detail || fallback;
}

async function fetchHealthData(start, end) {
  setLoading(true);
  try {
    const res = await fetch("/api/health-data", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ start, end }),
    });
    const data = await res.json();
    if (!res.ok)
      throw new Error(apiErrorDetail(data, "データ取得に失敗しました"));
    renderHealthData(data);
    ready = true;
    bannerEl.classList.add("hidden");
    return data;
  } catch (err) {
    renderHealthData(null);
    ready = false;
    throw err;
  } finally {
    setLoading(false);
  }
}

async function loadStatus() {
  const res = await fetch("/api/status");
  const data = await res.json();

  if (!data.gemini_ready) {
    bannerEl.classList.remove("hidden");
    bannerEl.querySelector("p").textContent =
      "GEMINI_API_KEY を .env に設定してください。";
    return;
  }

  if (!data.google_connected) {
    bannerEl.classList.remove("hidden");
    ready = false;
    return;
  }

  const range = data.default_range || data.period;
  if (range) {
    dateStartEl.value = range.start;
    dateEndEl.value = range.end;
  }

  if (data.health_loaded) {
    const healthRes = await fetch("/api/health-data");
    if (healthRes.ok) {
      renderHealthData(await healthRes.json());
      ready = true;
      bannerEl.classList.add("hidden");
    }
  }
}

dateApplyBtn.addEventListener("click", async () => {
  if (!dateStartEl.value || !dateEndEl.value) return;
  try {
    await fetchHealthData(dateStartEl.value, dateEndEl.value);
  } catch (err) {
    bannerEl.classList.remove("hidden");
    bannerEl.querySelector("p").textContent = err.message;
  }
});

formEl.addEventListener("submit", async (e) => {
  e.preventDefault();
  const message = inputEl.value.trim();
  if (!message || !ready) return;

  showQa(message, "", true);
  inputEl.value = "";
  inputEl.style.height = "auto";
  setLoading(true);

  try {
    const res = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(apiErrorDetail(data, "送信に失敗しました"));
    showQa(message, data.reply);
  } catch (err) {
    showQa(message, err.message);
  } finally {
    setLoading(false);
    inputEl.focus();
  }
});

inputEl.addEventListener("input", () => {
  inputEl.style.height = "auto";
  inputEl.style.height = `${Math.min(inputEl.scrollHeight, 120)}px`;
});

inputEl.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    formEl.requestSubmit();
  }
});

applyAiIconEverywhere();
loadStatus();

if (new URLSearchParams(location.search).get("connected") === "1") {
  history.replaceState({}, "", "/");
}
