import sys
import unittest
from pathlib import Path

import numpy as np


PYTHON_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PYTHON_DIR / "training"))

from train import create_sliding_windows


class IndoorTrainingWindowsTest(unittest.TestCase):
    def test_long_sequence_is_split_with_stride_and_final_window(self):
        sequence = np.arange(200 * 2, dtype=np.float32).reshape(200, 2)

        windows = create_sliding_windows(
            sequence,
            window_size=150,
            stride=30,
        )

        self.assertEqual([window.shape[0] for window in windows], [150, 150, 150])
        self.assertEqual([int(window[0, 0]) for window in windows], [0, 60, 100])

    def test_short_sequence_is_kept_as_one_window(self):
        sequence = np.zeros((31, 48), dtype=np.float32)

        windows = create_sliding_windows(sequence, window_size=150, stride=30)

        self.assertEqual(len(windows), 1)
        self.assertEqual(windows[0].shape, (31, 48))


if __name__ == "__main__":
    unittest.main()
