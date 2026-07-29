# ResetPath release notes

This changelog records user-visible improvements and important boundaries for
each published version. Download builds from the [GitHub Releases page](https://github.com/Nikhi00718/ResetPath/releases).

## 0.2.0 — Local context and privacy release

### Added

- free-form private diary pages with edit, export, and delete-all coverage;
- optional local diary retrieval for a single guided reflection;
- compact offline emotion router trained only on the public `dair-ai/emotion`
  dataset, with a user-controlled emotion choice and confidence abstention;
- stored light/dark appearance preference and route-aware back navigation;
- held-out model evaluation report and safety-focused test coverage.

### Improved

- pressing Android back returns to the previous ResetPath screen before exit;
- the old boxed journal experience was replaced by a normal freeform diary;
- the GitHub release now has separate ARM64, ARMv7, and x86_64 downloads.

### Safety boundaries

- diary pages are not used for model training;
- the router is not a mental-health or safety assessment model;
- diary retrieval is opt-in, local, temporary, and limited to three excerpts;
- Samsung Health direct sync remains out of scope for this version.

## 0.1.0 — First private Android release

### Added

- fluid warm interface with original calm-path and stepping-stone artwork;
- animated five-step reset and visual meditation;
- one-question-at-a-time conversational thought journal;
- reviewed local retrieval from `assets/support_library.json`;
- animated task evidence and progress charts;
- soft haptic feedback on supported devices;
- keyboard voice-typing flow with no ResetPath audio storage;
- local wearable CSV/JSON import and template download;
- optional mood and energy check-ins;
- SQLite schema v2 migration and expanded private export;
- privacy notes, device-feature documentation, tests, and Android packaging.
- split-per-ABI packaging and a smaller ARM64 phone download.

### Safety boundaries

- no diagnosis, treatment claims, safety classification, or generated crisis
  response;
- no unrestricted autonomous mental-health agent;
- no inferred wearable stress score;
- direct Health Connect permissions are not requested in this release.
