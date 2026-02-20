# ESP8266 Hand Controller Circuit Diagram

## Overview
This circuit diagram shows the connections between the ESP8266 microcontroller, 5 servo motors (for hand control), and the battery power supply.

## Components
- **ESP8266** - WiFi-enabled microcontroller
- **5x Servo Motors** - Standard servo motors (Thumb, Index, Middle, Ring, Little)
- **Battery** - Power supply (typically 5V-6V for servos, 3.3V for ESP8266)

## Circuit Diagram

```
                                    +-------------------+
                                    |   BATTERY PACK    |
                                    |   (5V-6V)         |
                                    +-------------------+
                                             |
                                    +--------+--------+
                                    |                 |
                                   (+)                (-)
                                    |                 |
                                    |                 |
                    +---------------+                 +------------------+
                    |                                 |                  |
                    |                                 |                  |
            +-------+-------+                 +------+------+    +------+------+
            |   SERVO 1     |                 |   SERVO 2   |    |   SERVO 3   |
            |   (THUMB)     |                 |   (INDEX)   |    |   (MIDDLE)  |
            +-------+-------+                 +------+------+    +------+------+
                    |                                 |                  |
                    |                                 |                  |
            [Red]   |   [Black]              [Red]    |   [Black] [Red]  |   [Black]
            (VCC)   |   (GND)                (VCC)    |   (GND)   (VCC)   |   (GND)
                    |                                 |                  |
                    |                                 |                  |
            [Orange/Yellow]                  [Orange/Yellow]    [Orange/Yellow]
            (Signal)                         (Signal)          (Signal)
                    |                                 |                  |
                    |                                 |                  |
                    +---------------------------------+------------------+
                                                      |
                                                      |
                    +---------------------------------+------------------+
                    |                                 |                  |
            [Orange/Yellow]                  [Orange/Yellow]    [Orange/Yellow]
            (Signal)                         (Signal)          (Signal)
                    |                                 |                  |
                    |                                 |                  |
            [Red]   |   [Black]              [Red]    |   [Black] [Red]  |   [Black]
            (VCC)   |   (GND)                (VCC)    |   (GND)   (VCC)   |   (GND)
                    |                                 |                  |
                    |                                 |                  |
            +-------+-------+                 +------+------+    +------+------+
            |   SERVO 4     |                 |   SERVO 5   |    |             |
            |   (RING)      |                 |   (LITTLE)  |    |             |
            +-------+-------+                 +------+------+    +-------------+
                    |                                 |
                    |                                 |
                    +---------------------------------+
                                 |
                                 |
                    +-------------+-------------+
                    |                           |
                   (+)                         (-)
                    |                           |
                    |                           |
            +-------+---------------------------+-------+
            |                                       |
            |            ESP8266                    |
            |                                       |
            |   [3.3V]  [GND]  [D1]  [D3]  [D4]   |
            |     |       |      |     |     |     |
            |     |       |      |     |     |     |
            |     |       +------+-----+-----+-----+
            |     |              |     |     |     |
            |     |              |     |     |     |
            |     |         [D7] |     |     |     |
            |     |              |     |     |     |
            |     |         [D8] |     |     |     |
            |     |              |     |     |     |
            |     |              |     |     |     |
            |     |              |     |     |     |
            +-----+--------------+-----+-----+-----+
                   |              |     |     |     |
                   |              |     |     |     |
                   |              |     |     |     |
            +------+------+  +----+--+  |     |     |
            |  3.3V REG  |  |       |  |     |     |
            |  (LDO)     |  |       |  |     |     |
            +------+-----+  |       |  |     |     |
                   |        |       |  |     |     |
                   +--------+       |  |     |     |
                            |       |  |     |     |
                            |       |  |     |     |
                            +-------+--+-----+-----+
                                     |  |     |     |
                                     |  |     |     |
                                     |  |     |     |
                            Signal   |  |     |     |
                            Pins:    |  |     |     |
                                     |  |     |     |
                            D1 --------+  |     |     |
                            D7 -----------+  |     |     |
                            D3 --------------+  |     |     |
                            D4 ------------------+     |     |
                            D8 ------------------------+
```

## Pin Connections

### ESP8266 GPIO to Servo Signal Pins

| ESP8266 Pin | GPIO Name | Servo | Signal Wire Color |
|-------------|-----------|-------|------------------|
| D1          | GPIO 5    | Thumb | Orange/Yellow   |
| D7          | GPIO 13   | Index | Orange/Yellow   |
| D3          | GPIO 0    | Middle| Orange/Yellow   |
| D4          | GPIO 2    | Ring  | Orange/Yellow   |
| D8          | GPIO 15   | Little| Orange/Yellow   |

### Power Connections

#### Battery to Servos
- **Battery Positive (+)**: Connected to all servo **VCC/Red** wires
- **Battery Negative (-)**: Connected to all servo **GND/Black** wires and ESP8266 GND

#### ESP8266 Power
- **ESP8266 VCC (3.3V)**: Can be powered via:
  - USB connection (5V, regulated internally to 3.3V)
  - OR via 3.3V regulator from battery (if battery voltage > 3.3V)
- **ESP8266 GND**: Connected to battery negative and all servo grounds

## Wiring Details

### Servo Motor Connections
Each servo motor has 3 wires:
1. **Red (VCC)**: Power supply (5V-6V from battery)
2. **Black (GND)**: Ground (common ground with ESP8266)
3. **Orange/Yellow (Signal)**: PWM control signal from ESP8266 GPIO pins

### Power Supply Requirements
- **Servos**: 5V-6V (typically 5V for standard servos)
- **ESP8266**: 3.3V (can be powered via USB or regulated from battery)
- **Current**: Ensure battery can supply sufficient current for all 5 servos + ESP8266
  - Typical servo: 500mA-1A under load
  - ESP8266: ~80-170mA during WiFi operation
  - Total: ~3-5A recommended capacity

## Important Notes

1. **Common Ground**: All components must share a common ground connection
2. **Power Isolation**: Servos draw significant current; ensure battery can handle peak loads
3. **Voltage Regulation**: If using a battery > 3.3V, use a voltage regulator for ESP8266
4. **PWM Signals**: ESP8266 GPIO pins output 3.3V PWM signals, which servos can typically read
5. **Servo Calibration**: Servos are calibrated with pulse width range 500-2500 microseconds

## Alternative Power Configuration

If using a single battery source:

```
Battery (5V-6V)
    |
    +----> [Voltage Regulator 3.3V] ---> ESP8266 VCC
    |
    +----> [Direct] ---> All Servos VCC
    |
    +----> [Common GND] ---> ESP8266 GND + All Servos GND
```

## Safety Considerations

1. **Fuse Protection**: Consider adding a fuse in series with battery positive
2. **Capacitor**: Add a large capacitor (1000µF) across battery terminals for current smoothing
3. **Diode Protection**: Consider reverse polarity protection diode
4. **Current Rating**: Ensure all wires can handle the maximum current draw

## Component Specifications

### ESP8266 Pinout Reference
- **3.3V**: Power input (3.3V)
- **GND**: Ground
- **D1 (GPIO 5)**: Thumb servo signal
- **D7 (GPIO 13)**: Index servo signal
- **D3 (GPIO 0)**: Middle servo signal
- **D4 (GPIO 2)**: Ring servo signal
- **D8 (GPIO 15)**: Little servo signal

### Servo Specifications
- **Type**: Standard servo motors (SG90 or similar)
- **Operating Voltage**: 4.8V - 6V
- **Control Signal**: PWM, 50Hz frequency
- **Pulse Width Range**: 500-2500 microseconds (as configured in code)









