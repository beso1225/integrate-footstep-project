
歩いている向きの変化と歩幅を取る + 感情としてニュートラルを取る(次回ニュートラル歩きをする)
heading_change は「その一歩でどれだけ向きが変わったか（ラジアン）」を表す値になり、正なら右旋回・負なら左旋回（符号は実機で確認して必要なら反転する）。
Processing側の使い方（メモ）: OSCで受け取った heading_change を累積して現在の進行方向 currentHeading を更新し、
currentHeading += heading_change;
x += step_length * cos(currentHeading);
y += step_length * sin(currentHeading);
のように次の足跡位置を計算すれば、まっすぐ歩けば直進、曲がればその分だけ足跡の軌道もカーブします。左右の足を交互に描くなら、currentHeading に垂直な方向に一定オフセットを加えて左右にずらすと自然です。
