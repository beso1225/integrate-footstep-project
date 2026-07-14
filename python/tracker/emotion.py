import os
import time
from datetime import datetime

import cv2
import numpy as np

from .config import (
    DEFAULT_INDOOR_EMOTION,
    ENABLE_INDOOR_EMOTION,
    INDOOR_EMOTION_LOG_INTERVAL_SECONDS,
    INDOOR_EMOTION_MODEL_PATH,
    INDOOR_EMOTIONS,
    MAX_EMOTION_FRAMES,
    POSE_LANDMARKER_MODEL_PATH,
)


emotion_model = None
pose = None
pad_sequences = None
mediapipe_image_class = None
mediapipe_image_format = None
sequence_buffers = {}
current_emotions = {}
last_emotion_log_times = {}
indoor_emotion_log_path = None


def setup_indoor_emotion():
    global emotion_model, pose, pad_sequences, mediapipe_image_class, mediapipe_image_format

    if not ENABLE_INDOOR_EMOTION:
        return False

    try:
        os.environ["TF_CPP_MIN_LOG_LEVEL"] = "2"
        import mediapipe as mp
        import tensorflow as tf
        from mediapipe.tasks import python as mp_tasks
        from mediapipe.tasks.python import vision as mp_vision
        from tensorflow.keras.preprocessing.sequence import pad_sequences as keras_pad_sequences

        emotion_model = tf.keras.models.load_model(INDOOR_EMOTION_MODEL_PATH)
        base_options = mp_tasks.BaseOptions(
            model_asset_path=str(POSE_LANDMARKER_MODEL_PATH)
        )
        options = mp_vision.PoseLandmarkerOptions(
            base_options=base_options,
            min_pose_detection_confidence=0.5,
            min_pose_presence_confidence=0.5,
            min_tracking_confidence=0.5,
            output_segmentation_masks=False,
        )
        pose = mp_vision.PoseLandmarker.create_from_options(options)
        pad_sequences = keras_pad_sequences
        mediapipe_image_class = mp.Image
        mediapipe_image_format = mp.ImageFormat.SRGB
        print(f"屋内感情モデルをロードしました: {INDOOR_EMOTION_MODEL_PATH}")
        print(f"姿勢推定モデルをロードしました: {POSE_LANDMARKER_MODEL_PATH}")
        return True
    except Exception as error:
        print(f"【警告】屋内感情推定を無効化します: {error}")
        return False


def extract_egait_features(landmarks):
    # ヘルパー関数: MediaPipeのランドマークからnumpy配列を取得
    def get_pt(idx):
        return np.array([landmarks[idx].x, landmarks[idx].y, landmarks[idx].z])

    # 1. MediaPipeに存在する関節を取得
    head = get_pt(0)       # 鼻を頭の代わりとする
    l_shoulder = get_pt(11)
    r_shoulder = get_pt(12)
    l_elbow = get_pt(13)
    r_elbow = get_pt(14)
    l_hand = get_pt(15)    # 手首を手の代わりとする
    r_hand = get_pt(16)
    l_hip = get_pt(23)
    r_hip = get_pt(24)
    l_knee = get_pt(25)
    r_knee = get_pt(26)
    l_foot = get_pt(27)    # 足首を足の代わりとする
    r_foot = get_pt(28)

    # 2. MediaPipeに存在しない関節（Root, Spine, Neck）を中間点から計算
    root = (l_hip + r_hip) / 2.0             # 左右の腰の中間
    neck = (l_shoulder + r_shoulder) / 2.0   # 左右の肩の中間
    spine = (root + neck) / 2.0              # 腰と首の中間を背骨とする

    # 3. ご指定の順番通りに16個の関節をリスト化
    joints = [
        root, spine, neck, head,
        l_shoulder, l_elbow, l_hand,
        r_shoulder, r_elbow, r_hand,
        l_hip, l_knee, l_foot,
        r_hip, r_knee, r_foot
    ]

    # 4. 腰(root)を原点(0,0,0)とする正規化
    # すべての関節座標からrootの座標を引き算する
    normalized_features = []
    for joint in joints:
        normalized_joint = joint - root
        normalized_features.extend(normalized_joint.tolist())

    # 48次元 (16関節 × 3座標) の1次元配列として返す
    return np.array(normalized_features, dtype=np.float32)


def get_cached_indoor_emotion(track_id):
    return current_emotions.get(track_id, DEFAULT_INDOOR_EMOTION)


def should_log_indoor_emotion_prediction(
    track_id, now_seconds, interval_seconds, last_log_times
):
    last_log_time = last_log_times.get(track_id)
    if last_log_time is None:
        return True

    return now_seconds - last_log_time >= interval_seconds


def format_indoor_emotion_prediction_log(
    track_id,
    emotion_index,
    emotion,
    prediction,
    sequence_length=None,
    feature_min=None,
    feature_max=None,
    feature_mean=None,
):
    prediction_values = np.asarray(prediction, dtype=float).ravel()
    formatted_prediction = ", ".join(
        f"{value:.4f}" for value in prediction_values
    )
    log_line = (
        f"屋内感情推定: track_id={track_id} "
        f"emotion_index={emotion_index} emotion={emotion} "
        f"prediction=[{formatted_prediction}]"
    )
    if sequence_length is not None:
        log_line += (
            f" sequence_length={sequence_length}"
            f" feature_min={feature_min:.4f}"
            f" feature_max={feature_max:.4f}"
            f" feature_mean={feature_mean:.4f}"
        )
    return log_line


def get_indoor_emotion_log_path():
    global indoor_emotion_log_path

    if indoor_emotion_log_path is not None:
        return indoor_emotion_log_path

    configured_path = os.getenv("INDOOR_EMOTION_LOG_PATH")
    if configured_path:
        indoor_emotion_log_path = os.path.expanduser(configured_path)
        return indoor_emotion_log_path

    log_directory = os.getenv("INDOOR_EMOTION_LOG_DIR")
    if not log_directory:
        return None

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    indoor_emotion_log_path = os.path.join(
        os.path.expanduser(log_directory),
        f"indoor-emotion-{timestamp}.log",
    )
    return indoor_emotion_log_path


def log_indoor_emotion_prediction(
    track_id,
    emotion_index,
    emotion,
    prediction,
    sequence_length=None,
    feature_min=None,
    feature_max=None,
    feature_mean=None,
):
    now_seconds = time.monotonic()
    if not should_log_indoor_emotion_prediction(
        track_id,
        now_seconds,
        INDOOR_EMOTION_LOG_INTERVAL_SECONDS,
        last_emotion_log_times,
    ):
        return

    log_line = format_indoor_emotion_prediction_log(
        track_id,
        emotion_index,
        emotion,
        prediction,
        sequence_length,
        feature_min,
        feature_max,
        feature_mean,
    )
    print(log_line)
    log_path = get_indoor_emotion_log_path()
    if log_path:
        log_file = os.path.expanduser(log_path)
        try:
            os.makedirs(os.path.dirname(log_file) or ".", exist_ok=True)
            with open(log_file, "a", encoding="utf-8") as output:
                output.write(log_line + "\n")
        except OSError as error:
            print(f"【警告】屋内感情ログを保存できません: {error}")
    last_emotion_log_times[track_id] = now_seconds


def predict_indoor_emotion(frame, box_bounds, track_id):
    if (
        emotion_model is None
        or pose is None
        or pad_sequences is None
        or mediapipe_image_class is None
        or mediapipe_image_format is None
    ):
        return DEFAULT_INDOOR_EMOTION

    x_min, y_min, x_max, y_max = box_bounds
    pad = 30
    height, width, _ = frame.shape
    y1, y2 = max(0, y_min - pad), min(height, y_max + pad)
    x1, x2 = max(0, x_min - pad), min(width, x_max + pad)
    crop_img = frame[y1:y2, x1:x2]

    if crop_img.shape[0] == 0 or crop_img.shape[1] == 0:
        return get_cached_indoor_emotion(track_id)

    crop_rgb = cv2.cvtColor(crop_img, cv2.COLOR_BGR2RGB)
    mp_image = mediapipe_image_class(
        image_format=mediapipe_image_format,
        data=crop_rgb,
    )
    pose_results = pose.detect(mp_image)

    if not pose_results.pose_world_landmarks:
        return get_cached_indoor_emotion(track_id)

    features = extract_egait_features(pose_results.pose_world_landmarks[0])
    sequence_buffers.setdefault(track_id, []).append(features)
    if len(sequence_buffers[track_id]) > MAX_EMOTION_FRAMES:
        sequence_buffers[track_id].pop(0)

    if len(sequence_buffers[track_id]) > 30:
        input_data = pad_sequences(
            [sequence_buffers[track_id]],
            maxlen=MAX_EMOTION_FRAMES,
            dtype="float32",
            padding="post",
            truncating="post",
            value=-999.0
        )
        prediction = emotion_model.predict(input_data, verbose=0)
        emotion_index = int(np.argmax(prediction[0]))
        emotion = INDOOR_EMOTIONS[emotion_index]
        current_emotions[track_id] = emotion
        log_indoor_emotion_prediction(
            track_id,
            emotion_index,
            emotion,
            prediction[0],
            sequence_length=len(sequence_buffers[track_id]),
            feature_min=float(np.min(features)),
            feature_max=float(np.max(features)),
            feature_mean=float(np.mean(features)),
        )

    return get_cached_indoor_emotion(track_id)
