from __future__ import annotations

import argparse
import csv
import json
import sqlite3
from dataclasses import asdict, dataclass
from pathlib import Path
from urllib.parse import urlparse

from ..base import build_tfidf_logreg, save_bundle
from ..metrics import evaluate, group_split, label_counts
from ..paths import ARTIFACTS_DIR, LABELING_DB
from .features import PageVerdictInput, make_text, normalize_space

DEFAULT_DB = LABELING_DB
DEFAULT_OUT = ARTIFACTS_DIR


@dataclass(frozen=True)
class Example:
    id: int
    query: str
    host: str
    title: str
    url: str
    display_url: str
    snippet: str
    rating: int
    label: str
    text: str


def host_from_url(url: str) -> str:
    try:
        return urlparse(url).hostname or ""
    except ValueError:
        return ""


def load_examples(db_path: Path) -> list[Example]:
    with sqlite3.connect(db_path) as con:
        con.row_factory = sqlite3.Row
        rows = con.execute(
            """
            SELECT
                id,
                query,
                title,
                url,
                display_url,
                snippet,
                rating,
                label
            FROM serp_results
            WHERE rating IS NOT NULL
                AND rating != 3
                AND label IN ('negative', 'positive')
            ORDER BY id
            """
        ).fetchall()

    examples: list[Example] = []
    for row in rows:
        examples.append(
            Example(
                id=row["id"],
                query=row["query"],
                host=host_from_url(row["url"]),
                title=normalize_space(row["title"]),
                url=normalize_space(row["url"]),
                display_url=normalize_space(row["display_url"]),
                snippet=normalize_space(row["snippet"]),
                rating=int(row["rating"]),
                label=row["label"],
                text=make_text(
                    PageVerdictInput(
                        title=row["title"],
                        url=row["url"],
                        display_url=row["display_url"],
                        snippet=row["snippet"],
                    )
                ),
            )
        )
    return examples


def build_model():
    return build_tfidf_logreg(
        word_ngram_range=(1, 2),
        char_ngram_range=(3, 5),
        max_iter=2000,
    )


def write_validation_predictions(model, valid: list[Example], output_path: Path) -> None:
    x_valid = [example.text for example in valid]
    y_pred = model.predict(x_valid).tolist()
    positive_index = list(model.classes_).index("positive")
    probabilities = model.predict_proba(x_valid)[:, positive_index]

    with output_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=[
                "id",
                "query",
                "host",
                "rating",
                "label",
                "prediction",
                "positive_probability",
                "title",
                "url",
                "display_url",
                "snippet",
            ],
        )
        writer.writeheader()
        for example, prediction, probability in zip(valid, y_pred, probabilities, strict=True):
            row = asdict(example)
            writer.writerow(
                {
                    "id": row["id"],
                    "query": row["query"],
                    "host": row["host"],
                    "rating": row["rating"],
                    "label": row["label"],
                    "prediction": prediction,
                    "positive_probability": f"{probability:.6f}",
                    "title": row["title"],
                    "url": row["url"],
                    "display_url": row["display_url"],
                    "snippet": row["snippet"],
                }
            )


def main() -> None:
    parser = argparse.ArgumentParser(description="Train the PageVerdict classifier")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--test-size", type=float, default=0.2)
    parser.add_argument("--random-state", type=int, default=13)
    args = parser.parse_args()

    examples = load_examples(args.db)
    if len(examples) < 100:
        raise SystemExit(f"Need at least 100 labeled examples, got {len(examples)}")

    labels = [example.label for example in examples]
    groups = [example.host or f"id:{example.id}" for example in examples]
    train_idx, valid_idx, split_method = group_split(
        labels, groups, test_size=args.test_size, random_state=args.random_state
    )
    train = [examples[i] for i in train_idx]
    valid = [examples[i] for i in valid_idx]

    model = build_model()
    model.fit([example.text for example in train], [example.label for example in train])
    metrics = evaluate(
        model, [example.text for example in valid], [example.label for example in valid]
    )

    args.out.mkdir(parents=True, exist_ok=True)
    model_path = args.out / "page_verdict.joblib"
    metrics_path = args.out / "page_metrics.json"
    predictions_path = args.out / "page_validation_predictions.csv"

    final_model = build_model()
    final_model.fit(
        [example.text for example in examples],
        [example.label for example in examples],
    )

    save_bundle(
        model_path,
        {
            "model": final_model,
            "feature_fields": ["title", "url", "display_url", "snippet"],
            "labels": ["negative", "positive"],
            "ignored_rating": 3,
            "training_examples": len(examples),
        },
    )
    write_validation_predictions(model, valid, predictions_path)

    report = {
        "db": str(args.db),
        "examples": len(examples),
        "train_examples": len(train),
        "validation_examples": len(valid),
        "split_method": split_method,
        "label_counts": label_counts(labels),
        "train_label_counts": label_counts([example.label for example in train]),
        "validation_label_counts": label_counts([example.label for example in valid]),
        "unique_hosts": len({example.host for example in examples}),
        "metrics": metrics,
        "final_model_training_examples": len(examples),
        "model_path": str(model_path),
        "validation_predictions_path": str(predictions_path),
    }
    metrics_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
