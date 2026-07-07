PVector indoorToScreen(float realX, float realY) {
  float revX = 1.0 - realX / 150.0;
  float revY = 1.0 - realY / 210.0;
  float screenX = lerp(
    lerp(p[0].x, p[1].x, revX), lerp(p[3].x, p[2].x, revX), revY
  );
  float screenY = lerp(
    lerp(p[0].y, p[1].y, revX), lerp(p[3].y, p[2].y, revX), revY
  );
  return new PVector(screenX, screenY);
}

class WalkerState {
  float prevRealX = 0, prevRealY = 0;
  boolean isRightFoot = false;
  int lastStepTime = 0;
  color myColor;

  WalkerState(int id) {
    colorMode(HSB, 360, 100, 100);
    myColor = color((id * 73) % 360, 80, 100);
    colorMode(RGB, 255);
  }
}
