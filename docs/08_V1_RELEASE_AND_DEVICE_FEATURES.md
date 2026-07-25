# ResetPath v0.1 Release and Device Features

This document records what the first downloadable release implements, what it
does not claim, and the exact path for later on-device AI and Health Connect
work.

## 1. Release architecture

ResetPath v0.1 is one Flet application packaged as an Android APK.

```text
User action
    |
    v
Flet screen and animation
    |
    +--> deterministic crisis-language gate --> human support screen
    |
    +--> reviewed local retrieval -----------> bounded suggestions
    |
    +--> SQLite ------------------------------> private local history
    |
    +--> Pandas / Flet Charts ----------------> personal trends
    |
    +--> Android services --------------------> haptics, files, links
```

There is no remote backend in this release. `database.py` is the persistence
backend and SQLite is the database.

## 2. Local retrieval instead of an unrestricted chatbot

The support library in `assets/support_library.json` contains reviewed cards
for comparison, placement uncertainty, study pressure, project friction, and a
general difficult moment.

The retrieval process is:

1. normalize the user's words;
2. run the explicit crisis-language redirect first;
3. count transparent keyword overlap with reviewed cards;
4. retrieve the best card;
5. insert the user's thought and emotion into a fixed response structure;
6. show three optional, low-risk actions.

This is a small retrieval-augmented system, but not a generative language
model. It does not diagnose, promise an outcome, or invent evidence.

## 3. Safe future on-device model

A later model can help summarize long reflections or make wording more natural,
but it must sit behind the existing safety gate and structured output schema.

Required output fields:

- acknowledged thought;
- selected or user-provided emotion;
- evidence supplied by the user;
- evidence that makes an absolute prediction less certain;
- one to three low-risk actions;
- retrieved support-card identifiers.

The model must not:

- diagnose a condition;
- decide whether a person is safe;
- replace the deterministic self-harm redirect;
- contact people, change tasks, or start interventions without confirmation;
- train on private entries by default;
- present wearable readings as proof of stress or recovery.

Large local models significantly increase APK size and memory use. They should
be an optional, checksum-verified download rather than silently bundled into
the base APK.

## 4. Voice input

Implemented in v0.1:

- standard text fields work with phone-keyboard voice typing;
- ResetPath stores only the resulting text;
- ResetPath does not start a recording or save audio;
- the interface tells users that keyboard-provider privacy settings apply.

Future fully local transcription:

1. add a mobile-compatible recorder;
2. request microphone permission only after a user taps the microphone;
3. run a small on-device speech model;
4. display an editable transcript;
5. delete temporary audio after confirmation;
6. provide a visible model size, checksum, language list, and delete option.

## 5. Haptic feedback

Flet's haptic service is used for:

- light impact on normal buttons;
- selection feedback for navigation, emotions, and suggested actions.

Unsupported desktops and browsers fail silently; haptics are an enhancement,
not a requirement for completing a flow.

## 6. Wearable context

Implemented in v0.1:

- local CSV or JSON import;
- strict 5 MB and 370-row limits;
- validation for date, sleep hours, resting heart rate, HRV, and steps;
- local SQLite storage;
- recent-context metrics and a sleep chart;
- optional mood and energy check-ins;
- export and delete-all coverage.

Use the in-app template headers:

```csv
date,sleep_hours,resting_heart_rate,hrv_ms,steps,source
2026-07-25,7.5,68,42,6200,My watch export
```

The chart is descriptive. ResetPath does not calculate a medical or
psychological interpretation.

## 7. Direct Health Connect roadmap

Direct sync is intentionally not represented as working in v0.1. Flet needs a
native Android extension around the Health Connect SDK.

The connector design is:

1. raise Android minimum support for the connector to API 28;
2. add the Health Connect client dependency;
3. create a native Flet extension with availability and permission methods;
4. add an in-app privacy-rationale activity;
5. request read access only for the fields the user enables;
6. aggregate steps to avoid double counting;
7. store source and recording metadata;
8. support disconnect, permission revocation, local deletion, and re-import;
9. test Android 9–13 with the Health Connect app and Android 14+ framework
   integration;
10. complete Google Play health-data declarations before store distribution.

Initial read-only records:

- sleep session duration;
- resting heart rate;
- heart-rate variability (RMSSD);
- steps.

No background sync is needed for the first connector. A user-initiated refresh
keeps the permission and data behavior easier to understand.

## 8. Release checklist

- run all unit tests;
- compile every Python module;
- inspect home, journal, evidence, help, and meditation on laptop;
- build a fresh APK from the exact release source;
- calculate SHA-256;
- install on a physical Android phone;
- test offline launch and SQLite persistence;
- test haptics and phone-keyboard dictation;
- test CSV import, export, delete-all, dialler links, and small screens;
- attach the APK and checksum to the GitHub release.
