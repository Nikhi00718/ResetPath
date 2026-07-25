# ResetPath local AI, RAG, voice and meditation plan

## What is implemented now

The current application includes:

- a one-question-at-a-time thought-unpacking flow;
- deterministic, topic-aware next-step suggestions;
- immediate crisis-language redirection before reflection content is saved;
- a two, five or ten-minute visual meditation timer;
- animated screen entry, breathing and meditation motion;
- phone-keyboard voice typing without ResetPath recording audio;
- retrieval from the reviewed local `assets/support_library.json` library;
- a visible source label on each retrieved support plan.

The journal remains deterministic after retrieval. This is intentional: the
reviewed local system can be tested before an optional model is allowed to
generate sensitive text.

## Can ResetPath use RAG and agentic AI?

Yes, but the model should be a bounded support component, not a therapist,
diagnostician or safety decision-maker.

RAG is useful because it can restrict suggestions to a small, reviewed library
instead of relying only on a model's training data. A limited agent can also
offer actions inside ResetPath, but its tools should be deliberately narrow.

Safe tools:

- show a grounding exercise;
- propose one of the reviewed ten-minute actions;
- open the meditation screen;
- prepare a task for the user to confirm;
- show the human-support screen.

Unsafe tools:

- diagnosing a condition;
- declaring that a person is safe;
- deciding whether emergency help is required;
- contacting someone without a separate user confirmation;
- changing medication or treatment;
- browsing the open web for mental-health advice;
- creating unrestricted multi-step plans.

## Recommended architecture

```text
Voice or typed input
        |
        v
Deterministic crisis phrase interception
        |
        +---- explicit crisis language ----> Human support screen
        |
        v
User confirms transcript
        |
        v
Local retrieval from reviewed support library
        |
        v
On-device small language model
        |
        v
Strict JSON response validator
        |
        +---- invalid or unsafe ----> Rule-based fallback
        |
        v
User chooses an action
        |
        v
Optional task save after confirmation
```

The crisis interception must run before retrieval or generation. A second
deterministic output filter should run after generation. A negative phrase
match must never be interpreted as proof that someone is safe.

## Local model recommendation

Start by benchmarking a small general instruction model rather than a model
marketed as a “mental-health model.” Specialised labels do not guarantee
clinical accuracy and can encourage users to treat generated text as medical
judgement.

Practical candidates:

1. **Gemma 3 1B with LiteRT-LM**
   - approximately 557 MB in the current official LiteRT-LM model table;
   - more realistic for mid-range Android devices;
   - text-only, which allows a separate smaller speech recogniser.
2. **Gemma 3n E2B**
   - accepts text and audio;
   - approximately 2.9 GB in the official LiteRT-LM model table;
   - should be an optional Wi-Fi model download, not embedded in the APK.

LiteRT-LM currently provides Kotlin support for Android and community Flutter
support. ResetPath would therefore need a small custom Flet/Flutter extension
that exposes model loading and generation to Python.

Official references:

- [LiteRT-LM](https://github.com/google-ai-edge/LiteRT-LM)
- [Gemma mobile deployment](https://ai.google.dev/gemma/docs/integrations/mobile)
- [Gemma 3n overview](https://ai.google.dev/gemma/docs/gemma-3n)

## RAG knowledge library

Keep the first corpus small and reviewable:

- selected exercises from WHO's *Doing What Matters in Times of Stress* where
  licensing permits inclusion;
- ResetPath-authored grounding and placement-planning actions;
- official campus counselling information configured by the institution;
- official Tele-MANAS contact information;
- a clear statement of what the app cannot do.

Every chunk should store:

- source title;
- source URL;
- review date;
- reviewer;
- language;
- allowed use;
- action category;
- risk level.

The app should display the source behind a suggestion when retrieval is used.
Do not retrieve from the open internet at response time.

## Voice-to-text implementation

Flet's official `flet-audio-recorder` extension supports Windows, Android, iOS
and web recording. Android requires microphone permission. Recording alone is
not transcription, so ResetPath still needs an on-device speech engine.

Recommended flow:

1. Request microphone permission only after the user presses the microphone.
2. Record mono PCM audio locally.
3. Transcribe with an on-device speech model through a custom Flutter
   extension.
4. Put the transcript into the journal editor.
5. Require the user to confirm or correct it.
6. Delete the temporary audio immediately after confirmation.
7. Run crisis-language interception on the confirmed transcript.

Possible speech engines:

- Gemma 3n audio input through LiteRT-LM on capable phones;
- `whisper.cpp` with a small multilingual model for broader device support.

Official references:

- [Flet AudioRecorder](https://flet.dev/docs/services/audiorecorder/)
- [whisper.cpp Android example](https://github.com/ggml-org/whisper.cpp/tree/master/examples/whisper.android)

## Strict model output

The model should return data shaped like this:

```json
{
  "acknowledgement": "One sentence that reflects the user's words.",
  "grounded_reframe": "One sentence separating feeling from prediction.",
  "suggested_actions": [
    {
      "label": "A concrete action",
      "minutes": 10,
      "source_id": "reviewed-source-id"
    }
  ],
  "support_reminder": "Optional human-support reminder.",
  "diagnosis": null,
  "safety_assessment": null
}
```

Reject output when it:

- includes a diagnosis or safety assessment;
- guarantees an outcome;
- invents a fact about the user;
- recommends treatment or medication;
- contains an action outside the approved tool list;
- lacks a reviewed source for a retrieved recommendation.

## Bounded agent behaviour

The model may recommend a tool call, but ResetPath executes nothing until the
user confirms it.

Example:

```text
Model suggestion: add “Review one DBMS topic for 10 minutes”
User sees:        Add this to today's tasks?
User confirms:    SQLite task is created
```

This is safer than an autonomous agent and easier to test.

## Delivery phases

### Phase 1 — completed in the current prototype

- conversational journal;
- rule-based contextual suggestions;
- meditation screen;
- deterministic safety redirect;
- voice entry point and privacy copy.

### Phase 2 — voice prototype

- add `flet-audio-recorder`;
- build the Android speech extension;
- add microphone permissions;
- transcribe locally;
- confirm transcript and delete audio;
- test English, Hindi and mixed-language speech.

### Phase 3 — offline RAG prototype

- create and review the source library;
- build embeddings during development;
- ship the small index with the app;
- retrieve a maximum of three short passages;
- display source attribution;
- retain the rule-based fallback.

### Phase 4 — optional model pack

- benchmark Gemma 3 1B and Gemma 3n E2B on target phones;
- download the selected quantised model after explicit consent;
- verify storage and memory before loading;
- provide a “Remove model pack” setting;
- never place a multi-gigabyte model directly inside the base APK.

### Phase 5 — safety evaluation

- clinician review of every retrieved action;
- crisis-language test suite with paraphrases and mixed languages;
- hallucination and invented-fact tests;
- adversarial prompt tests;
- accessibility and transcript-correction tests;
- low-memory and offline-device tests;
- documented human escalation behaviour.
