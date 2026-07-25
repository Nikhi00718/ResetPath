# ResetPath Product and Safety Specification

## 1. Product goal

ResetPath is a personal support application for students experiencing:

- comparison anxiety,
- placement fear,
- difficulty starting placement preparation,
- frightening predictions about their future,
- and a belief that they are making no progress.

The application helps a user slow down, identify what is happening, and select
one action under their control. It also records completed work as evidence
against absolute thoughts such as “I do nothing.”

ResetPath does not promise to cure anxiety or guarantee placement outcomes.

## 2. Intended user

Version 1 is designed for one person using their own phone.

It has:

- no user accounts,
- no cloud sync,
- no social feed,
- no friend list,
- no leaderboard,
- no public profile,
- and no comparison with other students.

A future student pilot would require separate privacy, consent,
authentication, support, and legal work. That is outside version 1.

## 3. Product principles

### Local first

Tasks and journal entries remain in an app-private SQLite database on the
device. The application does not require internet access for ordinary use.

### Action instead of motivation

ResetPath does not generate empty motivational quotes. It helps the user
identify:

- the thought,
- the emotion,
- evidence supporting the concern,
- evidence that makes the conclusion less certain,
- and one realistic ten-minute action.

### Personal progress only

Charts show the user’s completed actions. They do not show:

- rankings,
- peer averages,
- competitive points,
- percentiles,
- or punitive streaks.

### Human support remains visible

“Get Human Help” is always accessible. It is not hidden behind the journal,
onboarding, or progress screens.

## 4. Version 1 features

### Reset Now

The “I’m spiralling” button guides the user through:

1. gentle slow breathing,
2. naming five things they can see,
3. writing the frightening thought,
4. separating facts from predictions,
5. choosing one ten-minute action.

The reset session is not saved automatically. At the end, the user may save
only the selected action as a task.

### Today’s Tasks

The user may create any number of tasks under:

- DSA,
- Core CS,
- Project Development,
- Applications.

There are no penalties for unfinished work. Completed tasks generate evidence
statements.

### Thought Journal

The journal collects:

- thought,
- emotion,
- evidence supporting the concern,
- contrary or balancing evidence,
- next action.

The response is built from a fixed template using only the text supplied by the
user.

### Evidence Journal

Every completed task creates a statement such as:

> I completed “one array problem” today.

The user may add a reflection:

> I completed “one array problem” today. I started even though I felt anxious.

### My Progress

The app displays:

- completed tasks over 7 and 30 days,
- completed work grouped by track,
- estimated minutes completed,
- and recent evidence statements.

### Get Human Help

The screen contains:

- an editable trusted-person contact,
- editable campus-counsellor information,
- Tele-MANAS,
- a non-treatment disclaimer,
- and guidance to seek immediate human help when necessary.

## 5. Grounding source and wording

The experience is inspired by the World Health Organization’s
*Doing What Matters in Times of Stress*, including grounding, noticing and
naming thoughts, unhooking, and taking values-guided action.

ResetPath must:

- paraphrase concepts rather than copy large passages,
- cite the WHO guide,
- state that the project is not endorsed by WHO,
- and avoid presenting the app as a clinically validated adaptation.

Official reference:
[Doing What Matters in Times of Stress](https://www.who.int/publications-detail-redirect/9789240003927).

## 6. Crisis-language interception

### Purpose

The detector is a conservative redirect to human-help information. It is not a
diagnostic model and not a safety assessment.

### Where it runs

Run the detector on every submitted free-text field before:

- saving,
- creating a grounded response,
- completing a reset step,
- or creating a task from journal text.

### Normalization

Before matching:

1. apply Unicode `casefold()`,
2. standardize apostrophes,
3. replace punctuation with spaces,
4. collapse repeated whitespace,
5. strip leading and trailing whitespace.

### Initial phrase families

The rule set covers explicit references to:

- suicide or being suicidal,
- killing oneself,
- ending or taking one’s life,
- hurting or harming oneself,
- self-harm,
- not wanting to live,
- wishing to be dead,
- being better off dead,
- having no reason to live.

The exact phrases belong in one reviewed constant in `logic.py`. They must not
be distributed across UI event handlers.

### Response to a match

When a phrase matches:

1. Do not save the submitted text.
2. Do not generate a grounded response.
3. Clear the pending form state.
4. Navigate to Get Human Help.
5. Explain that the app cannot evaluate safety.
6. Encourage immediate contact with a person or professional service.

The app must not say “you are safe” when no phrase matches. Rule-based detection
has false positives and false negatives.

## 7. Human-help information

The verified India support entry in version 1 is:

- Tele-MANAS: [14416](tel:+9114416?oai_link_source=model_response_hotline)
- Official website:
  [telemanas.mohfw.gov.in](https://telemanas.mohfw.gov.in/home?oai_link_source=model_response_hotline)

Contact buttons open the device dialler. ResetPath does not automatically call,
message, or notify anybody.

Trusted-person and campus-counsellor data are entered by the user. No personal
contact information is hardcoded in the repository.

## 8. Required disclaimers

Show a short disclaimer during onboarding, on Get Human Help, and in Settings:

> ResetPath is a personal support and progress-tracking tool. It is not medical
> treatment, does not diagnose mental-health conditions, and cannot determine
> whether someone is safe. For serious or urgent concerns, contact a trusted
> person, qualified professional, or local emergency service.
