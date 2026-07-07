import oscP5.*;
import netP5.*;
import processing.video.*;
import java.util.HashMap;
import java.util.ArrayList;

void setup() {
  size(1200, 800);
  oscP5 = new OscP5(this, 12000);

  footHeight = round(cmToPixels(FOOT_LENGTH_CM));
  footWidth = round(footHeight * FOOT_WIDTH_TO_LENGTH_RATIO);

  happyMovie = new Movie(this, "movie/happy.mp4");
  happyMovie.loop();
  sadMovie = new Movie(this, "movie/sad.mp4");
  sadMovie.loop();
  neutralMovie = new Movie(this, "movie/neutral.mp4");
  neutralMovie.loop();

  PImage fullImage = loadImage("img/footprint.png");
  leftFootMask = fullImage.get(0, 0, fullImage.width / 2, fullImage.height);
  leftFootMask.resize(footWidth, footHeight);

  rightFootMask = fullImage.get(
    fullImage.width / 2, 0, fullImage.width / 2, fullImage.height
  );
  rightFootMask.resize(footWidth, footHeight);

  p[0] = new PVector(100, 100);
  p[1] = new PVector(width - 100, 100);
  p[2] = new PVector(width - 100, height - 100);
  p[3] = new PVector(100, height - 100);

  currentX = width / 2f;
  currentY = height / 2f;
  currentAngle = random(TWO_PI);

  imageMode(CENTER);
}

void movieEvent(Movie m) {
  m.read();
}

void draw() {
  background(0);
  drawFootprints();
  drawCalibrationOverlay();
}

void mousePressed() {
  boolean clickedCorner = false;

  if (isCalibrationMode) {
    for (int i = 0; i < 4; i++) {
      if (dist(mouseX, mouseY, p[i].x, p[i].y) < 20) {
        selectedCorner = i;
        clickedCorner = true;
        break;
      }
    }
  }

  if (!clickedCorner) {
    stepOutdoor(
      selectedEmotion,
      OUTDOOR_DEFAULT_STEP_LENGTH_CM / 100.0,
      radians(randomTurnForFoot(isRightFoot))
    );
  }
}

void mouseDragged() {
  if (isCalibrationMode && selectedCorner != -1) {
    p[selectedCorner].x = mouseX;
    p[selectedCorner].y = mouseY;
  }
}

void mouseReleased() {
  selectedCorner = -1;
}

void keyPressed() {
  if (key == 'c' || key == 'C') {
    isCalibrationMode = !isCalibrationMode;
  }
  if (key == '1') { selectedEmotion = "happy"; }
  else if (key == '2') { selectedEmotion = "sad"; }
  else if (key == '3') { selectedEmotion = "neutral"; }
}
