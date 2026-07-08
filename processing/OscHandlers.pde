void oscEvent(OscMessage msg) {
  if (msg.checkAddrPattern("/footstep")) {
    lastIndoorTime = millis();

    int id = (int)msg.get(0).floatValue();
    float realX = msg.get(1).floatValue();
    float realY = msg.get(2).floatValue();
    String indoorEmotion = indoorEmotionFromMessage(msg);

    if (!walkers.containsKey(id)) {
      WalkerState newWalker = new WalkerState(id);
      newWalker.prevRealX = realX;
      newWalker.prevRealY = realY;
      newWalker.lastStepTime = millis();
      walkers.put(id, newWalker);
      return;
    }

    WalkerState w = walkers.get(id);
    float distance = dist(realX, realY, w.prevRealX, w.prevRealY);
    int currentTime = millis();

    if (distance > moveThreshold && currentTime - w.lastStepTime > timeThreshold) {
      PVector previousScreen = indoorToScreen(w.prevRealX, w.prevRealY);
      PVector currentScreen = indoorToScreen(realX, realY);
      float footAngle = atan2(currentScreen.y - previousScreen.y, currentScreen.x - previousScreen.x);

      w.isRightFoot = !w.isRightFoot;
      float lateralOffset = cmToPixels(INDOOR_STEP_WIDTH_CM) / 2.0;
      footprints.add(new Footprint(
        currentScreen.x,
        currentScreen.y,
        footAngle,
        w.isRightFoot,
        indoorEmotion,
        lateralOffset
      ));

      w.prevRealX = realX;
      w.prevRealY = realY;
      w.lastStepTime = currentTime;
    }
  } else {
    if (millis() - lastIndoorTime > indoorTimeout) {
      if (msg.checkAddrPattern("/walking/prediction")) {
        int pred = 0;
        if (msg.checkTypetag("i")) pred = msg.get(0).intValue();
        else if (msg.checkTypetag("f")) pred = (int)msg.get(0).floatValue();

        if (pred == 0) latestOutdoorEmotion = "sad";
        else if (pred == 1) latestOutdoorEmotion = "neutral";
        else latestOutdoorEmotion = "happy";
      }
      else if (msg.checkAddrPattern("/walking/heading_change")) {
        latestHeadingChange = msg.get(0).floatValue();
      }
      else if (msg.checkAddrPattern("/walking/step_length")) {
        latestStepLength = msg.get(0).floatValue();
      }
      else if (msg.checkAddrPattern("/walking/peak_g")) {
        stepOutdoor(latestOutdoorEmotion, latestStepLength, latestHeadingChange);
      }
      else if (msg.checkAddrPattern("/step")) {
        if (msg.arguments().length >= 1 && msg.checkTypetag("s")) {
          stepOutdoor(
            msg.get(0).stringValue(),
            OUTDOOR_DEFAULT_STEP_LENGTH_CM / 100.0,
            radians(randomTurnForFoot(isRightFoot))
          );
        }
      }
    }
  }
}
