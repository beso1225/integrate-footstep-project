import sys
import os
from pathlib import Path

import cv2
import numpy as np
from ultralytics import YOLO
from pythonosc import udp_client


def mouse_callback(event, x, y, flags, param):
    if event == cv2.EVENT_LBUTTONDOWN:
        print(f"【クリックした座標】 X: {x}, Y: {y}")


print("1. YOLOモデルとライブラリを読み込み中...")
model_path = Path(__file__).resolve().parent / "yolov8n.pt"
model = YOLO(model_path)

client = udp_client.SimpleUDPClient("localhost", 12000)
print("データ送信先を設定しました -> localhost:12000")

ENABLE_INDOOR_EMOTION = os.getenv("ENABLE_INDOOR_EMOTION", "1") != "0"
INDOOR_EMOTION_MODEL_PATH = Path(__file__).resolve().parent / "2egait_lstm_model.h5"
POSE_LANDMARKER_MODEL_PATH = Path(__file__).resolve().parent / "pose_landmarker_full.task"
INDOOR_EMOTIONS = ["angry", "happy", "neutral", "sad"]
MAX_EMOTION_FRAMES = 150

emotion_model = None
pose = None
pad_sequences = None
mediapipe_image_class = None
mediapipe_image_format = None
sequence_buffers = {}
current_emotions = {}


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
    mp_indices = [24, 23, 0, 0, 11, 13, 15, 12, 14, 16, 23, 25, 27, 24, 26, 28]
    features = []
    for index in mp_indices:
        landmark = landmarks[index]
        features.extend([landmark.x, landmark.y, landmark.z])
    return np.array(features)


def predict_indoor_emotion(frame, box_bounds, track_id):
    if (
        emotion_model is None
        or pose is None
        or pad_sequences is None
        or mediapipe_image_class is None
        or mediapipe_image_format is None
    ):
        return "happy"

    x_min, y_min, x_max, y_max = box_bounds
    pad = 30
    height, width, _ = frame.shape
    y1, y2 = max(0, y_min - pad), min(height, y_max + pad)
    x1, x2 = max(0, x_min - pad), min(width, x_max + pad)
    crop_img = frame[y1:y2, x1:x2]

    if crop_img.shape[0] == 0 or crop_img.shape[1] == 0:
        return current_emotions.get(track_id, "happy")

    crop_rgb = cv2.cvtColor(crop_img, cv2.COLOR_BGR2RGB)
    mp_image = mediapipe_image_class(
        image_format=mediapipe_image_format,
        data=crop_rgb,
    )
    pose_results = pose.detect(mp_image)

    if not pose_results.pose_world_landmarks:
        return current_emotions.get(track_id, "happy")

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
        )
        prediction = emotion_model.predict(input_data, verbose=0)
        emotion_index = int(np.argmax(prediction[0]))
        current_emotions[track_id] = INDOOR_EMOTIONS[emotion_index]

    return current_emotions.get(track_id, "happy")


indoor_emotion_enabled = setup_indoor_emotion()

print("2. カメラを開きます...")
cap = cv2.VideoCapture(1)

if not cap.isOpened():
    print("【エラー】カメラを開けませんでした。")
    sys.exit()

print("3. カメラの起動に成功しました！")

window_name = "Room Tracking System"
cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
cv2.moveWindow(window_name, 100, 100)
cv2.resizeWindow(window_name, 800, 600)

cv2.setMouseCallback(window_name, mouse_callback)

# 現場で取得した綺麗な台形座標
pts_src = np.array(
    [[761, 617], [1322, 619], [1781, 1025], [574, 1022]], dtype=float
)
pts_dst = np.array([[0, 0], [150, 0], [150, 210], [0, 210]], dtype=float)
M = cv2.getPerspectiveTransform(
    pts_src.astype(np.float32), pts_dst.astype(np.float32)
)

print("システムを開始します。")

while cap.isOpened():
    success, frame = cap.read()
    if not success:
        break

    results = model.track(frame, persist=True, classes=[0], verbose=False)

    cv2.polylines(
        frame,
        [pts_src.astype(np.int32)],
        isClosed=True,
        color=(255, 0, 0),
        thickness=2,
    )

    for box in results[0].boxes:
        if box.id is None:
            continue

        track_id = int(box.id[0])
        x_min, y_min, x_max, y_max = map(int, box.xyxy[0])
        box_bounds = (x_min, y_min, x_max, y_max)

        # 元の「おへその真下」の綺麗な中心座標
        foot_x = (x_min + x_max) // 2
        foot_y = y_max

        # 実際の cm 座標に変換
        pixel_coord = np.array([[[foot_x, foot_y]]], dtype=float)
        real_coord = cv2.perspectiveTransform(pixel_coord, M)
        real_x, real_y = real_coord[0][0][0], real_coord[0][0][1]

        # 範囲内の人だけを処理（横0〜150cm, 縦0〜210cm）
        if 0 <= real_x <= 150 and 0 <= real_y <= 210:
            cv2.rectangle(frame, (x_min, y_min), (x_max, y_max), (0, 255, 0), 2)
            cv2.circle(frame, (foot_x, foot_y), 6, (0, 0, 255), -1)

            emotion = predict_indoor_emotion(frame, box_bounds, track_id)

            text = f"ID:{track_id} X={int(real_x)}, Y={int(real_y)}"
            if indoor_emotion_enabled:
                text = f"{text} {emotion}"
            cv2.putText(
                frame,
                text,
                (x_min, y_min - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (0, 0, 255),
                2,
            )

            footstep_payload = [float(track_id), float(real_x), float(real_y)]
            if indoor_emotion_enabled:
                footstep_payload.append(emotion)
            client.send_message("/footstep", footstep_payload)

    cv2.imshow(window_name, frame)

    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

cap.release()
cv2.destroyAllWindows()
