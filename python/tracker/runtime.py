import sys

import cv2
import numpy as np
from pythonosc import udp_client
from ultralytics import YOLO

from .calibration import CalibrationState
from .config import (
    CAMERA_INDEX,
    DEFAULT_INDOOR_EMOTION,
    GRID_CONFIG_PATH,
    GRID_DEFINITION,
    INDOOR_EMOTION_INTERVAL_FRAMES,
    PROCESSING_HOST,
    PROCESSING_PORT,
    PTS_SRC,
    WINDOW_NAME,
    WINDOW_POSITION,
    WINDOW_SIZE,
    YOLO_MODEL_PATH,
)
from .emotion import (
    get_cached_indoor_emotion,
    predict_indoor_emotion,
    setup_indoor_emotion,
)
from .grid import load_calibration_points, load_grid_definition, save_grid_definition


def create_calibration_state(grid_definition, calibration_points=None):
    if calibration_points is None:
        calibration_points = create_initial_center_cell_points(grid_definition)
    return CalibrationState(points=np.array(calibration_points, dtype=float))


def create_destination_points(grid_definition):
    return np.array(
        [
            [0.0, 0.0],
            [grid_definition.width_cm, 0.0],
            [grid_definition.width_cm, grid_definition.height_cm],
            [0.0, grid_definition.height_cm],
        ],
        dtype=float,
    )


def validate_grid_shape(grid_definition):
    if grid_definition.columns % 2 == 0 or grid_definition.rows % 2 == 0:
        raise ValueError("GRID_COLUMNS and GRID_ROWS must be odd for center-cell calibration.")


def create_center_cell_destination_points(grid_definition=GRID_DEFINITION):
    validate_grid_shape(grid_definition)
    center_column = grid_definition.columns // 2
    center_row = grid_definition.rows // 2
    left = center_column * grid_definition.cell_size_cm
    top = center_row * grid_definition.cell_size_cm
    right = left + grid_definition.cell_size_cm
    bottom = top + grid_definition.cell_size_cm
    return np.array(
        [
            [left, top],
            [right, top],
            [right, bottom],
            [left, bottom],
        ],
        dtype=float,
    )


def create_perspective_matrix(pts_src, grid_definition):
    pts_dst = create_center_cell_destination_points(grid_definition)
    matrix = cv2.getPerspectiveTransform(
        pts_src.astype(np.float32), pts_dst.astype(np.float32)
    )
    return matrix


def create_inverse_perspective_matrix(pts_src, grid_definition=GRID_DEFINITION):
    pts_dst = create_center_cell_destination_points(grid_definition)
    return cv2.getPerspectiveTransform(
        pts_dst.astype(np.float32), pts_src.astype(np.float32)
    )


def project_destination_point_to_source(inverse_matrix, real_x, real_y):
    destination_point = np.array([[[real_x, real_y]]], dtype=float)
    source_point = cv2.perspectiveTransform(destination_point, inverse_matrix)
    return source_point[0][0]


def create_initial_center_cell_points(grid_definition):
    legacy_outer_points = np.array(PTS_SRC, dtype=float)
    legacy_matrix = cv2.getPerspectiveTransform(
        legacy_outer_points.astype(np.float32),
        create_destination_points(grid_definition).astype(np.float32),
    )
    inverse_matrix = np.linalg.inv(legacy_matrix)
    center_cell_points = []
    for point in create_center_cell_destination_points(grid_definition):
        center_cell_points.append(
            project_destination_point_to_source(inverse_matrix, point[0], point[1])
        )
    return np.array(center_cell_points, dtype=float)


def mouse_callback(event, x, y, flags, param):
    calibration_state = param
    if event == cv2.EVENT_LBUTTONDOWN:
        if calibration_state.start_drag(x, y):
            print(f"中央補正マスの点 {calibration_state.dragging_index + 1} をドラッグ中です。")
        else:
            print(f"【クリックした座標】 X: {x}, Y: {y}")
    elif event == cv2.EVENT_MOUSEMOVE and flags & cv2.EVENT_FLAG_LBUTTON:
        calibration_state.drag_to(x, y)
    elif event == cv2.EVENT_LBUTTONUP:
        calibration_state.drag_to(x, y)
        calibration_state.stop_drag()


def open_camera():
    print("2. カメラを開きます...")
    cap = cv2.VideoCapture(CAMERA_INDEX)
    if not cap.isOpened():
        print("【エラー】カメラを開けませんでした。")
        sys.exit()
    print("3. カメラの起動に成功しました！")
    return cap


def configure_window(calibration_state):
    cv2.namedWindow(WINDOW_NAME, cv2.WINDOW_NORMAL)
    cv2.moveWindow(WINDOW_NAME, *WINDOW_POSITION)
    cv2.resizeWindow(WINDOW_NAME, *WINDOW_SIZE)
    cv2.setMouseCallback(WINDOW_NAME, mouse_callback, calibration_state)


def draw_tracking_area(frame, outer_points, center_points):
    cv2.polylines(
        frame,
        [outer_points.astype(np.int32)],
        isClosed=True,
        color=(255, 0, 0),
        thickness=2,
    )
    for index, point in enumerate(center_points.astype(np.int32)):
        color = (0, 255, 255)
        cv2.circle(frame, tuple(point), 10, color, -1)
        cv2.putText(
            frame,
            str(index + 1),
            (point[0] + 12, point[1] - 12),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            color,
            2,
        )


def draw_calibration_grid(frame, inverse_matrix, grid_definition):
    for column in range(grid_definition.columns + 1):
        real_x = column * grid_definition.cell_size_cm
        start = project_destination_point_to_source(inverse_matrix, real_x, 0.0)
        end = project_destination_point_to_source(
            inverse_matrix, real_x, grid_definition.height_cm
        )
        cv2.line(
            frame,
            tuple(start.astype(np.int32)),
            tuple(end.astype(np.int32)),
            (255, 255, 0),
            1,
        )

    for row in range(grid_definition.rows + 1):
        real_y = row * grid_definition.cell_size_cm
        start = project_destination_point_to_source(inverse_matrix, 0.0, real_y)
        end = project_destination_point_to_source(
            inverse_matrix, grid_definition.width_cm, real_y
        )
        cv2.line(
            frame,
            tuple(start.astype(np.int32)),
            tuple(end.astype(np.int32)),
            (255, 255, 0),
            1,
        )


def create_outer_source_points(inverse_matrix, grid_definition):
    corners = []
    for real_x, real_y in create_destination_points(grid_definition):
        corners.append(project_destination_point_to_source(inverse_matrix, real_x, real_y))
    return np.array(corners, dtype=float)


def to_real_coordinates(matrix, x_min, x_max, y_max):
    foot_x = (x_min + x_max) // 2
    foot_y = y_max
    pixel_coord = np.array([[[foot_x, foot_y]]], dtype=float)
    real_coord = cv2.perspectiveTransform(pixel_coord, matrix)
    real_x, real_y = real_coord[0][0][0], real_coord[0][0][1]
    return foot_x, foot_y, real_x, real_y


def draw_grid_status(frame, grid_definition):
    lines = [
        f"Grid: {grid_definition.columns}x{grid_definition.rows}  Cell: {grid_definition.cell_size_cm:.1f}cm",
        "A/D cols -/+2  X/W rows -/+2  J/K size -/+0.5cm",
        "P save JSON  R reload JSON  Q quit",
    ]
    for index, line in enumerate(lines):
        cv2.putText(
            frame,
            line,
            (20, 30 + index * 24),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (255, 255, 255),
            2,
        )


def should_run_indoor_emotion_inference(
    track_id, frame_index, interval_frames, last_inference_frames
):
    if interval_frames <= 1:
        return True

    last_frame_index = last_inference_frames.get(track_id)
    if last_frame_index is None:
        return True

    return frame_index - last_frame_index >= interval_frames


def process_box(
    frame,
    box,
    matrix,
    client,
    indoor_emotion_enabled,
    grid_definition,
    frame_index,
    last_emotion_inference_frames,
):
    if box.id is None:
        return

    track_id = int(box.id[0])
    x_min, y_min, x_max, y_max = map(int, box.xyxy[0])
    box_bounds = (x_min, y_min, x_max, y_max)

    foot_x, foot_y, real_x, real_y = to_real_coordinates(matrix, x_min, x_max, y_max)
    if not (0 <= real_x <= grid_definition.width_cm and 0 <= real_y <= grid_definition.height_cm):
        return

    cv2.rectangle(frame, (x_min, y_min), (x_max, y_max), (0, 255, 0), 2)
    cv2.circle(frame, (foot_x, foot_y), 6, (0, 0, 255), -1)

    emotion = DEFAULT_INDOOR_EMOTION
    if indoor_emotion_enabled:
        if should_run_indoor_emotion_inference(
            track_id,
            frame_index,
            INDOOR_EMOTION_INTERVAL_FRAMES,
            last_emotion_inference_frames,
        ):
            emotion = predict_indoor_emotion(frame, box_bounds, track_id)
            last_emotion_inference_frames[track_id] = frame_index
        else:
            emotion = get_cached_indoor_emotion(track_id)

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


def handle_keypress(key_code, grid_definition):
    if key_code == ord("a"):
        return grid_definition.adjust_columns(-1), "columns"
    if key_code == ord("d"):
        return grid_definition.adjust_columns(1), "columns"
    if key_code == ord("x"):
        return grid_definition.adjust_rows(-1), "rows"
    if key_code == ord("w"):
        return grid_definition.adjust_rows(1), "rows"
    if key_code == ord("j"):
        return grid_definition.adjust_cell_size(-0.5), "cell"
    if key_code == ord("k"):
        return grid_definition.adjust_cell_size(0.5), "cell"
    return grid_definition, None


def run():
    print("1. YOLOモデルとライブラリを読み込み中...")
    model = YOLO(YOLO_MODEL_PATH)
    client = udp_client.SimpleUDPClient(PROCESSING_HOST, PROCESSING_PORT)
    print(f"データ送信先を設定しました -> {PROCESSING_HOST}:{PROCESSING_PORT}")
    grid_definition = GRID_DEFINITION
    print("中央の1マスの四隅をドラッグして補正できます。終了は q キーです。")
    print("A/D で列数、X/W で行数、J/K で1マスの長さを調整、P で保存、R で再読込。")
    print(
        f"屋内グリッド: {grid_definition.columns} x {grid_definition.rows}, "
        f"1マス {grid_definition.cell_size_cm:.1f}cm, "
        f"全体 {grid_definition.width_cm:.1f}cm x {grid_definition.height_cm:.1f}cm"
    )

    indoor_emotion_enabled = setup_indoor_emotion()
    cap = open_camera()
    calibration_points = load_calibration_points(GRID_CONFIG_PATH)
    calibration_state = create_calibration_state(grid_definition, calibration_points)
    configure_window(calibration_state)
    frame_index = 0
    last_emotion_inference_frames = {}

    print("システムを開始します。")

    while cap.isOpened():
        success, frame = cap.read()
        if not success:
            break

        center_points = calibration_state.points
        matrix = create_perspective_matrix(center_points, grid_definition)
        inverse_matrix = create_inverse_perspective_matrix(center_points, grid_definition)
        outer_points = create_outer_source_points(inverse_matrix, grid_definition)
        results = model.track(frame, persist=True, classes=[0], verbose=False)
        draw_tracking_area(frame, outer_points, center_points)
        draw_calibration_grid(frame, inverse_matrix, grid_definition)
        draw_grid_status(frame, grid_definition)

        for box in results[0].boxes:
            process_box(
                frame,
                box,
                matrix,
                client,
                indoor_emotion_enabled,
                grid_definition,
                frame_index,
                last_emotion_inference_frames,
            )

        cv2.imshow(WINDOW_NAME, frame)
        frame_index += 1

        key_code = cv2.waitKey(1) & 0xFF
        if key_code == ord("q"):
            break
        if key_code == ord("p"):
            save_grid_definition(grid_definition, GRID_CONFIG_PATH, calibration_state.points)
            print(f"グリッド設定を保存しました: {GRID_CONFIG_PATH}")
        elif key_code == ord("r"):
            grid_definition = load_grid_definition(GRID_CONFIG_PATH)
            calibration_points = load_calibration_points(GRID_CONFIG_PATH)
            calibration_state.points = create_calibration_state(
                grid_definition, calibration_points
            ).points
            calibration_state.stop_drag()
            print(
                f"グリッド設定を再読込しました: {grid_definition.columns} x {grid_definition.rows}, "
                f"{grid_definition.cell_size_cm:.1f}cm"
            )
        else:
            updated_grid_definition, changed = handle_keypress(key_code, grid_definition)
            if changed is not None:
                grid_definition = updated_grid_definition
                print(
                    f"グリッド設定を更新: {grid_definition.columns} x {grid_definition.rows}, "
                    f"{grid_definition.cell_size_cm:.1f}cm"
                )

    cap.release()
    cv2.destroyAllWindows()
