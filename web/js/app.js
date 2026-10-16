import {
  MOODS,
  TRACKS,
  activeDays,
  addDays,
  containsCrisisLanguage,
  dateKey,
  escapeHtml as esc,
  focusMinutesByDay,
  formatClock,
  formatMinutes,
  greeting,
  habitCount,
  habitScore,
  isValidPhone,
  lastDays,
  supportFor,
  weekdayShort,
} from "./logic.js";
import { clear, defaultState, exportBackup, fromLegacy, hasSaved, importBackup, load, save, uid } from "./store.js";
import { NoiseEngine, PRESETS, SOUNDS } from "./noise.js";
import { Scene } from "./scene.js";

const native = globalThis.ResetPathNative ?? null;
const $ = (selector, root = document) => root.querySelector(selector);

let state = load();
let importedLegacy = false;
// First launch after upgrading from the Python build: bring the old data over.
if (!hasSaved() && native?.legacyData) {
  try {
    const legacy = native.legacyData();
    if (legacy) {
      state = fromLegacy(legacy);
      importedLegacy = state.tasks.length + state.journal.length > 0;
      save(state);
    }
  } catch {
    // Start fresh if the old database cannot be read.
  }
}
const engine = new NoiseEngine();
engine.masterLevel = state.mixer.master;

const viewEl = $("#view");
const sheetRoot = $("#sheet-root");
const miniPlayer = $("#mini-player");
const scene = new Scene($("#scene"), { motion: state.settings.motion, getLevel: () => engine.level() });

const route = { tab: "today", sub: null, param: null };
const ui = {
  track: "dsa",
  reset: null,
  breath: null,
};
const timer = {
  phase: "idle", // idle | focus | break
  next: "focus",
  running: false,
  endsAt: 0,
  left: state.settings.focusMinutes * 60,
  total: state.settings.focusMinutes * 60,
  taskId: null,
};

function commit() {
  if (!save(state)) toast("Could not save. Storage may be full.");
}

function haptic(pattern = 12) {
  if (state.settings.motion !== "off") navigator.vibrate?.(pattern);
}

function toast(message) {
  const el = $("#toast");
  el.textContent = message;
  el.classList.add("show");
  clearTimeout(toast.timer);
  toast.timer = setTimeout(() => el.classList.remove("show"), 2400);
}

function today() {
  return dateKey();
}

// ---------- Theme and motion ----------

function applyAppearance() {
  const root = document.documentElement;
  root.dataset.theme = state.settings.theme;
  root.dataset.motion = state.settings.motion;
  const css = getComputedStyle(root);
  const read = (name) => css.getPropertyValue(name).trim();
  $('meta[name="theme-color"]').content = read("--bg");
  native?.setBars?.(read("--bg"), state.settings.theme === "light");
  scene.setColors({ a: read("--orb-a"), b: read("--orb-b"), c: read("--orb-c") });
  scene.setMotion(state.settings.motion);
}

// ---------- Navigation ----------

function go(tab, sub = null, param = null) {
  const changedTab = tab !== route.tab;
  if (route.tab === "calm" && route.sub === "breathe" && (changedTab || sub !== "breathe")) stopBreathing();
  Object.assign(route, { tab, sub, param });
  render({ animate: true });
  if (changedTab) haptic(8);
}

function back() {
  if (sheetRoot.firstChild) {
    closeSheet();
    return true;
  }
  if (route.sub === "entry") {
    go("calm", "journal");
    return true;
  }
  if (route.sub) {
    go(route.tab);
    return true;
  }
  if (route.tab !== "today") {
    go("today");
    return true;
  }
  return false;
}
globalThis.rpBack = back;

document.querySelectorAll(".tabs button").forEach((button) => {
  button.addEventListener("click", () => go(button.dataset.tab));
});

addEventListener("keydown", (event) => {
  if (event.key === "Escape") back();
});

// ---------- Rendering ----------

const VIEWS = {
  today: renderToday,
  focus: renderFocus,
  sounds: renderSounds,
  calm: renderCalm,
  you: renderYou,
};

function render({ animate = false } = {}) {
  const scroll = viewEl.scrollTop;
  viewEl.innerHTML = VIEWS[route.tab]();
  [...viewEl.children].forEach((child, index) => child.style.setProperty("--i", index));
  if (animate) {
    viewEl.classList.remove("enter");
    void viewEl.offsetWidth;
    viewEl.classList.add("enter");
    viewEl.scrollTop = 0;
  } else {
    viewEl.classList.remove("enter");
    viewEl.scrollTop = scroll;
  }
  document.querySelectorAll(".tabs button").forEach((button) => {
    button.classList.toggle("on", button.dataset.tab === route.tab);
  });
  scene.setMode(sceneMode());
  scene.setRing(route.tab === "focus" ? timerProgress() : 0);
  updateMiniPlayer();
  updateLiveBits();
}

function sceneMode() {
  if (route.tab === "calm") return route.sub === "breathe" ? "breathe" : route.sub ? "mini" : "today";
  if (route.tab === "you") return "mini";
  return route.tab;
}

viewEl.addEventListener("scroll", () => scene.setScroll(viewEl.scrollTop), { passive: true });

// ---------- Today ----------

function renderToday() {
  const day = today();
  const name = state.settings.name ? `, ${esc(state.settings.name)}` : "";
  const tasks = state.tasks.filter((task) => task.day === day);
  const open = tasks.filter((task) => !task.doneAt).length;
  const focusToday = state.focus.filter((session) => session.day === day).reduce((sum, s) => sum + s.minutes, 0);
  const carry = state.tasks.filter((task) => !task.doneAt && task.day < day);
  const mood = state.moods[day];
  const dateText = new Date().toLocaleDateString(undefined, { weekday: "long", day: "numeric", month: "long" });

  return `
    <section class="hero">
      <div class="eyebrow">${esc(dateText)}</div>
      <h1>${greeting()}${name}</h1>
      <p class="muted">${open ? `${open} task${open > 1 ? "s" : ""} left` : tasks.length ? "Everything for today is done" : "Plan one small thing for today"} · ${formatMinutes(focusToday)} focused</p>
    </section>

    <div class="quick">
      <button data-act="go" data-tab="focus"><span class="q-icon">⏱️</span>Focus</button>
      <button data-act="go" data-tab="sounds"><span class="q-icon">🎧</span>Sounds</button>
      <button data-act="go" data-tab="calm" data-sub="breathe"><span class="q-icon">🫁</span>Breathe</button>
      <button data-act="new-entry"><span class="q-icon">✍️</span>Write</button>
    </div>

    <section class="card">
      <div class="card-head"><h2>How are you right now?</h2>${mood ? `<span class="muted small">Saved</span>` : ""}</div>
      <div class="moods">
        ${MOODS.map(
          (m) => `<button class="mood ${mood === m.value ? "on" : ""}" data-act="mood" data-value="${m.value}" aria-label="${m.label}"><span class="face">${m.face}</span>${m.label}</button>`,
        ).join("")}
      </div>
    </section>

    <section class="card">
      <div class="card-head"><h2>Today's tasks</h2><span class="muted small">${tasks.length - open}/${tasks.length}</span></div>
      ${
        carry.length
          ? `<button class="btn ghost block" data-act="carry">↪ Move ${carry.length} unfinished from earlier to today</button>`
          : ""
      }
      <div>${tasks.length ? tasks.map(taskRow).join("") : `<div class="empty">Nothing planned yet. Add one small task.</div>`}</div>
      <form class="add-row" data-form="add-task">
        <input class="input" name="title" placeholder="Add a task…" maxlength="200" autocomplete="off" enterkeyhint="done" />
        <button class="btn primary" aria-label="Add task">＋</button>
      </form>
      <div class="chips" style="margin-top:10px">
        ${Object.entries(TRACKS)
          .map(([id, label]) => `<button class="chip ${ui.track === id ? "on" : ""}" data-act="track" data-value="${id}">${label}</button>`)
          .join("")}
      </div>
    </section>

    <section class="card">
      <div class="card-head"><h2>Daily habits</h2><button class="chip" data-act="edit-habits">Edit</button></div>
      <div class="habits">${state.habits.map((habit) => habitTile(habit, day)).join("") || `<div class="empty">No habits yet.</div>`}</div>
      <p class="muted small" style="margin-top:10px">Tap to count. Long-press to undo one.</p>
    </section>
  `;
}

function taskRow(task) {
  return `
    <div class="task ${task.doneAt ? "done" : ""}" data-id="${task.id}">
      <button class="check" data-act="toggle-task" data-id="${task.id}" aria-label="Toggle done">✓</button>
      <div class="grow"><div class="title">${esc(task.title)}</div></div>
      <span class="tag">${TRACKS[task.track]}</span>
      <button class="icon-btn" data-act="task-menu" data-id="${task.id}" aria-label="Task options">⋯</button>
    </div>`;
}

function habitTile(habit, day) {
  const count = habitCount(state.habitLog, day, habit.id);
  const progress = Math.min(1, count / habit.target);
  return `
    <button class="habit ${progress >= 1 ? "met" : ""}" data-habit="${habit.id}" style="--p:${progress}">
      <span class="fill"></span>
      <div class="row"><span style="font-size:1.3rem">${esc(habit.icon)}</span><span class="name grow">${esc(habit.name)}</span></div>
      <div class="count">${habit.target > 1 ? `${count} / ${habit.target}` : progress >= 1 ? "Done ✓" : "Not yet"}</div>
    </button>`;
}

function bumpHabit(id, amount) {
  const day = today();
  const habit = state.habits.find((h) => h.id === id);
  if (!habit) return;
  state.habitLog[day] ??= {};
  const current = state.habitLog[day][id] ?? 0;
  const next = Math.max(0, Math.min(habit.target, current + amount));
  if (next === current) {
    if (amount > 0) toast(`${habit.name} is already done today`);
    return;
  }
  state.habitLog[day][id] = next;
  commit();
  haptic(amount > 0 ? 15 : [8, 40, 8]);
  if (amount > 0 && next === habit.target) {
    scene.pulse(1);
    toast(`${habit.icon} ${habit.name} done`);
  }
  render();
}

// Long-press on a habit undoes one count; a normal tap adds one.
let pressTimer = null;
let pressFired = false;
viewEl.addEventListener("pointerdown", (event) => {
  const tile = event.target.closest("[data-habit]");
  if (!tile) return;
  pressFired = false;
  pressTimer = setTimeout(() => {
    pressFired = true;
    bumpHabit(tile.dataset.habit, -1);
  }, 520);
});
for (const type of ["pointerup", "pointerleave", "pointercancel"]) {
  viewEl.addEventListener(type, () => clearTimeout(pressTimer));
}
viewEl.addEventListener("click", (event) => {
  const tile = event.target.closest("[data-habit]");
  if (tile && !pressFired) bumpHabit(tile.dataset.habit, 1);
});
viewEl.addEventListener("contextmenu", (event) => {
  if (event.target.closest("[data-habit]")) event.preventDefault();
});

// ---------- Focus ----------

function timerProgress() {
  if (timer.phase === "idle") return 0;
  return 1 - timer.left / timer.total;
}

function renderFocus() {
  const day = today();
  const sessions = state.focus.filter((session) => session.day === day);
  const minutes = sessions.reduce((sum, s) => sum + s.minutes, 0);
  const openTasks = state.tasks.filter((task) => task.day === day && !task.doneAt);
  const task = state.tasks.find((t) => t.id === timer.taskId);
  const phaseLabel = timer.phase === "focus" ? "Focus" : timer.phase === "break" ? "Break" : timer.next === "break" ? "Break next" : "Ready";
  const s = state.settings;

  return `
    <section class="hero center">
      <div class="phase" id="timer-phase">${phaseLabel}</div>
      <div class="timer" id="timer-digits">${formatClock(timer.left)}</div>
      <p class="muted" id="timer-task">${task ? esc(task.title) : "Pick a task below, or just begin"}</p>
      <div class="controls" style="margin-top:18px">
        <button class="btn primary big" data-act="timer-toggle" id="timer-toggle">${timer.running ? "Pause" : timer.phase === "idle" ? "Start" : "Resume"}</button>
        ${timer.phase !== "idle" ? `<button class="btn ghost" data-act="timer-skip">Skip</button><button class="btn ghost" data-act="timer-reset">Reset</button>` : ""}
      </div>
    </section>

    <section class="card">
      <div class="card-head"><h2>Focus length</h2><span class="muted small">break ${s.breakMinutes}m</span></div>
      <div class="chips">
        ${[15, 25, 45, 60, 90].map((m) => `<button class="chip ${s.focusMinutes === m ? "on" : ""}" data-act="focus-len" data-value="${m}">${m} min</button>`).join("")}
      </div>
      <div class="chips" style="margin-top:10px">
        ${[5, 10, 15].map((m) => `<button class="chip ${s.breakMinutes === m ? "on" : ""}" data-act="break-len" data-value="${m}">${m} min break</button>`).join("")}
      </div>
    </section>

    <section class="card">
      <div class="card-head"><h2>Sound while focusing</h2></div>
      <div class="chips">
        <button class="chip ${s.focusSound === "none" ? "on" : ""}" data-act="focus-sound" data-value="none">Silence</button>
        ${SOUNDS.slice(0, 10)
          .map((sound) => `<button class="chip ${s.focusSound === sound.id ? "on" : ""}" data-act="focus-sound" data-value="${sound.id}">${sound.icon} ${sound.name}</button>`)
          .join("")}
      </div>
    </section>

    <section class="card">
      <div class="card-head"><h2>Working on</h2></div>
      ${
        openTasks.length
          ? `<div class="chips wrap">${openTasks
              .map((t) => `<button class="chip ${timer.taskId === t.id ? "on" : ""}" data-act="focus-task" data-id="${t.id}">${esc(t.title)}</button>`)
              .join("")}</div>`
          : `<div class="empty">No open tasks today. Add one on Today.</div>`
      }
    </section>

    <section class="stats">
      <div class="stat"><b>${formatMinutes(minutes)}</b><span>focused today</span></div>
      <div class="stat"><b>${sessions.length}</b><span>sessions</span></div>
      <div class="stat"><b>${formatMinutes(state.focus.filter((x) => lastDays(7).includes(x.day)).reduce((a, x) => a + x.minutes, 0))}</b><span>this week</span></div>
    </section>
  `;
}

function startTimer() {
  if (timer.phase === "idle") {
    timer.phase = timer.next;
    timer.total = (timer.phase === "focus" ? state.settings.focusMinutes : state.settings.breakMinutes) * 60;
    timer.left = timer.total;
    if (timer.phase === "focus" && state.settings.focusSound !== "none" && !engine.voices.size) {
      engine.setVolume(state.settings.focusSound, state.mixer.volumes[state.settings.focusSound] || 0.55);
      engine.resume();
    }
  }
  timer.running = true;
  timer.endsAt = Date.now() + timer.left * 1000;
  native?.keepAwake?.(true);
  haptic(15);
  scene.pulse(0.6);
  render();
}

function pauseTimer() {
  timer.running = false;
  timer.left = Math.max(0, (timer.endsAt - Date.now()) / 1000);
  native?.keepAwake?.(false);
  render();
}

function resetTimer() {
  timer.running = false;
  timer.phase = "idle";
  timer.next = "focus";
  timer.total = timer.left = state.settings.focusMinutes * 60;
  native?.keepAwake?.(false);
  render();
}

function finishPhase({ skipped = false } = {}) {
  const finished = timer.phase;
  if (finished === "focus") {
    const minutes = Math.round((timer.total - (skipped ? timer.left : 0)) / 60);
    if (minutes >= 1) {
      state.focus.push({ id: uid(), day: today(), minutes, taskId: timer.taskId, at: Date.now() });
      commit();
    }
  }
  timer.running = false;
  timer.phase = "idle";
  timer.next = finished === "focus" ? "break" : "focus";
  timer.total = timer.left = (timer.next === "focus" ? state.settings.focusMinutes : state.settings.breakMinutes) * 60;
  native?.keepAwake?.(false);
  if (!skipped) {
    engine.chime();
    haptic([60, 80, 60, 80, 120]);
    scene.pulse(1.4);
    toast(finished === "focus" ? "Focus block done. Take a real break." : "Break over. Ready when you are.");
    native?.notify?.("ResetPath", finished === "focus" ? "Focus block done. Time for a break." : "Break over.");
  }
  render();
}

// ---------- Sounds ----------

function renderSounds() {
  const mix = engine.mix();
  const active = Object.keys(mix);
  const left = engine.sleepRemaining();
  return `
    <section class="hero">
      <div class="eyebrow">Sound space</div>
      <h1>${active.length ? esc(active.map((id) => SOUNDS.find((s) => s.id === id)?.name).join(" + ")) : "Mix your calm"}</h1>
      <p class="muted" id="sleep-status">${left ? `Sleep timer · fades out in ${formatClock(left / 1000)}` : "Generated on your phone. Works offline."}</p>
      <div class="row" style="margin-top:14px">
        <button class="btn primary big" data-act="sound-toggle-all">${engine.playing ? "Pause" : active.length ? "Play" : "Play rain"}</button>
        ${active.length ? `<button class="btn ghost" data-act="sound-stop">Stop all</button>` : ""}
      </div>
    </section>

    <section class="card">
      <div class="card-head"><h2>Mixes</h2></div>
      <div class="chips">
        ${PRESETS.map((preset) => `<button class="chip" data-act="preset" data-value="${preset.id}">${preset.name}</button>`).join("")}
      </div>
    </section>

    <section class="card">
      <div class="card-head"><h2>Sounds</h2><span class="muted small">tap to toggle, slide to mix</span></div>
      <div class="sound-grid">
        ${SOUNDS.map((sound) => {
          const volume = mix[sound.id] ?? 0;
          const stored = state.mixer.volumes[sound.id] ?? 0.5;
          return `
            <div class="sound ${volume ? "on" : ""}">
              <button class="sound-toggle" data-act="sound" data-id="${sound.id}"><span class="s-icon">${sound.icon}</span>${sound.name}</button>
              <input type="range" min="0" max="1" step="0.01" value="${volume || stored}" data-input="sound-vol" data-id="${sound.id}" aria-label="${sound.name} volume" />
            </div>`;
        }).join("")}
      </div>
    </section>

    <section class="card">
      <div class="card-head"><h2>Volume</h2></div>
      <input type="range" min="0" max="1" step="0.01" value="${state.mixer.master}" data-input="master" aria-label="Master volume" />
      <div class="card-head" style="margin-top:16px"><h2>Sleep timer</h2></div>
      <div class="chips">
        ${[0, 15, 30, 45, 60, 90]
          .map((m) => `<button class="chip ${m === 0 && !left ? "on" : ""}" data-act="sleep" data-value="${m}">${m ? `${m} min` : "Off"}</button>`)
          .join("")}
      </div>
      <p class="muted small" style="margin-top:10px">Sound keeps playing with the screen off. The timer fades it out over the last minute.</p>
    </section>
  `;
}

function updateMiniPlayer() {
  const ids = [...engine.voices.keys()];
  const showSound = ids.length > 0 && route.tab !== "sounds";
  const showTimer = timer.phase !== "idle" && route.tab !== "focus";
  miniPlayer.hidden = !(showSound || showTimer);
  native?.audioActive?.(engine.playing);
  if (miniPlayer.hidden) return;
  const icons = ids.map((id) => SOUNDS.find((s) => s.id === id)?.icon ?? "").join(" ");
  miniPlayer.innerHTML = `
    ${showSound ? `<span class="eq ${engine.playing ? "" : "paused"}"><i></i><i></i><i></i></span>` : ""}
    <button class="grow" data-act="go" data-tab="${showTimer ? "focus" : "sounds"}" style="all:unset;cursor:pointer;flex:1">
      ${showTimer ? `⏱️ <b id="mini-timer">${formatClock(timer.left)}</b> <span class="muted small">${timer.phase}</span> ` : ""}${showSound ? `${icons} ${showTimer ? "" : `<span class="muted small">${engine.playing ? "Playing" : "Paused"}</span>`}` : ""}
    </button>
    ${showSound ? `<button class="icon-btn" data-act="sound-toggle-all" aria-label="Play or pause sound">${engine.playing ? "⏸" : "▶"}</button><button class="icon-btn" data-act="sound-stop" aria-label="Stop sound">✕</button>` : ""}`;
}

engine.onchange = () => {
  if (route.tab === "sounds") render();
  else updateMiniPlayer();
};

function rememberMix() {
  state.mixer.volumes = { ...state.mixer.volumes, ...engine.mix() };
  commit();
}

// ---------- Calm ----------

const BREATH_PATTERNS = {
  calm: { name: "Calm 4·6", steps: [["Breathe in", 4], ["Breathe out", 6]] },
  box: { name: "Box 4·4·4·4", steps: [["Breathe in", 4], ["Hold", 4], ["Breathe out", 4], ["Hold", 4]] },
  sleep: { name: "Sleep 4·7·8", steps: [["Breathe in", 4], ["Hold", 7], ["Breathe out", 8]] },
};

function renderCalm() {
  if (route.sub === "breathe") return renderBreathe();
  if (route.sub === "reset") return renderReset();
  if (route.sub === "journal") return renderJournal();
  if (route.sub === "entry") return renderEntry();
  return `
    <section class="hero">
      <div class="eyebrow">Calm</div>
      <h1>Slow down for a minute</h1>
      <p class="muted">Short tools for when your head is loud.</p>
    </section>
    <div class="option-list">
      <button class="option" data-act="go" data-tab="calm" data-sub="breathe"><span class="o-icon">🫁</span><div><h2>Guided breathing</h2><p class="muted small">Follow the orb. 1–5 minutes.</p></div></button>
      <button class="option" data-act="go" data-tab="calm" data-sub="reset"><span class="o-icon">🧭</span><div><h2>2-minute reset</h2><p class="muted small">Ground, name the thought, pick one next step.</p></div></button>
      <button class="option" data-act="go" data-tab="calm" data-sub="journal"><span class="o-icon">📓</span><div><h2>Journal</h2><p class="muted small">${state.journal.length} private page${state.journal.length === 1 ? "" : "s"} on this phone.</p></div></button>
    </div>
    ${helpCard()}
  `;
}

function helpCard() {
  const s = state.settings;
  return `
    <section class="card help-card">
      <h2>Need someone now?</h2>
      <p class="muted small" style="margin:6px 0 12px">If you might act on thoughts of harming yourself, contact a person or emergency services now. In India, Tele-MANAS is free and 24×7.</p>
      <div class="row wrap">
        <a class="btn primary" href="tel:14416">Call Tele-MANAS 14416</a>
        ${s.trustedPhone ? `<a class="btn ghost" href="tel:${esc(s.trustedPhone.replace(/[^+\d]/g, ""))}">Call ${esc(s.trustedName || "trusted person")}</a>` : `<button class="btn ghost" data-act="go" data-tab="you">Add a trusted person</button>`}
      </div>
    </section>`;
}

function renderBreathe() {
  const pattern = BREATH_PATTERNS[ui.breathPattern ?? "calm"];
  const running = Boolean(ui.breath);
  return `
    <section class="hero center">
      <div class="breath-label" id="breath-label">${running ? "" : "Ready"}</div>
      <p class="muted" id="breath-sub">${running ? "" : pattern.name}</p>
    </section>
    <div class="controls">
      <button class="btn primary big" data-act="breath-toggle">${running ? "Stop" : "Start"}</button>
    </div>
    <section class="card">
      <div class="card-head"><h2>Pattern</h2></div>
      <div class="chips">
        ${Object.entries(BREATH_PATTERNS)
          .map(([id, p]) => `<button class="chip ${(ui.breathPattern ?? "calm") === id ? "on" : ""}" data-act="breath-pattern" data-value="${id}">${p.name}</button>`)
          .join("")}
      </div>
      <p class="muted small" style="margin-top:10px">Calm for everyday stress, box before an exam or interview, 4·7·8 for falling asleep. Your phone gives a soft tap at each change.</p>
    </section>
  `;
}

function startBreathing() {
  const pattern = BREATH_PATTERNS[ui.breathPattern ?? "calm"];
  const cycle = pattern.steps.reduce((sum, [, seconds]) => sum + seconds, 0);
  ui.breath = { started: performance.now(), pattern, cycle, lastStep: -1 };
  native?.keepAwake?.(true);
  render();
  const tick = (now) => {
    if (!ui.breath) return;
    const elapsed = (now - ui.breath.started) / 1000;
    const inCycle = elapsed % cycle;
    let t = 0;
    let index = 0;
    while (t + pattern.steps[index][1] <= inCycle) {
      t += pattern.steps[index][1];
      index += 1;
    }
    const [label, seconds] = pattern.steps[index];
    const local = (inCycle - t) / seconds;
    const eased = 0.5 - 0.5 * Math.cos(Math.PI * local);
    let value;
    if (label === "Breathe in") value = eased;
    else if (label === "Breathe out") value = 1 - eased;
    else value = index > 0 && pattern.steps[index - 1][0] === "Breathe in" ? 1 : 0;
    scene.setBreath(value);
    const stepKey = Math.floor(elapsed / cycle) * 10 + index;
    if (stepKey !== ui.breath.lastStep) {
      ui.breath.lastStep = stepKey;
      haptic(label === "Hold" ? 8 : 20);
      const labelEl = $("#breath-label");
      if (labelEl) labelEl.textContent = label;
    }
    const sub = $("#breath-sub");
    if (sub) sub.textContent = `${Math.ceil(seconds - (inCycle - t))} · round ${Math.floor(elapsed / cycle) + 1}`;
    requestAnimationFrame(tick);
  };
  requestAnimationFrame(tick);
}

function stopBreathing() {
  if (!ui.breath) return;
  ui.breath = null;
  scene.setBreath(null);
  native?.keepAwake?.(false);
}

function renderReset() {
  ui.reset ??= { step: 0, seen: ["", "", ""], thought: "", action: "" };
  const r = ui.reset;
  const steps = `<div class="steps">${[0, 1, 2, 3].map((i) => `<i class="${i <= r.step ? "on" : ""}"></i>`).join("")}</div>`;
  const head = (title, text) => `
    <section class="hero" style="min-height:28vh">
      <div class="eyebrow">2-minute reset · step ${r.step + 1} of 4</div>
      <h1>${title}</h1>
      <p class="muted">${text}</p>
      ${steps}
    </section>`;

  if (r.step === 0) {
    return `${head("Look around", "Name three things you can see right now. It pulls attention back into the room.")}
      <section class="card stack">
        ${r.seen.map((value, i) => `<input class="input" data-input="seen" data-index="${i}" value="${esc(value)}" placeholder="Thing ${i + 1}" maxlength="80" />`).join("")}
        <button class="btn primary block" data-act="reset-next">Next</button>
      </section>`;
  }
  if (r.step === 1) {
    return `${head("What's the thought?", "Write it the way it sounds in your head. Nobody else sees this.")}
      <section class="card stack">
        <textarea class="input" data-input="thought" placeholder="e.g. Everyone else is getting placed and I'm behind" maxlength="1000">${esc(r.thought)}</textarea>
        <div class="row"><button class="btn ghost" data-act="reset-back">Back</button><button class="btn primary grow" data-act="reset-next">Next</button></div>
      </section>`;
  }
  if (r.step === 2) {
    const support = supportFor(r.thought);
    return `${head("A steadier view", esc(support.reframe))}
      <section class="card">
        <div class="card-head"><h2>Pick one small next step</h2></div>
        <div class="option-list">
          ${support.actions
            .map((action) => `<button class="option ${r.action === action ? "on" : ""}" data-act="reset-action" data-value="${esc(action)}" style="${r.action === action ? "border-color:var(--accent)" : ""}"><span class="o-icon">${r.action === action ? "✅" : "▫️"}</span><span>${esc(action)}</span></button>`)
            .join("")}
        </div>
        <input class="input" style="margin-top:10px" data-input="reset-own" placeholder="Or write your own…" maxlength="160" value="${support.actions.includes(r.action) ? "" : esc(r.action)}" />
        <div class="row" style="margin-top:12px"><button class="btn ghost" data-act="reset-back">Back</button><button class="btn primary grow" data-act="reset-next">Next</button></div>
      </section>`;
  }
  return `${head("You did the hard part", "Pausing instead of spiralling is a real skill. Now make the next step easy to start.")}
    <section class="card stack">
      <p><b>${esc(r.action || "One small next step")}</b></p>
      <button class="btn primary block" data-act="reset-task">Add to today's tasks</button>
      <button class="btn ghost block" data-act="reset-focus">Start a 10-minute focus on it</button>
      <button class="btn ghost block" data-act="reset-done">Done</button>
    </section>`;
}

function renderJournal() {
  const entries = [...state.journal].sort((a, b) => b.updatedAt - a.updatedAt);
  return `
    <section class="hero" style="min-height:26vh">
      <div class="eyebrow">Journal</div>
      <h1>Your pages</h1>
      <p class="muted">Private and stored only on this phone.</p>
    </section>
    <button class="btn primary block" data-act="new-entry">✍️ New page</button>
    <section class="card">
      ${
        entries.length
          ? entries
              .map(
                (entry) => `
            <div class="entry" data-act="open-entry" data-id="${entry.id}">
              <div class="muted small">${new Date(entry.createdAt).toLocaleString(undefined, { weekday: "short", day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" })}</div>
              <p>${esc(entry.body.slice(0, 220))}</p>
            </div>`,
              )
              .join("")
          : `<div class="empty">Write whatever is on your mind. Nothing leaves this phone.</div>`
      }
    </section>`;
}

function renderEntry() {
  const entry = state.journal.find((e) => e.id === route.param);
  const prompts = ["What took most of my energy today?", "One thing that went okay:", "What am I worried about, exactly?", "Tomorrow I will try:"];
  return `
    <section class="hero" style="min-height:16vh">
      <div class="eyebrow">${entry ? new Date(entry.createdAt).toLocaleDateString(undefined, { weekday: "long", day: "numeric", month: "long" }) : "New page"}</div>
    </section>
    <section class="card stack">
      <div class="chips">${prompts.map((p) => `<button class="chip" data-act="prompt" data-value="${esc(p)}">${esc(p)}</button>`).join("")}</div>
      <textarea class="input" id="entry-body" style="min-height:45vh" placeholder="Write freely…" maxlength="20000">${esc(entry?.body ?? "")}</textarea>
      <div class="row">
        ${entry ? `<button class="btn danger" data-act="delete-entry">Delete</button>` : ""}
        <button class="btn primary grow" data-act="save-entry">Save</button>
      </div>
    </section>`;
}

function saveEntry() {
  const body = $("#entry-body").value.trim();
  if (!body) {
    toast("Write something first");
    return;
  }
  const existing = state.journal.find((e) => e.id === route.param);
  if (existing) {
    existing.body = body;
    existing.updatedAt = Date.now();
  } else {
    state.journal.push({ id: uid(), body, createdAt: Date.now(), updatedAt: Date.now() });
  }
  commit();
  haptic(15);
  scene.pulse(0.8);
  if (containsCrisisLanguage(body)) showCrisisSheet();
  else toast("Saved");
  go("calm", "journal");
}

function showCrisisSheet() {
  openSheet(`
    <h2>You don't have to handle this alone</h2>
    <p class="muted" style="margin:8px 0 14px">What you wrote sounds really heavy. If you might act on thoughts of harming yourself, please contact someone now, or go to the nearest emergency department.</p>
    ${helpCard()}
    <button class="btn ghost block" style="margin-top:12px" data-act="close-sheet">Close</button>
  `);
}

// ---------- You ----------

function renderYou() {
  const days7 = lastDays(7);
  const focus = focusMinutesByDay(state.focus, days7);
  const maxFocus = Math.max(30, ...focus.map((d) => d.minutes));
  const weekFocus = focus.reduce((sum, d) => sum + d.minutes, 0);
  const tasksDone = state.tasks.filter((t) => t.doneAt && days7.includes(dateKey(new Date(t.doneAt)))).length;
  const heatDays = lastDays(35);
  const moodDays = lastDays(14);
  const s = state.settings;
  const trackCounts = Object.keys(TRACKS).map((track) => [
    track,
    state.tasks.filter((t) => t.track === track && t.doneAt && t.doneAt > Date.now() - 30 * 864e5).length,
  ]);
  const maxTrack = Math.max(1, ...trackCounts.map(([, n]) => n));
  const todayKey = today();

  return `
    <section class="hero" style="min-height:22vh">
      <div class="eyebrow">Last 7 days</div>
      <h1>Your week</h1>
    </section>
    <section class="stats">
      <div class="stat"><b>${formatMinutes(weekFocus)}</b><span>focused</span></div>
      <div class="stat"><b>${tasksDone}</b><span>tasks done</span></div>
      <div class="stat"><b>${activeDays(state, days7)}/7</b><span>days active</span></div>
    </section>

    <section class="card">
      <div class="card-head"><h2>Focus minutes</h2></div>
      <div class="bars">
        ${focus
          .map(
            (d, i) => `<div class="bar ${d.day === todayKey ? "today" : ""}" style="--i:${i}"><small>${d.minutes || ""}</small><i style="--h:${(d.minutes / maxFocus) * 100}%"></i><span>${weekdayShort(d.day)}</span></div>`,
          )
          .join("")}
      </div>
    </section>

    <section class="card">
      <div class="card-head"><h2>Habits, last 5 weeks</h2></div>
      <div class="heat">
        ${heatDays.map((day, i) => `<i style="--v:${habitScore(state.habits, state.habitLog, day).toFixed(2)};--i:${i}" title="${day}"></i>`).join("")}
      </div>
    </section>

    <section class="card">
      <div class="card-head"><h2>Mood, last 2 weeks</h2></div>
      <div class="mood-line">
        ${moodDays
          .map((day) => {
            const mood = MOODS.find((m) => m.value === state.moods[day]);
            return `<span><b>${mood ? mood.face : "·"}</b>${weekdayShort(day)}</span>`;
          })
          .join("")}
      </div>
    </section>

    <section class="card">
      <div class="card-head"><h2>Done in 30 days</h2></div>
      ${trackCounts
        .map(
          ([track, n]) => `<div class="row" style="margin:6px 0"><span style="width:96px" class="small">${TRACKS[track]}</span><div class="grow" style="background:var(--surface-2);border-radius:6px;height:10px;overflow:hidden"><div style="height:100%;width:${(n / maxTrack) * 100}%;background:var(--accent);border-radius:6px;transition:width .6s"></div></div><b class="small" style="width:24px;text-align:right">${n}</b></div>`,
        )
        .join("")}
    </section>

    <section class="card">
      <div class="card-head"><h2>Settings</h2></div>
      <label class="field">Your name<input class="input" data-input="name" value="${esc(s.name)}" maxlength="40" placeholder="Optional" /></label>
      <div class="setting"><span>Dark theme</span><input type="checkbox" class="switch" data-input="theme" ${s.theme === "dark" ? "checked" : ""} /></div>
      <div class="setting"><span>Motion</span>
        <div class="chips">${["full", "low", "off"].map((m) => `<button class="chip ${s.motion === m ? "on" : ""}" data-act="motion" data-value="${m}">${m[0].toUpperCase() + m.slice(1)}</button>`).join("")}</div>
      </div>
      <p class="muted small">Low halves the frame rate to save battery. Off stops all animation.</p>
    </section>

    <section class="card stack">
      <h2>Trusted person</h2>
      <label class="field">Name<input class="input" data-input="trusted-name" value="${esc(s.trustedName)}" maxlength="60" /></label>
      <label class="field">Phone<input class="input" data-input="trusted-phone" value="${esc(s.trustedPhone)}" inputmode="tel" maxlength="20" /></label>
    </section>

    <section class="card stack">
      <h2>Your data</h2>
      <p class="muted small">Everything stays on this phone. No account, no cloud, no tracking. Back it up before you uninstall or change phones.</p>
      <div class="row wrap">
        <button class="btn" data-act="export">Save backup</button>
        <label class="btn">Restore backup<input type="file" accept="application/json,.json" data-input="import" hidden /></label>
      </div>
      <button class="btn danger" data-act="delete-all">Delete everything</button>
    </section>

    ${helpCard()}
    <p class="muted small" style="text-align:center;margin-top:18px">ResetPath 1.0 · a support and productivity tool, not medical care.</p>
  `;
}

// ---------- Sheets ----------

function openSheet(html) {
  sheetRoot.innerHTML = `<div class="scrim"><div class="sheet" role="dialog" aria-modal="true">${html}</div></div>`;
  $(".scrim", sheetRoot).addEventListener("click", (event) => {
    if (event.target.classList.contains("scrim")) closeSheet();
  });
}

function closeSheet() {
  sheetRoot.innerHTML = "";
}

function habitsSheet() {
  openSheet(`
    <h2>Daily habits</h2>
    <div style="margin:10px 0">
      ${state.habits
        .map(
          (h) => `<div class="setting"><span>${esc(h.icon)} ${esc(h.name)} <span class="muted small">× ${h.target}</span></span><button class="icon-btn" data-act="remove-habit" data-id="${h.id}" aria-label="Remove">✕</button></div>`,
        )
        .join("") || `<div class="empty">No habits.</div>`}
    </div>
    <form class="stack" data-form="add-habit">
      <div class="row"><input class="input" name="icon" style="width:64px;text-align:center" value="✅" maxlength="4" aria-label="Icon" /><input class="input grow" name="name" placeholder="New habit, e.g. Read 10 pages" maxlength="40" required /></div>
      <label class="field">Times per day<input class="input" name="target" type="number" min="1" max="20" value="1" /></label>
      <button class="btn primary block">Add habit</button>
    </form>
  `);
}

function taskSheet(task) {
  openSheet(`
    <h2>Edit task</h2>
    <form class="stack" data-form="edit-task" data-id="${task.id}" style="margin-top:12px">
      <input class="input" name="title" value="${esc(task.title)}" maxlength="200" required />
      <div class="chips wrap">${Object.entries(TRACKS)
        .map(([id, label]) => `<label class="chip ${task.track === id ? "on" : ""}"><input type="radio" name="track" value="${id}" ${task.track === id ? "checked" : ""} hidden />${label}</label>`)
        .join("")}</div>
      <div class="row">
        <button type="button" class="btn ghost" data-act="task-tomorrow" data-id="${task.id}">Move to tomorrow</button>
        <button type="button" class="btn danger" data-act="task-delete" data-id="${task.id}">Delete</button>
      </div>
      <button class="btn primary block">Save</button>
    </form>
  `);
  $("[data-form=edit-task]", sheetRoot).addEventListener("change", (event) => {
    if (event.target.name === "track") {
      sheetRoot.querySelectorAll(".chip").forEach((chip) => chip.classList.toggle("on", chip.contains(event.target)));
    }
  });
}

// ---------- Actions ----------

const actions = {
  go: (el) => go(el.dataset.tab, el.dataset.sub ?? null),
  "close-sheet": closeSheet,
  mood: (el) => {
    state.moods[today()] = Number(el.dataset.value);
    commit();
    haptic(15);
    scene.pulse(0.7);
    render();
  },
  track: (el) => {
    ui.track = el.dataset.value;
    render();
  },
  "toggle-task": (el) => {
    const task = state.tasks.find((t) => t.id === el.dataset.id);
    task.doneAt = task.doneAt ? null : Date.now();
    commit();
    if (task.doneAt) {
      haptic([10, 40, 20]);
      scene.pulse(1);
    }
    render();
  },
  "task-menu": (el) => taskSheet(state.tasks.find((t) => t.id === el.dataset.id)),
  "task-tomorrow": (el) => {
    const task = state.tasks.find((t) => t.id === el.dataset.id);
    task.day = addDays(today(), 1);
    commit();
    closeSheet();
    toast("Moved to tomorrow");
    render();
  },
  "task-delete": (el) => {
    state.tasks = state.tasks.filter((t) => t.id !== el.dataset.id);
    commit();
    closeSheet();
    render();
  },
  carry: () => {
    const day = today();
    let moved = 0;
    for (const task of state.tasks) {
      if (!task.doneAt && task.day < day) {
        task.day = day;
        moved += 1;
      }
    }
    commit();
    toast(`Moved ${moved} task${moved > 1 ? "s" : ""} to today`);
    render();
  },
  "edit-habits": habitsSheet,
  "remove-habit": (el) => {
    state.habits = state.habits.filter((h) => h.id !== el.dataset.id);
    commit();
    habitsSheet();
    render();
  },
  "timer-toggle": () => (timer.running ? pauseTimer() : startTimer()),
  "timer-skip": () => finishPhase({ skipped: true }),
  "timer-reset": resetTimer,
  "focus-len": (el) => {
    state.settings.focusMinutes = Number(el.dataset.value);
    commit();
    if (timer.phase === "idle" && timer.next === "focus") timer.total = timer.left = state.settings.focusMinutes * 60;
    render();
  },
  "break-len": (el) => {
    state.settings.breakMinutes = Number(el.dataset.value);
    commit();
    if (timer.phase === "idle" && timer.next === "break") timer.total = timer.left = state.settings.breakMinutes * 60;
    render();
  },
  "focus-sound": (el) => {
    state.settings.focusSound = el.dataset.value;
    commit();
    render();
  },
  "focus-task": (el) => {
    timer.taskId = timer.taskId === el.dataset.id ? null : el.dataset.id;
    render();
  },
  sound: (el) => {
    const id = el.dataset.id;
    if (engine.volumeOf(id)) engine.setVolume(id, 0);
    else engine.setVolume(id, state.mixer.volumes[id] || 0.5);
    engine.resume();
    haptic(10);
    scene.pulse(0.5);
    rememberMix();
  },
  "sound-toggle-all": () => {
    if (engine.playing) engine.pause();
    else if (engine.voices.size) engine.resume();
    else {
      engine.setVolume("rain", state.mixer.volumes.rain || 0.6);
      engine.resume();
    }
    haptic(10);
  },
  "sound-stop": () => engine.stopAll(),
  preset: (el) => {
    const preset = PRESETS.find((p) => p.id === el.dataset.value);
    engine.applyMix(preset.mix);
    engine.resume();
    rememberMix();
    scene.pulse(0.8);
    toast(preset.name);
  },
  sleep: (el) => {
    const minutes = Number(el.dataset.value);
    if (minutes) {
      if (!engine.voices.size) engine.setVolume("brown", 0.5);
      engine.resume();
      engine.startSleepTimer(minutes);
      toast(`Sound will fade out in ${minutes} minutes`);
    } else {
      engine.cancelSleepTimer();
      render();
    }
  },
  "breath-toggle": () => {
    if (ui.breath) {
      stopBreathing();
      render();
    } else startBreathing();
  },
  "breath-pattern": (el) => {
    ui.breathPattern = el.dataset.value;
    if (ui.breath) {
      stopBreathing();
      startBreathing();
    } else render();
  },
  "reset-next": () => {
    const r = ui.reset;
    if (r.step === 1) {
      if (!r.thought.trim()) {
        toast("Write the thought, even a few words");
        return;
      }
      if (containsCrisisLanguage(r.thought)) {
        showCrisisSheet();
        return;
      }
    }
    if (r.step === 2 && !r.action.trim()) {
      toast("Pick or write one small step");
      return;
    }
    r.step += 1;
    haptic(10);
    scene.pulse(0.5);
    render({ animate: true });
  },
  "reset-back": () => {
    ui.reset.step = Math.max(0, ui.reset.step - 1);
    render({ animate: true });
  },
  "reset-action": (el) => {
    ui.reset.action = el.dataset.value;
    render();
  },
  "reset-task": () => {
    addTask(ui.reset.action, "life");
    ui.reset = null;
    toast("Added to today");
    go("today");
  },
  "reset-focus": () => {
    const task = addTask(ui.reset.action, "life");
    ui.reset = null;
    timer.taskId = task.id;
    timer.phase = "idle";
    timer.next = "focus";
    timer.total = timer.left = 10 * 60;
    go("focus");
    startTimer();
  },
  "reset-done": () => {
    ui.reset = null;
    go("calm");
  },
  "new-entry": () => go("calm", "entry", null),
  "open-entry": (el) => go("calm", "entry", el.dataset.id),
  "save-entry": saveEntry,
  "delete-entry": () => {
    openSheet(`
      <h2>Delete this page?</h2>
      <p class="muted" style="margin:8px 0 14px">This cannot be undone.</p>
      <div class="row"><button class="btn ghost grow" data-act="close-sheet">Keep</button><button class="btn danger grow" data-act="confirm-delete-entry">Delete</button></div>`);
  },
  "confirm-delete-entry": () => {
    state.journal = state.journal.filter((e) => e.id !== route.param);
    commit();
    closeSheet();
    go("calm", "journal");
  },
  prompt: (el) => {
    const area = $("#entry-body");
    area.value = `${area.value ? `${area.value}\n\n` : ""}${el.dataset.value}\n`;
    area.focus();
    area.setSelectionRange(area.value.length, area.value.length);
  },
  motion: (el) => {
    state.settings.motion = el.dataset.value;
    commit();
    applyAppearance();
    render();
  },
  export: () => {
    const text = exportBackup(state);
    const name = `resetpath-backup-${today()}.json`;
    if (native?.saveFile) {
      native.saveFile(name, "application/json", text);
      return;
    }
    const link = document.createElement("a");
    link.href = URL.createObjectURL(new Blob([text], { type: "application/json" }));
    link.download = name;
    link.click();
    setTimeout(() => URL.revokeObjectURL(link.href), 2000);
  },
  "delete-all": () => {
    openSheet(`
      <h2>Delete everything?</h2>
      <p class="muted" style="margin:8px 0 14px">Tasks, habits, moods, focus history, journal pages, and settings will be removed from this phone. This cannot be undone.</p>
      <div class="row"><button class="btn ghost grow" data-act="close-sheet">Cancel</button><button class="btn danger grow" data-act="confirm-delete-all">Delete everything</button></div>`);
  },
  "confirm-delete-all": () => {
    clear();
    state = defaultState();
    state.settings.introSeen = true;
    commit();
    closeSheet();
    applyAppearance();
    toast("All data deleted");
    go("today");
  },
  "intro-done": () => {
    const input = $("[name=intro-name]", sheetRoot);
    state.settings.name = input.value.trim().slice(0, 40);
    state.settings.introSeen = true;
    commit();
    closeSheet();
    render({ animate: true });
  },
};

function addTask(title, track) {
  const task = { id: uid(), title: title.trim().slice(0, 200), track, day: today(), doneAt: null, createdAt: Date.now() };
  state.tasks.push(task);
  commit();
  return task;
}

function handleAction(event) {
  const el = event.target.closest("[data-act]");
  if (!el || !actions[el.dataset.act]) return;
  event.preventDefault();
  actions[el.dataset.act](el);
}

for (const root of [viewEl, sheetRoot, miniPlayer]) root.addEventListener("click", handleAction);

const field = (form, name) => form.elements.namedItem(name);

const forms = {
  "add-task": (form) => {
    const title = field(form, "title").value.trim();
    if (!title) return;
    addTask(title, ui.track);
    haptic(10);
    render();
    $("[data-form=add-task] input")?.focus();
  },
  "add-habit": (form) => {
    const name = field(form, "name").value.trim();
    if (!name) return;
    state.habits.push({
      id: uid(),
      name: name.slice(0, 40),
      icon: field(form, "icon").value.trim().slice(0, 4) || "✅",
      target: Math.min(20, Math.max(1, Number(field(form, "target").value) || 1)),
    });
    commit();
    habitsSheet();
    render();
  },
  "edit-task": (form) => {
    const task = state.tasks.find((t) => t.id === form.dataset.id);
    const title = field(form, "title").value.trim();
    if (!title) return;
    task.title = title.slice(0, 200);
    task.track = field(form, "track").value || task.track;
    commit();
    closeSheet();
    render();
  },
};

for (const root of [viewEl, sheetRoot]) {
  root.addEventListener("submit", (event) => {
    const form = event.target.closest("[data-form]");
    if (!form) return;
    event.preventDefault();
    forms[form.dataset.form]?.(form);
  });
}

const inputs = {
  "sound-vol": (el) => {
    const volume = Number(el.value);
    state.mixer.volumes[el.dataset.id] = volume;
    engine.setVolume(el.dataset.id, volume);
    engine.resume();
    commit();
  },
  master: (el) => {
    state.mixer.master = Number(el.value);
    engine.setMaster(state.mixer.master);
    commit();
  },
  seen: (el) => {
    ui.reset.seen[Number(el.dataset.index)] = el.value;
  },
  thought: (el) => {
    ui.reset.thought = el.value;
  },
  "reset-own": (el) => {
    ui.reset.action = el.value;
    viewEl.querySelectorAll("[data-act=reset-action]").forEach((option) => {
      option.style.borderColor = "";
      option.querySelector(".o-icon").textContent = "▫️";
    });
  },
  name: (el) => {
    state.settings.name = el.value.trim();
    commit();
  },
  "trusted-name": (el) => {
    state.settings.trustedName = el.value.trim();
    commit();
  },
  "trusted-phone": (el) => {
    if (!isValidPhone(el.value)) return;
    state.settings.trustedPhone = el.value.trim();
    commit();
  },
};

// Sliders update live without re-rendering, so dragging stays smooth.
viewEl.addEventListener("input", (event) => {
  const el = event.target.closest("[data-input]");
  if (el && inputs[el.dataset.input] && el.type !== "file" && el.type !== "checkbox") inputs[el.dataset.input](el);
});

viewEl.addEventListener("change", async (event) => {
  const el = event.target;
  if (el.dataset.input === "theme") {
    state.settings.theme = el.checked ? "dark" : "light";
    commit();
    applyAppearance();
  } else if (el.dataset.input === "trusted-phone" && !isValidPhone(el.value)) {
    toast("Use digits only, with an optional + country code");
  } else if (el.dataset.input === "import" && el.files?.[0]) {
    try {
      state = importBackup(await el.files[0].text());
      commit();
      applyAppearance();
      toast("Backup restored");
      render({ animate: true });
    } catch (error) {
      toast(error.message || "Could not read that file");
    }
  }
});

// ---------- Live updates ----------

function updateLiveBits() {
  const mini = $("#mini-timer");
  if (mini) mini.textContent = formatClock(timer.left);
  if (route.tab === "focus") {
    const digits = $("#timer-digits");
    if (digits) digits.textContent = formatClock(timer.left);
    scene.setRing(timerProgress());
  }
  if (route.tab === "sounds") {
    const status = $("#sleep-status");
    const left = engine.sleepRemaining();
    if (status && left) status.textContent = `Sleep timer · fades out in ${formatClock(left / 1000)}`;
  }
}

setInterval(() => {
  if (timer.running) {
    timer.left = Math.max(0, (timer.endsAt - Date.now()) / 1000);
    if (timer.left <= 0) finishPhase();
  }
  updateLiveBits();
}, 250);

// ---------- Start ----------

function showIntro() {
  openSheet(`
    <h2 style="font-size:1.4rem">Welcome to ResetPath</h2>
    <p class="muted" style="margin:8px 0 14px">Plan your day, focus with ambient sound, track small habits, and slow down when your head gets loud. Everything stays on this phone.</p>
    <label class="field">What should we call you?<input class="input" name="intro-name" maxlength="40" placeholder="Optional" /></label>
    <p class="muted small" style="margin:14px 0">ResetPath is a support and productivity tool, not medical care. In a crisis, contact a trusted person, Tele-MANAS (14416), or emergency services.</p>
    <button class="btn primary block big" data-act="intro-done">Let's go</button>
  `);
}

applyAppearance();
render({ animate: true });
scene.start();
if (!state.settings.introSeen) showIntro();
if (importedLegacy) toast(`Brought over ${state.tasks.length} tasks and ${state.journal.length} journal pages`);
