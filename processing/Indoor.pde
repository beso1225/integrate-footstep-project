float indoorOriginX() {
  return max(0, (width - cmToPixels(INDOOR_TRACKING_WIDTH_CM)) / 2.0);
}

float indoorOriginY() {
  return max(0, (height - cmToPixels(INDOOR_TRACKING_HEIGHT_CM)) / 2.0);
}

PVector indoorToScreen(float realX, float realY) {
  float screenX = indoorOriginX() + cmToPixels(realX);
  float screenY = indoorOriginY() + cmToPixels(realY);
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
