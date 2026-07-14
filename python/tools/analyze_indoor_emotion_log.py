import argparse
import json
import re
from collections import Counter
from pathlib import Path


PREDICTION_PATTERN = re.compile(
    r"track_id=(?P<track_id>\d+)\s+"
    r"emotion_index=(?P<emotion_index>\d+)\s+"
    r"emotion=(?P<emotion>\w+)\s+"
    r"prediction=\[(?P<prediction>[^]]+)\]"
    r"(?:\s+sequence_length=(?P<sequence_length>\d+)"
    r"\s+feature_min=(?P<feature_min>-?\d+(?:\.\d+)?)"
    r"\s+feature_max=(?P<feature_max>-?\d+(?:\.\d+)?)"
    r"\s+feature_mean=(?P<feature_mean>-?\d+(?:\.\d+)?))?"
)


def parse_log_lines(lines):
    records = []
    for line_number, line in enumerate(lines, start=1):
        match = PREDICTION_PATTERN.search(line)
        if not match:
            continue

        prediction = [
            float(value.strip())
            for value in match.group("prediction").split(",")
        ]
        emotion_index = int(match.group("emotion_index"))
        if not 0 <= emotion_index < len(prediction):
            continue
        record = {
                "line_number": line_number,
                "track_id": int(match.group("track_id")),
                "emotion_index": emotion_index,
                "emotion": match.group("emotion"),
                "prediction": prediction,
                "confidence": prediction[emotion_index],
            }
        if match.group("sequence_length") is not None:
            record.update(
                {
                    "sequence_length": int(match.group("sequence_length")),
                    "feature_min": float(match.group("feature_min")),
                    "feature_max": float(match.group("feature_max")),
                    "feature_mean": float(match.group("feature_mean")),
                }
            )
        records.append(record)
    return records


def analyze_records(records, high_happy_threshold=0.98):
    emotion_counts = dict(
        sorted(Counter(record["emotion"] for record in records).items())
    )
    high_happy_records = [
        record
        for record in records
        if record["emotion"] == "happy"
        and record["confidence"] >= high_happy_threshold
    ]
    happy_records = [
        index
        for index, record in enumerate(records)
        if record["emotion"] == "happy"
    ]
    debug_records = [record for record in records if "sequence_length" in record]

    return {
        "record_count": len(records),
        "track_ids": sorted({record["track_id"] for record in records}),
        "emotion_counts": emotion_counts,
        "high_happy_threshold": high_happy_threshold,
        "high_happy_count": len(high_happy_records),
        "high_happy_ratio": (
            len(high_happy_records) / len(records) if records else 0.0
        ),
        "first_happy_record": happy_records[0] if happy_records else None,
        "confidence_mean": (
            sum(record["confidence"] for record in records) / len(records)
            if records
            else 0.0
        ),
        "confidence_max": max(
            (record["confidence"] for record in records), default=0.0
        ),
        "sequence_length_min": min(
            (record["sequence_length"] for record in debug_records),
            default=None,
        ),
        "sequence_length_max": max(
            (record["sequence_length"] for record in debug_records),
            default=None,
        ),
        "feature_min_min": min(
            (record["feature_min"] for record in debug_records), default=None
        ),
        "feature_max_max": max(
            (record["feature_max"] for record in debug_records), default=None
        ),
        "feature_mean_min": min(
            (record["feature_mean"] for record in debug_records), default=None
        ),
        "feature_mean_max": max(
            (record["feature_mean"] for record in debug_records), default=None
        ),
    }


def main():
    parser = argparse.ArgumentParser(
        description="Analyze indoor emotion prediction logs emitted by the tracker."
    )
    parser.add_argument("log_path", type=Path)
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.98,
        help="Threshold for suspicious high-confidence happy predictions (default: 0.98).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Write the JSON summary to this path in addition to stdout.",
    )
    args = parser.parse_args()

    records = parse_log_lines(
        args.log_path.read_text(encoding="utf-8").splitlines()
    )
    summary = analyze_records(records, high_happy_threshold=args.threshold)
    rendered = json.dumps(summary, ensure_ascii=False, indent=2) + "\n"
    print(rendered, end="")
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")


if __name__ == "__main__":
    main()
