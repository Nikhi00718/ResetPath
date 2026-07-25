# ResetPath Frontend and User Flows

## 1. Navigation model

Use a Flet mobile layout with:

- `SafeArea`,
- bottom navigation,
- centralized route handling,
- Android system-back support,
- scrollable forms,
- and keyboard-safe spacing.

Primary screens:

```text
Home
Reset Now
Today’s Tasks
Thought Journal
My Progress
Get Human Help
Settings
```

“Get Human Help” must remain reachable from Home and every sensitive form.

## 2. Visual design

### Style

Use a calm, non-clinical visual language:

- deep slate for primary text,
- muted teal for primary actions,
- warm off-white backgrounds,
- soft borders,
- limited shadows,
- red only for urgent help or destructive confirmation.

Avoid:

- trophy graphics,
- flame icons,
- competitive badges,
- celebration confetti after large workloads,
- and language that shames incomplete tasks.

### Accessibility

- Use at least 44×44 logical-pixel touch targets.
- Do not communicate meaning by color alone.
- Provide text labels for icons.
- Maintain readable contrast.
- Allow text wrapping.
- Make long screens scroll.
- Provide Pause, Skip, and Stop for timed breathing.

## 3. Onboarding flow

### Screen 1: Welcome

Explain:

- what ResetPath supports,
- what it does not do,
- that information is stored locally,
- and that human help remains important.

### Screen 2: Safety boundaries

Require acknowledgement of:

> ResetPath is not medical treatment, does not diagnose conditions, and cannot
> determine whether someone is safe.

### Screen 3: Support contacts

Optional fields:

- trusted-person name,
- trusted-person phone,
- campus-counsellor name,
- campus-counsellor phone,
- campus-counsellor notes.

The user may skip and configure these later.

## 4. Home screen

Order:

1. ResetPath title and Settings button.
2. Large “I’m spiralling” button.
3. Visible “Get Human Help” action.
4. Today’s incomplete tasks.
5. Today’s completion count.
6. Most recent evidence card.
7. Short non-treatment footer.

Suggested copy:

> The goal is one manageable action, not a perfect day.

## 5. Reset Now flow

Keep reset form state in memory. Do not persist it automatically.

### Step 1: Breathing

- Five cycles.
- Four seconds in.
- Six seconds out.
- No breath hold.
- Animated circle or progress ring.
- Pause, Skip, and Stop remain visible.

Copy:

> Breathe gently. If this feels uncomfortable, stop and return to your normal
> breathing.

### Step 2: Five visible things

Display five small text inputs. Do not require elaborate descriptions.

### Step 3: Frightening thought

Prompt:

> What frightening thought is your mind giving you?

Run crisis interception when Continue is pressed.

### Step 4: Facts and prediction

Fields:

```text
What facts do you know right now?
What is your mind predicting?
```

The app guides rather than declaring which statements are factual.

### Step 5: Ten-minute action

Fields:

- action,
- track.

Actions:

- Finish without saving.
- Add action to Today’s Tasks.
- Go to task list.

## 6. Today’s Tasks

The task screen allows unlimited tasks, as selected for version 1.

### Add form

- title,
- track,
- planned date,
- optional estimated minutes.

### Task card

Show:

- title,
- track label,
- estimated minutes when present,
- completion checkbox,
- edit menu,
- delete action.

### Completion dialog

When completing, optionally ask:

> What makes this action meaningful today?

Save the generated evidence statement. Never require a reflection to complete a
task.

### Empty state

> No tasks are planned for today. A useful task can be very small.

## 7. Thought Journal

Fields:

1. Thought
2. Emotion
3. Evidence supporting the concern
4. Evidence that makes the conclusion less certain
5. One realistic ten-minute action

Emotion options:

- Anxious
- Afraid
- Overwhelmed
- Sad
- Ashamed
- Frustrated
- Uncertain
- Other

Flow:

1. Validate lengths and required fields.
2. Run safety interception across all fields.
3. Build the deterministic response.
4. Show a preview.
5. Let the user edit the form or save.

The application must call this “guided reflection” or “grounded response,” not
AI.

## 8. My Progress

Filters:

- Last 7 days
- Last 30 days
- All time

Components:

- completed-task total,
- estimated minutes,
- bar chart by track,
- daily/weekly line chart,
- recent evidence cards.

Do not show a streak counter or “failed day.”

Empty state:

> Completed actions will appear here as evidence of your effort.

## 9. Get Human Help

At the top:

> ResetPath cannot evaluate whether you are safe. If you may act on thoughts of
> self-harm or cannot remain safe, contact a trusted person, professional
> support, or local emergency service now.

Buttons:

- Call trusted person
- Call campus counsellor
- Call Tele-MANAS
- Open Tele-MANAS website
- Edit support contacts

Verified service:

- [Tele-MANAS 14416](tel:+9114416?oai_link_source=model_response_hotline)
- [Official website](https://telemanas.mohfw.gov.in/home?oai_link_source=model_response_hotline)

If a configured contact is missing, show an explanation and Settings link.

## 10. Settings

Sections:

- Trusted person
- Campus counsellor
- Privacy and storage
- Export my data
- Delete all data
- About and disclaimers
- Sources

Export and deletion must not be placed beside each other without clear labels
and confirmation.

## 11. Loading and error states

- Disable a submit button while its operation is running.
- Prevent duplicate task or journal inserts from repeated taps.
- Keep the user’s non-crisis form text when a recoverable database error occurs.
- Do not keep matched crisis text after redirecting to Human Help.
- Use inline validation near the affected field.
