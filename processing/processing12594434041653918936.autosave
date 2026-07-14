import oscP5.*;
import netP5.*;
import processing.video.*;
import java.util.HashMap;
import java.util.ArrayList;

void loadIndoorGridConfig() {
  JSONObject indoorGridConfig = loadJSONObject("indoor_grid.json");
  INDOOR_GRID_COLUMNS = indoorGridConfig.getInt("columns");
  INDOOR_GRID_ROWS = indoorGridConfig.getInt("rows");
  INDOOR_GRID_CELL_SIZE_CM = indoorGridConfig.getFloat("cell_size_cm");
  INDOOR_TRACKING_WIDTH_CM = INDOOR_GRID_COLUMNS * INDOOR_GRID_CELL_SIZE_CM;
  INDOOR_TRACKING_HEIGHT_CM = INDOOR_GRID_ROWS * INDOOR_GRID_CELL_SIZE_CM;
}

void setup() {
  size(1200, 800);
  oscP5 = new OscP5(this, 12000);
  loadIndoorGridConfig();

  footHeight = round(cmToPixels(FOOT_LENGTH_CM));
  footWidth = round(footHeight * FOOT_WIDTH_TO_LENGTH_RATIO);

  happyMovie = new Movie(this, "movie/happy.mp4");
  happyMovie.loop();
  sadMovie = new Movie(this, "movie/sad.mp4");
  sadMovie.loop();
  neutralMovie = new Movie(this, "movie/neutral.mp4");
  neutralMovie.loop();
  angryMovie = new Movie(this, "movie/angry.mp4");
  angryMovie.loop();

  PImage fullImage = loadImage("img/footprint.png");
  leftFootMask = fullImage.get(0, 0, fullImage.width / 2, fullImage.height);
  leftFootMask.resize(footWidth, footHeight);

  rightFootMask = fullImage.get(
    fullImage.width / 2, 0, fullImage.width / 2, fullImage.height
  );
  rightFootMask.resize(footWidth, footHeight);

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
  stepOutdoor(
    selectedEmotion,
    OUTDOOR_DEFAULT_STEP_LENGTH_CM / 100.0,
    radians(randomTurnForFoot(isRightFoot))
  );
}

void keyPressed() {
  if (key == 'c' || key == 'C') {
    isCalibrationMode = !isCalibrationMode;
  }
  if (key == 'r' || key == 'R') {
    loadIndoorGridConfig();
  }
  if (key == '1') { selectedEmotion = "happy"; }
  else if (key == '2') { selectedEmotion = "sad"; }
  else if (key == '3') { selectedEmotion = "neutral"; }
  else if (key == '4') { selectedEmotion = "angry"; }
}
