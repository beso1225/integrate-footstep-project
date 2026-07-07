OscP5 oscP5;

Movie happyMovie, sadMovie, neutralMovie;
PImage leftFootMask, rightFootMask;

final float PIXELS_PER_METER = 280.0;
final float FOOT_LENGTH_CM = 28.0;
final float FOOT_WIDTH_TO_LENGTH_RATIO = 0.5;
final float INDOOR_STEP_TRIGGER_CM = 50.0;
final float INDOOR_STEP_WIDTH_CM = 5.0;
final float OUTDOOR_MIN_STEP_LENGTH_CM = 55.0;
final float OUTDOOR_MAX_STEP_LENGTH_CM = 85.0;
final float OUTDOOR_DEFAULT_STEP_LENGTH_CM = 70.0;
final float OUTDOOR_STEP_WIDTH_CM = 5.0;
final float OUTDOOR_MAX_TURN_DEGREES = 25.0;
final float CLICK_MAX_TURN_DEGREES = 8.0;

int INDOOR_GRID_COLUMNS = 0;
int INDOOR_GRID_ROWS = 0;
float INDOOR_GRID_CELL_SIZE_CM = 0.0;
float INDOOR_TRACKING_WIDTH_CM = 0.0;
float INDOOR_TRACKING_HEIGHT_CM = 0.0;
float[] indoorHomography = {
  1.0, 0.0, 0.0,
  0.0, 1.0, 0.0,
  0.0, 0.0, 1.0
};

int footWidth;
int footHeight;

boolean isCalibrationMode = true;

HashMap<Integer, WalkerState> walkers = new HashMap<Integer, WalkerState>();
ArrayList<Footprint> footprints = new ArrayList<Footprint>();

float currentX, currentY;
float currentAngle;
boolean isRightFoot = true;
String selectedEmotion = "happy";

float moveThreshold = INDOOR_STEP_TRIGGER_CM;
int timeThreshold = 300;

int lastIndoorTime = -10000;
int indoorTimeout = 3000;

String latestOutdoorEmotion = "happy";
float latestStepLength = OUTDOOR_DEFAULT_STEP_LENGTH_CM / 100.0;
float latestHeadingChange = 0.0;

float cmToPixels(float centimeters) {
  return centimeters * PIXELS_PER_METER / 100.0;
}

float randomTurnForFoot(boolean rightFoot) {
  float magnitude = random(0, CLICK_MAX_TURN_DEGREES);
  return rightFoot ? magnitude : -magnitude;
}
