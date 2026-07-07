from pathlib import Path
import tomllib
import unittest


PYTHON_DIR = Path(__file__).resolve().parents[1]


class IntegrationFilesTest(unittest.TestCase):
    def test_training_script_declares_expected_training_assets(self):
        self.assertTrue((PYTHON_DIR / "train_model.py").is_file())
        script = (PYTHON_DIR / "train_model.py").read_text()
        self.assertIn('DATA_DIR = BASE_DIR / "walking_data"', script)
        for filename in ("sad_raw.csv", "neutral_raw.csv", "happy_raw.csv"):
            self.assertIn(f'"{filename}"', script)

    def test_training_script_uses_integrated_three_class_contract(self):
        script = (PYTHON_DIR / "train_model.py").read_text()
        self.assertIn('"sad_raw.csv": 0', script)
        self.assertIn('"neutral_raw.csv": 1', script)
        self.assertIn('"happy_raw.csv": 2', script)
        self.assertIn('"heading_change"', script)
        self.assertIn('MODEL_PATH = BASE_DIR / "walking_emotion_rf.pkl"', script)

    def test_tracker_enables_indoor_emotion_by_default(self):
        tracker = (PYTHON_DIR / "tracker.py").read_text()
        self.assertIn('ENABLE_INDOOR_EMOTION = os.getenv("ENABLE_INDOOR_EMOTION", "1") != "0"', tracker)
        self.assertIn('INDOOR_EMOTION_MODEL_PATH = Path(__file__).resolve().parent / "2egait_lstm_model.h5"', tracker)
        self.assertIn('POSE_LANDMARKER_MODEL_PATH = Path(__file__).resolve().parent / "pose_landmarker_full.task"', tracker)
        self.assertIn("PoseLandmarker.create_from_options", tracker)
        self.assertIn("pose_results.pose_world_landmarks[0]", tracker)
        self.assertIn("def setup_indoor_emotion():", tracker)
        self.assertIn("footstep_payload = [float(track_id), float(real_x), float(real_y)]", tracker)
        self.assertIn("footstep_payload.append(emotion)", tracker)
        self.assertTrue((PYTHON_DIR / "2egait_lstm_model.h5").is_file())
        self.assertTrue((PYTHON_DIR / "pose_landmarker_full.task").is_file())

    def test_indoor_emotion_dependencies_are_declared(self):
        pyproject = tomllib.loads((PYTHON_DIR / "pyproject.toml").read_text())
        self.assertEqual(pyproject["project"]["requires-python"], ">=3.13,<3.14")
        dependencies = pyproject["project"]["dependencies"]
        self.assertTrue(any(dependency.startswith("tensorflow") for dependency in dependencies))
        self.assertTrue(any(dependency.startswith("mediapipe") for dependency in dependencies))


if __name__ == "__main__":
    unittest.main()
