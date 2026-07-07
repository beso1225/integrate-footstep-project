from pathlib import Path

import joblib
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report
from sklearn.model_selection import train_test_split


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "walking_data"
MODEL_PATH = BASE_DIR / "walking_emotion_rf.pkl"

DROP_COLUMNS = ["step_num", "timestamp", "label", "heading_change"]
LABELS = {
    "sad_raw.csv": 0,
    "neutral_raw.csv": 1,
    "happy_raw.csv": 2,
}
TARGET_NAMES = ["Sad", "Neutral", "Happy"]


def load_training_data():
    frames = []
    for filename, label in LABELS.items():
        csv_path = DATA_DIR / filename
        frame = pd.read_csv(csv_path)
        frame["label"] = label
        frames.append(frame)

    data = pd.concat(frames, ignore_index=True)
    return data[data["step_num"] > 5]


def main():
    data = load_training_data()
    features = data.drop(columns=DROP_COLUMNS)
    labels = data["label"]

    print(f"学習データ総数: {len(data)} steps")
    print(f"使用する特徴量一覧 ({len(features.columns)}個):")
    print(list(features.columns))

    x_train, x_test, y_train, y_test = train_test_split(
        features, labels, test_size=0.2, random_state=42, stratify=labels
    )

    model = RandomForestClassifier(n_estimators=100, max_depth=7, random_state=42)
    model.fit(x_train, y_train)

    predictions = model.predict(x_test)
    print("\n--- Classification Report ---")
    print(classification_report(y_test, predictions, target_names=TARGET_NAMES))

    importances = pd.Series(
        model.feature_importances_, index=features.columns
    ).sort_values(ascending=False)
    print("\n--- Feature Importance ---")
    print(importances)

    joblib.dump(model, MODEL_PATH)
    print(f"\nモデルを保存しました: {MODEL_PATH}")


if __name__ == "__main__":
    main()
