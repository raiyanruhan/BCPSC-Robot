# Single PCB Design for InMoov Control

This document outlines the connections required to integrate the ESP32 (Face/Master) and ESP8266 (Hand/Slave) onto a single PCB using Serial (UART) communication.

## Schematic Overview

```mermaid
graph TD
    subgraph Power
        VCC[5V Power Source]
        GND[Common Ground]
    end

    subgraph ESP32_Master_Face
        ESP32_5V[5V/VIN]
        ESP32_GND[GND]
        ESP32_TX[GPIO 17 (TX2)]
        ESP32_RX[GPIO 16 (RX2)]
        ESP32_Servo1[GPIO 18 (Eye)]
        ESP32_Servo2[GPIO 19 (Jaw)]
    end

    subgraph ESP8266_Slave_Hand
        ESP8266_5V[5V/VIN]
        ESP8266_GND[GND]
        ESP8266_RX[RX (GPIO 3)]
        ESP8266_TX[TX (GPIO 1)]
        ESP8266_S1[D1 (Thumb)]
        ESP8266_S2[D7 (Index)]
        ESP8266_S3[D3 (Middle)]
        ESP8266_S4[D4 (Ring)]
        ESP8266_S5[D8 (Little)]
    end

    %% Power Connections
    VCC --> ESP32_5V
    VCC --> ESP8266_5V
    GND --> ESP32_GND
    GND --> ESP8266_GND
    ESP32_GND --- ESP8266_GND

    %% Serial Communication (The Core Request)
    ESP32_TX -->|Command Signal| ESP8266_RX
    
    %% Optional Feedback (Handshake)
    ESP8266_TX -.->|Optional Feedback| ESP32_RX

    %% Peripherals
    ESP32_Servo1 --> EyeServo
    ESP32_Servo2 --> JawServo
    
    ESP8266_S1 --> ThumbServo
    ESP8266_S2 --> IndexServo
    ESP8266_S3 --> MiddleServo
    ESP8266_S4 --> RingServo
    ESP8266_S5 --> LittleServo

    style ESP32_TX stroke:#0f0,stroke-width:2px
    style ESP8266_RX stroke:#0f0,stroke-width:2px
```

## Connection Table

| Signal | ESP32 Pin | ESP8266 Pin | Notes |
|--------|-----------|-------------|-------|
| **TX Data** | GPIO 17 (TX2) | RX (GPIO 3) | **Primary Command Line** |
| **RX Data** | GPIO 16 (RX2) | TX (GPIO 1) | Optional (for status implementation) |
| **Ground** | GND | GND | **MUST be connected** |
| Power | 5V / VIN | 5V / VIN | Shared power supply |

## Notes for PCB Designer

1.  **Level Shifting**: Both ESP32 and ESP8266 are 3.3V logic. Connecting them directly is safe.
2.  **Boot strapping**:
    *   ESP8266 GPIO 0, 2, 15 must be in correct states for boot.
    *   ESP8266 RX (GPIO 3) is high impedance during boot, which is fine.
    *   Ensure ESP32 GPIO 17 (TX) doesn't pull ESP8266 RX low during boot if that affects startup (usually fine).
3.  **Programming**: Include headers to program both chips individually if they are soldered directly tailored. If using dev modules (NodeMCU/ESP32 DevKit), provide pin headers.
