import os 
import numpy as np 
import h5py 
import tensorflow as tf 
from tensorflow.keras.models import Sequential 
from tensorflow.keras.layers import LSTM, Dense, Dropout, Masking 
from tensorflow.keras.preprocessing.sequence import pad_sequences 
from tensorflow.keras.utils import to_categorical 
from tensorflow.keras.callbacks import EarlyStopping, ReduceLROnPlateau
from tensorflow.keras.optimizers import Adam

# TensorFlowの不要なシステム警告ログを非表示にしてスッキリさせる 
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2' 

# ========================================== 
# 設定と定数 
# ========================================== 
EMOTIONS = ['Happy', 'Sad', 'Angry', 'Neutral'] # ラベルの順序を変更して、モデルの出力と一致させる 
MAX_FRAMES = 150 # 歩行データの最大フレーム数（パディング用） 
NUM_FEATURES = 48 # 16関節 × 3座標(x,y,z) 
MODEL_PATH = 'egait_lstm_model.h5' 
MASK_VALUE = -999.0 # 0.0は正常な座標なのでパディングには使わない 

# ========================================== 
# AIモデルの構造定義 
# ========================================== 
def create_model(): 
    """モデルの構造を定義する関数""" 
    model = Sequential([ 
        Masking(mask_value=MASK_VALUE, input_shape=(MAX_FRAMES, NUM_FEATURES)), 
        LSTM(64, return_sequences=True), 
        Dropout(0.5), 
        LSTM(32), 
        Dropout(0.5), 
        Dense(32, activation='relu'), 
        Dense(len(EMOTIONS), activation='softmax') 
    ]) 
    return model 

# ========================================== 
# データ前処理用の独自関数
# ========================================== 
def normalize_to_root(data):
    """
    各フレームのroot関節を(0,0,0)とするように全関節の座標を平行移動する。
    data: (フレーム数, 48) のNumPy配列
    """
    # 各フレームの先頭3要素 (rootの x, y, z) を取得 -> 形状: (フレーム数, 3)
    root_coords = data[:, :3]
    
    # root座標を16関節分（16回）繰り返して、形状を元のデータ(フレーム数, 48)に合わせる
    num_joints = NUM_FEATURES // 3
    root_tiled = np.tile(root_coords, num_joints)
    
    # 全データからroot座標を引き算することで相対座標（基準化）にする
    normalized_data = data - root_tiled
    
    return normalized_data


def compute_class_weight(y):
    """one-hot label から balanced class_weight を作る。"""
    class_ids = np.argmax(y, axis=1)
    class_counts = np.bincount(class_ids, minlength=len(EMOTIONS))
    total_count = class_ids.size
    class_weight = {}
    for class_index, count in enumerate(class_counts):
        if count == 0:
            continue
        class_weight[class_index] = total_count / (len(EMOTIONS) * count)
    return class_weight

# ========================================== 
# 1. データ読み込みと前処理 
# ========================================== 
def load_data(): 
    data_files = [ 
        ('features.h5', 'labels.h5'), 
    ] 
    elmd_files = ('features_ELMD.h5', 'labels_ELMD.h5') 

    if os.path.exists(elmd_files[0]) and os.path.exists(elmd_files[1]): 
        data_files.append(elmd_files) 
        print(f"Detected ELMD dataset: {elmd_files[0]} / {elmd_files[1]} を追加読み込みします。") 
    else: 
        print(f"ELMD dataset を検出できませんでした。{elmd_files[0]} または {elmd_files[1]} が存在しません。") 

    X_list, y_list = [], [] 

    for feat_file, lab_file in data_files: 
        print(f"Loading data from {feat_file} and {lab_file}...") 
        if not os.path.exists(feat_file) or not os.path.exists(lab_file): 
            raise FileNotFoundError(f"{feat_file} または {lab_file} が見つかりません。同じディレクトリに配置してください。") 
        
        # ELMDファイルかどうかを判定
        is_elmd = 'ELMD' in feat_file

        with h5py.File(feat_file, 'r') as f_feat, h5py.File(lab_file, 'r') as f_lab: 
            for key in f_feat: 
                feat_data = np.array(f_feat[key])
                
                # ELMDデータの場合のみ、root座標による基準化を実行
                # ELMDデータの場合のみ、root座標による基準化を実行
                if is_elmd:
                    # 【確認用に追加】基準化前の最初のフレームの先頭12要素（Root〜Head）を表示
                    print(f"\n--- {key} の変換テスト ---")
                    print("変換前 Root座標:", feat_data[0, :3])
                    
                    feat_data = normalize_to_root(feat_data)
                    
                    # 【確認用に追加】基準化後の同じデータを表示
                    print("変換後 Root座標:", feat_data[0, :3])
                    print("変換後 Spine座標:", feat_data[0, 3:6]) # Spineは相対的な値になるはず
                    print("------------------------\n")
                
                X_list.append(feat_data) 
                y_list.append(np.array(f_lab[key])) 

    if len(X_list) == 0: 
        raise ValueError("読み込めるデータがありませんでした。features.h5 あるいは ELMD データセットを配置してください。") 

    # MASK_VALUE を追加して -999.0 でパディングする 
    X = pad_sequences(X_list, maxlen=MAX_FRAMES, dtype='float32', padding='post', truncating='post', value=MASK_VALUE) 
    y = to_categorical(np.array(y_list).flatten(), num_classes=len(EMOTIONS)) 
    print(f"Data loaded! X shape: {X.shape}, y shape: {y.shape}") 
    return X, y 

# ========================================== 
# 2. モデル構築と学習 (修正版)
# ========================================== 
def train(X, y): 
    # 学習データと検証データが偏らないように完全にシャッフルする 
    indices = np.arange(X.shape[0]) 
    np.random.shuffle(indices) 
    X = X[indices] 
    y = y[indices] 
    print("データをシャッフルしました。") 
    class_weight = compute_class_weight(y)
    print(f"class_weight: {class_weight}")

    model = create_model() 
    
    # 対策1: LSTMの勾配爆発を防ぐため、clipnorm（勾配クリッピング）を設定
    optimizer = Adam(learning_rate=0.001, clipnorm=1.0)
    model.compile(optimizer=optimizer, loss='categorical_crossentropy', metrics=['accuracy']) 
    model.summary() 

    # 対策2: 学習を自動制御するコールバック機能
    callbacks = [
        # 精度が10エポック改善しなかったら学習を打ち切り、一番良かった時点の重みを復元する
        EarlyStopping(monitor='val_loss', patience=10, restore_best_weights=True, verbose=1),
        # 精度が停滞したら、学習率を下げて細かく調整する
        ReduceLROnPlateau(monitor='val_loss', factor=0.5, patience=5, min_lr=1e-5, verbose=1)
    ]

    print("Training model...") 
    # callbacksをfitメソッドに追加
    model.fit(
        X,
        y,
        epochs=50,
        batch_size=32,
        validation_split=0.2,
        callbacks=callbacks,
        class_weight=class_weight,
    ) 

    model.save(MODEL_PATH) 
    print(f"Model saved to {MODEL_PATH}")

# ========================================== 
# メイン処理 
# ========================================== 
if __name__ == "__main__": 
    print("=== 学習プロセスを開始します ===") 
    X_train, y_train = load_data() 
    train(X_train, y_train)
    
