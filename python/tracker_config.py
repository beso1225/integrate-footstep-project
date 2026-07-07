import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent

YOLO_MODEL_PATH = BASE_DIR / "yolov8n.pt"
INDOOR_EMOTION_MODEL_PATH = BASE_DIR / "2egait_lstm_model.h5"
POSE_LANDMARKER_MODEL_PATH = BASE_DIR / "pose_landmarker_full.task"

PROCESSING_HOST = "localhost"
PROCESSING_PORT = 12000
CAMERA_INDEX = 1

ENABLE_INDOOR_EMOTION = os.getenv("ENABLE_INDOOR_EMOTION", "1") != "0"
INDOOR_EMOTIONS = ["angry", "happy", "neutral", "sad"]
MAX_EMOTION_FRAMES = 150

WINDOW_NAME = "Room Tracking System"
WINDOW_POSITION = (100, 100)
WINDOW_SIZE = (800, 600)

PTS_SRC = [
    [761, 617],
    [1322, 619],
    [1781, 1025],
    [574, 1022],
]
PTS_DST = [
    [0, 0],
    [150, 0],
    [150, 210],
    [0, 210],
]
