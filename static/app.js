"use strict";

const $ = (id) => document.getElementById(id);
const APP_TITLE = "Video Speaker Labeler";
const STATUS = {
  onscreen: "On-screen → A",
  offscreen: "Off-screen → B",
  unclear: "Unclear",
};

let state = null;   // last /api/state response (ready)
let current = 0;    // index into state.items

// ---------------------------------------------------------------- helpers

async function api(method, url, body) {
  const res = await fetch(url, {
    method,
    headers: body ? { "Content-Type": "application/json" } : {},
    body: body ? JSON.stringify(body) : undefined,
  });
  let data = {};
  try { data = await res.json(); } catch (_) { /* empty body */ }
  if (!res.ok || data.ok === false) throw new Error(data.error || `Request failed (${res.status})`);
  return data;
}

let toastTimer = null;
function toast(msg, isError = false) {
  const el = $("toast");
  el.textContent = msg;
  el.classList.toggle("error", isError);
  el.classList.remove("hidden");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => el.classList.add("hidden"), isError ? 6000 : 2500);
}

// UI preferences are stored per project so each project keeps its own settings.
function prefKey(name) { return `labeler:${state ? state.project : ""}:${name}`; }
function getPref(name, fallback) {
  const v = localStorage.getItem(prefKey(name));
  return v === null ? fallback : JSON.parse(v);
}
function setPref(name, value) { localStorage.setItem(prefKey(name), JSON.stringify(value)); }

// ---------------------------------------------------------------- setup screen

function showSetup(cfg = {}) {
  state = null;
  document.title = APP_TITLE;
  $("player").removeAttribute("src");
  $("player").load();
  $("labeler").classList.add("hidden");
  $("setup").classList.remove("hidden");
  $("setup-error").classList.add("hidden");
  if (cfg.last_project !== undefined) $("setup-project").value = cfg.last_project;
  if (cfg.last_videos !== undefined) $("setup-videos").value = cfg.last_videos;
  if (cfg.last_output !== undefined) $("setup-output").value = cfg.last_output;
  $(cfg.last_videos ? "setup-project" : "setup-videos").focus();
}

async function submitSetup() {
  const btn = $("setup-go");
  btn.disabled = true;
  $("setup-error").classList.add("hidden");
  try {
    await api("POST", "/api/setup", {
      project: $("setup-project").value,
      videos: $("setup-videos").value,
      output: $("setup-output").value,
    });
    await load();
  } catch (e) {
    $("setup-error").textContent = e.message;
    $("setup-error").classList.remove("hidden");
  } finally {
    btn.disabled = false;
  }
}

// ---------------------------------------------------------------- labeler

async function load() {
  const data = await api("GET", "/api/state");
  if (!data.ready) return showSetup(data);
  state = data;
  $("setup").classList.add("hidden");
  $("labeler").classList.remove("hidden");

  document.title = `${state.project} · ${APP_TITLE}`;
  $("project-name").textContent = state.project;
  $("project-path").textContent = `${state.videos_dir}  →  ${state.output_file}`;
  $("project-path").title = $("project-path").textContent;
  $("auto-advance").checked = getPref("autoAdvance", true);
  $("only-unlabeled").checked = getPref("onlyUnlabeled", false);
  $("sidebar").classList.toggle("collapsed", getPref("sidebarHidden", false));
  $("search").value = "";

  const empty = state.items.length === 0;
  $("empty").classList.toggle("hidden", !empty);
  $("work").classList.toggle("hidden", empty);
  updateCounts(state);
  renderList();
  if (!empty) {
    const done = state.first_unlabeled === null;
    select(done ? 0 : state.first_unlabeled);
    toast(done ? `Project "${state.project}": all videos are labeled` : `Project "${state.project}" opened`);
  }
}

function updateCounts(c) {
  state.total = c.total;
  state.labeled = c.labeled;
  state.first_unlabeled = c.first_unlabeled;
  $("count-labeled").textContent = c.labeled;
  $("count-total").textContent = c.total;
  $("progress-bar").style.width = c.total ? `${(100 * c.labeled) / c.total}%` : "0";
}

function renderList() {
  const q = $("search").value.trim().toLowerCase();
  const onlyUnlabeled = $("only-unlabeled").checked;
  const ul = $("video-list");
  ul.innerHTML = "";
  for (const item of state.items) {
    if (q && !item.name.toLowerCase().includes(q)) continue;
    if (onlyUnlabeled && item.label && item.index !== current) continue;
    const li = document.createElement("li");
    li.dataset.index = item.index;
    li.className = item.index === current ? "active" : "";
    li.title = item.file;
    const dot = document.createElement("span");
    dot.className = `dot ${item.label || ""}`;
    const name = document.createElement("span");
    name.className = "name";
    name.textContent = item.name;
    li.append(dot, name);
    ul.appendChild(li);
  }
}

function select(index) {
  if (!state || !state.items.length) return;
  current = Math.max(0, Math.min(index, state.items.length - 1));
  const item = state.items[current];
  const player = $("player");
  $("video-error").classList.add("hidden");
  player.src = `/video/${encodeURIComponent(item.file)}`;
  player.play().catch(() => { /* autoplay may be blocked */ });
  $("current-name").textContent = item.name;
  $("current-name").title = item.file;
  $("current-pos").textContent = `${current + 1} / ${state.items.length}`;
  renderStatus();
  renderList();
  const active = $("video-list").querySelector("li.active");
  if (active) active.scrollIntoView({ block: "nearest" });
}

function renderStatus() {
  const label = state.items[current].label;
  const badge = $("current-status");
  badge.textContent = label ? STATUS[label] : "Not labeled";
  badge.className = `status-badge ${label || ""}`;
  document.querySelectorAll(".choice").forEach((b) => b.classList.toggle("selected", b.dataset.label === label));
}

function nextUnlabeled(from) {
  const n = state.items.length;
  for (let k = 1; k <= n; k++) {
    const i = (from + k) % n;
    if (!state.items[i].label) return i;
  }
  return null;
}

async function setLabel(label) {
  if (!state || !state.items.length) return;
  const item = state.items[current];
  try {
    const counts = await api("POST", "/api/label", { file: item.file, label });
    item.label = label;
    updateCounts(counts);
    renderStatus();
    renderList();
    if ($("auto-advance").checked) {
      const next = nextUnlabeled(current);
      if (next !== null) select(next);
      else toast(`All videos in "${state.project}" are labeled 🎉`);
    }
  } catch (e) {
    toast(e.message, true);
  }
}

async function clearLabel() {
  if (!state || !state.items.length) return;
  const item = state.items[current];
  if (!item.label) return;
  try {
    const counts = await api("DELETE", `/api/label/${encodeURIComponent(item.file)}`);
    item.label = null;
    updateCounts(counts);
    renderStatus();
    renderList();
  } catch (e) {
    toast(e.message, true);
  }
}

function jumpUnlabeled() {
  const next = nextUnlabeled(current);
  if (next === null) toast(`All videos in "${state.project}" are labeled`);
  else select(next);
}

async function changeProject() {
  await api("POST", "/api/close");
  await load();
}

// ---------------------------------------------------------------- events

$("setup-go").addEventListener("click", submitSetup);
["setup-project", "setup-videos", "setup-output"].forEach((id) =>
  $(id).addEventListener("keydown", (e) => { if (e.key === "Enter") submitSetup(); }));

$("change-project").addEventListener("click", () => changeProject().catch((e) => toast(e.message, true)));
$("toggle-sidebar").addEventListener("click", () => {
  const hidden = $("sidebar").classList.toggle("collapsed");
  setPref("sidebarHidden", hidden);
});
$("search").addEventListener("input", renderList);
$("only-unlabeled").addEventListener("change", (e) => { setPref("onlyUnlabeled", e.target.checked); renderList(); });
$("auto-advance").addEventListener("change", (e) => setPref("autoAdvance", e.target.checked));
$("video-list").addEventListener("click", (e) => {
  const li = e.target.closest("li");
  if (li) select(Number(li.dataset.index));
});

$("prev").addEventListener("click", () => select(current - 1));
$("next").addEventListener("click", () => select(current + 1));
$("clear-label").addEventListener("click", clearLabel);
$("jump-unlabeled").addEventListener("click", jumpUnlabeled);
document.querySelectorAll(".choice").forEach((b) => b.addEventListener("click", () => setLabel(b.dataset.label)));
$("player").addEventListener("error", () => {
  if ($("player").getAttribute("src")) $("video-error").classList.remove("hidden");
});

document.addEventListener("keydown", (e) => {
  if (!state || $("labeler").classList.contains("hidden")) return;
  if (e.ctrlKey || e.altKey || e.metaKey) return;
  const tag = (e.target.tagName || "").toLowerCase();
  if (tag === "input" || tag === "textarea") return;
  const player = $("player");
  const actions = {
    ArrowLeft: () => select(current - 1),
    ArrowRight: () => select(current + 1),
    "1": () => setLabel("onscreen"),
    "2": () => setLabel("offscreen"),
    "3": () => setLabel("unclear"),
    " ": () => (player.paused ? player.play() : player.pause()),
    r: () => { player.currentTime = 0; player.play(); },
    n: jumpUnlabeled,
  };
  const action = actions[e.key.length === 1 ? e.key.toLowerCase() : e.key];
  if (action) {
    e.preventDefault();
    action();
  }
});

load().catch((e) => toast(e.message, true));
