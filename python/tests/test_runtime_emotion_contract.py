import unittest
from pathlib import Path


PYTHON_DIR = Path(__file__).resolve().parents[1]


class RuntimeEmotionContractTest(unittest.TestCase):
    def test_runtime_declares_indoor_emotion_inference_interval_usage(self):
        config_module = (PYTHON_DIR / "tracker" / "config.py").read_text()
        runtime_module = (PYTHON_DIR / "tracker" / "runtime.py").read_text()

        self.assertIn('INDOOR_EMOTION_INTERVAL_FRAMES = max(', config_module)
        self.assertIn('"INDOOR_EMOTION_INTERVAL_FRAMES"', config_module)
        self.assertIn("should_run_indoor_emotion_inference(", runtime_module)
        self.assertIn("last_emotion_inference_frames", runtime_module)


if __name__ == "__main__":
    unittest.main()
