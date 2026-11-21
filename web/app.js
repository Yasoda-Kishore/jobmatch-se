// JobMatch SE frontend: talks to the FastAPI backend on the same address.
const API = window.JOBMATCH_API_URL || "";

let scene = null;
try {
  const { startScene } = await import("./scene.js");
  scene = startScene(document.getElementById("sky"));
} catch (error) {
  console.warn("3D background unavailable:", error);
  document.body.classList.add("no-webgl");
}

// Say honestly where the CV goes: a local model, or a cloud AI provider
fetch(`${API}/config`)
  .then((r) => (r.ok ? r.json() : null))
  .then((config) => {
    if (config?.llm_location === "cloud") {
      document.getElementById("privacy-note").textContent =
        "Live ads from Arbetsförmedlingen. Your CV is sent to a cloud AI model to be read, and is not stored.";
    }
  })
  .catch(() => {});

const escape = (value) =>
  String(value ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);

function showMessage(element, text) {
  element.textContent = text;
  element.hidden = !text;
}

function params(form, names) {
  const data = new FormData(form);
  const query = new URLSearchParams();
  for (const name of names) {
    const value = String(data.get(name) ?? "").trim();
    if (value) query.set(name, value);
  }
  return query;
}

async function readError(response) {
  try {
    const body = await response.json();
    return typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
  } catch {
    return `The server answered with status ${response.status}.`;
  }
}

const API_DOWN = "Can't reach the JobMatch API. Start it with: uvicorn jobmatch.api.main:app, then reload this page.";

/* ---------- Match my CV ---------- */

const matchForm = document.getElementById("match-form");
const fileInput = document.getElementById("cv-file");
const dropzone = document.getElementById("dropzone");
const dropzoneText = document.getElementById("dropzone-text");
const topRange = document.getElementById("top-range");
const matchLoading = document.getElementById("match-loading");
const scanText = document.getElementById("scan-text");
const matchMessage = document.getElementById("match-message");
const matchResults = document.getElementById("match-results");
const matchButton = document.getElementById("match-button");

topRange.addEventListener("input", () => (document.getElementById("top-value").textContent = topRange.value));
fileInput.addEventListener("change", () => {
  dropzoneText.textContent = fileInput.files[0] ? `Ready: ${fileInput.files[0].name}` : "Drop your CV here as a PDF, or choose a file";
});
for (const type of ["dragenter", "dragover"]) {
  dropzone.addEventListener(type, (e) => { e.preventDefault(); dropzone.classList.add("drag"); });
}
for (const type of ["dragleave", "drop"]) {
  dropzone.addEventListener(type, () => dropzone.classList.remove("drag"));
}
dropzone.addEventListener("drop", (e) => {
  e.preventDefault();
  if (e.dataTransfer.files.length) {
    fileInput.files = e.dataTransfer.files;
    fileInput.dispatchEvent(new Event("change"));
  }
});

const SCAN_STEPS = ["Reading your CV", "Finding your skills", "Searching 2,000 live job ads", "Reading the best ads", "Scoring each job"];

function ring(score) {
  const r = 42;
  const length = 2 * Math.PI * r;
  const colour = score >= 75 ? "var(--aurora-green)" : score >= 50 ? "var(--glacier)" : "var(--ember)";
  return `
    <svg class="ring" viewBox="0 0 100 100" role="img" aria-label="Fit score ${score} out of 100">
      <circle class="ring-track" cx="50" cy="50" r="${r}"></circle>
      <circle class="ring-fill" cx="50" cy="50" r="${r}" stroke="${colour}"
        stroke-dasharray="${length}" stroke-dashoffset="${length}" data-offset="${length * (1 - score / 100)}"></circle>
      <text x="50" y="56">${score}</text>
      <text class="ring-small" x="50" y="72">fit</text>
    </svg>`;
}

const PART_LABELS = {
  required_skills: "Required skills (60%)",
  experience: "Experience (20%)",
  nice_to_have: "Nice to have (10%)",
  seniority: "Seniority (10%)",
};

function statBars(parts) {
  return Object.entries(PART_LABELS)
    .map(([key, label]) => {
      const value = parts[key] ?? 0;
      return `
        <div class="stat-bar">
          <span>${label}</span>
          <span class="stat-bar-track"><span class="stat-bar-fill" style="width:${Math.round(value * 100)}%"></span></span>
          <span class="stat-bar-value">${Math.round(value * 100)}%</span>
        </div>`;
    })
    .join("");
}

const chips = (skills, kind) =>
  skills.length ? `<ul class="chips">${skills.map((s) => `<li class="chip chip-${kind}">${escape(s)}</li>`).join("")}</ul>` : "<p>None</p>";

function matchCard(m) {
  return `
    <li class="match">
      ${ring(m.score)}
      <div>
        <h4>${escape(m.title)}</h4>
        <p class="match-meta">${escape(m.employer || "Employer not given")}, ${escape(m.city || "no city given")}</p>
        ${m.requires_swedish ? '<span class="badge-swedish">Swedish required</span>' : ""}
        <div class="skill-group"><span class="skill-group-label">You have</span>${chips(m.matching_skills, "have")}</div>
        <div class="skill-group"><span class="skill-group-label">Missing</span>${chips(m.missing_skills, "missing")}</div>
        <ul class="reasons">${m.reasons.map((r) => `<li>${escape(r)}</li>`).join("")}</ul>
        <div class="stat-bars">${statBars(m.score_parts)}</div>
        ${m.url ? `<a class="match-link" href="${escape(m.url)}" target="_blank" rel="noopener">Open the ad on Platsbanken</a>` : ""}
      </div>
    </li>`;
}

function skillTree(matches) {
  // Count each missing skill once per job, ignoring upper/lower case ("TensorFlow" = "Tensorflow")
  const counts = new Map();
  for (const m of matches) {
    const seen = new Set();
    for (const skill of m.missing_skills) {
      const key = skill.trim().toLowerCase();
      if (seen.has(key)) continue;
      seen.add(key);
      const entry = counts.get(key) || { name: skill.trim(), count: 0 };
      entry.count += 1;
      counts.set(key, entry);
    }
  }
  const top = [...counts.values()].sort((a, b) => b.count - a.count).slice(0, 8);
  if (!top.length) return "";
  const total = matches.length;
  return `
    <h3 class="section-title">Skills to learn next</h3>
    <ul class="skill-tree">
      ${top
        .map(
          (s) => `
        <li>
          <span>${escape(s.name)}</span>
          <span class="skill-tree-bar" style="width:${Math.round((s.count / total) * 100)}%"></span>
          <span class="skill-tree-count">${s.count} of ${total} jobs</span>
        </li>`,
        )
        .join("")}
    </ul>`;
}

function renderMatch(result) {
  const p = result.profile;
  matchResults.innerHTML = `
    <div class="profile">
      <h3 class="section-title">Your profile</h3>
      <div class="stats">
        <div class="stat"><span class="stat-value">${escape(p.years_of_experience)}</span><span class="stat-label">years of experience</span></div>
        <div class="stat"><span class="stat-value">${p.skills.length}</span><span class="stat-label">skills found in your CV</span></div>
        <div class="stat"><span class="stat-value">${result.matches.length}</span><span class="stat-label">jobs scored</span></div>
      </div>
      <p class="roles">${escape(p.target_roles.join(", "))}</p>
      ${chips(p.skills, "have")}
    </div>
    <h3 class="section-title">Your best matches</h3>
    <ol class="matches">${result.matches.map(matchCard).join("")}</ol>
    ${skillTree(result.matches)}`;
  // Fill the score rings after they are on the page, so they animate
  requestAnimationFrame(() =>
    matchResults.querySelectorAll(".ring-fill").forEach((c) => (c.style.strokeDashoffset = c.dataset.offset)),
  );
  matchResults.querySelector(".profile").scrollIntoView({ behavior: "smooth", block: "start" });
}

matchForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!fileInput.files[0]) return;
  showMessage(matchMessage, "");
  matchResults.innerHTML = "";
  matchLoading.hidden = false;
  matchButton.disabled = true;
  scene?.setIntensity(4);
  let step = 0;
  scanText.textContent = SCAN_STEPS[0];
  const timer = setInterval(() => (scanText.textContent = SCAN_STEPS[Math.min(++step, SCAN_STEPS.length - 1)]), 9000);

  const body = new FormData();
  body.append("cv", fileInput.files[0]);
  try {
    const response = await fetch(`${API}/match?${params(matchForm, ["city", "language", "top"])}`, { method: "POST", body });
    if (!response.ok) throw new Error(await readError(response));
    renderMatch(await response.json());
  } catch (error) {
    showMessage(matchMessage, error instanceof TypeError ? API_DOWN : `Matching failed: ${error.message}`);
  } finally {
    clearInterval(timer);
    matchLoading.hidden = true;
    matchButton.disabled = false;
    scene?.setIntensity(1);
  }
});

/* ---------- Search jobs ---------- */

const searchForm = document.getElementById("search-form");
const searchResults = document.getElementById("search-results");
const searchMessage = document.getElementById("search-message");

searchForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  showMessage(searchMessage, "");
  searchResults.innerHTML = "";
  try {
    const response = await fetch(`${API}/search?${params(searchForm, ["q", "mode", "city", "language"])}`);
    if (!response.ok) throw new Error(await readError(response));
    const { results } = await response.json();
    if (!results.length) {
      searchResults.innerHTML = '<li class="empty">No jobs found. Try fewer words, or remove the city filter.</li>';
      return;
    }
    searchResults.innerHTML = results
      .map(
        (r) => `
        <li class="result">
          <div>
            <h3>${escape(r.title)}<span class="lang lang-${escape(r.language)}">${r.language === "sv" ? "Swedish" : "English"}</span></h3>
            <p>${escape(r.employer || "Employer not given")}, ${escape(r.city || "no city given")}</p>
          </div>
          ${r.url ? `<a href="${escape(r.url)}" target="_blank" rel="noopener">Open ad</a>` : ""}
        </li>`,
      )
      .join("");
  } catch (error) {
    showMessage(searchMessage, error instanceof TypeError ? API_DOWN : `Search failed: ${error.message}`);
  }
});
