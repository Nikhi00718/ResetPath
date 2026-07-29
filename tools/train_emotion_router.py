"""Train ResetPath's small, non-clinical emotion router.

This is deliberately *not* a mental-health model. It learns six ordinary
communication labels from the public dair-ai/emotion dataset, then exports a
small linear classifier for local, offline routing to reviewed support cards.
Diary pages are never loaded by this script.
"""

from __future__ import annotations

import json
from pathlib import Path

from datasets import load_dataset
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, f1_score


ROOT = Path(__file__).resolve().parent.parent
ARTIFACT = ROOT / "assets" / "emotion_router.json"
REPORT = ROOT / "docs" / "emotion-router-evaluation.json"
LABELS = ("sadness", "joy", "love", "anger", "fear", "surprise")


def main() -> None:
    dataset = load_dataset("dair-ai/emotion", "split")
    train = dataset["train"]
    validation = dataset["validation"]

    vectorizer = TfidfVectorizer(
        lowercase=True,
        strip_accents="unicode",
        ngram_range=(1, 2),
        min_df=2,
        max_features=5_000,
        sublinear_tf=True,
    )
    train_features = vectorizer.fit_transform(train["text"])
    classifier = LogisticRegression(
        max_iter=500,
        C=4.0,
        class_weight="balanced",
        random_state=42,
    )
    classifier.fit(train_features, train["label"])
    prediction = classifier.predict(vectorizer.transform(validation["text"]))
    report = classification_report(
        validation["label"], prediction, target_names=LABELS, output_dict=True
    )
    macro_f1 = f1_score(validation["label"], prediction, average="macro")

    vocabulary = {term: int(index) for term, index in vectorizer.vocabulary_.items()}
    idf = vectorizer.idf_
    artifact = {
        "format": "resetpath-emotion-router-v1",
        "purpose": "non-clinical emotion routing for local support-card retrieval",
        "dataset": "dair-ai/emotion",
        "labels": list(LABELS),
        "vocabulary": vocabulary,
        "idf": [round(float(value), 8) for value in idf],
        "coefficients": [
            [round(float(value), 8) for value in row] for row in classifier.coef_
        ],
        "intercepts": [round(float(value), 8) for value in classifier.intercept_],
        "minimum_confidence": 0.45,
    }
    ARTIFACT.write_text(json.dumps(artifact, separators=(",", ":")), encoding="utf-8")
    REPORT.write_text(
        json.dumps(
            {
                "dataset": "dair-ai/emotion",
                "split": "validation",
                "macro_f1": round(float(macro_f1), 4),
                "samples": len(validation),
                "classification_report": report,
                "safety_note": (
                    "This metric measures public emotion-label classification only. "
                    "It does not measure mental-health assessment, clinical safety, "
                    "or suitability for crisis support."
                ),
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"Saved {ARTIFACT.name}; validation macro F1: {macro_f1:.3f}")


if __name__ == "__main__":
    main()
