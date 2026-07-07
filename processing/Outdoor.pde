void stepOutdoor(
  String receivedEmotion,
  float inputStepLengthMeters,
  float inputHeadingChangeRadians
) {
  receivedEmotion = normalizeEmotion(receivedEmotion);

  // iPhone側はyaw差分をラジアンで送るため、そのまま累積する
  float maxTurnRadians = radians(OUTDOOR_MAX_TURN_DEGREES);
  float angleDelta = inputHeadingChangeRadians;
  angleDelta = constrain(angleDelta, -maxTurnRadians, maxTurnRadians);
  currentAngle = (currentAngle + angleDelta + TWO_PI) % TWO_PI;

  float stepLengthCm = inputStepLengthMeters * 100.0;
  if (stepLengthCm <= 0) stepLengthCm = OUTDOOR_DEFAULT_STEP_LENGTH_CM;
  stepLengthCm = constrain(
    stepLengthCm, OUTDOOR_MIN_STEP_LENGTH_CM, OUTDOOR_MAX_STEP_LENGTH_CM
  );
  float actualStepPixels = cmToPixels(stepLengthCm);

  float nextX = currentX + cos(currentAngle) * actualStepPixels;
  float nextY = currentY + sin(currentAngle) * actualStepPixels;

  if (nextX < 0) {
    nextX += width;
  } else if (nextX > width) {
    nextX -= width;
  }

  if (nextY < 0) {
    nextY += height;
  } else if (nextY > height) {
    nextY -= height;
  }

  currentX = nextX;
  currentY = nextY;

  float normX = currentX / width;
  float normY = currentY / height;
  float screenX = lerp(lerp(p[0].x, p[1].x, normX), lerp(p[3].x, p[2].x, normX), normY);
  float screenY = lerp(lerp(p[0].y, p[1].y, normX), lerp(p[3].y, p[2].y, normX), normY);

  float lateralOffset = cmToPixels(OUTDOOR_STEP_WIDTH_CM) / 2.0;
  Footprint newFootprint = new Footprint(
    screenX, screenY, currentAngle, isRightFoot, receivedEmotion, lateralOffset
  );
  footprints.add(newFootprint);
  isRightFoot = !isRightFoot;

  fadeOldFootprints();
}
