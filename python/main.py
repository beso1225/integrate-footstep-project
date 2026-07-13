from pathlib import Path

import pandas as pd
import joblib
from pythonosc import osc_server
from pythonosc import dispatcher
from pythonosc import udp_client

# 設定パラメータ
IP_IPHONE = "0.0.0.0"
PORT_FROM_IPHONE = 5005

IP_PROCESSING = "127.0.0.1"
PORT_TO_PROCESSING = 12000

# モデルのロード
MODEL_PATH = Path(__file__).resolve().parent / "walking_emotion_rf.pkl"
try:
    model = joblib.load(MODEL_PATH)
    print(f"モデルをロードしました: {MODEL_PATH}")
except FileNotFoundError:
    print(f"Error: {MODEL_PATH} が見つかりません。先に学習を実行してください。")
    exit(1)

processing_client = udp_client.SimpleUDPClient(IP_PROCESSING, PORT_TO_PROCESSING)

FEATURE_KEYS = [
    'peak_g', 'step_interval', 'step_interval_var_5', 'peak_g_var_5',
    'gyro_norm_at_peak', 'gyro_norm_rms', 'gyro_norm_std',
    'lr_asymmetry', 'heading_change', 'step_length'
]

MODEL_FEATURE_KEYS = [key for key in FEATURE_KEYS if key != "heading_change"]
EMOTION_NAMES = {0: "Sad", 1: "Neutral", 2: "Happy", 3: "Angry"}

def step_handler(address, *args):
    if len(args) != len(FEATURE_KEYS):
        print(f"Warning: 引数の数が一致しません。想定: {len(FEATURE_KEYS)}, 受信: {len(args)}")
        return

    full_features = pd.DataFrame([args], columns=FEATURE_KEYS)
    model_input = full_features[MODEL_FEATURE_KEYS]

    probabilities = model.predict_proba(model_input)[0]
    prediction = int(model.predict(model_input)[0])
    emotion_label = EMOTION_NAMES.get(prediction, "Unknown")
    
    sad_prob = float(probabilities[0])
    neutral_prob = float(probabilities[1])
    happy_prob = float(probabilities[2])
    angry_prob = float(probabilities[3])
    
    print(f"[推論結果] {emotion_label:8} | Sad: {sad_prob:.2f}, Neu: {neutral_prob:.2f}, Pos: {happy_prob:.2f}, Ang: {angry_prob:.2f}")

    processing_client.send_message("/walking/prediction", prediction)
    processing_client.send_message("/walking/sad_prob", sad_prob)
    processing_client.send_message("/walking/neutral_prob", neutral_prob)
    processing_client.send_message("/walking/happy_prob", happy_prob)
    processing_client.send_message("/walking/angry_prob", angry_prob)

    processing_client.send_message("/walking/heading_change", float(full_features['heading_change'].iloc[0]))
    processing_client.send_message("/walking/step_length", float(full_features['step_length'].iloc[0]))
    processing_client.send_message("/walking/peak_g", float(full_features['peak_g'].iloc[0]))

if __name__ == "__main__":
    disp = dispatcher.Dispatcher()
    disp.map("/step/features", step_handler)

    server = osc_server.ThreadingOSCUDPServer((IP_IPHONE, PORT_FROM_IPHONE), disp)
    print(f"OSCサーバー起動: {IP_IPHONE}:{PORT_FROM_IPHONE} でiPhoneからのデータを待機中...")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nサーバーを停止します。")
