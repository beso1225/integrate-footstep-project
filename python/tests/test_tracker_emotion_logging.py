import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import patch


PYTHON_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PYTHON_DIR))

from tracker.emotion import (
    format_indoor_emotion_prediction_log,
    log_indoor_emotion_prediction,
    should_log_indoor_emotion_prediction,
)
import tracker.emotion as emotion_module


class TrackerEmotionLoggingTest(unittest.TestCase):
    def setUp(self):
        emotion_module.indoor_emotion_log_path = None

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

    def test_prediction_log_can_include_sequence_debug_stats(self):
        log_line = format_indoor_emotion_prediction_log(
            track_id=3,
            emotion_index=0,
            emotion="happy",
            prediction=[0.98, 0.01, 0.005, 0.005],
            sequence_length=31,
            feature_min=-0.75,
            feature_max=1.25,
            feature_mean=0.031234,
        )

        self.assertIn("sequence_length=31", log_line)
        self.assertIn("feature_min=-0.7500", log_line)
        self.assertIn("feature_max=1.2500", log_line)
        self.assertIn("feature_mean=0.0312", log_line)

    def test_prediction_log_is_appended_to_configured_file(self):
        with tempfile.TemporaryDirectory() as directory:
            log_path = Path(directory) / "indoor-emotion.log"
            output = StringIO()
            with patch.dict("os.environ", {"INDOOR_EMOTION_LOG_PATH": str(log_path)}):
                with redirect_stdout(output):
                    log_indoor_emotion_prediction(
                        track_id=4,
                        emotion_index=0,
                        emotion="happy",
                        prediction=[0.98, 0.01, 0.005, 0.005],
                    )

            self.assertIn("track_id=4", log_path.read_text())
            self.assertIn("track_id=4", output.getvalue())

    def test_log_directory_gets_timestamped_file_name(self):
        with tempfile.TemporaryDirectory() as directory:
            output = StringIO()
            with patch.dict(
                "os.environ",
                {"INDOOR_EMOTION_LOG_DIR": directory},
                clear=True,
            ):
                with redirect_stdout(output):
                    log_indoor_emotion_prediction(
                        track_id=5,
                        emotion_index=3,
                        emotion="neutral",
                        prediction=[0.05, 0.23, 0.19, 0.53],
                    )

            log_files = list(Path(directory).glob("indoor-emotion-*.log"))
            self.assertEqual(len(log_files), 1)
            self.assertIn("track_id=5", log_files[0].read_text())


if __name__ == "__main__":
    unittest.main()
