import sys
import unittest
from pathlib import Path


PYTHON_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PYTHON_DIR))

from tools.analyze_indoor_emotion_log import analyze_records, parse_log_lines


class IndoorEmotionLogAnalysisTest(unittest.TestCase):
    def test_parser_reads_prediction_lines(self):
        records = parse_log_lines([
            "屋内感情推定: track_id=1 emotion_index=3 emotion=neutral "
            "prediction=[0.0505, 0.2305, 0.1960, 0.5230] "
            "sequence_length=31 feature_min=-0.7500 feature_max=1.2500 "
            "feature_mean=0.0312\n",
            "unrelated line\n",
        ])

        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["track_id"], 1)
        self.assertEqual(records[0]["emotion"], "neutral")
        self.assertAlmostEqual(records[0]["confidence"], 0.523)
        self.assertEqual(records[0]["sequence_length"], 31)
        self.assertAlmostEqual(records[0]["feature_min"], -0.75)
        self.assertAlmostEqual(records[0]["feature_max"], 1.25)
        self.assertAlmostEqual(records[0]["feature_mean"], 0.0312)

    def test_analysis_reports_high_happy_predictions(self):
        records = parse_log_lines([
            "屋内感情推定: track_id=1 emotion_index=0 emotion=happy "
            "prediction=[0.9855, 0.0031, 0.0068, 0.0046] "
            "sequence_length=31 feature_min=-0.7500 feature_max=1.2500 "
            "feature_mean=0.0312\n",
            "屋内感情推定: track_id=1 emotion_index=3 emotion=neutral "
            "prediction=[0.0505, 0.2305, 0.1960, 0.5230] "
            "sequence_length=31 feature_min=-0.5000 feature_max=1.0000 "
            "feature_mean=0.0200\n",
        ])

        summary = analyze_records(records, high_happy_threshold=0.98)

        self.assertEqual(summary["record_count"], 2)
        self.assertEqual(summary["emotion_counts"], {"happy": 1, "neutral": 1})
        self.assertEqual(summary["high_happy_count"], 1)
        self.assertEqual(summary["first_happy_record"], 0)
        self.assertEqual(summary["sequence_length_min"], 31)
        self.assertEqual(summary["sequence_length_max"], 31)
        self.assertAlmostEqual(summary["feature_min_min"], -0.75)
        self.assertAlmostEqual(summary["feature_max_max"], 1.25)


if __name__ == "__main__":
    unittest.main()
