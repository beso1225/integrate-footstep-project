# Integrated Footstep Project

屋内カメラトラッキング、屋外 iPhone 歩行データ、Processing の足跡描画を統合したプロジェクトです。

## ディレクトリ構成

- `processing/`: 足跡を描画する Processing sketch です。
- `python/main.py`: 屋外モード用です。iPhone アプリから OSC を受け取り、感情推定して Processing に転送します。
- `python/tracker.py`: 屋内モード用です。カメラ映像から人の足元座標を推定して Processing に送ります。
- `python/train_model.py`: 屋外モードの Random Forest モデルを再学習するスクリプトです。
- `python/walking_data/`: 屋外モデルの学習用 CSV です。

## 通信ポート

- 屋外モード: iPhone アプリ -> `python/main.py` は `5005`、`python/main.py` -> Processing は `12000` です。
- 屋内モード: `python/tracker.py` -> Processing は `12000` です。
- Processing は常に `12000` で OSC を待ち受けます。

## 初回セットアップ

Python 側は `uv` を使います。

```sh
cd python
uv sync
```

Processing 側は Processing IDE で `processing/processing.pde` を開いてください。動画と足跡画像は `processing/data/` 配下を参照します。

## 基本的な実行方法

最初に Processing を起動します。

```sh
processing/processing.pde
```

Processing IDE で sketch を開き、Run してください。

屋外モードを使う場合は、別ターミナルで `main.py` を起動します。

```sh
cd python
uv run python main.py
```

この状態で iPhone アプリから `5005` に `/step/features` を送ると、`main.py` が感情推定を行い、Processing に `/walking/*` を転送します。

屋内モードを使う場合は、別ターミナルで `tracker.py` を起動します。

```sh
cd python
uv run python tracker.py
```

`tracker.py` がカメラを開き、検出した人の座標を `/footstep` として Processing に送ります。Processing は `/footstep` を受け取ると屋内モードになり、しばらく受信が止まると屋外モードに戻ります。

## 屋内感情推定を使う場合

通常の `tracker.py` は座標だけを送ります。屋内でも LSTM/MediaPipe による感情推定を有効にする場合は、環境変数を付けて起動します。

```sh
cd python
ENABLE_INDOOR_EMOTION=1 uv run python tracker.py
```

この機能には `tensorflow` と `mediapipe` が必要です。現在の `pyproject.toml` には必須依存として入れていないため、使う場合は実行環境に追加してください。依存が足りない場合は警告を出して、通常の座標送信モードに戻ります。

## モデル再学習

屋外モードのモデルを再学習する場合は次を実行します。

```sh
cd python
uv run python train_model.py
```

学習データは `python/walking_data/` の `sad_raw.csv`、`neutral_raw.csv`、`happy_raw.csv` を使います。出力モデルは `python/walking_emotion_rf.pkl` です。

## テスト

```sh
cd python
PYTHONDONTWRITEBYTECODE=1 uv run python -m unittest discover -s tests -v
```

`PYTHONDONTWRITEBYTECODE=1` は `__pycache__` の更新を避けるために付けています。

## よくある確認点

- Processing の動画読み込みエラーが出る場合は、`processing/data/movie/happy.mp4`、`sad.mp4`、`neutral.mp4` が存在するか確認してください。
- カメラを開けない場合は、macOS のカメラ権限、他アプリでカメラを使用中でないか、`python/tracker.py` の `cv2.VideoCapture(0)` の番号を確認してください。
- 屋外モードで足跡が出ない場合は、iPhone アプリが `5005` に送信しているか、`main.py` が起動しているか、Processing が `12000` で起動しているか確認してください。
