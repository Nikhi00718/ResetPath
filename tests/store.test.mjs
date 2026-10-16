import assert from "node:assert/strict";
import { test } from "node:test";

import {
  defaultState,
  exportBackup,
  fromLegacy,
  hasSaved,
  importBackup,
  load,
  normalizeState,
  save,
} from "../web/js/store.js";

function memoryStorage() {
  const data = new Map();
  return {
    getItem: (key) => (data.has(key) ? data.get(key) : null),
    setItem: (key, value) => data.set(key, String(value)),
    removeItem: (key) => data.delete(key),
  };
}

test("state survives a save and load round trip", () => {
  const storage = memoryStorage();
  const state = defaultState();
  state.tasks.push({ id: "a", title: "Revise joins", track: "core", day: "2026-10-16", doneAt: null, createdAt: 1 });
  assert.ok(!hasSaved(storage));
  assert.ok(save(state, storage));
  assert.ok(hasSaved(storage));
  assert.deepEqual(load(storage), state);
});

test("corrupt storage falls back to defaults", () => {
  const storage = memoryStorage();
  storage.setItem("resetpath.v3", "{not json");
  assert.deepEqual(load(storage), defaultState());
});

test("normalize drops malformed records and clamps settings", () => {
  const state = normalizeState({
    settings: { focusMinutes: 999, breakMinutes: -4, theme: "neon", motion: "wild" },
    tasks: [null, { title: 5 }, { title: "ok", track: "unknown", day: "bad" }],
    journal: [{ body: "page" }, { nope: true }],
    habits: [{ id: "h", name: "Read", target: 100 }],
  });
  assert.equal(state.settings.focusMinutes, 120);
  assert.equal(state.settings.breakMinutes, 1);
  assert.equal(state.settings.theme, "dark");
  assert.equal(state.settings.motion, "full");
  assert.equal(state.tasks.length, 1);
  assert.equal(state.tasks[0].track, "life");
  assert.match(state.tasks[0].day, /^\d{4}-\d{2}-\d{2}$/);
  assert.equal(state.journal.length, 1);
  assert.equal(state.habits[0].target, 20);
});

test("backup export and import round trip", () => {
  const state = defaultState();
  state.journal.push({ id: "j", body: "hello", createdAt: 1, updatedAt: 2 });
  assert.deepEqual(importBackup(exportBackup(state)), state);
});

test("import rejects files that are not ResetPath backups", () => {
  assert.throws(() => importBackup(JSON.stringify({ tasks: [] })), /not a ResetPath backup/);
  assert.throws(() => importBackup("garbage"));
});

test("legacy SQLite export maps into the new state", () => {
  const state = fromLegacy(
    JSON.stringify({
      tasks: [
        { title: "Two pointers", track: "dsa", planned_date: "2026-07-20", completed_at: "2026-07-20T10:00:00+00:00", created_at: "2026-07-19T09:00:00+00:00" },
        { title: "Apply to X", track: "applications", planned_date: "2026-07-21", completed_at: null, created_at: "2026-07-19T09:00:00+00:00" },
        { title: null, track: "dsa" },
      ],
      diary: [{ body: "A long day.", created_at: "2026-07-22T18:00:00+00:00", updated_at: "2026-07-22T18:30:00+00:00" }],
      thoughts: [{ thought: "I am behind", next_action: "Solve one problem", created_at: "2026-07-23T08:00:00+00:00" }],
      settings: [{ trusted_person_name: "Asha", trusted_person_phone: "+919800000000", theme_mode: "light" }],
    }),
  );
  assert.equal(state.tasks.length, 2);
  assert.equal(state.tasks[0].track, "dsa");
  assert.equal(state.tasks[0].day, "2026-07-20");
  assert.equal(state.tasks[0].doneAt, Date.parse("2026-07-20T10:00:00+00:00"));
  assert.equal(state.tasks[1].track, "apply");
  assert.equal(state.tasks[1].doneAt, null);
  assert.equal(state.journal.length, 2);
  assert.equal(state.journal[1].body, "Reset: I am behind\nNext step: Solve one problem");
  assert.equal(state.settings.trustedName, "Asha");
  assert.equal(state.settings.theme, "light");
});

test("legacy import tolerates missing tables", () => {
  const state = fromLegacy("{}");
  assert.deepEqual(state.tasks, []);
  assert.deepEqual(state.journal, []);
});
