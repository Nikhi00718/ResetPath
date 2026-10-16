// Pure helpers with no DOM, audio, or storage access, so they run under
// `node --test` as well as in the app.

export const TRACKS = {
  dsa: "DSA",
  core: "Core CS",
  project: "Project",
  apply: "Applications",
  life: "Personal",
};

export const MOODS = [
  { value: 1, face: "😞", label: "Low" },
  { value: 2, face: "😕", label: "Meh" },
  { value: 3, face: "😐", label: "Okay" },
  { value: 4, face: "🙂", label: "Good" },
  { value: 5, face: "😄", label: "Great" },
];

const CRISIS_PATTERNS = [
  /\bsuicide\b/,
  /\bsuicidal\b/,
  /\bkill myself\b/,
  /\bkilling myself\b/,
  /\bend my life\b/,
  /\bending my life\b/,
  /\btake my life\b/,
  /\btaking my life\b/,
  /\bhurt myself\b/,
  /\bhurting myself\b/,
  /\bharm myself\b/,
  /\bharming myself\b/,
  /\bself harm\b/,
  /\bdon t want to live\b/,
  /\bdo not want to live\b/,
  /\bno longer want to live\b/,
  /\bwish i (?:was|were) dead\b/,
  /\bwish to be dead\b/,
  /\bbetter off dead\b/,
  /\bno reason to live\b/,
];

export function normalizeText(value) {
  return String(value ?? "")
    .normalize("NFKC")
    .toLowerCase()
    .replace(/[’`]/g, "'")
    .replace(/[^a-z0-9\s']/g, " ")
    .replace(/'/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

export function containsCrisisLanguage(text) {
  const normalized = normalizeText(text);
  return CRISIS_PATTERNS.some((pattern) => pattern.test(normalized));
}

const SUPPORT_LIBRARY = [
  {
    id: "comparison",
    title: "Comparison and feeling behind",
    keywords: ["everyone", "roommate", "friend", "friends", "comparison", "behind", "ahead", "others"],
    reframe: "Other people's visible progress does not prove your final outcome or measure the value of your path.",
    actions: [
      "Step away from the comparison trigger for ten minutes",
      "Write one action that belongs only to your path",
      "Look back at one thing you finished this week",
    ],
  },
  {
    id: "placement",
    title: "Placement uncertainty",
    keywords: ["placement", "placements", "job", "interview", "internship", "offer", "resume", "application", "rejected"],
    reframe: "This is a fear about an uncertain result, not confirmation of what will happen.",
    actions: [
      "Open one role and note a single requirement",
      "Practise one interview answer aloud for five minutes",
      "Improve one line of your resume",
    ],
  },
  {
    id: "study",
    title: "Study pressure",
    keywords: ["exam", "exams", "study", "dsa", "dbms", "revision", "subject", "learn", "gate", "syllabus"],
    reframe: "Feeling behind is not the same as being unable to learn the next small part.",
    actions: [
      "Pick one topic and focus on it for 25 minutes",
      "Write three facts you already remember",
      "Write down one specific doubt to ask someone",
    ],
  },
  {
    id: "project",
    title: "Project friction",
    keywords: ["project", "code", "bug", "function", "app", "build", "error", "deploy"],
    reframe: "A hard project moment describes the current obstacle, not your ability to finish the project.",
    actions: [
      "Name the smallest blocked piece",
      "Write or test one small function",
      "Leave a note describing the next technical step",
    ],
  },
  {
    id: "tired",
    title: "Low energy",
    keywords: ["tired", "sleep", "exhausted", "sleepy", "drained", "burnt", "burnout"],
    reframe: "Low energy is information about what you need, not a verdict on your effort.",
    actions: [
      "Drink a glass of water and stretch for two minutes",
      "Do one 10 minute task, then rest without guilt",
      "Play brown noise and lie down for 20 minutes",
    ],
  },
  {
    id: "general",
    title: "A difficult moment",
    keywords: [],
    reframe: "The feeling is real. The conclusion in the thought is not automatically a confirmed fact.",
    actions: [
      "Put both feet down and take three slow breaths",
      "Choose the smallest useful action you can do in ten minutes",
      "Tell one trusted person that this is a hard moment",
    ],
  },
];

export function supportFor(thought) {
  const words = new Set(normalizeText(thought).split(" "));
  let best = SUPPORT_LIBRARY[SUPPORT_LIBRARY.length - 1];
  let bestScore = 0;
  for (const entry of SUPPORT_LIBRARY) {
    const score = entry.keywords.filter((keyword) => words.has(keyword)).length;
    if (score > bestScore) {
      best = entry;
      bestScore = score;
    }
  }
  return best;
}

export function dateKey(date = new Date()) {
  const y = date.getFullYear();
  const m = String(date.getMonth() + 1).padStart(2, "0");
  const d = String(date.getDate()).padStart(2, "0");
  return `${y}-${m}-${d}`;
}

export function addDays(key, amount) {
  const [y, m, d] = key.split("-").map(Number);
  return dateKey(new Date(y, m - 1, d + amount));
}

export function lastDays(count, today = dateKey()) {
  const days = [];
  for (let i = count - 1; i >= 0; i -= 1) days.push(addDays(today, -i));
  return days;
}

export function weekdayShort(key) {
  const [y, m, d] = key.split("-").map(Number);
  return new Date(y, m - 1, d).toLocaleDateString(undefined, { weekday: "short" }).slice(0, 2);
}

export function formatClock(totalSeconds) {
  const seconds = Math.max(0, Math.round(totalSeconds));
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
}

export function formatMinutes(minutes) {
  const value = Math.round(minutes);
  if (value < 60) return `${value}m`;
  const h = Math.floor(value / 60);
  const m = value % 60;
  return m ? `${h}h ${m}m` : `${h}h`;
}

export function greeting(hour = new Date().getHours()) {
  if (hour < 5) return "Still up";
  if (hour < 12) return "Good morning";
  if (hour < 17) return "Good afternoon";
  if (hour < 22) return "Good evening";
  return "Winding down";
}

export function focusMinutesByDay(sessions, days) {
  const totals = Object.fromEntries(days.map((day) => [day, 0]));
  for (const session of sessions) {
    if (session.day in totals) totals[session.day] += session.minutes;
  }
  return days.map((day) => ({ day, minutes: totals[day] }));
}

export function habitCount(habitLog, day, habitId) {
  return habitLog?.[day]?.[habitId] ?? 0;
}

// Share of the day's habit targets that were met, 0..1.
export function habitScore(habits, habitLog, day) {
  if (!habits.length) return 0;
  const total = habits.reduce(
    (sum, habit) => sum + Math.min(1, habitCount(habitLog, day, habit.id) / habit.target),
    0,
  );
  return total / habits.length;
}

// Days in the window that had any focus, task, or habit activity. Shown as
// a gentle count, never as a streak that can be lost.
export function activeDays(state, days) {
  const set = new Set();
  for (const session of state.focus) set.add(session.day);
  for (const task of state.tasks) if (task.doneAt) set.add(dateKey(new Date(task.doneAt)));
  for (const [day, counts] of Object.entries(state.habitLog)) {
    if (Object.values(counts).some((count) => count > 0)) set.add(day);
  }
  return days.filter((day) => set.has(day)).length;
}

export function escapeHtml(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

export function isValidPhone(value) {
  const digits = String(value).replace(/[\s()-]/g, "");
  return digits === "" || /^\+?\d{6,15}$/.test(digits);
}
