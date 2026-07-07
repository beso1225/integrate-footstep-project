import sys

import cv2
import numpy as np
from pythonosc import udp_client
from ultralytics import YOLO

from .config import (
    CAMERA_INDEX,
    PROCESSING_HOST,
    PROCESSING_PORT,
    PTS_DST,
    PTS_SRC,
    WINDOW_NAME,
    WINDOW_POSITION,
    WINDOW_SIZE,
    YOLO_MODEL_PATH,
)
from .emotion import predict_indoor_emotion, setup_indoor_emotion


def mouse_callback(event, x, y, flags, param):
    if event == cv2.EVENT_LBUTTONDOWN:
        print(f"【クリックした座標】 X: {x}, Y: {y}")


def create_perspective_matrix():
    pts_src = np.array(PTS_SRC, dtype=float)
    pts_dst = np.array(PTS_DST, dtype=float)
    matrix = cv2.getPerspectiveTransform(
        pts_src.astype(np.float32), pts_dst.astype(np.float32)
    )
    return pts_src, matrix


def open_camera():
    print("2. カメラを開きます...")
    cap = cv2.VideoCapture(CAMERA_INDEX)
    if not cap.isOpened():
        print("【エラー】カメラを開けませんでした。")
        sys.exit()
    print("3. カメラの起動に成功しました！")
    return cap


def configure_window():
    cv2.namedWindow(WINDOW_NAME, cv2.WINDOW_NORMAL)
    cv2.moveWindow(WINDOW_NAME, *WINDOW_POSITION)
    cv2.resizeWindow(WINDOW_NAME, *WINDOW_SIZE)
    cv2.setMouseCallback(WINDOW_NAME, mouse_callback)


def draw_tracking_area(frame, pts_src):
    cv2.polylines(
        frame,
        [pts_src.astype(np.int32)],
        isClosed=True,
        color=(255, 0, 0),
        thickness=2,
    )


def to_real_coordinates(matrix, x_min, x_max, y_max):
    foot_x = (x_min + x_max) // 2
    foot_y = y_max
    pixel_coord = np.array([[[foot_x, foot_y]]], dtype=float)
    real_coord = cv2.perspectiveTransform(pixel_coord, matrix)
    real_x, real_y = real_coord[0][0][0], real_coord[0][0][1]
    return foot_x, foot_y, real_x, real_y


def process_box(frame, box, matrix, client, indoor_emotion_enabled):
    if box.id is None:
        return

    track_id = int(box.id[0])
    x_min, y_min, x_max, y_max = map(int, box.xyxy[0])
    box_bounds = (x_min, y_min, x_max, y_max)

    foot_x, foot_y, real_x, real_y = to_real_coordinates(matrix, x_min, x_max, y_max)
    if not (0 <= real_x <= 150 and 0 <= real_y <= 210):
        return

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


def run():
    print("1. YOLOモデルとライブラリを読み込み中...")
    model = YOLO(YOLO_MODEL_PATH)
    client = udp_client.SimpleUDPClient(PROCESSING_HOST, PROCESSING_PORT)
    print(f"データ送信先を設定しました -> {PROCESSING_HOST}:{PROCESSING_PORT}")

    indoor_emotion_enabled = setup_indoor_emotion()
    cap = open_camera()
    configure_window()
    pts_src, matrix = create_perspective_matrix()

    print("システムを開始します。")

    while cap.isOpened():
        success, frame = cap.read()
        if not success:
            break

        results = model.track(frame, persist=True, classes=[0], verbose=False)
        draw_tracking_area(frame, pts_src)

        for box in results[0].boxes:
            process_box(frame, box, matrix, client, indoor_emotion_enabled)

        cv2.imshow(WINDOW_NAME, frame)

        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    cap.release()
    cv2.destroyAllWindows()
