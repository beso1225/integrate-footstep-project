import sys
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np


PYTHON_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PYTHON_DIR))

from tracker import emotion


class TrackerEmotionDefaultsTest(unittest.TestCase):
    def setUp(self):
        emotion.current_emotions.clear()

    def test_missing_cached_emotion_defaults_to_neutral(self):
        self.assertEqual(emotion.get_cached_indoor_emotion(track_id=99), "neutral")

    def test_unavailable_indoor_emotion_runtime_defaults_to_neutral(self):
        frame = np.zeros((10, 10, 3), dtype=np.uint8)

        with (
            patch.object(emotion, "emotion_model", None),
            patch.object(emotion, "pose", None),
            patch.object(emotion, "pad_sequences", None),
            patch.object(emotion, "mediapipe_image_class", None),
            patch.object(emotion, "mediapipe_image_format", None),
        ):
            self.assertEqual(
                emotion.predict_indoor_emotion(
                    frame,
                    box_bounds=(0, 0, 10, 10),
                    track_id=1,
                ),
                "neutral",
            )


if __name__ == "__main__":
    unittest.main()
