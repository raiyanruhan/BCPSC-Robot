#include <WiFi.h>
#include <WebServer.h>

// WiFi credentials
const char* ssid = "ESP32_Robot";
const char* password = "12345678";

WebServer server(80);

// Motor pins
#define R_RPWM 19
#define R_LPWM 21
#define L_RPWM 22
#define L_LPWM 23

int speedVal = 0; // -255 to 255
int steerVal = 0; // -100 to 100
String currentDir = "stop";

// Security system
unsigned long lastClientCheck = 0;
const unsigned long CLIENT_CHECK_INTERVAL = 500;
int connectedClients = 0;
bool motorsEnabled = false;

// --- Helper Functions ---
void setMotorSpeeds(int leftSpeed, int rightSpeed, bool forward) {
  if (!motorsEnabled) {
    analogWrite(L_RPWM, 0);
    analogWrite(L_LPWM, 0);
    analogWrite(R_RPWM, 0);
    analogWrite(R_LPWM, 0);
    return;
  }

  leftSpeed = constrain(leftSpeed, 0, 255);
  rightSpeed = constrain(rightSpeed, 0, 255);

  if (forward) {
    analogWrite(L_RPWM, leftSpeed);
    analogWrite(L_LPWM, 0);
    analogWrite(R_RPWM, 0);
    analogWrite(R_LPWM, rightSpeed);
  } else {
    analogWrite(L_RPWM, 0);
    analogWrite(L_LPWM, leftSpeed);
    analogWrite(R_RPWM, rightSpeed);
    analogWrite(R_LPWM, 0);
  }
}

void stopMotors() {
  analogWrite(R_RPWM, 0);
  analogWrite(R_LPWM, 0);
  analogWrite(L_RPWM, 0);
  analogWrite(L_LPWM, 0);
  currentDir = "stop";
  speedVal = 0;
  steerVal = 0;
}

// --- Driving Logic ---
void drive(int speed, int steer) {
  if (speed == 0) {
    stopMotors();
    return;
  }

  bool forward = speed > 0;
  int absSpeed = abs(speed);

  float leftFactor = 1.0, rightFactor = 1.0;
  if (steer > 0) leftFactor = 1.0 - (steer / 100.0);
  else if (steer < 0) rightFactor = 1.0 - (abs(steer) / 100.0);

  int leftSpeed = absSpeed * leftFactor;
  int rightSpeed = absSpeed * rightFactor;

  setMotorSpeeds(leftSpeed, rightSpeed, forward);
  currentDir = forward ? "forward" : "backward";
}

// --- Security ---
void checkConnectedClients() {
  connectedClients = WiFi.softAPgetStationNum();
  if (connectedClients == 0 && motorsEnabled) {
    motorsEnabled = false;
    stopMotors();
    Serial.println("SECURITY: No clients connected - Motors STOPPED");
  } else if (connectedClients > 0 && !motorsEnabled) {
    motorsEnabled = true;
    Serial.print("SECURITY: Client connected - Motors ENABLED (");
    Serial.print(connectedClients);
    Serial.println(" client(s))");
  }
}

// --- Web Page ---
void handleRoot() {
  String html = R"rawliteral(
<html>
<head>
<title>ESP32 Robot Dual Joystick</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
body{text-align:center;background:#f2f2f2;font-family:Arial;padding:20px;}
.security-status{background:#4CAF50;color:white;padding:10px;border-radius:5px;margin-bottom:20px;font-weight:bold;}
.container{display:flex;justify-content:center;align-items:center;gap:30px;flex-wrap:wrap;}
.joystick-wrapper{text-align:center;}
canvas{background:#ddd;border-radius:10px;touch-action:none;margin:10px;}
h2{color:#333;}h4{color:#666;margin:5px;}
.status{margin-top:20px;font-size:18px;color:#333;}
.emergency-btn{background:red;color:white;font-weight:bold;padding:15px 30px;border:none;border-radius:10px;font-size:18px;cursor:pointer;margin-top:20px;}
.emergency-btn:hover{background:#cc0000;}
</style>
</head>
<body>
<h2>ESP32 Robot Dual Joystick Control</h2>
<div class="security-status">🔒 Security System Active - Connection Verified</div>

<div class="container">
<div class="joystick-wrapper">
<h4>Speed Control</h4>
<canvas id="speedJoystick" width="200" height="300"></canvas>
</div>
<div class="joystick-wrapper">
<h4>Steering Control</h4>
<canvas id="steerJoystick" width="300" height="200"></canvas>
</div>
</div>

<button class="emergency-btn" onclick="emergencyStop()">EMERGENCY STOP</button>

<div class="status">
<h3>Speed: <span id="sp">0</span> | Steering: <span id="st">0</span></h3>
</div>

<script>
let currentSpeed=0,currentSteer=0,lastSend=0;

// Emergency stop
function emergencyStop(){
  currentSpeed=0;currentSteer=0;
  document.getElementById('sp').innerText=0;
  document.getElementById('st').innerText=0;
  fetch('/emergencystop');
}

// Joystick variables
const speedCanvas=document.getElementById('speedJoystick');
const steerCanvas=document.getElementById('steerJoystick');

const speedCtx=speedCanvas.getContext('2d');
const steerCtx=steerCanvas.getContext('2d');

const speedCenter={x:speedCanvas.width/2,y:speedCanvas.height/2};
const steerCenter={x:steerCanvas.width/2,y:steerCanvas.height/2};

const speedTrackHeight=250,speedKnobRadius=25;
const steerTrackWidth=250,steerKnobRadius=25;

let speedKnob={x:speedCenter.x,y:speedCenter.y};
let steerKnob={x:steerCenter.x,y:steerCenter.y};

let speedDragging=false,steerDragging=false;

// Draw functions
function drawSpeedJoystick(){
  speedCtx.clearRect(0,0,speedCanvas.width,speedCanvas.height);
  speedCtx.fillStyle="#ccc";
  speedCtx.fillRect(speedCenter.x-30,speedCenter.y-125,60,250);
  speedCtx.strokeStyle="#999"; speedCtx.lineWidth=2;
  speedCtx.beginPath();
  speedCtx.moveTo(speedCenter.x-40,speedCenter.y); speedCtx.lineTo(speedCenter.x+40,speedCenter.y);
  speedCtx.stroke();
  speedCtx.beginPath(); speedCtx.arc(speedKnob.x,speedKnob.y,speedKnobRadius,0,Math.PI*2);
  speedCtx.fillStyle="#4CAF50"; speedCtx.fill();
  speedCtx.strokeStyle="#333"; speedCtx.lineWidth=2; speedCtx.stroke();
}

function drawSteerJoystick(){
  steerCtx.clearRect(0,0,steerCanvas.width,steerCanvas.height);
  steerCtx.fillStyle="#ccc";
  steerCtx.fillRect(steerCenter.x-125,steerCenter.y-30,250,60);
  steerCtx.strokeStyle="#999"; steerCtx.lineWidth=2;
  steerCtx.beginPath();
  steerCtx.moveTo(steerCenter.x,steerCenter.y-40); steerCtx.lineTo(steerCenter.x,steerCenter.y+40);
  steerCtx.stroke();
  steerCtx.beginPath(); steerCtx.arc(steerKnob.x,steerKnob.y,steerKnobRadius,0,Math.PI*2);
  steerCtx.fillStyle="#2196F3"; steerCtx.fill();
  steerCtx.strokeStyle="#333"; steerCtx.lineWidth=2; steerCtx.stroke();
}

// Send joystick values
function sendControl(){
  document.getElementById('sp').innerText=currentSpeed;
  document.getElementById('st').innerText=currentSteer;
  const now=Date.now();
  if(now-lastSend>50){
    fetch(`/joystick?speed=${currentSpeed}&steer=${currentSteer}`);
    lastSend=now;
  }
}

// Speed joystick events
function moveSpeedKnob(e){
  const rect=speedCanvas.getBoundingClientRect();
  const y=e.clientY-rect.top;
  speedKnob.x=speedCenter.x;
  speedKnob.y=Math.max(speedCenter.y-125+speedKnobRadius,Math.min(y,speedCenter.y+125-speedKnobRadius));
  const dy=speedCenter.y-speedKnob.y;
  currentSpeed=Math.round((dy/125)*255);
  drawSpeedJoystick(); sendControl();
}
speedCanvas.addEventListener('pointerdown',e=>{speedDragging=true; moveSpeedKnob(e);});
speedCanvas.addEventListener('pointermove',e=>{if(speedDragging) moveSpeedKnob(e);});
speedCanvas.addEventListener('pointerup',e=>{speedDragging=false; speedKnob={x:speedCenter.x,y:speedCenter.y}; currentSpeed=0; drawSpeedJoystick(); sendControl();});
speedCanvas.addEventListener('pointerleave',e=>{speedDragging=false; speedKnob={x:speedCenter.x,y:speedCenter.y}; currentSpeed=0; drawSpeedJoystick(); sendControl();});

// Steering joystick events
function moveSteerKnob(e){
  const rect=steerCanvas.getBoundingClientRect();
  const x=e.clientX-rect.left;
  steerKnob.y=steerCenter.y;
  steerKnob.x=Math.max(steerCenter.x-125+steerKnobRadius,Math.min(x,steerCenter.x+125-steerKnobRadius));
  const dx=steerKnob.x-steerCenter.x;
  currentSteer=Math.round((dx/125)*100);
  drawSteerJoystick(); sendControl();
}
steerCanvas.addEventListener('pointerdown',e=>{steerDragging=true; moveSteerKnob(e);});
steerCanvas.addEventListener('pointermove',e=>{if(steerDragging) moveSteerKnob(e);});
steerCanvas.addEventListener('pointerup',e=>{steerDragging=false; steerKnob={x:steerCenter.x,y:steerCenter.y}; currentSteer=0; drawSteerJoystick(); sendControl();});
steerCanvas.addEventListener('pointerleave',e=>{steerDragging=false; steerKnob={x:steerCenter.x,y:steerCenter.y}; currentSteer=0; drawSteerJoystick(); sendControl();});

// Initial draw
drawSpeedJoystick();
drawSteerJoystick();
</script>
</body>
</html>
)rawliteral";

  server.send(200,"text/html",html);
}

// --- Setup ---
void setup() {
  Serial.begin(115200);

  pinMode(R_RPWM, OUTPUT);
  pinMode(R_LPWM, OUTPUT);
  pinMode(L_RPWM, OUTPUT);
  pinMode(L_LPWM, OUTPUT);
  stopMotors();

  WiFi.softAP(ssid,password);
  Serial.println("WiFi AP started");
  Serial.print("IP: "); Serial.println(WiFi.softAPIP());
  Serial.println("SECURITY: Waiting for client connection...");

  server.on("/", handleRoot);

  server.on("/joystick",[](){
    if(server.hasArg("speed") && server.hasArg("steer")){
      int s=constrain(server.arg("speed").toInt(),-255,255);
      int t=constrain(server.arg("steer").toInt(),-100,100);
      speedVal=s; steerVal=t;
      drive(speedVal,steerVal);
    }
    server.send(200,"text/plain","OK");
  });

  server.on("/emergencystop",[](){
    stopMotors();
    server.send(200,"text/plain","EMERGENCY STOP ACTIVATED");
    Serial.println("EMERGENCY STOP triggered!");
  });

  server.on("/status",[](){
    String json="{\"clients\":"+String(connectedClients)+",\"enabled\":"+String(motorsEnabled)+"}";
    server.send(200,"application/json",json);
  });

  server.begin();
  Serial.println("Server started");
}

// --- Loop ---
void loop(){
  server.handleClient();

  if(millis()-lastClientCheck>=CLIENT_CHECK_INTERVAL){
    lastClientCheck=millis();
    checkConnectedClients();
  }

  if(Serial.available()){
    String cmd=Serial.readStringUntil('\n');
    cmd.trim(); cmd.toLowerCase();

    if(cmd=="status"){
      Serial.print("Connected clients: "); Serial.print(connectedClients);
      Serial.print(" | Motors: "); Serial.println(motorsEnabled?"ENABLED":"DISABLED");
    } else if(!motorsEnabled){
      Serial.println("WARNING: No clients connected - Motors disabled for safety!");
    } else if(cmd=="stop") stopMotors();
    else if(cmd.startsWith("speed ")){
      int val=constrain(cmd.substring(6).toInt(),-255,255);
      speedVal=val; drive(speedVal,steerVal);
    } else if(cmd.startsWith("steer ")){
      int val=constrain(cmd.substring(6).toInt(),-100,100);
      steerVal=val; drive(speedVal,steerVal);
    } else if(cmd.startsWith("move ")){
      int comma=cmd.indexOf(',');
      if(comma!=-1){
        int s=constrain(cmd.substring(5,comma).toInt(),-255,255);
        int t=constrain(cmd.substring(comma+1).toInt(),-100,100);
        speedVal=s; steerVal=t; drive(speedVal,steerVal);
      }
    } else Serial.println("Commands: stop | speed <val> | steer <val> | move <speed,steer> | status");
  }
}