import json
from pathlib import Path
import tomllib
import unittest


PYTHON_DIR = Path(__file__).resolve().parents[1]


class IntegrationFilesTest(unittest.TestCase):
    def test_shared_indoor_grid_config_exists(self):
        config_path = PYTHON_DIR.parent / "processing" / "data" / "indoor_grid.json"
        self.assertTrue(config_path.is_file())
        config = json.loads(config_path.read_text())
        self.assertGreater(config["columns"], 0)
        self.assertGreater(config["rows"], 0)
        self.assertGreater(config["cell_size_cm"], 0)

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
        config_module = (PYTHON_DIR / "tracker" / "config.py").read_text()
        emotion_module = (PYTHON_DIR / "tracker" / "emotion.py").read_text()
        runtime_module = (PYTHON_DIR / "tracker" / "runtime.py").read_text()

        self.assertIn("from tracker.runtime import run", tracker)
        self.assertIn('if __name__ == "__main__":', tracker)
        self.assertIn("run()", tracker)
        self.assertIn('ENABLE_INDOOR_EMOTION = os.getenv("ENABLE_INDOOR_EMOTION", "1") != "0"', config_module)
        self.assertIn('INDOOR_EMOTION_MODEL_PATH = BASE_DIR / "2egait_lstm_model.h5"', config_module)
        self.assertIn('POSE_LANDMARKER_MODEL_PATH = BASE_DIR / "pose_landmarker_full.task"', config_module)
        self.assertIn("from .config import (", emotion_module)
        self.assertIn("from .config import (", runtime_module)
        self.assertIn("from .emotion import predict_indoor_emotion, setup_indoor_emotion", runtime_module)
        self.assertIn("import json", config_module)
        self.assertIn('GRID_CONFIG_PATH = BASE_DIR.parent / "processing" / "data" / "indoor_grid.json"', config_module)
        self.assertIn("GRID_CONFIG = json.loads(GRID_CONFIG_PATH.read_text())", config_module)
        self.assertIn("GRID_DEFINITION = load_grid_definition(GRID_CONFIG_PATH)", config_module)
        self.assertIn("GRID_COLUMNS", config_module)
        self.assertIn("GRID_ROWS", config_module)
        self.assertIn("GRID_CELL_SIZE_CM", config_module)
        self.assertIn("TRACKING_AREA_WIDTH_CM = GRID_COLUMNS * GRID_CELL_SIZE_CM", config_module)
        self.assertIn("TRACKING_AREA_HEIGHT_CM = GRID_ROWS * GRID_CELL_SIZE_CM", config_module)
        self.assertIn("PoseLandmarker.create_from_options", emotion_module)
        self.assertIn("pose_results.pose_world_landmarks[0]", emotion_module)
        self.assertIn("def setup_indoor_emotion():", emotion_module)
        self.assertIn("footstep_payload = [float(track_id), float(real_x), float(real_y)]", runtime_module)
        self.assertIn("footstep_payload.append(emotion)", runtime_module)
        self.assertIn("save_grid_definition(grid_definition, GRID_CONFIG_PATH)", runtime_module)
        self.assertIn("grid_definition = load_grid_definition(GRID_CONFIG_PATH)", runtime_module)
        self.assertIn("handle_keypress", runtime_module)
        self.assertTrue((PYTHON_DIR / "tracker" / "__init__.py").is_file())
        self.assertTrue((PYTHON_DIR / "tracker" / "config.py").is_file())
        self.assertTrue((PYTHON_DIR / "tracker" / "grid.py").is_file())
        self.assertTrue((PYTHON_DIR / "tracker" / "emotion.py").is_file())
        self.assertTrue((PYTHON_DIR / "tracker" / "runtime.py").is_file())
        self.assertTrue((PYTHON_DIR / "2egait_lstm_model.h5").is_file())
        self.assertTrue((PYTHON_DIR / "pose_landmarker_full.task").is_file())
        self.assertIn('loadJSONObject("indoor_grid.json")', (PYTHON_DIR.parent / "processing" / "processing.pde").read_text())
        self.assertIn("if (key == 'r' || key == 'R')", (PYTHON_DIR.parent / "processing" / "processing.pde").read_text())

    def test_indoor_emotion_dependencies_are_declared(self):
        pyproject = tomllib.loads((PYTHON_DIR / "pyproject.toml").read_text())
        self.assertEqual(pyproject["project"]["requires-python"], ">=3.13,<3.14")
        dependencies = pyproject["project"]["dependencies"]
        self.assertTrue(any(dependency.startswith("tensorflow") for dependency in dependencies))
        self.assertTrue(any(dependency.startswith("mediapipe") for dependency in dependencies))


if __name__ == "__main__":
    unittest.main()
