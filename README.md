# Integrated Footstep Project

屋内カメラトラッキング、屋外 iPhone 歩行データ、Processing の足跡描画を統合したプロジェクトです。

## ディレクトリ構成

- `processing/`: 足跡を描画する Processing sketch です。
- `python/main.py`: 屋外モード用です。iPhone アプリから OSC を受け取り、感情推定して Processing に転送します。
- `python/tracker.py`: 屋内モード用です。カメラ映像から人の足元座標を推定して Processing に送ります。
- `python/train_model.py`: 屋外モードの Random Forest モデルを再学習するスクリプトです。
- `python/walking_data/`: 屋外モデルの学習用 CSV を配置するディレクトリです（repo には含めません）。

## 通信ポート

- 屋外モード: iPhone アプリ -> `python/main.py` は `5005`、`python/main.py` -> Processing は `12000` です。
- 屋内モード: `python/tracker.py` -> Processing は `12000` です。
- Processing は常に `12000` で OSC を待ち受けます。

## 初回セットアップ

Python 側は `uv` を使います。TensorFlow が Python 3.14 に未対応のため、Python 3.13 を使います。

```sh
cd python
uv python install 3.13
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

`tracker.py` の補正は中央 1 マスを基準に行います。`tracker.py` の表示ウィンドウ上の黄色いハンドルで中央マスの四隅を地面上の基準正方形に合わせると、青い外枠とグリッド全体がその場で再計算されます。

屋内の台形補正は、固定長の正方形グリッドを基準にしています。グリッド設定は `processing/data/indoor_grid.json` を `tracker` と `Processing` が共通で読み込みます。中央マスの四隅を地面上の基準正方形に合わせると、全体グリッドと足座標が同じ実寸座標系で扱われます。

`Processing` はプロジェクタ補正を行いません。`/footstep` で受け取る `realX`, `realY` をそのまま `PIXELS_PER_METER` に従って top-down に描画します。投影面への台形補正は外部アプリ側で行う前提です。

`tracker.py` のウィンドウでは、`A` / `D` で列数、`X` / `W` で行数、`J` / `K` で 1 マスの辺長を調整できます。`P` で `indoor_grid.json` に保存し、`R` で保存済み設定を再読込します。Processing を起動中なら、Processing 側で `R` キーを押すと同じ設定ファイルを再読込できます。

## 屋内感情推定

`tracker.py` はデフォルトで LSTM/MediaPipe による屋内感情推定を有効にします。推定に成功すると `/footstep` の4番目の値として `happy`、`neutral`、`sad` などの感情名を Processing に送ります。

```sh
cd python
uv run python tracker.py
```

感情推定を無効化して座標だけを送りたい場合は、次のように起動します。

```sh
cd python
ENABLE_INDOOR_EMOTION=0 uv run python tracker.py
```

## モデル再学習

屋外モードのモデルを再学習する場合は次を実行します。

```sh
cd python
uv run python train_model.py
```

学習データは `python/walking_data/` に `sad_raw.csv`、`neutral_raw.csv`、`happy_raw.csv` として配置してください。これらの生データ (raw data) は repo に含めません。出力モデルは `python/walking_emotion_rf.pkl` です。

## テスト

```sh
cd python
PYTHONDONTWRITEBYTECODE=1 uv run python -m unittest discover -s tests -v
```

`PYTHONDONTWRITEBYTECODE=1` は `__pycache__` の更新を避けるために付けています。

## よくある確認点

- Processing の動画読み込みエラーが出る場合は、`processing/data/movie/happy.mp4`、`sad.mp4`、`neutral.mp4` が存在するか確認してください。
- カメラを開けない場合は、macOS のカメラ権限、他アプリでカメラを使用中でないか、`python/tracker/config.py` の `CAMERA_INDEX` を確認してください。
- 屋外モードで足跡が出ない場合は、iPhone アプリが `5005` に送信しているか、`main.py` が起動しているか、Processing が `12000` で起動しているか確認してください。
