import oscP5.*;
import netP5.*;
import processing.video.*;
import java.util.HashMap;
import java.util.ArrayList;

OscP5 oscP5;

// 動画用変数（Neutralを含む）
Movie happyMovie, sadMovie, neutralMovie;
PImage leftFootMask, rightFootMask;

// ★【変更】足跡のサイズをちょっとだけ小さく（40x80 -> 32x64）
int footWidth = 32;  
int footHeight = 64;

PVector[] p = new PVector[4];
int selectedCorner = -1;
boolean isCalibrationMode = true; 

HashMap<Integer, WalkerState> walkers = new HashMap<Integer, WalkerState>();
ArrayList<Footprint> footprints = new ArrayList<Footprint>();

// === 屋外シミュレーション用変数 ===
float currentX, currentY;
float currentAngle; // メモ内の currentHeading に相当
float stepSize = 100; 
boolean isRightFoot = true;
String selectedEmotion = "happy"; 

// 屋内カメラの感度設定
float moveThreshold = 15.0; 
int timeThreshold = 300; 

// === モード切り替え・新OSC受信用の変数 ===
int lastIndoorTime = -10000; 
int indoorTimeout = 3000;    

String latestOutdoorEmotion = "happy";
float latestStepLength = 100.0;
float latestHeadingChange = 0.0;

void setup() {
  size(1200, 800); 
  // ポートは12000で統一
  oscP5 = new OscP5(this, 12000);
  
  happyMovie = new Movie(this, "happy.mp4");
  happyMovie.loop();
  sadMovie = new Movie(this, "sad.mp4");
  sadMovie.loop();
  neutralMovie = new Movie(this, "neutral.mp4");
  neutralMovie.loop();
  
  leftFootMask = loadImage("left.png");
  leftFootMask.resize(footWidth, footHeight); 
  
  rightFootMask = loadImage("right.png");
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

      // 進行方向（fp.angle）に対して垂直な方向にオフセットを加えて左右にずらして描画
      pushMatrix();
      translate(fp.x, fp.y);
      rotate(fp.angle + PI/2); 
      float offset = fp.isRight ? 15 : -15; // 左右の足の開き幅
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

  if (isCalibrationMode) {
    stroke(0, 255, 0);
    strokeWeight(2);
    line(p[0].x, p[0].y, p[1].x, p[1].y);
    line(p[1].x, p[1].y, p[2].x, p[2].y);
    line(p[2].x, p[2].y, p[3].x, p[3].y);
    line(p[3].x, p[3].y, p[0].x, p[0].y);
    for (int i = 0; i < 4; i++) {
      fill(255, 0, 0);
      noStroke();
      ellipse(p[i].x, p[i].y, 20, 20);
    }
    fill(255);
    textSize(16);
    text("Calibration Mode: Drag red corners. Press 'c' to hide lines.", 20, 30);
    text("Keys for click test: [1] Happy  [2] Sad  [3] Neutral", 20, 50);
    
    if (millis() - lastIndoorTime <= indoorTimeout) {
      fill(255, 255, 0);
      text("Current Mode: INDOOR (Camera Priority)", 20, 80);
    } else {
      fill(0, 255, 255);
      text("Current Mode: OUTDOOR (iPhone/Auto)", 20, 80);
    }
  }
}

Movie getMovieForEmotion(String emotion) {
  if (emotion.equals("sad")) return sadMovie;
  if (emotion.equals("neutral")) return neutralMovie;
  return happyMovie; 
}

void oscEvent(OscMessage msg) {
  // === 1. 屋内モード（カメラトラッキング） ===
  if (msg.checkAddrPattern("/footstep")) {
    lastIndoorTime = millis(); 
    
    int id = (int)msg.get(0).floatValue();
    float realX = msg.get(1).floatValue();
    float realY = msg.get(2).floatValue();
    
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
      float footAngle = atan2(realY - w.prevRealY, realX - w.prevRealX);
      float normX = realX / 150.0; 
      float normY = realY / 210.0;
      float revX = 1.0 - normX;
      float revY = 1.0 - normY;
      float screenX = lerp(lerp(p[0].x, p[1].x, revX), lerp(p[3].x, p[2].x, revX), revY);
      float screenY = lerp(lerp(p[0].y, p[1].y, revX), lerp(p[3].y, p[2].y, revX), revY);
      
      w.isRightFoot = !w.isRightFoot;
      footprints.add(new Footprint(screenX, screenY, footAngle, w.isRightFoot, "happy"));
      
      w.prevRealX = realX;
      w.prevRealY = realY;
      w.lastStepTime = currentTime;
      fadeOldFootprints();
    }
  }
  
  // === 2. 屋外モード（新OSC・仕様完全連動） ===
  else {
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
          stepOutdoor(msg.get(0).stringValue(), stepSize, random(-PI/12, PI/12));
        }
      }
    }
  }
}

// ループ（パックマン）方式の屋外処理
void stepOutdoor(String receivedEmotion, float inputStepLength, float inputHeadingChange) {
  
  // 1. カーブ角度（ラジアン）の累積更新
  float angleDelta = inputHeadingChange;
  if (abs(angleDelta) > 10.0) {
    angleDelta = radians(angleDelta); 
  }
  currentAngle += angleDelta; 

  // 2. 【大幅変更】実際の歩幅の反映とピクセル換算
  float actualStepPixels = inputStepLength;
  if (actualStepPixels > 0 && actualStepPixels < 5.0) {
    actualStepPixels *= 280.0; // ★元の140から280へ倍増（歩幅をかなり大きめに）
  }
  actualStepPixels = constrain(actualStepPixels, 60, 450); // ★上限も220から450へ引き上げ

  // 3. 次の位置を計算
  float nextX = currentX + cos(currentAngle) * actualStepPixels;
  float nextY = currentY + sin(currentAngle) * actualStepPixels;
  
  // 画面端を越えたら反対側にループさせる（パックマン仕様）
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

  // 4. 新しい位置を台形緑枠内へマッピング
  float normX = currentX / width;
  float normY = currentY / height;
  float screenX = lerp(lerp(p[0].x, p[1].x, normX), lerp(p[3].x, p[2].x, normX), normY);
  float screenY = lerp(lerp(p[0].y, p[1].y, normX), lerp(p[3].y, p[2].y, normX), normY);

  Footprint newFootprint = new Footprint(screenX, screenY, currentAngle, isRightFoot, receivedEmotion);
  footprints.add(newFootprint);
  isRightFoot = !isRightFoot; 
  
  fadeOldFootprints();
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

// クリックお試し機能（1クリックで最大45度変化・パックマンループ）
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
    stepOutdoor(selectedEmotion, stepSize, random(-PI/4, PI/4));
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

class Footprint {
  float x, y, angle;
  boolean isRight;
  String emotion; 
  float alpha;
  float fadeSpeed;
  String state;
  boolean isComplete;
  
  ArrayList<Particle> particles = new ArrayList<Particle>();
  int maxParticles = 20; 

  Footprint(float tempX, float tempY, float tempAngle, boolean tempIsRight, String tempEmotion) {
    x = tempX;
    y = tempY;
    angle = tempAngle;
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
