# Face Recognition (YuNet + SFace) for Windows and Raspberry Pi 5

This project detects and recognizes faces from a webcam using OpenCV's YuNet (detector) and SFace (recognizer). It prints the recognized person name to the terminal. Designed to be lightweight and accurate, it aims to use ~50% CPU by limiting threads and frame rate.

## Features
- Auto-download ONNX models from OpenCV Zoo (fallback to manual if blocked)
- Load multiple images per person from `known_person/`
- Audio greetings when person is recognized (plays `greeting.wav` files)
- Works on Windows and Raspberry Pi 5 (8GB)
- CPU governor to maintain ~50% utilization

## Folder structure
- `main.py` — app entry
- `requirements.txt` — dependencies
- `models/` — YuNet and SFace ONNX models (auto-populated)
- `known_person/` — put your reference images here
  - Option A: `known_person/<person_name>/*.jpg`
  - Option B: files directly inside with the name inferred from filename stem, e.g. `alice_1.jpg`

## Install (Windows)
1. Install Python 3.10–3.12.
2. In PowerShell:
```powershell
cd "E:\BCPSC Robot\face4"
python -m venv .venv
. .venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install -r requirements.txt
```

## Install (Raspberry Pi 5)
1. Raspberry Pi OS (Bookworm) with Python 3.11 recommended.
2. In terminal:
```bash
cd ~/face4
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install --extra-index-url https://www.piwheels.org/simple -r requirements.txt
```
If `opencv-contrib-python` fails on Pi, try:
```bash
pip install opencv-python==4.8.0.76
```
(Note: YuNet/SFace require contrib; if contrib wheel is unavailable, install OpenCV from OS packages or build from source.)

## Prepare known persons
- Create folder `known_person/` and add reference images.
- Best results with clear frontal and some slight-angle photos; multiple per person improve accuracy.
- **Audio greetings**: Add `greeting.wav` files for personalized audio when recognized.

Examples:
```
known_person/
  Alice/
    alice1.jpg
    alice2.png
    greeting.wav          # Plays when Alice is recognized
  Bob/
    bob_front.jpg
    greeting.wav          # Plays when Bob is recognized
```
Or flat:
```
known_person/
  alice_1.jpg
  alice_greeting.wav      # Plays when Alice is recognized
  bob-office.png
  bob_greeting.wav        # Plays when Bob is recognized
```

## Run
```bash
python main.py
```
- The script will download YuNet and SFace ONNX files to `models/` (if possible).
- It opens your default camera (index 0). Change settings inside `main.py` `DEFAULTS` if needed.
- Recognized names print to terminal, debounced to ~1s per identity.
- **Audio greetings** play when person is recognized (3s cooldown to avoid spam).

## Tips
- If auto-download fails, manually download:
  - YuNet: face_detection_yunet_2023mar.onnx
  - SFace: face_recognition_sface_2021dec.onnx
  Place both in `models/`.
- To constrain CPU further, reduce `frame_width/height`, or increase `initial_frame_skip` in `DEFAULTS`.
- For side-profile tolerance, include slight left/right/up/down photos in `known_person/`.
- **Audio settings**: Set `"play_greeting": False` in `DEFAULTS` to disable audio.
- **Audio format**: Use `.wav` files for best compatibility. Keep files short (< 5 seconds).

## Troubleshooting
- "Could not open camera": set `camera_index` in `DEFAULTS` or plug the correct camera.
- High CPU: lower resolution, increase frame skip.
- No recognition: add more reference images, raise `recognition_threshold` for stricter matching.
