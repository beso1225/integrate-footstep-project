import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report
import joblib

def main():
    # 1. データの読み込み (4クラスに対応)
    try:
        sad_df = pd.read_csv('sad_raw.csv')
        neutral_df = pd.read_csv('neutral_raw.csv')
        happy_df = pd.read_csv('happy_raw.csv')
        angry_df = pd.read_csv('angry_raw.csv')
    except FileNotFoundError as e:
        print(f"Error: ファイルが見つかりません。パスを確認してください。: {e}")
        return

    # 2. ラベルの付与 (Sad=0, Neutral=1, happy=2, Angry=3)
    sad_df['label'] = 0
    neutral_df['label'] = 1
    happy_df['label'] = 2
    angry_df['label'] = 3

    # 3. データの結合と前処理
    df = pd.concat([sad_df, neutral_df, happy_df, angry_df], ignore_index=True)
    
    # 歩き始めの不安定なデータ（最初の5歩）を削除
    df = df[df['step_num'] > 5]

    # 特徴量（X）とターゲット（y）の分離
    # 推論時と同様に 'heading_change' を除外し、方向不変な9個の特徴量にする
    drop_cols = ['step_num', 'timestamp', 'label', 'heading_change']
    X = df.drop(columns=drop_cols)
    y = df['label']

    print(f"学習データ総数: {len(df)} ステップ")
    print(f"構成 -> Sad: {len(sad_df)}, Neutral: {len(neutral_df)}, Happy: {len(happy_df)}, Angry: {len(angry_df)}")
    print(f"使用する特徴量一覧 ({len(X.columns)}個): {list(X.columns)}")

    # 4. 訓練データとテストデータに分割 (8:2)
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

    # 5. Random Forest モデルの訓練 (不均衡補正付き)
    model = RandomForestClassifier(
        n_estimators=100, 
        max_depth=7, 
        random_state=42, 
        class_weight='balanced'
    )
    model.fit(X_train, y_train)

    # 6. 評価 (4クラスのレポート)
    y_pred = model.predict(X_test)
    print("\n--- 分類パフォーマンス評価 (※参考値) ---")
    print(classification_report(y_test, y_pred, target_names=['Sad', 'Neutral', 'Happy', 'Angry']))

    # 7. 特徴量の重要度（Feature Importance）の出力
    print("\n--- 特徴量重要度 (貢献度が高い順) ---")
    importances = model.feature_importances_
    feat_importances = pd.Series(importances, index=X.columns).sort_values(ascending=False)
    print(feat_importances)

    # 8. モデルの保存
    model_filename = 'walking_emotion_rf.pkl'
    joblib.dump(model, model_filename)
    print(f"\nモデルを保存しました: {model_filename}")

if __name__ == '__main__':
    main()