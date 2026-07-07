import h5py
import json
import traceback

print("=== ターミナルから直接作成した最新版です ===")
try:
    with h5py.File('2egait_lstm_model.h5', 'r+') as f:
        c = f.attrs.get('model_config')
        if c is not None:
            # decode機能があるか安全にチェック
            s = c.decode('utf-8') if hasattr(c, 'decode') else str(c)
            d = json.loads(s)
            fixed = False
            for layer in d.get('config', {}).get('layers', []):
                if layer.get('class_name') == 'LSTM' and 'time_major' in layer.get('config', {}):
                    del layer['config']['time_major']
                    fixed = True
                    print("👉 LSTMレイヤーから 'time_major' を削除しました！")
            if fixed:
                ns = json.dumps(d)
                f.attrs.modify('model_config', ns.encode('utf-8') if hasattr(c, 'decode') else ns)
                print("✨ モデルの手術が完了しました！")
            else:
                print("🤔 'time_major' は既になくなっているか、見つかりませんでした。")
        else:
            print("❌ model_configがありません。")
except Exception as e:
    print("▼エラー詳細▼")
    traceback.print_exc()
