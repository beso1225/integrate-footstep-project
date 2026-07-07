from pathlib import Path
import unittest


PYTHON_DIR = Path(__file__).resolve().parents[1]


class IntegrationFilesTest(unittest.TestCase):
    def test_training_assets_are_available_in_python_dir(self):
        self.assertTrue((PYTHON_DIR / "train_model.py").is_file())
        for filename in ("sad_raw.csv", "neutral_raw.csv", "happy_raw.csv"):
            self.assertTrue((PYTHON_DIR / "walking_data" / filename).is_file())

    def test_training_script_uses_integrated_three_class_contract(self):
        script = (PYTHON_DIR / "train_model.py").read_text()
        self.assertIn('"sad_raw.csv": 0', script)
        self.assertIn('"neutral_raw.csv": 1', script)
        self.assertIn('"happy_raw.csv": 2', script)
        self.assertIn('"heading_change"', script)
        self.assertIn('MODEL_PATH = BASE_DIR / "walking_emotion_rf.pkl"', script)

    def test_tracker_keeps_indoor_emotion_optional(self):
        tracker = (PYTHON_DIR / "tracker.py").read_text()
        self.assertIn('ENABLE_INDOOR_EMOTION = os.getenv("ENABLE_INDOOR_EMOTION") == "1"', tracker)
        self.assertIn('INDOOR_EMOTION_MODEL_PATH = Path(__file__).resolve().parent / "2egait_lstm_model.h5"', tracker)
        self.assertIn("def setup_indoor_emotion():", tracker)
        self.assertIn("footstep_payload = [float(track_id), float(real_x), float(real_y)]", tracker)
        self.assertIn("footstep_payload.append(emotion)", tracker)
        self.assertTrue((PYTHON_DIR / "2egait_lstm_model.h5").is_file())


if __name__ == "__main__":
    unittest.main()
