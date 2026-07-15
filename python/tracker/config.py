import json
import os
from pathlib import Path

from .grid import load_grid_definition


BASE_DIR = Path(__file__).resolve().parent.parent

YOLO_MODEL_PATH = BASE_DIR / "yolov8n.pt"
INDOOR_EMOTION_MODEL_PATH = BASE_DIR / "egait_lstm_model_0714_3.h5"
POSE_LANDMARKER_MODEL_PATH = BASE_DIR / "pose_landmarker_full.task"

PROCESSING_HOST = "localhost"
PROCESSING_PORT = 12000
CAMERA_INDEX = 0

ENABLE_INDOOR_EMOTION = os.getenv("ENABLE_INDOOR_EMOTION", "1") != "0"
INDOOR_EMOTIONS = ["happy", "sad", "angry", "neutral"]
DEFAULT_INDOOR_EMOTION = "neutral"
MAX_EMOTION_FRAMES = 150
INDOOR_EMOTION_INTERVAL_FRAMES = max(
    1, int(os.getenv("INDOOR_EMOTION_INTERVAL_FRAMES", "1"))
)
INDOOR_EMOTION_LOG_INTERVAL_SECONDS = max(
    1.0, float(os.getenv("INDOOR_EMOTION_LOG_INTERVAL_SECONDS", "3"))
)

WINDOW_NAME = "Room Tracking System"
WINDOW_POSITION = (100, 100)
WINDOW_SIZE = (800, 600)

GRID_CONFIG_PATH = BASE_DIR.parent / "processing" / "data" / "indoor_grid.json"
GRID_CONFIG = json.loads(GRID_CONFIG_PATH.read_text())
GRID_DEFINITION = load_grid_definition(GRID_CONFIG_PATH)

GRID_COLUMNS = GRID_DEFINITION.columns
GRID_ROWS = GRID_DEFINITION.rows
GRID_CELL_SIZE_CM = GRID_DEFINITION.cell_size_cm
TRACKING_AREA_WIDTH_CM = GRID_COLUMNS * GRID_CELL_SIZE_CM
TRACKING_AREA_HEIGHT_CM = GRID_ROWS * GRID_CELL_SIZE_CM

PTS_SRC = [
    [761, 617],
    [1322, 619],
    [1781, 1025],
    [574, 1022],
]
