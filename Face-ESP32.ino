#include <ESP32Servo.h>
#include <WiFi.h>
#include <WebServer.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include <Preferences.h>

// WiFi Settings
const char* ap_ssid = "InMoov-Control";
const char* ap_password = "InMoov2024"; // Default AP password
const char* wifi_ssid = ".";
const char* wifi_password = "###A1a2a3###";

// ESP8266 Hand Controller IP (WiFi - MANDATORY)
const char* handControllerIP = "192.168.4.2";

// HTTP Communication for Hand (WiFi is MANDATORY)
// Serial2/RX-TX communication is OPTIONAL and not used for hand control

Preferences preferences;

WebServer server(80);
Servo eyeServo;
Servo jawServo;

// Servo configuration
const int eyeServoPin = 18;
const int jawServoPin = 19;

// Eye calibration (60 = Right, 100 = Middle/Front, 130 = Left)
#define EYE_RIGHT 60
#define EYE_CENTER 100
#define EYE_LEFT 130

// Eye movement variables
float currentPos = EYE_CENTER;
float targetPos = EYE_CENTER;
const float eyeAlpha = 0.08;  // Smoothing coefficient for EMA (0.05-0.15 works well)

// Jaw calibration (20 = fully closed, 54 = fully open)
#define JAW_CLOSED 20
#define JAW_OPEN 54
#define JAW_HALF_OPEN 70

// Jaw movement variables
float jawCurrentPos = JAW_CLOSED;
float jawTargetPos = JAW_CLOSED;
float jawVelocity = 0.0;

// Control settings
bool eyeActive = true;
int shakeIntensity = 50;
String behaviorMode = "Normal";
bool manualControl = false;
int manualPosition = EYE_CENTER;
bool targetLockMode = true; // Start in Auto mode (target middle)
int targetLockPosition = EYE_CENTER; // Middle position

// Jaw control settings
bool jawActive = false;
bool jawTalking = false;
bool jawYawning = false;
bool jawChewing = false;
bool jawManualControl = false;
int jawManualPosition = JAW_CLOSED;
String jawMode = "Closed";
int talkingSpeed = 50;
unsigned long talkingStartTime = 0;
unsigned long talkingDuration = 0;
unsigned long lastJawUpdate = 0;
unsigned long nextJawAction = 0;
unsigned long yawnStartTime = 0;

// Hand gesture during talking
unsigned long lastHandGesture = 0;
unsigned long nextHandGesture = 0;
bool handGesturingActive = false;

// Timing
unsigned long lastUpdate = 0;
unsigned long lastBehaviorChange = 0;
unsigned long nextActionTime = 0;

// Behavior state
enum EyeState { FIXATING, SACCADE, SCANNING, GLANCING };
EyeState currentState = FIXATING;
float fixationPoint = EYE_CENTER;

// Serial command control
bool serialControlActive = false;
unsigned long serialControlTimeout = 0;
String serialBuffer = "";

// ESP8266 connection status
bool handControllerConnected = false;
unsigned long lastHandCheck = 0;

// Shake sequence state
enum ShakeState { SHAKE_IDLE, SHAKE_OPENING, SHAKE_SHAKING, SHAKE_REOPENING, SHAKE_COMPLETE };
ShakeState shakeState = SHAKE_IDLE;
unsigned long shakeStartTime = 0;
unsigned long shakeNextAction = 0;
bool shakeSequenceActive = false;

// Debug logging helper - outputs to Serial in NDJSON format
void debugLog(String location, String message, String hypothesisId, String data) {
  unsigned long timestamp = millis();
  // Escape quotes in strings for JSON
  location.replace("\"", "\\\"");
  message.replace("\"", "\\\"");
  data.replace("\"", "\\\"");
  String logEntry = "{\"timestamp\":" + String(timestamp) + ",\"location\":\"" + location + "\",\"message\":\"" + message + "\",\"hypothesisId\":\"" + hypothesisId + "\",\"data\":\"" + data + "\",\"sessionId\":\"debug-session\"}";
  Serial.println(logEntry);
}

void setup() {
  Serial.begin(115200);
  
  // Initialize preferences
  preferences.begin("inmoov", false);
  
  // Setup eye servo
  ESP32PWM::allocateTimer(0);
  eyeServo.setPeriodHertz(50);
  eyeServo.attach(eyeServoPin, 500, 2400);
  eyeServo.write(EYE_CENTER);
  
  // Setup jaw servo
  ESP32PWM::allocateTimer(1);
  jawServo.setPeriodHertz(50);
  jawServo.attach(jawServoPin, 500, 2400);
  jawServo.write(JAW_CLOSED);
  jawCurrentPos = JAW_CLOSED;
  jawTargetPos = JAW_CLOSED;
  
  // Setup WiFi AP mode
  Serial.println("\nSetting up Access Point...");
  WiFi.mode(WIFI_AP_STA);
  
  // Get AP password from preferences or use default
  String storedPassword = preferences.getString("ap_password", ap_password);
  
  // Create Access Point
  IPAddress apIP(192, 168, 4, 1);
  IPAddress gateway(192, 168, 4, 1);
  IPAddress subnet(255, 255, 255, 0);
  
  WiFi.softAPConfig(apIP, gateway, subnet);
  WiFi.softAP(ap_ssid, storedPassword.c_str());
  
  Serial.print("AP Started: ");
  Serial.println(ap_ssid);
  Serial.print("AP IP: ");
  Serial.println(WiFi.softAPIP());
  
  // Try to connect to external WiFi (optional)
  Serial.println("\nConnecting to external WiFi...");
  WiFi.begin(wifi_ssid, wifi_password);
  
  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 30) {
    delay(500);
    Serial.print(".");
    attempts++;
  }
  
  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\n✓ External WiFi Connected!");
    Serial.print("Station IP: ");
    Serial.println(WiFi.localIP());
  } else {
    Serial.println("\n⚠ External WiFi not connected (using AP only)");
  }
  
  Serial.println("\nSerial command interface ready");
  Serial.println("Send JSON commands: {\"command\":\"HAND:FIST\"}");
  Serial.println("\nWiFi Communication with ESP8266:");
  Serial.println("  - ESP8266 IP: " + String(handControllerIP));
  Serial.println("  - WiFi is MANDATORY for hand control");
  Serial.println("  - Serial2/RX-TX is OPTIONAL and not used");
  
  // Initial check for ESP8266 connection
  Serial.println("\nChecking ESP8266 connection...");
  checkHandControllerConnection();
  if (handControllerConnected) {
    Serial.println("✓ ESP8266 hand controller is reachable via WiFi");
  } else {
    Serial.println("⚠ ESP8266 hand controller not reachable - will retry in loop()");
    Serial.println("  Make sure ESP8266 is connected to AP: " + String(ap_ssid));
  }
  
  server.on("/", handleRoot);
  server.on("/control", handleControl);
  server.on("/status", handleStatus);
  server.begin();
  
  randomSeed(analogRead(34));
  delay(500);
}

void loop() {
  server.handleClient();
  
  // Check for serial commands
  checkSerialCommands();
  
  // Check ESP8266 connection status periodically
  unsigned long now = millis();
  if (now - lastHandCheck > 5000) {
    lastHandCheck = now;
    checkHandControllerConnection();
  }
  
  // Reset serial control flag after timeout
  if (serialControlActive && (now - serialControlTimeout > 100)) {
    // #region agent log
    debugLog("loop:187", "Serial control timeout", "H5", "timeout=" + String(now - serialControlTimeout));
    // #endregion
    serialControlActive = false;
  }
  
  // High-speed smooth update (every 5ms = 200Hz)
  if (now - lastUpdate >= 5) {
    lastUpdate = now;
    updateEyeMovement();
  }
  
  // Jaw smooth update (every 10ms = 100Hz)
  if (now - lastJawUpdate >= 10) {
    lastJawUpdate = now;
    updateJawMovement();
  }
  
  // Eye behavior decision (varies by mode)
  // During talking, reduce eye movement and center
  if (jawTalking || jawChewing) {
    // Center eyes and reduce movement during talking
    if (now >= nextActionTime) {
      targetPos = EYE_CENTER;
      currentState = FIXATING;
      fixationPoint = EYE_CENTER;
      nextActionTime = now + 500; // Update less frequently during talking
    }
  } else if (eyeActive && now >= nextActionTime) {
    if (manualControl) {
      // Direct manual control - immediate response
      targetPos = manualPosition;
      currentState = FIXATING;
      fixationPoint = manualPosition;
      nextActionTime = now + 200; // Update frequently for responsiveness
    } else if (targetLockMode) {
      updateTargetLock();
    } else {
      updateNaturalBehavior();
    }
  }
  
  // Jaw behavior decision
  if (jawActive && now >= nextJawAction) {
    if (jawYawning) {
      updateYawningAnimation();
    } else if (jawTalking || jawChewing) {
      updateTalkingAnimation();
    } else if (jawManualControl) {
      jawTargetPos = jawManualPosition;
      nextJawAction = now + 100;
    } else if (jawMode == "Serial") {
      // Serial control - just maintain target position, no idle animations
      nextJawAction = now + 100;
    } else {
      updateJawIdle();
    }
  }
  
  // Check if talking duration expired
  if (jawTalking && talkingDuration > 0 && (now - talkingStartTime) >= talkingDuration) {
    jawTalking = false;
    jawTargetPos = JAW_CLOSED;
    jawMode = "Closed";
    handGesturingActive = false; // Stop hand gestures
  }
  
  // Check if yawning completed
  if (jawYawning && (now - yawnStartTime) >= 4000) {
    jawYawning = false;
    jawTargetPos = JAW_CLOSED;
    jawMode = "Closed";
  }
  
  // Handle shake sequence
  if (shakeSequenceActive) {
    updateShakeSequence();
  }
  
  // Handle hand gestures during talking
  if (handGesturingActive && (jawTalking || jawChewing) && now >= nextHandGesture) {
    // #region agent log
    debugLog("loop:262", "Hand gesture triggered", "H2", "nextHandGesture=" + String(nextHandGesture) + " now=" + String(now));
    // #endregion
    updateHandGesturesDuringTalking();
  }
  // #region agent log
  if (handGesturingActive && nextHandGesture == 0) {
    debugLog("loop:267", "nextHandGesture uninitialized", "H2", "handGesturingActive=true nextHandGesture=0");
  }
  // #endregion
}

void updateEyeMovement() {
  // Exponential Moving Average (EMA) smoothing
  // Adaptive alpha based on movement type and shake intensity
  float alpha = eyeAlpha;
  
  // During talking, use very low alpha to minimize movement
  if (jawTalking || jawChewing) {
    alpha = 0.03; // Very smooth, minimal movement
  }
  // Manual control - high responsiveness
  else if (manualControl) {
    alpha = 0.35; // Very responsive for slider control
  }
  // Target lock mode - moderate responsiveness with stability
  else if (targetLockMode) {
    alpha = 0.20; // Responsive but stable
  }
  // Natural behavior modes
  else if (currentState == SACCADE) {
    // Fast, snappy saccades - higher alpha for quicker response
    alpha = 0.25;
  } else if (currentState == SCANNING) {
    // Smooth, controlled scanning - lower alpha for smoother motion
    alpha = 0.05;
  } else {
    // Natural drift and fixation - adjust based on shake intensity
    float intensityFactor = shakeIntensity / 100.0;
    alpha = eyeAlpha * (0.5 + intensityFactor * 0.5); // Range: 0.04 to 0.12
  }
  
  // Exponential moving average (EMA)
  float newPos = (alpha * targetPos) + ((1.0 - alpha) * currentPos);
  // #region agent log
  if (newPos < EYE_RIGHT || newPos > EYE_LEFT) {
    debugLog("updateEyeMovement:298", "Position out of bounds before constraint", "H6", "newPos=" + String(newPos) + " target=" + String(targetPos) + " current=" + String(currentPos));
  }
  // #endregion
  currentPos = newPos;
  
  // Constrain position
  currentPos = constrain(currentPos, EYE_RIGHT, EYE_LEFT);
  
  // Write smoothed position to servo
  eyeServo.write((int)currentPos);
}

void updateJawMovement() {
  // Physics-based smooth jaw movement
  float diff = jawTargetPos - jawCurrentPos;
  
  // Adaptive smoothing based on jaw mode
  float smoothFactor = 0.25;
  float maxSpeed = 15.0;
  
  if (jawMode == "Yawning") {
    // Slow yawning
    smoothFactor = 0.1;
    maxSpeed = 8.0;
  }
  // Note: Talking and chewing now use same default physics (smoothFactor 0.25, maxSpeed 15.0)
  
  // Calculate velocity with acceleration
  float acceleration = diff * smoothFactor;
  jawVelocity += acceleration;
  
  // Limit maximum speed
  if (abs(jawVelocity) > maxSpeed) {
    jawVelocity = (jawVelocity > 0) ? maxSpeed : -maxSpeed;
  }
  
  // Apply velocity with damping
  jawVelocity *= 0.85;
  jawCurrentPos += jawVelocity;
  
  // Constrain position
  jawCurrentPos = constrain(jawCurrentPos, JAW_CLOSED, JAW_OPEN);
  
  // Write to jaw servo
  jawServo.write((int)jawCurrentPos);
}

void updateTalkingAnimation() {
  unsigned long now = millis();
  
  // Talking animation with natural patterns
  // Speed affects how fast the mouth opens/closes
  int speedFactor = map(talkingSpeed, 0, 100, 150, 50); // Higher speed = faster (lower delay)
  
  // Random talking pattern (varying open amounts)
  int pattern = random(100);
  
  if (pattern < 30) {
    // Small mouth movements (whispering, soft speech)
    jawTargetPos = random(JAW_CLOSED + 10, JAW_CLOSED + 40);
    nextJawAction = now + random(speedFactor, speedFactor * 2);
  } else if (pattern < 60) {
    // Medium mouth movements (normal speech)
    jawTargetPos = random(JAW_CLOSED + 30, JAW_OPEN - 20);
    nextJawAction = now + random(speedFactor, speedFactor * 2);
  } else if (pattern < 85) {
    // Large mouth movements (emphasized words)
    jawTargetPos = random(JAW_OPEN - 40, JAW_OPEN);
    nextJawAction = now + random(speedFactor, speedFactor * 2);
  } else {
    // Quick close (between words)
    jawTargetPos = random(JAW_CLOSED, JAW_CLOSED + 10);
    nextJawAction = now + random(speedFactor / 2, speedFactor);
  }
}

void updateYawningAnimation() {
  unsigned long now = millis();
  unsigned long elapsed = now - yawnStartTime;
  
  if (elapsed < 2000) {
    // Opening phase (0-2 seconds)
    float progress = elapsed / 2000.0;
    jawTargetPos = JAW_CLOSED + (progress * (JAW_OPEN - JAW_CLOSED));
    nextJawAction = now + 50;
  } else if (elapsed < 3500) {
    // Hold open (2-3.5 seconds)
    jawTargetPos = JAW_OPEN;
    nextJawAction = now + 50;
  } else {
    // Closing phase (3.5-4 seconds)
    float progress = (elapsed - 3500) / 500.0;
    jawTargetPos = JAW_OPEN - (progress * (JAW_OPEN - JAW_CLOSED));
    nextJawAction = now + 50;
  }
}

void updateJawIdle() {
  unsigned long now = millis();
  
  // Occasional natural jaw movements when idle
  int action = random(100);
  
  if (action < 5) {
    // Small random movement (breathing, slight adjustment)
    jawTargetPos = random(JAW_CLOSED, JAW_CLOSED + 5);
    nextJawAction = now + random(2000, 5000);
  } else {
    // Stay closed
    jawTargetPos = JAW_CLOSED;
    nextJawAction = now + random(1000, 3000);
  }
}

void updateHandGesturesDuringTalking() {
  unsigned long now = millis();
  
  // Natural hand gestures during talking to enhance communication
  // These gestures emphasize points, show emotion, and aid memory
  int gestureType = random(100);
  
  if (gestureType < 25) {
    // Pointing gesture - emphasizing a point
    sendHandCommandDirect("point");
    nextHandGesture = now + random(800, 1500);
  } else if (gestureType < 40) {
    // Open hand - showing openness or explanation
    sendHandCommandDirect("open");
    nextHandGesture = now + random(600, 1200);
  } else if (gestureType < 55) {
    // OK gesture - agreement or understanding
    sendHandCommandDirect("ok");
    nextHandGesture = now + random(700, 1300);
  } else if (gestureType < 70) {
    // Thumbs up - positive emphasis
    sendHandCommandDirect("thumbsup");
    nextHandGesture = now + random(800, 1400);
  } else if (gestureType < 82) {
    // Peace gesture - friendly, relaxed
    sendHandCommandDirect("peace");
    nextHandGesture = now + random(900, 1600);
  } else if (gestureType < 92) {
    // Like gesture - approval
    sendHandCommandDirect("like");
    nextHandGesture = now + random(700, 1300);
  } else {
    // Return to neutral/open position
    sendHandCommandDirect("open");
    nextHandGesture = now + random(1000, 2000);
  }
}

void updateNaturalBehavior() {
  unsigned long now = millis();
  
  // Get behavior timing multipliers
  float timeMult = 1.0;
  float rangeMult = 1.0;
  
  if (behaviorMode == "Calm") {
    timeMult = 1.8;
    rangeMult = 0.7;
  } else if (behaviorMode == "Active") {
    timeMult = 0.6;
    rangeMult = 1.3;
  } else if (behaviorMode == "Jittery") {
    timeMult = 0.3;
    rangeMult = 1.5;
  }
  
  int action = random(100);
  
  if (action < 25) {
    // Quick saccade to new position
    currentState = SACCADE;
    int side = random(0, 2);
    if (side == 0) {
      // Right side
      targetPos = EYE_RIGHT + random(0, 20) * rangeMult;
    } else {
      // Left side
      targetPos = EYE_LEFT - random(0, 20) * rangeMult;
    }
    fixationPoint = targetPos;
    nextActionTime = now + random(300, 800) * timeMult;
    
  } else if (action < 45) {
    // Return to center with drift
    currentState = SACCADE;
    targetPos = EYE_CENTER + random(-15, 16) * rangeMult;
    fixationPoint = targetPos;
    nextActionTime = now + random(800, 1800) * timeMult;
    
  } else if (action < 60) {
    // Smooth scanning movement
    currentState = SCANNING;
    int scanStart = random(0, 2) ? EYE_RIGHT + 10 : EYE_LEFT - 10;
    int scanEnd = (scanStart < EYE_CENTER) ? EYE_LEFT - 10 : EYE_RIGHT + 10;
    
    // Multi-step scan
    if (abs(currentPos - scanStart) > 10) {
      currentState = SACCADE;
      targetPos = scanStart;
      nextActionTime = now + 200;
    } else {
      targetPos = scanEnd;
      nextActionTime = now + random(1500, 3000) * timeMult;
    }
    
  } else if (action < 85) {
    // Fixation with natural drift
    currentState = FIXATING;
    float intensityFactor = shakeIntensity / 100.0;
    
    // Microsaccade or drift around fixation point
    if (random(100) < 40) {
      // Microsaccade
      targetPos = fixationPoint + random(-12, 13) * intensityFactor;
    } else {
      // Slow drift
      targetPos = currentPos + random(-8, 9) * intensityFactor * 0.6;
    }
    
    targetPos = constrain(targetPos, EYE_RIGHT, EYE_LEFT);
    nextActionTime = now + random(80, 250);
    
  } else {
    // Small exploratory movement
    currentState = SACCADE;
    targetPos = currentPos + random(-35, 36) * rangeMult;
    targetPos = constrain(targetPos, EYE_RIGHT + 5, EYE_LEFT - 5);
    fixationPoint = targetPos;
    nextActionTime = now + random(400, 900) * timeMult;
  }
}

void updateTargetLock() {
  unsigned long now = millis();
  float intensityFactor = shakeIntensity / 100.0;
  
  int action = random(100);
  
  if (action < 85) {
    // Fixate on target with minimal drift - stay locked
    currentState = FIXATING;
    fixationPoint = targetLockPosition;
    
    // Very small microsaccades - stay close to target
    if (random(100) < 30) {
      // Tiny microsaccade around target
      targetPos = targetLockPosition + random(-5, 6) * intensityFactor * 0.5;
    } else {
      // Stay on target
      targetPos = targetLockPosition;
    }
    
    targetPos = constrain(targetPos, EYE_RIGHT, EYE_LEFT);
    nextActionTime = now + random(150, 300);
    
  } else if (action < 95) {
    // Occasional small glance away (much smaller)
    currentState = FIXATING;
    int glanceDir = random(0, 2) ? -1 : 1;
    targetPos = targetLockPosition + (glanceDir * random(8, 15));
    targetPos = constrain(targetPos, EYE_RIGHT, EYE_LEFT);
    nextActionTime = now + random(200, 400);
    
  } else {
    // Return to target
    currentState = FIXATING;
    targetPos = targetLockPosition;
    fixationPoint = targetLockPosition;
    nextActionTime = now + random(100, 250);
  }
}

void handleRoot() {
  String html = "<!DOCTYPE html><html><head>";
  html += "<meta charset='UTF-8'>";
  html += "<meta name='viewport' content='width=device-width,initial-scale=1'>";
  html += "<style>";
  html += "*{margin:0;padding:0;box-sizing:border-box}";
  html += "body{font-family:'Courier New',monospace;background:#1a1a2e;background-image:repeating-linear-gradient(0deg,transparent,transparent 2px,rgba(0,0,0,0.1) 2px,rgba(0,0,0,0.1) 4px);min-height:100vh;padding:15px;color:#00ff00;overflow-x:hidden}";
  html += ".container{max-width:600px;margin:0 auto;background:#0d1117;border:3px solid #00ff00;padding:20px;box-shadow:0 0 20px rgba(0,255,0,0.3),inset 0 0 20px rgba(0,255,0,0.1)}";
  html += "h1{text-align:center;font-size:28px;margin-bottom:15px;color:#00ff00;text-shadow:0 0 10px #00ff00,2px 2px 0 #000;font-weight:bold;letter-spacing:2px;border-bottom:2px solid #00ff00;padding-bottom:10px}";
  html += ".info{background:#000;border:2px solid #00ff00;padding:10px;margin:15px 0;font-size:12px;text-align:center;color:#00ff00;font-family:monospace;box-shadow:inset 0 0 10px rgba(0,255,0,0.2)}";
  html += ".status{background:#000;border:2px solid #00ff00;padding:15px;margin:15px 0;text-align:center;box-shadow:inset 0 0 15px rgba(0,255,0,0.3)}";
  html += ".status-label{font-size:11px;color:#00ff00;margin-bottom:8px;text-transform:uppercase;letter-spacing:1px}";
  html += ".status-value{font-size:42px;font-weight:bold;margin:8px 0;color:#00ff00;text-shadow:0 0 15px #00ff00,0 0 30px #00ff00;font-family:'Courier New',monospace;white-space:nowrap}";
  html += ".status-state{font-size:14px;color:#ffff00;margin-top:5px;text-transform:uppercase;letter-spacing:1px}";
  html += ".btn-group{display:flex;gap:8px;margin:12px 0;flex-wrap:wrap}";
  html += ".btn{flex:1;min-width:80px;padding:12px 8px;border:3px outset #00ff00;font-size:13px;font-weight:bold;cursor:pointer;background:#0a0;color:#000;text-align:center;font-family:'Courier New',monospace;text-transform:uppercase;letter-spacing:1px;box-shadow:2px 2px 4px rgba(0,0,0,0.8),inset 0 0 5px rgba(0,255,0,0.3);position:relative;user-select:none}";
  html += ".btn:active{border:3px inset #00ff00;box-shadow:inset 2px 2px 4px rgba(0,0,0,0.8),inset 0 0 10px rgba(0,255,0,0.5);transform:translate(1px,1px)}";
  html += ".btn:hover{background:#0f0;box-shadow:0 0 10px #00ff00,2px 2px 4px rgba(0,0,0,0.8),inset 0 0 5px rgba(0,255,0,0.3)}";
  html += ".btn-stop{background:#a00;color:#fff;border-color:#f00}";
  html += ".btn-stop:hover{background:#f00;box-shadow:0 0 10px #ff0000}";
  html += ".btn-stop:active{border-color:#f00}";
  html += ".slider-box{background:#000;border:2px solid #00ff00;padding:15px;margin:15px 0;box-shadow:inset 0 0 10px rgba(0,255,0,0.2)}";
  html += ".slider-label{font-size:13px;font-weight:bold;margin-bottom:12px;color:#00ff00;text-transform:uppercase;letter-spacing:1px;display:flex;justify-content:space-between;align-items:center;white-space:nowrap}";
  html += ".slider-value{font-size:18px;color:#ffff00;text-shadow:0 0 8px #ffff00;font-family:monospace;white-space:nowrap}";
  html += ".slider-hint{font-size:10px;color:#888;margin-bottom:8px;font-family:monospace;white-space:nowrap}";
  html += "input[type=range]{width:100%;height:6px;background:#000;border:1px solid #00ff00;outline:none;-webkit-appearance:none;margin:10px 0}";
  html += "input[type=range]::-webkit-slider-thumb{-webkit-appearance:none;width:20px;height:20px;background:#00ff00;border:2px solid #000;cursor:pointer;box-shadow:0 0 8px #00ff00,inset 0 0 5px rgba(0,255,0,0.5)}";
  html += "input[type=range]::-moz-range-thumb{width:20px;height:20px;background:#00ff00;border:2px solid #000;cursor:pointer;box-shadow:0 0 8px #00ff00}";
  html += "details{background:#000;border:2px solid #00ff00;padding:10px;margin:10px 0;color:#00ff00}";
  html += "summary{font-weight:bold;cursor:pointer;padding:5px;text-transform:uppercase;letter-spacing:1px}";
  html += "summary:hover{background:#0a0;color:#000}";
  html += ".hand-status{font-size:11px;text-align:center;padding:5px;margin-bottom:10px;border:1px solid #00ff00;background:#000;font-family:monospace;white-space:nowrap}";
  html += ".hand-status.connected{color:#0f0;border-color:#0f0}";
  html += ".hand-status.disconnected{color:#f00;border-color:#f00}";
  html += "</style></head><body>";
  html += "<div class='container'>";
  html += "<h1>FACE CONTROL SYSTEM</h1>";
  String ipInfo = "AP: " + WiFi.softAPIP().toString();
  if (WiFi.status() == WL_CONNECTED) {
    ipInfo += " | STA: " + WiFi.localIP().toString();
  }
  html += "<div class='info'>" + String(ap_ssid) + " | " + ipInfo + "</div>";
  
  html += "<div class='status'><div class='status-label'>EYE POSITION</div>";
  html += "<div class='status-value' id='pos'>100</div><div class='status-state' id='state'>AUTO</div></div>";
  
  html += "<div class='status'><div class='status-label'>JAW POSITION</div>";
  html += "<div class='status-value' id='jawPos'>0</div><div class='status-state' id='jawState'>INACTIVE</div></div>";
  
  html += "<div class='slider-box'>";
  html += "<div class='slider-label' style='margin-bottom:15px'>EYE CONTROL</div>";
  html += "<div class='btn-group'>";
  html += "<button class='btn' onclick=\"eyeCmd('auto')\">AUTO</button>";
  html += "<button class='btn' onclick=\"eyeCmd('circumstances')\">SCAN</button>";
  html += "</div>";
  html += "<div class='slider-label' style='margin-top:20px'>MANUAL TARGET <span class='slider-value' id='eyeManVal'>100</span></div>";
  html += "<div class='slider-hint'>60 = RIGHT | 100 = CENTER | 130 = LEFT</div>";
  html += "<input type='range' min='60' max='130' value='100' id='eyeManual' oninput=\"setEyeManual(this.value)\">";
  html += "<div class='btn-group' style='margin-top:15px'>";
  html += "<button class='btn' onclick=\"eyeCmd('manual')\">SET TARGET</button>";
  html += "</div></div>";
  
  html += "<div class='slider-box'>";
  html += "<div class='slider-label' style='margin-bottom:10px'>HAND CONTROL</div>";
  html += "<div class='hand-status' id='handStatus'>STATUS: CHECKING...</div>";
  html += "<div class='btn-group'>";
  html += "<button class='btn' onclick=\"handCmd('open')\">OPEN</button>";
  html += "<button class='btn' onclick=\"handCmd('fist')\">FIST</button>";
  html += "</div>";
  html += "<div class='btn-group' style='margin-top:10px'>";
  html += "<button class='btn' onclick=\"handCmd('like')\">LIKE</button>";
  html += "<button class='btn' onclick=\"handCmd('peace')\">PEACE</button>";
  html += "</div>";
  html += "<div class='btn-group' style='margin-top:10px'>";
  html += "<button class='btn' onclick=\"handCmd('ok')\">OK</button>";
  html += "<button class='btn' onclick=\"handCmd('point')\">POINT</button>";
  html += "</div>";
  html += "<div class='btn-group' style='margin-top:10px'>";
  html += "<button class='btn' onclick=\"handCmd('handshake')\">SHAKE</button>";
  html += "<button class='btn' onclick=\"handCmd('thumbsup')\">THUMB UP</button>";
  html += "</div>";
  html += "<div class='btn-group' style='margin-top:10px'>";
  html += "<button class='btn' onclick=\"handCmd('number1')\">1</button>";
  html += "<button class='btn' onclick=\"handCmd('number2')\">2</button>";
  html += "<button class='btn' onclick=\"handCmd('number3')\">3</button>";
  html += "<button class='btn' onclick=\"handCmd('number4')\">4</button>";
  html += "<button class='btn' onclick=\"handCmd('number5')\">5</button>";
  html += "</div>";
  html += "<details style='margin-top:15px'>";
  html += "<summary>MORE GESTURES</summary>";
  html += "<div class='btn-group' style='margin-top:10px'>";
  html += "<button class='btn' onclick=\"handCmd('thumbsdown')\">THUMB DN</button>";
  html += "<button class='btn' onclick=\"handCmd('pinch')\">PINCH</button>";
  html += "</div>";
  html += "<div class='btn-group' style='margin-top:10px'>";
  html += "<button class='btn' onclick=\"handCmd('pinkyup')\">PINKY UP</button>";
  html += "<button class='btn' onclick=\"handCmd('pinkyringup')\">PINKY+RING</button>";
  html += "</div>";
  html += "<div class='btn-group' style='margin-top:10px'>";
  html += "<button class='btn' onclick=\"handCmd('gimme')\">GIMME</button>";
  html += "<button class='btn' onclick=\"handCmd('iloveyou')\">I LOVE U</button>";
  html += "</div>";
  html += "<div class='btn-group' style='margin-top:10px'>";
  html += "<button class='btn' onclick=\"handCmd('swag')\">SWAG</button>";
  html += "<button class='btn' onclick=\"handCmd('stop')\">STOP</button>";
  html += "</div>";
  html += "</details></div>";
  
  html += "<div class='slider-box'>";
  html += "<div class='slider-label' style='margin-bottom:10px'>JAW CONTROL</div>";
  html += "<div class='btn-group'>";
  html += "<button class='btn' onclick=\"jawCmd('open')\">OPEN</button>";
  html += "<button class='btn' onclick=\"jawCmd('close')\">CLOSE</button>";
  html += "</div>";
  html += "<div class='btn-group' style='margin-top:10px'>";
  html += "<button class='btn' onclick=\"jawCmd('talk')\">TALK</button>";
  html += "<button class='btn btn-stop' onclick=\"jawCmd('stop')\">STOP</button>";
  html += "</div>";
  html += "<div class='btn-group' style='margin-top:10px'>";
  html += "<button class='btn' onclick=\"jawCmd('yawn')\">YAWN</button>";
  html += "<button class='btn' onclick=\"jawCmd('chew')\">CHEW</button>";
  html += "</div>";
  html += "<div class='slider-label' style='margin-top:15px'>TALK SPEED <span class='slider-value' id='talkSpeedVal'>50</span>%</div>";
  html += "<input type='range' min='0' max='100' value='50' id='talkSpeed' oninput=\"setTalkSpeed(this.value)\">";
  html += "<div class='slider-label' style='margin-top:15px'>MANUAL JAW <span class='slider-value' id='jawManVal'>20</span></div>";
  html += "<input type='range' min='20' max='54' value='20' id='jawManual' oninput=\"setJawManual(this.value)\">";
  html += "<div class='btn-group' style='margin-top:15px'>";
  html += "<button class='btn' onclick=\"jawCmd('manualOn')\">MANUAL ON</button>";
  html += "<button class='btn btn-stop' onclick=\"jawCmd('manualOff')\">AUTO MODE</button>";
  html += "</div></div>";
  
  html += "</div>";
  
  html += "<script>";
  html += "function eyeCmd(c){fetch('/control?eyeCmd='+c)}";
  html += "function jawCmd(c){fetch('/control?jawCmd='+c)}";
  html += "function handCmd(c){fetch('/control?handCmd='+c).then(r=>{if(!r.ok)alert('HAND CMD FAILED')})}";
  html += "function setEyeManual(v){document.getElementById('eyeManVal').innerText=v;fetch('/control?eyeManual='+v)}";
  html += "function setTalkSpeed(v){document.getElementById('talkSpeedVal').innerText=v;fetch('/control?talkSpeed='+v)}";
  html += "function setJawManual(v){document.getElementById('jawManVal').innerText=v;fetch('/control?jawManual='+v)}";
  html += "function updateStatus(d){";
  html += "document.getElementById('pos').innerText=d.pos;";
  html += "document.getElementById('state').innerText=d.state.toUpperCase();";
  html += "document.getElementById('jawPos').innerText=d.jawPos;";
  html += "document.getElementById('jawState').innerText=d.jawState.toUpperCase();";
  html += "const hs=document.getElementById('handStatus');";
  html += "if(d.handConnected){hs.innerText='STATUS: CONNECTED';hs.className='hand-status connected'}";
  html += "else{hs.innerText='STATUS: DISCONNECTED';hs.className='hand-status disconnected'}}";
  html += "setInterval(()=>{fetch('/status').then(r=>r.json()).then(updateStatus)},200);";
  html += "</script></body></html>";
  
  server.send(200, "text/html", html);
}

void handleControl() {
  // Check if serial control is active (priority)
  if (serialControlActive) {
    server.send(200, "text/plain", "Serial control active");
    return;
  }
  
  // Eye controls
  if (server.hasArg("eyeCmd")) {
    String c = server.arg("eyeCmd");
    if (c == "auto") {
      // Auto mode: target middle and move naturally
      eyeActive = true;
      manualControl = false;
      targetLockMode = true;
      targetLockPosition = EYE_CENTER; // Middle
      behaviorMode = "Normal";
    } else if (c == "circumstances") {
      // Circumstances mode: see everything naturally (natural scanning)
      eyeActive = true;
      manualControl = false;
      targetLockMode = false;
      behaviorMode = "Normal";
    } else if (c == "manual") {
      // Manual mode: direct control via slider
      eyeActive = true;
      manualControl = true;
      targetLockMode = false;
      targetPos = manualPosition;
      currentState = FIXATING;
      fixationPoint = manualPosition;
    }
  }
  if (server.hasArg("eyeManual")) {
    manualPosition = server.arg("eyeManual").toInt();
    manualPosition = constrain(manualPosition, EYE_RIGHT, EYE_LEFT);
    // If in manual control mode, update target immediately
    if (manualControl) {
      targetPos = manualPosition;
      fixationPoint = manualPosition;
    }
    // If in target lock mode, update target lock position
    else if (targetLockMode) {
      targetLockPosition = manualPosition;
    }
  }
  
  // Jaw controls
  if (server.hasArg("jawCmd")) {
    String jc = server.arg("jawCmd");
    if (jc == "open") {
      jawActive = true;
      jawTalking = false;
      jawYawning = false;
      jawChewing = false;
      jawManualControl = false;
      jawMode = "Open";
      jawTargetPos = JAW_OPEN;
    } else if (jc == "close") {
      jawActive = true;
      jawTalking = false;
      jawYawning = false;
      jawChewing = false;
      jawManualControl = false;
      jawMode = "Closed";
      jawTargetPos = JAW_CLOSED;
    } else if (jc == "talk") {
      jawActive = true;
      jawTalking = true;
      jawYawning = false;
      jawChewing = false;
      jawManualControl = false;
      jawMode = "Talking";
      talkingStartTime = millis();
      talkingDuration = 0; // Continuous until stopped
      // Initialize hand gestures
      handGesturingActive = true;
      nextHandGesture = millis() + 500; // Start gestures after 500ms
    } else if (jc == "stop") {
      jawTalking = false;
      jawYawning = false;
      jawChewing = false;
      jawMode = "Closed";
      jawTargetPos = JAW_CLOSED;
      handGesturingActive = false; // Stop hand gestures
    } else if (jc == "yawn") {
      jawActive = true;
      jawTalking = false;
      jawYawning = true;
      jawChewing = false;
      jawManualControl = false;
      jawMode = "Yawning";
      yawnStartTime = millis();
      nextJawAction = millis();
    } else if (jc == "chew") {
      jawActive = true;
      jawTalking = false;
      jawYawning = false;
      jawChewing = true;
      jawManualControl = false;
      jawMode = "Chewing";
      talkingSpeed = 30; // Slower for chewing
      // Initialize hand gestures
      handGesturingActive = true;
      nextHandGesture = millis() + 500; // Start gestures after 500ms
    } else if (jc == "manualOn") {
      jawManualControl = true;
      jawTalking = false;
    } else if (jc == "manualOff") {
      jawManualControl = false;
      jawTargetPos = JAW_CLOSED;
    }
  }
  if (server.hasArg("talkSpeed")) {
    talkingSpeed = server.arg("talkSpeed").toInt();
    talkingSpeed = constrain(talkingSpeed, 0, 100);
  }
  if (server.hasArg("jawManual")) {
    jawManualPosition = server.arg("jawManual").toInt();
    jawManualPosition = constrain(jawManualPosition, JAW_CLOSED, JAW_OPEN);
    if (jawManualControl) {
      jawTargetPos = jawManualPosition;
    }
  }
  
  // Hand controls
  if (server.hasArg("handCmd")) {
    String hc = server.arg("handCmd");
    hc.toLowerCase();
    
    // Forward hand command to ESP8266
    bool success = sendHandCommand(hc);
    
    if (!success) {
      server.send(500, "text/plain", "Hand command failed - ESP8266 not connected");
      return;
    }
  }
  
  server.send(200, "text/plain", "OK");
}

void handleStatus() {
  String json = "{\"pos\":" + String((int)currentPos) + ",\"state\":\"";
  if (!eyeActive) json += "Stopped";
  else if (targetLockMode && targetLockPosition == EYE_CENTER) json += "Auto";
  else if (targetLockMode) json += "Manual";
  else json += "Circumstances";
  json += "\",\"jawPos\":" + String((int)jawCurrentPos) + ",\"jawState\":\"";
  if (!jawActive) json += "Inactive";
  else if (jawYawning) json += "Yawning";
  else if (jawTalking || jawChewing) json += jawMode;
  else if (jawMode == "Serial") json += "Serial";
  else if (jawManualControl) json += "Manual";
  else json += jawMode;
  json += "\",\"handConnected\":" + String(handControllerConnected ? "true" : "false");
  json += ",\"serialActive\":" + String(serialControlActive ? "true" : "false");
  json += "}";
  server.send(200, "application/json", json);
}

// ================= SERIAL COMMAND PARSING =================

void checkSerialCommands() {
  while (Serial.available()) {
    char c = Serial.read();
    
    if (c == '\n' || c == '\r') {
      if (serialBuffer.length() > 0) {
        // #region agent log
        debugLog("checkSerialCommands:89", "Parsing serial command", "H1", "len=" + String(serialBuffer.length()));
        // #endregion
        parseSerialCommand(serialBuffer);
        serialBuffer = "";
      }
    } else {
      serialBuffer += c;
      // Prevent buffer overflow
      // #region agent log
      if (serialBuffer.length() >= 250) {
        debugLog("checkSerialCommands:97", "Buffer near overflow", "H1", "len=" + String(serialBuffer.length()));
      }
      // #endregion
      if (serialBuffer.length() > 256) {
        // #region agent log
        debugLog("checkSerialCommands:102", "Buffer overflow - clearing", "H1", "len=" + String(serialBuffer.length()));
        // #endregion
        serialBuffer = "";
      }
    }
  }
}

void parseSerialCommand(String command) {
  // Set serial control active
  serialControlActive = true;
  serialControlTimeout = millis();
  
  // Parse JSON
  StaticJsonDocument<256> doc;
  DeserializationError error = deserializeJson(doc, command);
  
  if (error) {
    sendSerialResponse("error", "Invalid JSON: " + String(error.c_str()));
    return;
  }
  
  if (!doc.containsKey("command")) {
    sendSerialResponse("error", "Missing 'command' field");
    return;
  }
  
  String cmd = doc["command"].as<String>();
  cmd.toUpperCase();
  
  // Execute command
  bool success = executeCommand(cmd);
  
  if (success) {
    sendSerialResponse("ok", cmd);
  } else {
    sendSerialResponse("error", "Unknown command: " + cmd);
  }
}

bool executeCommand(String cmd) {
  // HAND commands - forward to ESP8266
  if (cmd.startsWith("HAND:")) {
    String handCmd = cmd.substring(5);
    return sendHandCommand(handCmd);
  }
  
  // EYE commands
  else if (cmd.startsWith("EYE:")) {
    String eyeCmd = cmd.substring(4);
    return executeEyeCommand(eyeCmd);
  }
  
  // JAW commands
  else if (cmd.startsWith("JAW:")) {
    String jawCmd = cmd.substring(4);
    return executeJawCommand(jawCmd);
  }
  
  return false;
}

bool executeEyeCommand(String cmd) {
  cmd.toUpperCase();
  
  if (cmd == "AUTO") {
    eyeActive = true;
    manualControl = false;
    targetLockMode = true;
    targetLockPosition = EYE_CENTER;
    behaviorMode = "Normal";
    return true;
  }
  else if (cmd == "CIRCUMSTANCES") {
    eyeActive = true;
    manualControl = false;
    targetLockMode = false;
    behaviorMode = "Normal";
    return true;
  }
  else if (cmd.startsWith("MANUAL:")) {
    int pos = cmd.substring(7).toInt();
    pos = constrain(pos, EYE_RIGHT, EYE_LEFT);
    eyeActive = true;
    manualControl = false;
    targetLockMode = true;
    targetLockPosition = pos;
    manualPosition = pos;
    // Immediately set target for responsiveness
    targetPos = pos;
    currentState = FIXATING;
    fixationPoint = pos;
    return true;
  }
  
  return false;
}

bool executeJawCommand(String cmd) {
  cmd.toUpperCase();
  
  if (cmd == "OPEN") {
    jawActive = true;
    jawTalking = false;
    jawYawning = false;
    jawChewing = false;
    jawManualControl = false;
    jawMode = "Open";
    jawTargetPos = JAW_OPEN;
    return true;
  }
  else if (cmd == "CLOSE") {
    jawActive = true;
    jawTalking = false;
    jawYawning = false;
    jawChewing = false;
    jawManualControl = false;
    jawMode = "Closed";
    jawTargetPos = JAW_CLOSED;
    return true;
  }
  else if (cmd == "TALK") {
    jawActive = true;
    jawTalking = true;
    jawYawning = false;
    jawChewing = false;
    jawManualControl = false;
    jawMode = "Talking";
    talkingStartTime = millis();
    talkingDuration = 0;
    // Initialize hand gestures
    handGesturingActive = true;
    nextHandGesture = millis() + 500; // Start gestures after 500ms
    return true;
  }
  else if (cmd == "STOP") {
    jawTalking = false;
    jawYawning = false;
    jawChewing = false;
    jawMode = "Closed";
    jawTargetPos = JAW_CLOSED;
    handGesturingActive = false; // Stop hand gestures
    return true;
  }
  else if (cmd == "YAWN") {
    jawActive = true;
    jawTalking = false;
    jawYawning = true;
    jawChewing = false;
    jawManualControl = false;
    jawMode = "Yawning";
    yawnStartTime = millis();
    nextJawAction = millis();
    return true;
  }
  else if (cmd == "CHEW") {
    jawActive = true;
    jawTalking = false;
    jawYawning = false;
    jawChewing = true;
    jawManualControl = false;
    jawMode = "Chewing";
    talkingSpeed = 30;
    // Initialize hand gestures
    handGesturingActive = true;
    nextHandGesture = millis() + 500; // Start gestures after 500ms
    return true;
  }
  else if (cmd.startsWith("SET:")) {
    // Format: SET:<float> where float is 0.0 to 1.0 (openness)
    String valueStr = cmd.substring(4);
    float openness = valueStr.toFloat();

    // Clamp openness between 0.0 and 1.0
    openness = constrain(openness, 0.0, 1.0);

    // Convert openness to angle: angle = 20 + openness * 34
    float angle = JAW_CLOSED + openness * (JAW_OPEN - JAW_CLOSED);

    // Clamp final angle to 20..54
    angle = constrain(angle, JAW_CLOSED, JAW_OPEN);

    // Set jaw target position and override any automated behavior
    jawActive = true;
    jawTalking = false;
    jawYawning = false;
    jawChewing = false;
    jawManualControl = false; // Use a separate mode for serial control
    jawMode = "Serial";
    jawTargetPos = angle;
    handGesturingActive = false; // Stop hand gestures

    return true;
  }

  return false;
}

bool sendHandCommand(String cmd) {
  // Check for SET command first (before lowercasing)
  String cmdUpper = cmd;
  cmdUpper.toUpperCase();
  
  if (cmdUpper.startsWith("SET:")) {
    // Format: HAND:SET:index:90 or HAND:SET:thumb:135
    int colon1 = cmd.indexOf(':', 4);
    if (colon1 > 0) {
      String finger = cmd.substring(4, colon1);
      finger.toLowerCase();
      int value = cmd.substring(colon1 + 1).toInt();
      value = constrain(value, 0, 180);
      String endpoint = "/set?f=" + finger + "&v=" + String(value);
      
      return sendHTTPRequest(endpoint);
    } else {
      return false;
    }
  }
  
  cmd.toLowerCase();
  
  // Special handling for handshake - start shake sequence
  if (cmd == "handshake") {
    // Start shake sequence
    shakeSequenceActive = true;
    shakeState = SHAKE_OPENING;
    shakeStartTime = millis();
    shakeNextAction = millis();
    return true;
  }
  
  // Map command to ESP8266 endpoint
  String endpoint = "";
  
  if (cmd == "fist") endpoint = "/fist";
  else if (cmd == "open") endpoint = "/open";
  else if (cmd == "like" || cmd == "thumbsup") endpoint = "/like";
  else if (cmd == "thumbsdown") endpoint = "/thumbsdown";
  else if (cmd == "peace") endpoint = "/peace";
  else if (cmd == "ok") endpoint = "/ok";
  else if (cmd == "point") endpoint = "/point";
  else if (cmd == "pinch") endpoint = "/pinch";
  else if (cmd == "pinkyup") endpoint = "/pinkyup";
  else if (cmd == "pinkyringup") endpoint = "/pinkyringup";
  else if (cmd == "allfingersextended") endpoint = "/allfingersextended";
  else if (cmd == "allfingerscurled") endpoint = "/allfingerscurled";
  else if (cmd == "gimme") endpoint = "/gimme";
  else if (cmd == "spider") endpoint = "/spider";
  else if (cmd == "claw") endpoint = "/claw";
  else if (cmd == "iloveyou") endpoint = "/iloveyou";
  else if (cmd == "stop") endpoint = "/stop";
  else if (cmd == "swag") endpoint = "/swag";
  else if (cmd == "number1") endpoint = "/number1";
  else if (cmd == "number2") endpoint = "/number2";
  else if (cmd == "number3") endpoint = "/number3";
  else if (cmd == "number4") endpoint = "/number4";
  else if (cmd == "number5") endpoint = "/number5";
  else {
    return false;
  }
  
  // Send HTTP request to ESP8266
  return sendHTTPRequest(endpoint);
}

void sendSerialResponse(String status, String message) {
  StaticJsonDocument<128> doc;
  doc["status"] = status;
  doc["command"] = message;
  
  String response;
  serializeJson(doc, response);
  Serial.println(response);
}

void checkHandControllerConnection() {
  // Check ESP8266 connection via WiFi (MANDATORY)
  HTTPClient http;
  String url = "http://" + String(handControllerIP) + "/status";
  
  http.begin(url);
  http.setTimeout(2000); // 2 second timeout
  http.setReuse(true);
  
  int httpCode = http.GET();
  
  if (httpCode == 200) {
    handControllerConnected = true;
  } else {
    handControllerConnected = false;
    // #region agent log
    debugLog("checkHandControllerConnection", "ESP8266 not reachable via WiFi", "H3", "code=" + String(httpCode));
    // #endregion
  }
  
  http.end();
}

void updateShakeSequence() {
  unsigned long now = millis();
  
  // #region agent log
  debugLog("updateShakeSequence:1190", "Shake sequence update", "H4", "state=" + String(shakeState) + " active=" + String(shakeSequenceActive));
  // #endregion
  
  switch (shakeState) {
    case SHAKE_IDLE:
      break;
      
    case SHAKE_OPENING:
      // Open the hand fully
      if (now >= shakeNextAction) {
        // #region agent log
        debugLog("updateShakeSequence:1199", "Shake opening - sending open", "H4", "");
        // #endregion
        bool success = sendHandCommandDirect("open");
        // #region agent log
        if (!success) {
          debugLog("updateShakeSequence:1202", "Shake open command failed", "H4", "");
        }
        // #endregion
        shakeState = SHAKE_SHAKING;
        shakeNextAction = now + 500; // Wait 500ms for hand to open
      }
      break;
      
    case SHAKE_SHAKING:
      // Shake for a few seconds (3 seconds)
      if (now - shakeStartTime < 3000) {
        // Send handshake command repeatedly to create shaking effect
        if (now >= shakeNextAction) {
          sendHandCommandDirect("handshake");
          shakeNextAction = now + 200; // Shake every 200ms
        }
      } else {
        // Done shaking, move to reopening
        shakeState = SHAKE_REOPENING;
        shakeNextAction = now + 100;
      }
      break;
      
    case SHAKE_REOPENING:
      // Open again
      if (now >= shakeNextAction) {
        sendHandCommandDirect("open");
        shakeState = SHAKE_COMPLETE;
        shakeNextAction = now + 500; // Wait for hand to open
      }
      break;
      
    case SHAKE_COMPLETE:
      // Send success response via serial
      if (now >= shakeNextAction) {
        sendSerialResponse("ok", "HAND:HANDSHAKE");
        shakeSequenceActive = false;
        shakeState = SHAKE_IDLE;
      }
      break;
  }
}

bool sendHandCommandDirect(String cmd) {
  // Internal function to send hand command without triggering shake sequence
  cmd.toLowerCase();
  
  // Map command to ESP8266 endpoint
  String endpoint = "";
  
  if (cmd == "fist") endpoint = "/fist";
  else if (cmd == "open") endpoint = "/open";
  else if (cmd == "like" || cmd == "thumbsup") endpoint = "/like";
  else if (cmd == "thumbsdown") endpoint = "/thumbsdown";
  else if (cmd == "peace") endpoint = "/peace";
  else if (cmd == "ok") endpoint = "/ok";
  else if (cmd == "point") endpoint = "/point";
  else if (cmd == "pinch") endpoint = "/pinch";
  else if (cmd == "pinkyup") endpoint = "/pinkyup";
  else if (cmd == "pinkyringup") endpoint = "/pinkyringup";
  else if (cmd == "allfingersextended") endpoint = "/allfingersextended";
  else if (cmd == "allfingerscurled") endpoint = "/allfingerscurled";
  else if (cmd == "gimme") endpoint = "/gimme";
  else if (cmd == "spider") endpoint = "/spider";
  else if (cmd == "claw") endpoint = "/claw";
  else if (cmd == "iloveyou") endpoint = "/iloveyou";
  else if (cmd == "stop") endpoint = "/stop";
  else if (cmd == "swag") endpoint = "/swag";
  else if (cmd == "handshake") endpoint = "/handshake";
  else if (cmd == "number1") endpoint = "/number1";
  else if (cmd == "number2") endpoint = "/number2";
  else if (cmd == "number3") endpoint = "/number3";
  else if (cmd == "number4") endpoint = "/number4";
  else if (cmd == "number5") endpoint = "/number5";
  else {
    return false;
  }
  
  return sendHTTPRequest(endpoint);
}

// Helper function to send HTTP requests to ESP8266 via WiFi (MANDATORY)
bool sendHTTPRequest(String endpoint) {
  // Ensure WiFi is available (AP mode should always be active)
  if (WiFi.getMode() == WIFI_OFF) {
    debugLog("sendHTTPRequest", "WiFi not initialized", "H3", "");
    handControllerConnected = false;
    return false;
  }
  
  HTTPClient http;
  String url = "http://" + String(handControllerIP) + endpoint;
  
  // #region agent log
  debugLog("sendHTTPRequest", "Sending HTTP request via WiFi", "H3", "url=" + url);
  // #endregion
  
  http.begin(url);
  http.setTimeout(2000); // 2 second timeout for reliability
  http.setReuse(true); // Reuse connection for better performance
  
  int httpCode = http.GET();
  
  if (httpCode == 200) {
    handControllerConnected = true;
    http.end();
    return true;
  } else {
    // #region agent log
    debugLog("sendHTTPRequest", "HTTP request failed", "H3", "code=" + String(httpCode) + " endpoint=" + endpoint);
    // #endregion
    handControllerConnected = false;
    http.end();
    return false;
  }
}
