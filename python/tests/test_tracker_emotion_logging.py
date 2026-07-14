import sys
import unittest
from pathlib import Path


PYTHON_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PYTHON_DIR))

from tracker.emotion import (
    format_indoor_emotion_prediction_log,
    should_log_indoor_emotion_prediction,
)


class TrackerEmotionLoggingTest(unittest.TestCase):
    def test_first_prediction_for_track_is_logged(self):
        self.assertTrue(
            should_log_indoor_emotion_prediction(
                track_id=1,
                now_seconds=10.0,
                interval_seconds=3.0,
                last_log_times={},
            )
        )

    def test_prediction_is_skipped_until_interval_has_elapsed(self):
        last_log_times = {2: 10.0}

        self.assertFalse(
            should_log_indoor_emotion_prediction(
                track_id=2,
                now_seconds=12.9,
                interval_seconds=3.0,
                last_log_times=last_log_times,
            )
        )
        self.assertTrue(
            should_log_indoor_emotion_prediction(
                track_id=2,
                now_seconds=13.0,
                interval_seconds=3.0,
                last_log_times=last_log_times,
            )
        )

    def test_prediction_log_includes_prediction_values(self):
        log_line = format_indoor_emotion_prediction_log(
            track_id=3,
            emotion_index=1,
            emotion="sad",
            prediction=[0.123456, 0.7, 0.05, 0.126544],
        )

        self.assertIn("track_id=3", log_line)
        self.assertIn("emotion_index=1", log_line)
        self.assertIn("emotion=sad", log_line)
        self.assertIn("prediction=[0.1235, 0.7000, 0.0500, 0.1265]", log_line)


if __name__ == "__main__":
    unittest.main()
