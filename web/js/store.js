// Local persistence. Everything lives in this device's WebView storage; the
// app has no network access and no backend.

import { TRACKS, dateKey } from "./logic.js";

const KEY = "resetpath.v3";
export const SCHEMA_VERSION = 3;

export const DEFAULT_HABITS = [
  { id: "water", name: "Water", icon: "💧", target: 8 },
  { id: "move", name: "Move 20 min", icon: "🚶", target: 1 },
  { id: "dsa", name: "1 DSA problem", icon: "🧩", target: 1 },
  { id: "sleep", name: "Sleep by 12", icon: "🌙", target: 1 },
];

export function defaultState() {
  return {
    version: SCHEMA_VERSION,
    settings: {
      name: "",
      theme: "dark",
      motion: "full",
      focusMinutes: 25,
      breakMinutes: 5,
      focusSound: "rain",
      trustedName: "",
      trustedPhone: "",
      introSeen: false,
      orbHintSeen: false,
    },
    tasks: [],
    habits: DEFAULT_HABITS.map((habit) => ({ ...habit })),
    habitLog: {},
    moods: {},
    focus: [],
    journal: [],
    mixer: { master: 0.8, volumes: { rain: 0.6 } },
  };
}

// Fill missing fields and drop malformed records so an old or hand-edited
// backup can never crash rendering.
export function normalizeState(raw) {
  const base = defaultState();
  if (!raw || typeof raw !== "object") return base;
  const text = (value, max = 4000) => (typeof value === "string" ? value.slice(0, max) : "");
  const list = (value) => (Array.isArray(value) ? value : []);
  const settings = { ...base.settings, ...(raw.settings && typeof raw.settings === "object" ? raw.settings : {}) };
  settings.focusMinutes = clampInt(settings.focusMinutes, 5, 120, 25);
  settings.breakMinutes = clampInt(settings.breakMinutes, 1, 60, 5);
  if (!["dark", "light"].includes(settings.theme)) settings.theme = "dark";
  if (!["full", "low", "off"].includes(settings.motion)) settings.motion = "full";

  const habits = list(raw.habits)
    .filter((habit) => habit && typeof habit.id === "string" && typeof habit.name === "string")
    .map((habit) => ({
      id: habit.id,
      name: text(habit.name, 40),
      icon: text(habit.icon, 8) || "✅",
      target: clampInt(habit.target, 1, 20, 1),
    }));

  return {
    version: SCHEMA_VERSION,
    settings,
    tasks: list(raw.tasks)
      .filter((task) => task && typeof task.title === "string")
      .map((task) => ({
        id: text(task.id, 40) || uid(),
        title: text(task.title, 200),
        track: task.track in TRACKS ? task.track : "life",
        day: /^\d{4}-\d{2}-\d{2}$/.test(task.day) ? task.day : dateKey(),
        doneAt: typeof task.doneAt === "number" ? task.doneAt : null,
        createdAt: typeof task.createdAt === "number" ? task.createdAt : Date.now(),
      })),
    habits: raw.habits ? habits : base.habits,
    habitLog: raw.habitLog && typeof raw.habitLog === "object" ? raw.habitLog : {},
    moods: raw.moods && typeof raw.moods === "object" ? raw.moods : {},
    focus: list(raw.focus).filter(
      (session) => session && typeof session.day === "string" && typeof session.minutes === "number",
    ),
    journal: list(raw.journal)
      .filter((entry) => entry && typeof entry.body === "string")
      .map((entry) => ({
        id: text(entry.id, 40) || uid(),
        body: text(entry.body, 20000),
        createdAt: typeof entry.createdAt === "number" ? entry.createdAt : Date.now(),
        updatedAt: typeof entry.updatedAt === "number" ? entry.updatedAt : Date.now(),
      })),
    mixer: {
      master: typeof raw.mixer?.master === "number" ? raw.mixer.master : base.mixer.master,
      volumes: raw.mixer?.volumes && typeof raw.mixer.volumes === "object" ? raw.mixer.volumes : {},
    },
  };
}

function clampInt(value, min, max, fallback) {
  const number = Math.round(Number(value));
  return Number.isFinite(number) ? Math.min(max, Math.max(min, number)) : fallback;
}

export function uid() {
  return Date.now().toString(36) + Math.random().toString(36).slice(2, 8);
}

export function load(storage = globalThis.localStorage) {
  try {
    const raw = storage?.getItem(KEY);
    return normalizeState(raw ? JSON.parse(raw) : null);
  } catch {
    return defaultState();
  }
}

export function save(state, storage = globalThis.localStorage) {
  try {
    storage?.setItem(KEY, JSON.stringify(state));
    return true;
  } catch {
    return false;
  }
}

export function clear(storage = globalThis.localStorage) {
  try {
    storage?.removeItem(KEY);
  } catch {
    // Nothing else to do; the in-memory state is reset by the caller.
  }
}

export function hasSaved(storage = globalThis.localStorage) {
  try {
    return storage?.getItem(KEY) != null;
  } catch {
    return false;
  }
}

const LEGACY_TRACKS = { dsa: "dsa", core_cs: "core", project: "project", applications: "apply" };

function legacyTime(value) {
  const time = Date.parse(value ?? "");
  return Number.isFinite(time) ? time : null;
}

// Converts the JSON read from the 0.1/0.2 SQLite database into this state.
export function fromLegacy(json, base = defaultState()) {
  const legacy = typeof json === "string" ? JSON.parse(json) : json;
  const state = structuredClone(base);
  for (const row of legacy.tasks ?? []) {
    if (!row.title) continue;
    const createdAt = legacyTime(row.created_at) ?? Date.now();
    state.tasks.push({
      id: uid(),
      title: String(row.title).slice(0, 200),
      track: LEGACY_TRACKS[row.track] ?? "life",
      day: /^\d{4}-\d{2}-\d{2}$/.test(row.planned_date ?? "") ? row.planned_date : dateKey(new Date(createdAt)),
      doneAt: legacyTime(row.completed_at),
      createdAt,
    });
  }
  for (const row of legacy.diary ?? []) {
    if (!row.body) continue;
    const createdAt = legacyTime(row.created_at) ?? Date.now();
    state.journal.push({ id: uid(), body: String(row.body), createdAt, updatedAt: legacyTime(row.updated_at) ?? createdAt });
  }
  for (const row of legacy.thoughts ?? []) {
    if (!row.thought) continue;
    const createdAt = legacyTime(row.created_at) ?? Date.now();
    const body = `Reset: ${row.thought}${row.next_action ? `\nNext step: ${row.next_action}` : ""}`;
    state.journal.push({ id: uid(), body, createdAt, updatedAt: createdAt });
  }
  const settings = legacy.settings?.[0];
  if (settings) {
    state.settings.trustedName = String(settings.trusted_person_name ?? "").slice(0, 60);
    state.settings.trustedPhone = String(settings.trusted_person_phone ?? "").slice(0, 20);
    if (settings.theme_mode === "light" || settings.theme_mode === "dark") state.settings.theme = settings.theme_mode;
  }
  return normalizeState(state);
}

export function exportBackup(state) {
  return JSON.stringify({ app: "ResetPath", exportedAt: new Date().toISOString(), ...state }, null, 2);
}

export function importBackup(text) {
  const parsed = JSON.parse(text);
  if (!parsed || parsed.app !== "ResetPath") throw new Error("This file is not a ResetPath backup.");
  return normalizeState(parsed);
}
