# Local emotion router

ResetPath includes a compact offline linear classifier at
`assets/emotion_router.json`. It was trained only on the public
[`dair-ai/emotion`](https://huggingface.co/datasets/dair-ai/emotion) dataset;
it has never accessed a ResetPath diary, task, mood check-in, or health record.

## What it does

- identifies a broad communication-tone label: sadness, joy, love, anger,
  fear, or surprise;
- displays the label only as an optional private hint in the guided reflection;
- allows the person to select their own emotion instead;
- abstains when confidence is low or explicit crisis language appears.

## What it does not do

- diagnose anxiety, depression, trauma, or any other condition;
- calculate safety, stress, or recovery;
- replace the crisis-language redirect or human support;
- train on, upload, or silently profile diary pages.

## RAG and diary memory

If the person explicitly checks **Use relevant private diary pages for this one
response**, ResetPath uses local keyword retrieval to select up to three short
matching excerpts. It displays those excerpts as context and does not call a
remote service. The retrieval is temporary: it is not a hidden permanent
profile and it is not model training.

## Reproduce training

The training-only dependencies are `datasets` and `scikit-learn`; they are not
needed by the app at runtime. Run:

```powershell
.\.venv\Scripts\python.exe tools\train_emotion_router.py
```

The script refreshes the local model artifact and writes held-out validation
metrics to `docs/emotion-router-evaluation.json`. Review those results before
shipping a replacement model.
