import sys
import cv2
import numpy as np
import os
from ultralytics import YOLO
from pythonosc import udp_client

# TensorFlowのログをすっきりさせる
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'
import tensorflow as tf
from tensorflow.keras.preprocessing.sequence import pad_sequences

# === 修正箇所：MediaPipeの読み込みをより一般的な方法に変更 ===
try:
        # MediaPipeの読み込みを以下に差し替えてください
    import mediapipe as mp
    # 下の1行を追加・修正することで、確実に解決します
    from mediapipe.tasks import python
    from mediapipe import solutions as mp_solutions

    # もしこれまでの mp_pose.Pose が必要なら、以下のように書き換えます
    mp_pose = mp_solutions.pose
    pose = mp_pose.Pose(min_detection_confidence=0.5, min_tracking_confidence=0.5)
except Exception as e:
    print(f"【エラー】MediaPipeの読み込みに失敗しました: {e}")
    sys.exit(1)

def mouse_callback(event, x, y, flags, param):
    if event == cv2.EVENT_LBUTTONDOWN:
        print(f"【クリックした座標】 X: {x}, Y: {y}")

print("1. YOLOモデルとLSTM感情モデルを読み込み中...")
model_yolo = YOLO("yolov8n.pt")

# LSTMモデルの読み込み
try:
    model_emotion = tf.keras.models.load_model('2egait_lstm_model.h5')
    print("感情モデル (2egait_lstm_model.h5) をロードしました！")
except Exception as e:
    print(f"【エラー】モデルの読み込みに失敗しました: {e}")
    sys.exit(1)

EMOTIONS = ['Angry', 'Happy', 'Neutral', 'Sad']
MAX_FRAMES = 150

# 感情判定用の特徴量抽出関数
def extract_egait_features(landmarks):
    mp_indices = [
        24, 23, 0, 0, 11, 13, 15, 12, 14, 16, 23, 25, 27, 24, 26, 28
    ]
    features = []
    for idx in mp_indices:
        lm = landmarks.landmark[idx]
        features.extend([lm.x, lm.y, lm.z])
    return np.array(features)

client = udp_client.SimpleUDPClient("127.0.0.1", 5005)
print("データ送信先を設定しました -> localhost:5005 (Processingへ)")

cap = cv2.VideoCapture(1)
if not cap.isOpened():
    print("【エラー】カメラを開けませんでした。")
    sys.exit()

window_name = "Room Tracking System"
cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
cv2.moveWindow(window_name, 100, 100)
cv2.resizeWindow(window_name, 800, 600)
cv2.setMouseCallback(window_name, mouse_callback)

pts_src = np.array([[761, 617], [1322, 619], [1781, 1025], [574, 1022]], dtype=float)
pts_dst = np.array([[0, 0], [150, 0], [150, 210], [0, 210]], dtype=float)
M = cv2.getPerspectiveTransform(pts_src.astype(np.float32), pts_dst.astype(np.float32))

# 人（ID）ごとの歩行データを記憶するバッファ
sequence_buffers = {}
current_emotions = {}

print("システムを開始します。")

while cap.isOpened():
    success, frame = cap.read()
    if not success:
        break

    results = model_yolo.track(frame, persist=True, classes=[0], verbose=False)
    cv2.polylines(frame, [pts_src.astype(np.int32)], isClosed=True, color=(255, 0, 0), thickness=2)

    for box in results[0].boxes:
        if box.id is None:
            continue

        track_id = int(box.id[0])
        x_min, y_min, x_max, y_max = map(int, box.xyxy[0])

        foot_x = (x_min + x_max) // 2
        foot_y = y_max

        pixel_coord = np.array([[[foot_x, foot_y]]], dtype=float)
        real_coord = cv2.perspectiveTransform(pixel_coord, M)
        real_x, real_y = real_coord[0][0][0], real_coord[0][0][1]

        if 0 <= real_x <= 150 and 0 <= real_y <= 210:
            cv2.rectangle(frame, (x_min, y_min), (x_max, y_max), (0, 255, 0), 2)
            cv2.circle(frame, (foot_x, foot_y), 6, (0, 0, 255), -1)

            # ─── 感情推定ロジック ───
            # 1. 人の周りを少し広めに切り取る（MediaPipe用）
            pad = 30
            h, w, _ = frame.shape
            y1, y2 = max(0, y_min - pad), min(h, y_max + pad)
            x1, x2 = max(0, x_min - pad), min(w, x_max + pad)
            crop_img = frame[y1:y2, x1:x2]

            if crop_img.shape[0] > 0 and crop_img.shape[1] > 0:
                crop_rgb = cv2.cvtColor(crop_img, cv2.COLOR_BGR2RGB)
                mp_results = pose.process(crop_rgb)

                if mp_results.pose_world_landmarks:
                    features = extract_egait_features(mp_results.pose_world_landmarks)
                    
                    if track_id not in sequence_buffers:
                        sequence_buffers[track_id] = []
                    
                    sequence_buffers[track_id].append(features)

                    # 規定フレームを超えたら古いものを捨てる
                    if len(sequence_buffers[track_id]) > MAX_FRAMES:
                        sequence_buffers[track_id].pop(0)

                    # 30フレーム以上データが溜まったら予測を実行
                    if len(sequence_buffers[track_id]) > 30:
                        input_data = pad_sequences([sequence_buffers[track_id]], maxlen=MAX_FRAMES, dtype='float32', padding='post', truncating='post')
                        prediction = model_emotion.predict(input_data, verbose=0)
                        emotion_idx = np.argmax(prediction[0])
                        current_emotions[track_id] = EMOTIONS[emotion_idx]

            # 判定結果の取得（まだデータが足りない時はNeutralとする）
            emotion_str = current_emotions.get(track_id, "Neutral")

            text = f"ID:{track_id} {emotion_str} X={int(real_x)}"
            cv2.putText(frame, text, (x_min, y_min - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)

            # ─── 送信データを拡張：[ID, X, Y, 感情(String)] の4つを送信 ───
            client.send_message("/footstep", [float(track_id), float(real_x), float(real_y), str(emotion_str)])

    cv2.imshow(window_name, frame)
    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

cap.release()
cv2.destroyAllWindows()