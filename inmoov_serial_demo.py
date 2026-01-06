#!/usr/bin/env python3
"""
InMoov Serial Control Demo

Controls:
  - Hand gestures (HAND:...)
  - Eye modes and manual angles (EYE:...)
  - Jaw actions (JAW:...)
"""

import sys
import time
import json
import threading

import serial  # pip install pyserial


class InMoovSerial:
    def __init__(self, port, baud=115200, timeout=1.0):
        """
        port: e.g. 'COM3' on Windows, '/dev/ttyUSB0' or '/dev/ttyACM0' on Linux
        """
        self.port_name = port
        self.ser = serial.Serial(port, baud, timeout=timeout)
        time.sleep(2)  # allow ESP32 to reboot on serial open

        self._lock = threading.Lock()
        self._reader_thread = threading.Thread(target=self._reader_loop, daemon=True)
        self._running = True
        self._last_response = None
        self._reader_thread.start()

    def close(self):
        self._running = False
        try:
            self.ser.close()
        except Exception:
            pass

    # ------------------------- low-level I/O -------------------------

    def _reader_loop(self):
        """Background reader to capture responses."""
        buf = b""
        while self._running:
            try:
                chunk = self.ser.read(1)
                if not chunk:
                    continue
                if chunk in (b"\n", b"\r"):
                    line = buf.decode(errors="replace").strip()
                    buf = b""
                    if line:
                        self._handle_line(line)
                else:
                    buf += chunk
            except Exception as e:
                # You might want to log this
                time.sleep(0.1)

    def _handle_line(self, line: str):
        # Try to parse as JSON; if not JSON, keep raw
        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            data = {"raw": line}

        with self._lock:
            self._last_response = data

        print("[ESP32]", data)

    def send_raw_command(self, cmd_str: str):
        """
        Send a raw command string (e.g. 'HAND:FIST').
        Automatically wraps it as JSON: {"command": "<cmd_str>"} and appends newline.
        """
        payload = json.dumps({"command": cmd_str})
        self.ser.write(payload.encode("utf-8") + b"\n")

    def send_and_wait(self, cmd_str: str, wait_time=0.3):
        """
        Send a command and wait briefly for a response.
        Returns last parsed JSON/line seen from ESP32 (may be from previous commands).
        """
        with self._lock:
            self._last_response = None
        self.send_raw_command(cmd_str)
        time.sleep(wait_time)
        with self._lock:
            return self._last_response

    # -------------------------- HAND CONTROL -------------------------

    def hand_gesture(self, name: str):
        """
        name: FIST, OPEN, LIKE, THUMBSUP, THUMBSDOWN, PEACE, OK, POINT,
              PINCH, PINKYUP, PINKYRINGUP, ALLFINGERSEXTENDED,
              ALLFINGERSCURLED, GIMME, SPIDER, CLAW, ILOVEYOU,
              STOP, SWAG, HANDSHAKE, NUMBER1..NUMBER5
        """
        name = name.upper()
        return self.send_and_wait(f"HAND:{name}")

    def hand_set_finger(self, finger: str, angle: int):
        """
        finger: 'thumb', 'index', 'middle', 'ring', 'little'
        angle: 0-180
        """
        finger = finger.lower()
        angle = max(0, min(180, int(angle)))
        return self.send_and_wait(f"HAND:SET:{finger}:{angle}")

    # --------------------------- EYE CONTROL -------------------------

    def eye_auto(self):
        """Center with natural drift."""
        return self.send_and_wait("EYE:AUTO")

    def eye_circumstances(self):
        """Free scanning mode."""
        return self.send_and_wait("EYE:CIRCUMSTANCES")

    def eye_manual(self, angle: int):
        """
        angle: 0-180 (0 = full right, 90 = center, 180 = full left)
        """
        angle = max(0, min(180, int(angle)))
        return self.send_and_wait(f"EYE:MANUAL:{angle}")

    # ---------------------------- JAW CONTROL ------------------------

    def jaw_open(self):
        return self.send_and_wait("JAW:OPEN")

    def jaw_close(self):
        return self.send_and_wait("JAW:CLOSE")

    def jaw_talk(self):
        """Continuous talking animation (until JAW:STOP)."""
        return self.send_and_wait("JAW:TALK")

    def jaw_stop(self):
        return self.send_and_wait("JAW:STOP")

    def jaw_yawn(self):
        """Single yawn animation (~4s)."""
        return self.send_and_wait("JAW:YAWN")

    def jaw_chew(self):
        """Chewing animation."""
        return self.send_and_wait("JAW:CHEW")


# ---------------------------------------------------------------------
# Demo / CLI
# ---------------------------------------------------------------------

def demo_sequence(ctrl: InMoovSerial):
    print("\n--- DEMO: Hand greeting + eye and jaw ---")

    # Hand: open -> handshake -> like
    print("Hand: OPEN")
    ctrl.hand_gesture("OPEN")
    time.sleep(1)

    print("Hand: HANDSHAKE")
    ctrl.hand_gesture("HANDSHAKE")
    time.sleep(1.5)

    print("Hand: LIKE")
    ctrl.hand_gesture("LIKE")
    time.sleep(1)

    # Eye: look around
    print("Eye: AUTO (center)")
    ctrl.eye_auto()
    time.sleep(2)

    print("Eye: MANUAL 40 (right)")
    ctrl.eye_manual(40)
    time.sleep(2)

    print("Eye: MANUAL 140 (left)")
    ctrl.eye_manual(140)
    time.sleep(2)

    print("Eye: CIRCUMSTANCES (scan)")
    ctrl.eye_circumstances()
    time.sleep(3)

    # Jaw: talk a bit, then stop
    print("Jaw: TALK for 5 seconds")
    ctrl.jaw_talk()
    time.sleep(5)
    ctrl.jaw_stop()
    print("Jaw: STOP")

    # Finish with a fist
    print("Hand: FIST")
    ctrl.hand_gesture("FIST")
    time.sleep(1)


def interactive_cli(ctrl: InMoovSerial):
    print("\n--- Interactive CLI ---")
    print("Type commands like:")
    print("  HAND:FIST")
    print("  HAND:SET:index:90")
    print("  EYE:AUTO")
    print("  EYE:MANUAL:120")
    print("  JAW:TALK")
    print("  JAW:STOP")
    print("Press Enter on empty line to exit.\n")

    while True:
        try:
            line = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not line:
            break

        resp = ctrl.send_and_wait(line)
        print("Response:", resp)

    print("Exiting CLI.")


def main():
    if len(sys.argv) < 2:
        print("Usage: python inmoov_serial_demo.py <serial_port>")
        print("  Example Windows: python inmoov_serial_demo.py COM3")
        print("  Example Linux:   python inmoov_serial_demo.py /dev/ttyUSB0")
        sys.exit(1)

    port = sys.argv[1]

    ctrl = InMoovSerial(port)

    try:
        # Run a scripted demo
        demo_sequence(ctrl)

        # Then allow interactive control
        interactive_cli(ctrl)

    finally:
        ctrl.close()


if __name__ == "__main__":
    main()