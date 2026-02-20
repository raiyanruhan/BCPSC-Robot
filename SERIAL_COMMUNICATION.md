# Serial Communication Documentation

## Overview

The InMoov robot control system uses USB Serial communication between the Raspberry Pi (robot brain) and the ESP32 (master controller). The ESP32 acts as a bridge, forwarding hand commands to the ESP8266 via WiFi while directly controlling the eye and jaw servos.

## Architecture

```
Raspberry Pi (Brain)
    |
    | USB Serial (115200 baud)
    v
ESP32 (Master Controller)
    |
    | Direct Control
    +--> Eye Servo (Pin 18)
    +--> Jaw Servo (Pin 19)
    |
    | WiFi HTTP (192.168.4.2)
    v
ESP8266 (Hand Controller)
    |
    +--> Finger Servos (5 servos)
```

## Connection Setup

### Hardware Connection

1. Connect Raspberry Pi to ESP32 via USB cable
2. Ensure ESP32 is powered and running
3. ESP32 will create WiFi AP: `InMoov-Control` (IP: 192.168.4.1)
4. ESP8266 connects to ESP32's AP (IP: 192.168.4.2)

### Software Setup

#### Raspberry Pi (Python Example)

```python
import serial
import json
import time

# Open serial connection
ser = serial.Serial('/dev/ttyUSB0', 115200, timeout=1)
time.sleep(2)  # Wait for ESP32 to initialize

def send_command(command):
    """Send a JSON command to ESP32"""
    cmd = {"command": command}
    ser.write(json.dumps(cmd).encode() + b'\n')
    
    # Wait for response
    response = ser.readline().decode().strip()
    if response:
        return json.loads(response)
    return None

# Example usage
response = send_command("HAND:FIST")
print(response)  # {"status": "ok", "command": "HAND:FIST"}
```

#### Raspberry Pi (Node.js Example)

```javascript
const SerialPort = require('serialport');
const Readline = require('@serialport/parser-readline');

const port = new SerialPort('/dev/ttyUSB0', { baudRate: 115200 });
const parser = port.pipe(new Readline({ delimiter: '\n' }));

function sendCommand(command) {
    const cmd = JSON.stringify({ command: command }) + '\n';
    port.write(cmd);
}

parser.on('data', (data) => {
    try {
        const response = JSON.parse(data.toString());
        console.log('Response:', response);
    } catch (e) {
        console.log('Raw:', data.toString());
    }
});

// Example usage
sendCommand("HAND:OPEN");
```

## Command Format

### JSON Structure

All commands must be sent as JSON objects with a `command` field:

```json
{"command":"HAND:FIST"}
```

### Command Categories

Commands are organized into three categories:
- **HAND:** - Hand/finger control (forwarded to ESP8266)
- **EYE:** - Eye servo control (direct ESP32 control)
- **JAW:** - Jaw servo control (direct ESP32 control)

## Hand Commands

Hand commands are forwarded to the ESP8266 hand controller via WiFi HTTP.

### Basic Gestures

| Command | Description |
|---------|-------------|
| `HAND:FIST` | All fingers curled into palm |
| `HAND:OPEN` | All fingers extended straight |
| `HAND:LIKE` | Thumbs up gesture |
| `HAND:THUMBSUP` | Thumbs up (alias for LIKE) |
| `HAND:THUMBSDOWN` | Thumbs down gesture |
| `HAND:PEACE` | Peace sign (V sign) |
| `HAND:OK` | OK sign (thumb and index circle) |
| `HAND:POINT` | Pointing gesture (index finger only) |
| `HAND:PINCH` | Pinching gesture |
| `HAND:PINKYUP` | Pinky finger up |
| `HAND:PINKYRINGUP` | Pinky and ring fingers up |
| `HAND:ALLFINGERSEXTENDED` | All fingers extended |
| `HAND:ALLFINGERSCURLED` | All fingers curled (fist) |

### Complex Gestures

| Command | Description |
|---------|-------------|
| `HAND:GIMME` | All fingers extended except thumb |
| `HAND:SPIDER` | All fingers extended and spread |
| `HAND:CLAW` | Fingers curled downward |
| `HAND:ILOVEYOU` | ASL "I Love You" gesture |
| `HAND:STOP` | Open palm (stop gesture) |
| `HAND:SWAG` | Swag gesture |
| `HAND:HANDSHAKE` | Handshake position (half fist) |

### Number Gestures

| Command | Description |
|---------|-------------|
| `HAND:NUMBER1` | Show number 1 |
| `HAND:NUMBER2` | Show number 2 |
| `HAND:NUMBER3` | Show number 3 |
| `HAND:NUMBER4` | Show number 4 |
| `HAND:NUMBER5` | Show number 5 |

### Individual Finger Control

Control individual fingers with the SET command:

**Format:** `HAND:SET:<finger>:<angle>`

- `<finger>`: `thumb`, `index`, `middle`, `ring`, `little`
- `<angle>`: 0-180 degrees

**Examples:**
```json
{"command":"HAND:SET:index:90"}
{"command":"HAND:SET:thumb:135"}
{"command":"HAND:SET:middle:40"}
```

## Eye Commands

Eye commands control the eye servo directly on the ESP32.

### Eye Control Modes

| Command | Description |
|---------|-------------|
| `EYE:AUTO` | Auto mode - targets middle (90°) and moves naturally with drift |
| `EYE:CIRCUMSTANCES` | Natural scanning mode - looks around naturally without fixed target |
| `EYE:MANUAL:<angle>` | Manual mode - locks eye to specific angle with natural drift |

**Angle Reference:**
- `0°` = Full Right
- `90°` = Middle (center)
- `180°` = Full Left

**Examples:**
```json
{"command":"EYE:AUTO"}
{"command":"EYE:CIRCUMSTANCES"}
{"command":"EYE:MANUAL:45"}
{"command":"EYE:MANUAL:135"}
```

## Jaw Commands

Jaw commands control the jaw servo directly on the ESP32.

### Basic Jaw Control

| Command | Description |
|---------|-------------|
| `JAW:OPEN` | Open mouth fully (180°) |
| `JAW:CLOSE` | Close mouth (0°) |
| `JAW:TALK` | Start talking animation (continuous mouth movements) |
| `JAW:STOP` | Stop talking and close mouth |
| `JAW:YAWN` | Perform yawning animation (4 seconds) |
| `JAW:CHEW` | Start chewing animation (slower rhythmic movements) |

**Examples:**
```json
{"command":"JAW:OPEN"}
{"command":"JAW:CLOSE"}
{"command":"JAW:TALK"}
{"command":"JAW:STOP"}
{"command":"JAW:YAWN"}
{"command":"JAW:CHEW"}
```

## Response Format

### Success Response

When a command is successfully executed:

```json
{"status":"ok","command":"HAND:FIST"}
```

### Error Response

When a command fails or is invalid:

```json
{"status":"error","command":"Invalid JSON: ..."}
```

or

```json
{"status":"error","command":"Unknown command: HAND:INVALID"}
```

## Command Priority

The ESP32 enforces command priority:

1. **Raspberry Pi (USB Serial)** - Highest priority
2. **Web UI (Human control)** - Lower priority
3. **Fallback / manual testing**

When a serial command is received:
- Serial control flag is activated for 100ms
- Web UI commands are ignored during this period
- This prevents conflicting commands

## Error Handling

### Common Errors

1. **Invalid JSON Format**
   ```json
   {"status":"error","command":"Invalid JSON: ..."}
   ```
   - Solution: Ensure valid JSON syntax with `{"command":"..."}`

2. **Missing Command Field**
   ```json
   {"status":"error","command":"Missing 'command' field"}
   ```
   - Solution: Include `command` field in JSON

3. **Unknown Command**
   ```json
   {"status":"error","command":"Unknown command: HAND:INVALID"}
   ```
   - Solution: Check command spelling and format

4. **ESP8266 Connection Failed**
   - Hand commands may fail if ESP8266 is not connected
   - ESP32 checks connection status every 5 seconds
   - Check ESP8266 is connected to `InMoov-Control` AP

## Complete Examples

### Python Example Script

```python
import serial
import json
import time

class InMoovController:
    def __init__(self, port='/dev/ttyUSB0', baud=115200):
        self.ser = serial.Serial(port, baud, timeout=1)
        time.sleep(2)  # Wait for initialization
    
    def send(self, command):
        """Send command and return response"""
        cmd = {"command": command}
        self.ser.write(json.dumps(cmd).encode() + b'\n')
        
        response = self.ser.readline().decode().strip()
        if response:
            try:
                return json.loads(response)
            except:
                return {"raw": response}
        return None
    
    def hand_fist(self):
        return self.send("HAND:FIST")
    
    def hand_open(self):
        return self.send("HAND:OPEN")
    
    def hand_like(self):
        return self.send("HAND:LIKE")
    
    def eye_auto(self):
        return self.send("EYE:AUTO")
    
    def eye_manual(self, angle):
        return self.send(f"EYE:MANUAL:{angle}")
    
    def jaw_talk(self):
        return self.send("JAW:TALK")
    
    def jaw_stop(self):
        return self.send("JAW:STOP")
    
    def close(self):
        self.ser.close()

# Usage
controller = InMoovController()

# Hand gestures
controller.hand_open()
time.sleep(1)
controller.hand_fist()
time.sleep(1)
controller.hand_like()

# Eye control
controller.eye_auto()
time.sleep(2)
controller.eye_manual(45)  # Look right
time.sleep(2)
controller.eye_manual(135)  # Look left

# Jaw control
controller.jaw_talk()
time.sleep(5)
controller.jaw_stop()

controller.close()
```

### Sequence Example: Greeting

```python
# Greeting sequence
controller.send("HAND:OPEN")      # Open hand
time.sleep(0.5)
controller.send("HAND:HANDSHAKE")  # Handshake position
time.sleep(1)
controller.send("EYE:AUTO")        # Look naturally
time.sleep(0.5)
controller.send("JAW:TALK")        # Start talking
time.sleep(3)
controller.send("JAW:STOP")        # Stop talking
controller.send("HAND:LIKE")       # Thumbs up
```

## Technical Specifications

### Serial Settings

- **Baud Rate:** 115200
- **Data Bits:** 8
- **Stop Bits:** 1
- **Parity:** None
- **Flow Control:** None

### Command Format

- **Encoding:** UTF-8
- **Line Ending:** `\n` (newline)
- **Max Command Length:** 256 characters
- **Response Timeout:** 1 second (for hand commands via HTTP)

### ESP32 Serial Interface

- **Port:** USB Serial (typically `/dev/ttyUSB0` on Linux, `COMx` on Windows)
- **Buffer Size:** 256 bytes
- **Command Processing:** Immediate (non-blocking)

## Troubleshooting

### ESP32 Not Responding

1. Check USB connection
2. Verify baud rate is 115200
3. Check ESP32 Serial Monitor for errors
4. Ensure ESP32 is powered and running

### Hand Commands Not Working

1. Verify ESP8266 is connected to `InMoov-Control` AP
2. Check ESP8266 IP is `192.168.4.2`
3. Test ESP8266 directly via HTTP: `http://192.168.4.2/status`
4. Check ESP32 Serial Monitor for HTTP errors

### Commands Timing Out

1. Increase serial timeout in your code
2. Check for buffer overflow (commands too long)
3. Verify JSON format is correct
4. Check ESP32 Serial Monitor for parsing errors

### Web UI Conflicts

- Serial commands have priority over web UI
- If web UI is not responding, check if serial is active
- Serial control flag resets after 100ms of inactivity

## Status Monitoring

### Check ESP8266 Connection

The ESP32 periodically checks ESP8266 connection status. You can query it via the web UI status endpoint:

```
GET http://192.168.4.1/status
```

Response includes:
```json
{
  "pos": 90,
  "state": "Auto",
  "jawPos": 0,
  "jawState": "Closed",
  "handConnected": true,
  "serialActive": false
}
```

## Best Practices

1. **Always wait for responses** before sending next command
2. **Use appropriate delays** between commands (especially for servos)
3. **Handle errors gracefully** - check response status
4. **Close serial connection** properly when done
5. **Use try-catch blocks** for JSON parsing
6. **Log commands and responses** for debugging

## Command Reference Quick Sheet

```
HAND Commands:
  FIST, OPEN, LIKE, THUMBSUP, THUMBSDOWN, PEACE, OK, POINT, PINCH
  PINKYUP, PINKYRINGUP, ALLFINGERSEXTENDED, ALLFINGERSCURLED
  GIMME, SPIDER, CLAW, ILOVEYOU, STOP, SWAG, HANDSHAKE
  NUMBER1, NUMBER2, NUMBER3, NUMBER4, NUMBER5
  SET:<finger>:<angle>

EYE Commands:
  AUTO, CIRCUMSTANCES, MANUAL:<angle>

JAW Commands:
  OPEN, CLOSE, TALK, STOP, YAWN, CHEW
```

## Support

For issues or questions:
1. Check ESP32 Serial Monitor for error messages
2. Verify all connections (USB, WiFi)
3. Test commands individually
4. Check ESP8266 connection status via web UI

---

**Last Updated:** Implementation complete
**Version:** 1.0













