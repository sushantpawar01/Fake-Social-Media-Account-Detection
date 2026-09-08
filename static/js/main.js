const PLATFORM_MAP = {
  "github.com":    { label: "GitHub",    icon: "icon-user" },
  "instagram.com": { label: "Instagram", icon: "icon-user" },
  "twitter.com":   { label: "Twitter",   icon: "icon-user" },
  "x.com":         { label: "X",         icon: "icon-user" },
  "facebook.com":  { label: "Facebook",  icon: "icon-user" },
  "linkedin.com":  { label: "LinkedIn",  icon: "icon-user" },
  "tiktok.com":    { label: "TikTok",    icon: "icon-user" },
  "youtube.com":   { label: "YouTube",   icon: "icon-user" },
};

function svgUse(id, cls = "") {
  return `<svg class="inline-icon ${cls}"><use href="#${id}"/></svg>`;
}

document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("detectForm");
  const urlInput = document.getElementById("urlInput");
  const platformBadge = document.getElementById("platformBadge");
  if (!form) return;

  urlInput.addEventListener("input", () => {
    const info = detectPlatform(urlInput.value.trim());
    if (info) {
      platformBadge.innerHTML = `${svgUse(info.icon)} ${info.label} profile detected`;
      platformBadge.className = "platform-detected";
    } else {
      platformBadge.className = "platform-detected hidden";
    }
  });

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const url = urlInput.value.trim();
    if (!url) return;

    const btn = document.getElementById("analyzeBtn");
    btn.innerHTML = `${svgUse("icon-loader", "spin")} Analyzing...`;
    btn.disabled = true;
    document.getElementById("result").classList.add("hidden");

    try {
      const res = await fetch("/api/detect", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url }),
      });
      const data = await res.json();
      if (data.error) showError(data.error);
      else renderResult(data);
    } catch {
      showError("Detection failed. Check your connection and try again.");
    } finally {
      btn.innerHTML = `${svgUse("icon-search")} Analyze Account`;
      btn.disabled = false;
    }
  });
});

function detectPlatform(url) {
  try {
    const host = new URL(url.startsWith("http") ? url : "https://" + url).hostname.replace("www.", "");
    return PLATFORM_MAP[host] || null;
  } catch { return null; }
}

function renderResult(data) {
  const panel = document.getElementById("result");
  panel.classList.remove("hidden");

  // Result badge
  const iconMap = { Fake: "icon-x-circle", Suspicious: "icon-alert", Genuine: "icon-check-circle" };
  document.getElementById("resultIcon").innerHTML = `<use href="#${iconMap[data.label] || "icon-search"}"/>`;
  document.getElementById("resultLabel").textContent = `${data.label.toUpperCase()} ACCOUNT`;
  document.getElementById("resultBadge").className = "result-badge " + data.label.toLowerCase();

  // Platform & username
  const pInfo = PLATFORM_MAP[data.platform] || { label: data.platform, icon: "icon-globe" };
  document.getElementById("resultPlatform").innerHTML = `${svgUse(pInfo.icon, "ptag-icon")} ${pInfo.label}`;
  document.getElementById("resultUsername").textContent = data.username ? `@${data.username}` : "";

  // Age source badge
  const ageBadge = document.getElementById("ageSourceBadge");
  const ageText  = document.getElementById("ageSourceText");
  const ageLabels = {
    "default":               { text: "Account age estimated (365 days default — not found in page)", cls: "age-warn" },
    "json-ld:dateCreated":   { text: "Account age from page structured data (dateCreated)",          cls: "age-ok" },
    "json-ld:foundingDate":  { text: "Account age from page structured data (foundingDate)",         cls: "age-ok" },
    "json-ld:startDate":     { text: "Account age from page structured data (startDate)",            cls: "age-ok" },
    "time-element":          { text: "Account age from HTML time element",                           cls: "age-ok" },
    "joined-text":           { text: "Account age from Joined text on page",                         cls: "age-ok" },
    "linkedin-since":        { text: "Account age from LinkedIn member since text",                  cls: "age-ok" },
    "keyword-iso":           { text: "Account age from ISO date near profile keywords",              cls: "age-ok" },
    "iso-fallback":          { text: "Account age estimated from earliest date found on page",       cls: "age-approx" },
    "github-api":            { text: "Account age from GitHub API (exact)",                          cls: "age-exact" },
  };
  const src  = data.age_source || "default";
  const info = ageLabels[src] || { text: `Account age source: ${src}`, cls: "age-approx" };
  ageText.textContent = info.text;
  ageBadge.className = `age-source-badge ${info.cls}`;

  // Score bar
  const bar = document.getElementById("scoreBar");
  bar.style.width = data.score + "%";
  bar.style.background = data.label === "Fake" ? "#ef4444" : data.label === "Suspicious" ? "#f59e0b" : "#22c55e";
  document.getElementById("scoreVal").textContent = data.score + " / 100";
  document.getElementById("confVal").textContent = data.confidence;

  // Probability bars
  const probs = data.probabilities || {};
  const setProbBar = (id, valId, val) => {
    document.getElementById(id).style.width = val + "%";
    document.getElementById(valId).textContent = val + "%";
  };
  setProbBar("probGenuine",    "probGenuineVal",    probs.Genuine    || 0);
  setProbBar("probSuspicious", "probSuspiciousVal", probs.Suspicious || 0);
  setProbBar("probFake",       "probFakeVal",       probs.Fake       || 0);

  // Reasons
  document.getElementById("reasonsList").innerHTML =
    data.reasons.map(r => `<li>${svgUse("icon-alert", "reason-icon")} ${r}</li>`).join("");

  // Features table
  document.getElementById("featuresTable").innerHTML =
    Object.entries(data.features)
      .map(([k, v]) => `<tr><td>${k.replace(/_/g, " ")}</td><td>${v}</td></tr>`)
      .join("");

  panel.scrollIntoView({ behavior: "smooth", block: "start" });
}

function showError(msg) {
  const panel = document.getElementById("result");
  panel.classList.remove("hidden");
  panel.innerHTML = `<div class="error-msg">${svgUse("icon-error")} ${msg}</div>`;
  panel.scrollIntoView({ behavior: "smooth" });
}
