import assert from "node:assert/strict";
import { test } from "node:test";

import {
  activeDays,
  addDays,
  containsCrisisLanguage,
  escapeHtml,
  focusMinutesByDay,
  formatClock,
  formatMinutes,
  habitScore,
  isValidPhone,
  lastDays,
  supportFor,
} from "../web/js/logic.js";

test("crisis language is detected through punctuation and case", () => {
  assert.ok(containsCrisisLanguage("I don't want to live anymore"));
  assert.ok(containsCrisisLanguage("thinking about SELF-HARM"));
  assert.ok(containsCrisisLanguage("I wish I were dead"));
});

test("ordinary stress is not treated as crisis language", () => {
  assert.ok(!containsCrisisLanguage("This exam is killing me"));
  assert.ok(!containsCrisisLanguage("I feel behind everyone in placements"));
  assert.ok(!containsCrisisLanguage(""));
});

test("support matches the strongest topic and falls back to general", () => {
  assert.equal(supportFor("everyone got an internship offer before me").id, "placement");
  assert.equal(supportFor("my friends are ahead and I am behind").id, "comparison");
  assert.equal(supportFor("so tired and drained").id, "tired");
  assert.equal(supportFor("something unrelated").id, "general");
});

test("date helpers cross month and year boundaries", () => {
  assert.equal(addDays("2026-12-31", 1), "2027-01-01");
  assert.equal(addDays("2026-03-01", -1), "2026-02-28");
  assert.deepEqual(lastDays(3, "2026-10-01"), ["2026-09-29", "2026-09-30", "2026-10-01"]);
});

test("formatters", () => {
  assert.equal(formatClock(1500), "25:00");
  assert.equal(formatClock(-3), "00:00");
  assert.equal(formatClock(59.6), "01:00");
  assert.equal(formatMinutes(45), "45m");
  assert.equal(formatMinutes(120), "2h");
  assert.equal(formatMinutes(95), "1h 35m");
});

test("focus minutes are summed per day and ignore days outside the window", () => {
  const sessions = [
    { day: "2026-10-15", minutes: 25 },
    { day: "2026-10-15", minutes: 50 },
    { day: "2026-10-01", minutes: 25 },
  ];
  assert.deepEqual(focusMinutesByDay(sessions, ["2026-10-15", "2026-10-16"]), [
    { day: "2026-10-15", minutes: 75 },
    { day: "2026-10-16", minutes: 0 },
  ]);
});

test("habit score caps each habit at its target", () => {
  const habits = [
    { id: "water", target: 8 },
    { id: "move", target: 1 },
  ];
  const log = { "2026-10-16": { water: 4, move: 3 } };
  assert.equal(habitScore(habits, log, "2026-10-16"), 0.75);
  assert.equal(habitScore(habits, log, "2026-10-15"), 0);
  assert.equal(habitScore([], log, "2026-10-16"), 0);
});

test("active days count any focus, task, or habit activity", () => {
  const state = {
    focus: [{ day: "2026-10-14", minutes: 25 }],
    tasks: [{ doneAt: new Date(2026, 9, 15, 12).getTime() }],
    habitLog: { "2026-10-16": { water: 1 }, "2026-10-13": { water: 0 } },
  };
  assert.equal(activeDays(state, lastDays(4, "2026-10-16")), 3);
});

test("html escaping covers attribute and tag characters", () => {
  assert.equal(escapeHtml(`<img src=x onerror="a('b')">&`), "&lt;img src=x onerror=&quot;a(&#39;b&#39;)&quot;&gt;&amp;");
});

test("phone validation", () => {
  assert.ok(isValidPhone("+91 98765 43210"));
  assert.ok(isValidPhone(""));
  assert.ok(!isValidPhone("call me"));
  assert.ok(!isValidPhone("12"));
});
