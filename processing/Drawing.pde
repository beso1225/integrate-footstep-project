void drawFootprints() {
  for (int i = footprints.size() - 1; i >= 0; i--) {
    Footprint fp = footprints.get(i);

    if (fp.state.equals("fadeIn")) {
      fp.alpha = min(fp.alpha + fp.fadeSpeed, 255);
    } else if (fp.state.equals("fadeOut")) {
      fp.alpha = max(fp.alpha - fp.fadeSpeed, 0);
      if (fp.alpha == 0) { fp.isComplete = true; }
    }
    if (fp.isComplete) {
      footprints.remove(i);
      continue;
    }

    Movie currentMovie = getMovieForEmotion(fp.emotion);
    if (currentMovie.available() || currentMovie.width > 0) {
      PImage frame = currentMovie.get();
      frame.resize(footWidth, footHeight);
      PImage maskImage = fp.isRight ? rightFootMask : leftFootMask;
      frame.mask(maskImage);

      pushMatrix();
      translate(fp.x, fp.y);
      rotate(fp.angle + PI/2);
      float offset = fp.isRight ? fp.lateralOffset : -fp.lateralOffset;
      tint(255, fp.alpha);
      image(frame, offset, 0);
      popMatrix();
    }

    pushMatrix();
    translate(fp.x, fp.y);
    fp.drawAnimation();
    popMatrix();
  }
  noTint();
}

void drawCalibrationOverlay() {
  if (!isCalibrationMode) return;

  stroke(0, 255, 0);
  strokeWeight(2);
  noFill();
  rect(
    indoorOriginX(),
    indoorOriginY(),
    cmToPixels(INDOOR_TRACKING_WIDTH_CM),
    cmToPixels(INDOOR_TRACKING_HEIGHT_CM)
  );

  stroke(255, 255, 0, 180);
  strokeWeight(1);
  for (int column = 1; column < INDOOR_GRID_COLUMNS; column++) {
    float realX = column * INDOOR_GRID_CELL_SIZE_CM;
    PVector start = indoorToScreen(realX, 0.0);
    PVector end = indoorToScreen(realX, INDOOR_TRACKING_HEIGHT_CM);
    line(start.x, start.y, end.x, end.y);
  }
  for (int row = 1; row < INDOOR_GRID_ROWS; row++) {
    float realY = row * INDOOR_GRID_CELL_SIZE_CM;
    PVector start = indoorToScreen(0.0, realY);
    PVector end = indoorToScreen(INDOOR_TRACKING_WIDTH_CM, realY);
    line(start.x, start.y, end.x, end.y);
  }
  fill(255);
  textSize(16);
  text("Grid Overlay: Press 'c' to hide lines.", 20, 30);
  text(
    "Indoor grid: " + int(INDOOR_GRID_COLUMNS) + " x " + int(INDOOR_GRID_ROWS) +
    " cells, " + nf(INDOOR_GRID_CELL_SIZE_CM, 0, 1) + " cm each",
    20,
    50
  );
  text("Keys for click test: [1] Happy  [2] Sad  [3] Neutral", 20, 70);

  if (millis() - lastIndoorTime <= indoorTimeout) {
    fill(255, 255, 0);
    text("Current Mode: INDOOR (Camera Priority)", 20, 100);
  } else {
    fill(0, 255, 255);
    text("Current Mode: OUTDOOR (iPhone/Auto)", 20, 100);
  }
}

void fadeOldFootprints() {
  int activeCount = 0;
  for (int i = footprints.size() - 1; i >= 0; i--) {
    if (!footprints.get(i).state.equals("fadeOut")) {
      activeCount++;
      if (activeCount > 4) footprints.get(i).state = "fadeOut";
    }
  }
}

class Footprint {
  float x, y, angle;
  float lateralOffset;
  boolean isRight;
  String emotion;
  float alpha;
  float fadeSpeed;
  String state;
  boolean isComplete;

  ArrayList<Particle> particles = new ArrayList<Particle>();
  int maxParticles = 20;

  Footprint(
    float tempX,
    float tempY,
    float tempAngle,
    boolean tempIsRight,
    String tempEmotion,
    float tempLateralOffset
  ) {
    x = tempX;
    y = tempY;
    angle = tempAngle;
    lateralOffset = tempLateralOffset;
    isRight = tempIsRight;
    emotion = tempEmotion;
    alpha = 0;
    fadeSpeed = 10;
    state = "fadeIn";
    isComplete = false;

    initializeParticles();
  }

  void initializeParticles() {
    particles.clear();
    for (int i = 0; i < maxParticles; i++) {
      Particle p = new Particle(emotion);
      particles.add(p);
    }
  }

  void drawAnimation() {
    for (int i = particles.size()-1; i >= 0; i--) {
      Particle p = particles.get(i);
      p.update();
      p.display(alpha);
    }
  }
}

class Particle {
  PVector pos;
  PVector vel;
  float size;
  float rotation;
  float rotVel;
  String emotion;
  float life;
  float fadeRate;

  Particle(String tempEmotion) {
    emotion = tempEmotion;
    pos = new PVector(random(-25, 25), random(-footHeight/2.5f, footHeight/2.5f));
    life = 255;
    fadeRate = random(4, 8);

    if (emotion.equals("happy")) {
      vel = new PVector(random(-0.4, 0.4), random(-0.7, -0.2));
      size = random(2.5, 6.5);
      rotation = random(TWO_PI);
      rotVel = random(-0.08, 0.08);
    } else if (emotion.equals("neutral")) {
      vel = new PVector(random(-0.3, 0.3), random(-0.4, 0.1));
      size = random(4.0, 7.5);
      rotation = random(TWO_PI);
      rotVel = random(-0.05, 0.05);
    } else {
      vel = new PVector(random(-0.15, 0.15), random(-0.25, 0.25));
      size = random(4, 10);
    }
  }

  void update() {
    pos.add(vel);
    if (emotion.equals("happy") || emotion.equals("neutral")) rotation += rotVel;
    life -= fadeRate;
    if (life < 0) life = 0;
  }

  void display(float footprintsAlpha) {
    float baseAlpha = min(life, map(footprintsAlpha, 0, 255, 0, 160));
    if (baseAlpha <= 0) return;
    pushMatrix();
    translate(pos.x, pos.y);
    noStroke();

    if (emotion.equals("happy")) {
      fill(255, 182, 193, baseAlpha);
      rotate(rotation);
      ellipse(0, 0, size * 1.5f, size);
      fill(255, 255, 255, baseAlpha);
      ellipse(0, 0, size * 0.5f, size * 0.5f);
    } else if (emotion.equals("neutral")) {
      fill(120, 220, 140, baseAlpha);
      rotate(rotation);
      ellipse(0, 0, size * 1.8f, size * 0.8f);
      fill(200, 255, 200, baseAlpha * 0.7f);
      ellipse(0, 0, size * 0.8f, size * 0.3f);
    } else {
      fill(173, 216, 230, baseAlpha * 0.6f);
      ellipse(0, 0, size, size);
    }
    popMatrix();
  }
}
