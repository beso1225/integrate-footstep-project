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
MODEL_PATH = 'walking_emotion_rf.pkl'
try:
    model = joblib.load(MODEL_PATH)
    print(f"モデルをロードしました: {MODEL_PATH}")
except FileNotFoundError:
    print(f"Error: {MODEL_PATH} が見つかりません。先に学習を実行してください。")
    exit(1)

processing_client = udp_client.SimpleUDPClient(IP_PROCESSING, PORT_TO_PROCESSING)

# ★ Swift側の15個の特徴量と完全に一致させる
FEATURE_KEYS = [
    'peak_g', 'step_interval', 'step_interval_var_5', 'peak_g_var_5',
    'gyro_norm_at_peak', 'gyro_x_rms', 'gyro_y_rms', 'gyro_z_rms',
    'lr_asymmetry', 'gravity_x_std', 'gravity_y_std', 'pitch_std', 'roll_std',
    'heading_change', 'step_length'
]

EMOTION_NAMES = {0: "Sad", 1: "Neutral", 2: "Happy"}

def step_handler(address, *args):
    if len(args) != len(FEATURE_KEYS):
        print(f"⚠️【データ数不一致】アドレス: {address} | 想定: {len(FEATURE_KEYS)}個, 受信: {len(args)}個")
        return

    # 全15特徴量のDataFrameを作成
    full_features = pd.DataFrame([args], columns=FEATURE_KEYS)
    
    # 推論時：学習モデルに合わせるため 'heading_change' を除外 (14特徴量にする)
    model_input = full_features.drop(columns=['heading_change'])
    
    # 確率とクラス推論 (Sad=0, Neutral=1, Happy=2)
    probabilities = model.predict_proba(model_input)[0]
    prediction = int(model.predict(model_input)[0])
    emotion_label = EMOTION_NAMES.get(prediction, "Unknown")
    
    print(f"[推論結果] {emotion_label} | Sad: {probabilities[0]:.2f}, Neutral: {probabilities[1]:.2f}, Happy: {probabilities[2]:.2f}")
    
    # Processingへアニメーション・感情情報をすべて転送
    processing_client.send_message("/walking/prediction", prediction)
    processing_client.send_message("/walking/sad_prob", float(probabilities[0]))
    processing_client.send_message("/walking/neutral_prob", float(probabilities[1]))
    processing_client.send_message("/walking/happy_prob", float(probabilities[2]))
    
    # アニメーション描画用の物理パラメータをパススルー送信
    processing_client.send_message("/walking/heading_change", float(full_features['heading_change'].iloc[0]))
    processing_client.send_message("/walking/step_length", float(full_features['step_length'].iloc[0]))
    processing_client.send_message("/walking/peak_g", float(full_features['peak_g'].iloc[0]))

# ★【追加】想定外のアドレス（/step/features 以外）で届いたパケットを全て表示するキャッチャー
def default_handler(address, *args):
    print(f"🚨【宛先違いで受信！】届いたアドレス名: '{address}' (データ数: {len(args)}個)")

if __name__ == "__main__":
    disp = dispatcher.Dispatcher()
    disp.map("/step/features", step_handler)
    
    # ★【追加】何のアドレスで届いても一度必ずキャッチする
    disp.set_default_handler(default_handler)

    server = osc_server.ThreadingOSCUDPServer((IP_IPHONE, PORT_FROM_IPHONE), disp)
    print(f"OSCサーバー起動: {IP_IPHONE}:{PORT_FROM_IPHONE} でiPhoneからのデータを待機中...")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nサーバーを停止します。")