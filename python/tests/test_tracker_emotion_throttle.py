import sys
import unittest
from pathlib import Path


PYTHON_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PYTHON_DIR))

from tracker.runtime import should_run_indoor_emotion_inference


class TrackerEmotionThrottleTest(unittest.TestCase):
    def test_interval_one_runs_every_frame(self):
        self.assertTrue(
            should_run_indoor_emotion_inference(
                track_id=1,
                frame_index=0,
                interval_frames=1,
                last_inference_frames={},
            )
        )
        self.assertTrue(
            should_run_indoor_emotion_inference(
                track_id=1,
                frame_index=10,
                interval_frames=1,
                last_inference_frames={1: 0},
            )
        )

    def test_first_frame_for_track_runs_inference(self):
        self.assertTrue(
            should_run_indoor_emotion_inference(
                track_id=7,
                frame_index=12,
                interval_frames=5,
                last_inference_frames={},
            )
        )

    def test_inference_is_skipped_until_interval_has_elapsed(self):
        last_inference_frames = {3: 8}

        self.assertFalse(
            should_run_indoor_emotion_inference(
                track_id=3,
                frame_index=11,
                interval_frames=4,
                last_inference_frames=last_inference_frames,
            )
        )
        self.assertTrue(
            should_run_indoor_emotion_inference(
                track_id=3,
                frame_index=12,
                interval_frames=4,
                last_inference_frames=last_inference_frames,
            )
        )


if __name__ == "__main__":
    unittest.main()
