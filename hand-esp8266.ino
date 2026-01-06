#include <ESP8266WiFi.h>
#include <ESP8266WebServer.h>
#include <Servo.h>

// ================= WIFI =================
const char* ssid = "InMoov-Control";
const char* password = "InMoov2024";

ESP8266WebServer server(80);

// ================= SERVOS =================
Servo Thumb, Index, Middle, Ring, Little;

// Safe pins
#define THUMB_PIN   D1
#define INDEX_PIN   D7
#define MIDDLE_PIN  D3
#define RING_PIN    D4
#define LITTLE_PIN  D8

// ===== Calibrated degrees (from hand.txt) =====
#define THUMB_OPEN   26
#define THUMB_FIST   135

#define INDEX_OPEN   180
#define INDEX_FIST   0

#define MIDDLE_OPEN  168
#define MIDDLE_FIST  40

#define RING_OPEN    159
#define RING_FIST    32

#define LITTLE_OPEN  0
#define LITTLE_FIST  150

// Intermediate positions for complex gestures
#define THUMB_MID    ((THUMB_OPEN + THUMB_FIST) / 2)
#define INDEX_MID    ((INDEX_OPEN + INDEX_FIST) / 2)
#define MIDDLE_MID   ((MIDDLE_OPEN + MIDDLE_FIST) / 2)
#define RING_MID     ((RING_OPEN + RING_FIST) / 2)
#define LITTLE_MID   ((LITTLE_OPEN + LITTLE_FIST) / 2)

// ================= BASIC GESTURES =================

// 1. Fist - All fingers curled into the palm
void fist() {
  Thumb.write(THUMB_FIST);
  Index.write(INDEX_FIST);
  Middle.write(MIDDLE_FIST);
  Ring.write(RING_FIST);
  Little.write(LITTLE_FIST);
}

// 2. Open Hand - All fingers extended straight
void openHand() {
  Thumb.write(THUMB_OPEN);
  Index.write(INDEX_OPEN);
  Middle.write(MIDDLE_OPEN);
  Ring.write(RING_OPEN);
  Little.write(LITTLE_OPEN);
}

// 3. Thumbs Up - Only thumb extended upward; other fingers curled
void thumbsUp() {
  Thumb.write(THUMB_OPEN);
  Index.write(INDEX_FIST);
  Middle.write(MIDDLE_FIST);
  Ring.write(RING_FIST);
  Little.write(LITTLE_FIST);
}

// 4. Thumbs Down - Only thumb extended downward; other fingers curled
void thumbsDown() {
  Thumb.write(THUMB_FIST);
  Index.write(INDEX_FIST);
  Middle.write(MIDDLE_FIST);
  Ring.write(RING_FIST);
  Little.write(LITTLE_FIST);
}

// 5. Peace Sign (V Sign) - Index and middle fingers extended; others curled
void peaceSign() {
  Thumb.write(THUMB_FIST);
  Index.write(INDEX_OPEN);
  Middle.write(MIDDLE_OPEN);
  Ring.write(RING_FIST);
  Little.write(LITTLE_FIST);
}

// 6. OK Sign - Thumb and index finger forming a circle; other fingers extended
void okSign() {
  Thumb.write(THUMB_MID);
  Index.write(INDEX_MID);
  Middle.write(MIDDLE_OPEN);
  Ring.write(RING_OPEN);
  Little.write(LITTLE_OPEN);
}

// 7. Pointing - Only index finger extended; others curled
void pointing() {
  Thumb.write(THUMB_FIST);
  Index.write(INDEX_OPEN);
  Middle.write(MIDDLE_FIST);
  Ring.write(RING_FIST);
  Little.write(LITTLE_FIST);
}

// 8. Pinching - Thumb and index finger touching; others curled
void pinching() {
  Thumb.write(THUMB_MID);
  Index.write(INDEX_MID);
  Middle.write(MIDDLE_FIST);
  Ring.write(RING_FIST);
  Little.write(LITTLE_FIST);
}

// 9. Pinky Up - Only pinky finger extended; others curled
void pinkyUp() {
  Thumb.write(THUMB_FIST);
  Index.write(INDEX_FIST);
  Middle.write(MIDDLE_FIST);
  Ring.write(RING_FIST);
  Little.write(LITTLE_OPEN);
}

// 10. Pinky and Ring Finger Up - Pinky and ring fingers extended; others curled
void pinkyRingUp() {
  Thumb.write(THUMB_FIST);
  Index.write(INDEX_FIST);
  Middle.write(MIDDLE_FIST);
  Ring.write(RING_OPEN);
  Little.write(LITTLE_OPEN);
}

// 11. All Fingers Extended - Same as open hand
void allFingersExtended() {
  openHand();
}

// 12. All Fingers Curled - Same as fist
void allFingersCurled() {
  fist();
}

// ================= COMPLEX GESTURES =================

// Pinch - Thumb touching index finger (similar to pinching)
void pinch() {
  Thumb.write(THUMB_MID);
  Index.write(INDEX_MID);
  Middle.write(MIDDLE_FIST);
  Ring.write(RING_FIST);
  Little.write(LITTLE_FIST);
}

// Gimme - All fingers extended except thumb, which is curled inward
void gimme() {
  Thumb.write(THUMB_FIST);
  Index.write(INDEX_OPEN);
  Middle.write(MIDDLE_OPEN);
  Ring.write(RING_OPEN);
  Little.write(LITTLE_OPEN);
}

// Spider - All fingers extended and spread apart (same as open)
void spider() {
  openHand();
}

// Claw - Fingers curled with fingertips facing downward (same as fist)
void claw() {
  fist();
}

// ================= SIGN LANGUAGE / EXPRESSIVE GESTURES =================

// I Love You (ASL) - Thumb, index finger, pinky extended; middle and ring fingers curled
void iLoveYou() {
  Thumb.write(THUMB_OPEN);
  Index.write(INDEX_OPEN);
  Middle.write(MIDDLE_FIST);
  Ring.write(RING_FIST);
  Little.write(LITTLE_OPEN);
}

// Stop - Open palm facing outward (same as open hand)
void stopGesture() {
  openHand();
}

// ================= LEGACY GESTURES (for backward compatibility) =================

// Like (same as thumbs up)
void likeGesture() {
  thumbsUp();
}

// Peace (same as peace sign)
void peaceGesture() {
  peaceSign();
}

// Swag - Thumb and index open, middle and ring fisted, pinky open
void swagGesture() {
  Thumb.write(THUMB_OPEN);
  Index.write(INDEX_OPEN);
  Middle.write(MIDDLE_FIST);
  Ring.write(RING_FIST);
  Little.write(LITTLE_OPEN);
}

// Handshake (half fist)
void handshakeGesture() {
  Thumb.write(THUMB_MID);
  Index.write(INDEX_MID);
  Middle.write(MIDDLE_MID);
  Ring.write(RING_MID);
  Little.write(LITTLE_MID);
}

// ================= NUMBER GESTURES =================

// Number 1 - Only index finger extended
void number1() {
  pointing();
}

// Number 2 - Index and middle extended
void number2() {
  Thumb.write(THUMB_FIST);
  Index.write(INDEX_OPEN);
  Middle.write(MIDDLE_OPEN);
  Ring.write(RING_FIST);
  Little.write(LITTLE_FIST);
}

// Number 3 - Index, middle, ring extended
void number3() {
  Thumb.write(THUMB_FIST);
  Index.write(INDEX_OPEN);
  Middle.write(MIDDLE_OPEN);
  Ring.write(RING_OPEN);
  Little.write(LITTLE_FIST);
}

// Number 4 - Index, middle, ring, pinky extended
void number4() {
  Thumb.write(THUMB_FIST);
  Index.write(INDEX_OPEN);
  Middle.write(MIDDLE_OPEN);
  Ring.write(RING_OPEN);
  Little.write(LITTLE_OPEN);
}

// Number 5 - All fingers extended
void number5() {
  openHand();
}

// ================= API ROUTES =================
void setup() {
  Serial.begin(115200);

  // Configure static IP for ESP8266
  IPAddress localIP(192, 168, 4, 2);
  IPAddress gateway(192, 168, 4, 1);
  IPAddress subnet(255, 255, 255, 0);
  
  WiFi.config(localIP, gateway, subnet);
  
  Serial.print("Connecting to ");
  Serial.println(ssid);
  
  WiFi.begin(ssid, password);
  
  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 30) {
    delay(500);
    Serial.print(".");
    attempts++;
  }
  
  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\nWiFi connected!");
    Serial.print("IP address: ");
    Serial.println(WiFi.localIP());
  } else {
    Serial.println("\nWiFi connection failed!");
    // #region agent log
    Serial.println("{\"timestamp\":" + String(millis()) + ",\"location\":\"setup:289\",\"message\":\"WiFi connection failed\",\"hypothesisId\":\"H7\",\"data\":\"attempts=30\",\"sessionId\":\"debug-session\"}");
    // #endregion
  }

  // #region agent log
  Serial.println("{\"timestamp\":" + String(millis()) + ",\"location\":\"setup:292\",\"message\":\"Attaching servos\",\"hypothesisId\":\"H8\",\"data\":\"\",\"sessionId\":\"debug-session\"}");
  // #endregion
  
  Thumb.attach(THUMB_PIN, 500, 2500);
  Index.attach(INDEX_PIN, 500, 2500);
  Middle.attach(MIDDLE_PIN, 500, 2500);
  Ring.attach(RING_PIN, 500, 2500);
  Little.attach(LITTLE_PIN, 500, 2500);

  openHand();

  // Basic gestures
  server.on("/fist", [](){ fist(); server.send(200,"text/plain","OK"); });
  server.on("/open", [](){ openHand(); server.send(200,"text/plain","OK"); });
  server.on("/thumbsup", [](){ thumbsUp(); server.send(200,"text/plain","OK"); });
  server.on("/thumbsdown", [](){ thumbsDown(); server.send(200,"text/plain","OK"); });
  server.on("/peace", [](){ peaceSign(); server.send(200,"text/plain","OK"); });
  server.on("/ok", [](){ okSign(); server.send(200,"text/plain","OK"); });
  server.on("/point", [](){ pointing(); server.send(200,"text/plain","OK"); });
  server.on("/pinch", [](){ pinching(); server.send(200,"text/plain","OK"); });
  server.on("/pinkyup", [](){ pinkyUp(); server.send(200,"text/plain","OK"); });
  server.on("/pinkyringup", [](){ pinkyRingUp(); server.send(200,"text/plain","OK"); });
  server.on("/allfingersextended", [](){ allFingersExtended(); server.send(200,"text/plain","OK"); });
  server.on("/allfingerscurled", [](){ allFingersCurled(); server.send(200,"text/plain","OK"); });

  // Complex gestures
  server.on("/gimme", [](){ gimme(); server.send(200,"text/plain","OK"); });
  server.on("/spider", [](){ spider(); server.send(200,"text/plain","OK"); });
  server.on("/claw", [](){ claw(); server.send(200,"text/plain","OK"); });

  // Sign language / expressive gestures
  server.on("/iloveyou", [](){ iLoveYou(); server.send(200,"text/plain","OK"); });
  server.on("/stop", [](){ stopGesture(); server.send(200,"text/plain","OK"); });

  // Legacy gestures (backward compatibility)
  server.on("/like", [](){ likeGesture(); server.send(200,"text/plain","OK"); });
  server.on("/swag", [](){ swagGesture(); server.send(200,"text/plain","OK"); });
  server.on("/handshake", [](){ handshakeGesture(); server.send(200,"text/plain","OK"); });

  // Number gestures
  server.on("/number1", [](){ number1(); server.send(200,"text/plain","OK"); });
  server.on("/number2", [](){ number2(); server.send(200,"text/plain","OK"); });
  server.on("/number3", [](){ number3(); server.send(200,"text/plain","OK"); });
  server.on("/number4", [](){ number4(); server.send(200,"text/plain","OK"); });
  server.on("/number5", [](){ number5(); server.send(200,"text/plain","OK"); });

  // Individual finger control API
  server.on("/set", [](){
    String f = server.arg("f");
    int v = constrain(server.arg("v").toInt(),0,180);
    // #region agent log
    Serial.println("{\"timestamp\":" + String(millis()) + ",\"location\":\"setup:336\",\"message\":\"Setting finger\",\"hypothesisId\":\"H8\",\"data\":\"finger=" + f + " value=" + String(v) + "\",\"sessionId\":\"debug-session\"}");
    // #endregion
    if(f=="thumb") Thumb.write(v);
    else if(f=="index") Index.write(v);
    else if(f=="middle") Middle.write(v);
    else if(f=="ring") Ring.write(v);
    else if(f=="little") Little.write(v);
    else {
      // #region agent log
      Serial.println("{\"timestamp\":" + String(millis()) + ",\"location\":\"setup:343\",\"message\":\"Unknown finger\",\"hypothesisId\":\"H8\",\"data\":\"finger=" + f + "\",\"sessionId\":\"debug-session\"}");
      // #endregion
    }
    server.send(200,"text/plain","OK");
  });

  // Health check endpoint
  server.on("/status", [](){
    server.send(200,"application/json","{\"status\":\"ok\",\"ip\":\"" + WiFi.localIP().toString() + "\"}");
  });

  server.begin();
  Serial.println("Hand controller API ready");
}

void loop() {
  server.handleClient();
}
