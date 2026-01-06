# InMoov Robot – Final Control Architecture

## Overview

This document describes the **final, intended architecture** for controlling an InMoov humanoid robot using:

- Raspberry Pi (robot brain)
- ESP32 (master controller)
- ESP8266 (hand controller)

The goal is to build a **stable, modular, scalable system** that supports:
- AI control
- Manual control
- Calibration & testing
- Network independence
- No frequent reflashing

---

## Design Goals

- Single point of control for the robot
- Clear separation of responsibilities
- No hard-coded IP dependencies for the user
- Ability to change Wi-Fi without re-uploading firmware
- Allow both AI (Pi) and humans to control the robot safely
- Stable servo control without Wi-Fi interference

---

## Final Architecture

```

Raspberry Pi (Brain)
|
|  USB Serial (primary, stable)
v
ESP32 (Master Controller)
|
|  Wi-Fi (internal, secured AP)
v
ESP8266 (Hand Controller)

```

---

## Component Responsibilities

### 1. Raspberry Pi — Robot Brain

**Role:** High-level decision maker

Responsibilities:
- AI / LLM logic
- Vision and audio processing
- Face tracking
- Behavior planning

Characteristics:
- Does NOT control servos directly
- Does NOT talk to ESP8266
- Talks ONLY to ESP32 via **USB serial**
- Sends simple, human-readable commands

Example commands:
```

HAND:FIST
HAND:LIKE
HEAD:YAW:90
HEAD:PITCH:30

```

---

### 2. ESP32 — Master Controller & Gateway

**Role:** Central robot controller

Responsibilities:
- Controls head servos directly
- Routes hand commands to ESP8266
- Hosts the main Web UI
- Manages Wi-Fi
- Acts as a bridge between Pi, ESP8266, and humans

#### Wi-Fi Behavior (Critical)

ESP32 always operates in **AP mode**, and optionally in **STA mode**.

##### Access Point (always ON)
- SSID: `InMoov-Control`
- Secured with WPA2
- IP: `192.168.4.1`
- Used for:
  - Manual control
  - Calibration
  - Testing
  - Wi-Fi configuration
  - Emergency access

##### Station Mode (optional)
- Connects to home / lab / hotspot Wi-Fi
- Used for:
  - External access
  - Raspberry Pi networking
  - Internet-based features

Wi-Fi credentials are:
- Entered via a web configuration page
- Saved in flash (NVS / Preferences)
- Changeable without reflashing firmware

---

### 3. ESP8266 — Hand Controller

**Role:** Dedicated actuator controller

Responsibilities:
- Controls finger servos only
- Executes commands received from ESP32

Characteristics:
- Connects ONLY to ESP32’s Wi-Fi AP
- Uses secured Wi-Fi
- Fixed IP (typically `192.168.4.2`)
- No Web UI
- No direct human access
- No router / internet dependency

This keeps the hand:
- Stable
- Simple
- Isolated from heavy logic
- Easy to replace or debug

---

## Communication Paths

| From | To | Method | Purpose |
|---|---|---|---|
| Raspberry Pi | ESP32 | USB Serial | Primary control |
| ESP32 | ESP8266 | Wi-Fi (HTTP / API) | Hand control |
| Human (Phone / Laptop) | ESP32 | Wi-Fi (Web UI) | Manual control & setup |

---

## Control Priority

ESP32 enforces command priority:

1. **Raspberry Pi (USB Serial)** — highest priority  
2. **Web UI (Human control)**  
3. **Fallback / manual testing**

This prevents conflicting commands and keeps AI in control.

---

## Hand Control Model

ESP8266 exposes a simple internal API, for example:

```

/set?f=index&v=90
/fist
/open
/like
/handshake

```

ESP32 translates:
- Pi serial commands
- Web UI actions

into these internal requests.

---

## Why This Architecture

This design:
- Avoids IP instability issues
- Avoids servo + Wi-Fi timing conflicts
- Allows offline operation
- Scales to more subsystems (face, torso, legs)
- Matches real-world robotics & IoT practices

---

## Non-Goals

- ESP8266 will not host UI
- Raspberry Pi will not drive servos directly
- No direct Pi ↔ ESP8266 communication
- No Bluetooth-based control

---

## Status

This document represents the **final agreed architecture**.

All future implementation should follow this structure unless explicitly revised.