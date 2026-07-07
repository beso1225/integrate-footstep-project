import oscP5.*;
import netP5.*;
import java.util.HashMap;
import java.util.ArrayList;

OscP5 oscP5;
PImage leftFoot, rightFoot;

PVector[] p = new PVector[4];
int selectedCorner = -1;
boolean isCalibrationMode = true; 

HashMap<Integer, WalkerState> walkers = new HashMap<Integer, WalkerState>();
ArrayList<Footprint> footprints = new ArrayList<Footprint>();

float moveThreshold = 15.0; 
int timeThreshold = 300; 

void setup() {
  size(1024, 768); 
  oscP5 = new OscP5(this, 5005);
  
  leftFoot = loadImage("left.png");
  rightFoot = loadImage("right.png");
  imageMode(CENTER);
  
  p[0] = new PVector(100, 100);             
  p[1] = new PVector(width - 100, 100);     
  p[2] = new PVector(width - 100, height - 100); 
  p[3] = new PVector(100, height - 100);    
}

void draw() {
  background(0); 
  
  for (int i = footprints.size() - 1; i >= 0; i--) {
    Footprint fp = footprints.get(i);
    fp.display();
    if (fp.opacity <= 0) {
      footprints.remove(i);
    }
  }
  
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
    text("Calibration Mode: Drag red corners to fit your floor area. Press 'c' to hide lines.", 20, 30);
  }
}

void mousePressed() {
  if (!isCalibrationMode) return;
  for (int i = 0; i < 4; i++) {
    if (dist(mouseX, mouseY, p[i].x, p[i].y) < 20) {
      selectedCorner = i;
      break;
    }
  }
}

void mouseDragged() {
  if (selectedCorner != -1) {
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
}

void oscEvent(OscMessage msg) {
  if (msg.checkAddrPattern("/footstep")) {
    int id = (int)msg.get(0).floatValue();
    float realX = msg.get(1).floatValue();
    float realY = msg.get(2).floatValue();
    String emotion = msg.get(3).stringValue(); // 【追加】Pythonからの感情データ
    
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
      
      float footAngle = atan2(realY - w.prevRealY, realX - w.prevRealX) + HALF_PI + PI;
      
      float normX = realX / 150.0; 
      float normY = realY / 210.0;
      
      float revX = 1.0 - normX;
      float revY = 1.0 - normY;
      
      float screenX = lerp(lerp(p[0].x, p[1].x, revX), lerp(p[3].x, p[2].x, revX), revY);
      float screenY = lerp(lerp(p[0].y, p[1].y, revX), lerp(p[3].y, p[2].y, revX), revY);
      
      w.isRightFoot = !w.isRightFoot;
      
      // 【変更】感情(emotion)をFootprintクラスに渡す
      footprints.add(new Footprint(screenX, screenY, footAngle, w.isRightFoot, w.myColor, emotion));
      
      w.prevRealX = realX;
      w.prevRealY = realY;
      w.lastStepTime = currentTime;
    }
  }
}

// -------------------------------------------------------------------
// 足跡 & パーティクルクラス
// -------------------------------------------------------------------
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
  float x, y, angle, opacity;
  boolean isRight;
  color tintColor;
  boolean isFadingIn;
  String emotion;
  ArrayList<Particle> particles = new ArrayList<Particle>();

  Footprint(float x, float y, float angle, boolean isRight, color c, String emotion) {
    this.x = x; this.y = y; this.angle = angle;
    this.isRight = isRight; this.tintColor = c;
    this.emotion = emotion;
    this.opacity = 0;
    this.isFadingIn = true;
    
    // パーティクルの生成
    for (int i = 0; i < 20; i++) {
      particles.add(new Particle(emotion));
    }
  }

  void display() {
    pushMatrix();
    translate(x, y);
    rotate(angle);
    
    tint(red(tintColor), green(tintColor), blue(tintColor), opacity); 
    if (isRight) image(rightFoot, 0, 0, 40, 80);
    else image(leftFoot, 0, 0, 40, 80);
    popMatrix();
    
    // パーティクルの描画
    pushMatrix();
    translate(x, y);
    for (int i = particles.size()-1; i >= 0; i--) {
      Particle p = particles.get(i);
      p.update(); 
      p.display(opacity); 
    }
    popMatrix();
    
    if (isFadingIn) {
      opacity += 20.0; 
      if (opacity >= 255) {
        opacity = 255;
        isFadingIn = false; 
      }
    } else {
      opacity -= 3.0; 
    }
  }
}

class Particle {
  PVector pos, vel; 
  float size, rotation, rotVel, life, fadeRate; 
  String emotion;
  
  Particle(String emotion) {
    this.emotion = emotion;
    pos = new PVector(random(-25, 25), random(-30, 30));
    life = 255; 
    fadeRate = random(4, 8);
    
    // 感情ごとの動きの設定
    if (emotion.equals("Happy")) {
      vel = new PVector(random(-0.4, 0.4), random(-0.7, -0.2)); // 桜：ふわっと上へ
      size = random(2.5, 6.5);
      rotation = random(TWO_PI);
      rotVel = random(-0.08, 0.08);
    } else if (emotion.equals("Sad") || emotion.equals("Angry")) {
      vel = new PVector(random(-0.15, 0.15), random(-0.25, 0.25)); // 霧：どんより漂う
      size = random(4, 10);
    } else {
      vel = new PVector(random(-0.2, 0.2), random(-0.2, 0.2)); // Neutral：静かに漂う光
      size = random(3, 6);
    }
  }

  void update() {
    pos.add(vel);
    if (emotion.equals("Happy")) rotation += rotVel;
    life -= fadeRate;
    if (life < 0) life = 0;
  }

  void display(float footprintsAlpha) {
    float baseAlpha = min(life, map(footprintsAlpha, 0, 255, 0, 160));
    if (baseAlpha <= 0) return; 
    
    pushMatrix();
    translate(pos.x, pos.y); 
    noStroke();
    
    if (emotion.equals("Happy")) {
      fill(255, 182, 193, baseAlpha);
      rotate(rotation);
      ellipse(0, 0, size * 1.5f, size); 
      fill(255, 255, 255, baseAlpha); 
      ellipse(0, 0, size * 0.5f, size * 0.5f);
    } else if (emotion.equals("Sad") || emotion.equals("Angry")) {
      fill(173, 216, 230, baseAlpha * 0.6f); 
      ellipse(0, 0, size, size);
    } else {
      fill(255, 255, 200, baseAlpha * 0.8f);
      ellipse(0, 0, size, size);
    }
    popMatrix();
  }
}
