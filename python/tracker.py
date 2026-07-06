import sys
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

print("2. カメラを開きます...")
cap = cv2.VideoCapture(0)

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

            text = f"ID:{track_id} X={int(real_x)}, Y={int(real_y)}"
            cv2.putText(
                frame,
                text,
                (x_min, y_min - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (0, 0, 255),
                2,
            )

            # 送信データを元に戻す：[ID, X, Y] の3つのみ送信
            client.send_message(
                "/footstep", [float(track_id), float(real_x), float(real_y)]
            )

    cv2.imshow(window_name, frame)

    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

cap.release()
cv2.destroyAllWindows()
