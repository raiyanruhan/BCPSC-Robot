import os
import sys
import time
import json
import math
import threading
from pathlib import Path
from typing import Dict, List, Tuple

import cv2
import numpy as np
import psutil
import requests

# Try to import pygame for audio, fallback to system beep if not available
try:
    import pygame
    PYGAME_AVAILABLE = True
except ImportError:
    PYGAME_AVAILABLE = False
    print("pygame not available - will use system beep for audio")

# -------------------------------
# Configuration
# -------------------------------
PROJECT_ROOT = Path(__file__).parent.resolve()
MODELS_DIR = PROJECT_ROOT / "models"
KNOWN_DIR = PROJECT_ROOT / "known_person"

# Model filenames expected
YUNET_FILENAME = "face_detection_yunet_2023mar.onnx"
SFACE_FILENAME = "face_recognition_sface_2021dec.onnx"

# Candidate URLs (multiple mirrors/paths for robustness)
MODEL_URLS: Dict[str, List[str]] = {
    YUNET_FILENAME: [
        # OpenCV Zoo repo (Git LFS raw)
        "https://raw.githubusercontent.com/opencv/opencv_zoo/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx",
        # GitHub blob with ?raw=1 fallback
        "https://github.com/opencv/opencv_zoo/blob/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx?raw=1",
    ],
    SFACE_FILENAME: [
        "https://raw.githubusercontent.com/opencv/opencv_zoo/main/models/face_recognition_sface/face_recognition_sface_2021dec.onnx",
        "https://github.com/opencv/opencv_zoo/blob/main/models/face_recognition_sface/face_recognition_sface_2021dec.onnx?raw=1",
    ],
}

# Defaults optimized for speed and instant recognition
DEFAULTS = {
    "camera_index": 8,
    "frame_width": 320,   # Much lower resolution for speed
    "frame_height": 240,
    "det_score_thresh": 0.6,  # Higher threshold for faster processing
    "det_nms_thresh": 0.4,    # Higher NMS for fewer detections
    "det_top_k": 1000,        # Reduced from 5000 for speed
    "recognition_metric": "cosine",  # or "l2"
    "recognition_threshold": 0.4,      # Lowered for faster recognition
    "cpu_target_percent": 70,          # Allow higher CPU usage for speed
    "initial_frame_skip": 2,           # Process every 2nd frame for speed
    "show_preview": True,              # set to False to disable preview window
    "play_greeting": True,             # set to False to disable audio greetings
    "enable_sideways_detection": False,  # Disabled for speed
    "rotation_angles": [0, -90, -45, 45, 90],  # Angles to test for sideways faces
    "sideways_confidence_boost": 0.1,  # Boost confidence for frontal faces
    "sideways_confidence_penalty": 0.05,  # Penalty for rotated faces
    # Speed optimization settings
    "fast_mode": True,                  # Enable fast mode optimizations
    "skip_audio_delay": False,         # Keep audio processing for greetings
    "max_faces_per_frame": 3,          # Limit faces processed per frame
    "recognition_cache_size": 10,       # Cache recent recognitions
    "min_face_size": 30,               # Minimum face size to process
}

# -------------------------------
# Audio utilities
# -------------------------------

def init_audio():
    """Initialize audio system with multiple fallback options"""
    if PYGAME_AVAILABLE:
        try:
            # Try primary settings
            pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)
            print("✅ Pygame audio initialized successfully")
            return True
        except Exception as e:
            print(f"Primary audio init failed: {e}")
            try:
                # Try fallback settings
                pygame.mixer.init(frequency=22050, size=-16, channels=1, buffer=1024)
                print("✅ Pygame audio initialized with fallback settings")
                return True
            except Exception as e2:
                print(f"Fallback audio init failed: {e2}")
                return False
    else:
        print("❌ Pygame not available")
        return False

def play_audio_file(file_path: Path) -> None:
    """Play audio file in background thread with improved error handling"""
    def play_audio():
        try:
            print(f"🔊 Attempting to play: {file_path}")
            
            if PYGAME_AVAILABLE and init_audio():
                print(f"Loading audio file: {file_path}")
                pygame.mixer.music.load(str(file_path))
                print("Starting audio playback...")
                pygame.mixer.music.play()
                
                # Wait for audio to finish
                while pygame.mixer.music.get_busy():
                    time.sleep(0.1)
                print("✅ Audio playback completed")
            else:
                print("Pygame not available, using system beep fallback")
                # Fallback: system beep
                try:
                    import winsound
                    winsound.Beep(1000, 500)  # 1000Hz for 500ms
                    print("✅ System beep played")
                except ImportError:
                    print("❌ No audio system available")
        except Exception as e:
            print(f"❌ Audio playback error: {e}")
            # Try system beep as final fallback
            try:
                import winsound
                winsound.Beep(1000, 500)
                print("✅ Fallback beep played")
            except:
                print("❌ No audio system available")
    
    # Play in background thread to avoid blocking
    thread = threading.Thread(target=play_audio, daemon=True)
    thread.start()

def get_greeting_file(person_name: str) -> Path:
    """Get greeting file path for a person"""
    # Try both folder structure and flat structure
    greeting_paths = [
        KNOWN_DIR / person_name / "greeting.wav",
        KNOWN_DIR / person_name / "greeting.WAV",
        KNOWN_DIR / f"{person_name}_greeting.wav",
        KNOWN_DIR / f"{person_name}_greeting.WAV",
    ]
    
    for path in greeting_paths:
        if path.exists():
            return path
    return None

# -------------------------------
# Utilities
# -------------------------------

def ensure_dirs() -> None:
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    KNOWN_DIR.mkdir(parents=True, exist_ok=True)


def download_file(url: str, dest_path: Path, timeout: int = 60) -> bool:
    try:
        with requests.get(url, stream=True, timeout=timeout) as r:
            r.raise_for_status()
            total = int(r.headers.get("content-length", 0))
            with open(dest_path, "wb") as f:
                downloaded = 0
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
        # Basic sanity check: ensure file is non-trivial size
        return dest_path.exists() and dest_path.stat().st_size > 100_000
    except Exception:
        return False


def download_models_if_needed() -> None:
    ensure_dirs()
    for fname, urls in MODEL_URLS.items():
        target = MODELS_DIR / fname
        if target.exists() and target.stat().st_size > 100_000:
            continue
        ok = False
        for url in urls:
            print(f"Downloading {fname} from {url} ...")
            if download_file(url, target):
                ok = True
                print(f"Saved {fname} to {target}")
                break
        if not ok:
            print(
                f"WARNING: Could not auto-download {fname}.\n"
                f"Please download it manually and place at: {target}\n"
                f"- YuNet (detector): face_detection_yunet_2023mar.onnx\n"
                f"- SFace (recognizer): face_recognition_sface_2021dec.onnx\n"
            )


# -------------------------------
# CPU/resource management
# -------------------------------

def limit_process_affinity_to_half_cores() -> None:
    try:
        proc = psutil.Process()
        cores = psutil.cpu_count(logical=True) or 2
        half = max(1, cores // 2)
        allowed = list(range(half))
        # On Windows and Linux this sets affinity; on some systems might require privileges
        proc.cpu_affinity(allowed)
    except Exception:
        pass


def set_opencv_threads() -> None:
    try:
        cores = psutil.cpu_count(logical=True) or 2
        target_threads = max(1, min(2, cores // 2))
        try:
            cv2.setNumThreads(target_threads)
        except Exception:
            pass
        try:
            cv2.ocl.setUseOpenCL(False)
        except Exception:
            pass
    except Exception:
        pass


# -------------------------------
# Recognition cache for speed
# -------------------------------

class RecognitionCache:
    def __init__(self, max_size: int = 10):
        self.cache = {}
        self.max_size = max_size
        self.access_order = []
    
    def get(self, face_feature: np.ndarray, threshold: float = 0.4) -> Tuple[str, float]:
        """Get cached recognition result if available"""
        if not DEFAULTS["fast_mode"]:
            return None, 0.0
        
        # Simple hash of feature for cache key
        feature_hash = hash(tuple(face_feature.flatten()[:10]))  # Use first 10 values for speed
        
        if feature_hash in self.cache:
            name, score, timestamp = self.cache[feature_hash]
            # Check if cache is still valid (within 2 seconds)
            if time.time() - timestamp < 2.0 and score >= threshold:
                # Update access order
                if feature_hash in self.access_order:
                    self.access_order.remove(feature_hash)
                self.access_order.append(feature_hash)
                return name, score
        
        return None, 0.0
    
    def put(self, face_feature: np.ndarray, name: str, score: float):
        """Cache recognition result"""
        if not DEFAULTS["fast_mode"]:
            return
        
        feature_hash = hash(tuple(face_feature.flatten()[:10]))
        
        # Remove oldest if cache is full
        if len(self.cache) >= self.max_size:
            oldest = self.access_order.pop(0)
            if oldest in self.cache:
                del self.cache[oldest]
        
        self.cache[feature_hash] = (name, score, time.time())
        if feature_hash in self.access_order:
            self.access_order.remove(feature_hash)
        self.access_order.append(feature_hash)


# -------------------------------
# Face detection and recognition
# -------------------------------

def create_detector(yunet_path: Path, input_size: Tuple[int, int], score: float, nms: float, top_k: int):
    # OpenCV provides FaceDetectorYN in contrib builds
    detector = cv2.FaceDetectorYN.create(
        str(yunet_path),
        "",
        input_size,
        score,
        nms,
        top_k,
    )
    return detector


def rotate_image(image: np.ndarray, angle: float) -> Tuple[np.ndarray, np.ndarray]:
    """Rotate image by given angle and return rotation matrix for coordinate transformation"""
    h, w = image.shape[:2]
    center = (w // 2, h // 2)
    
    # Get rotation matrix
    rotation_matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
    
    # Calculate new dimensions to avoid cropping
    cos_angle = abs(rotation_matrix[0, 0])
    sin_angle = abs(rotation_matrix[0, 1])
    new_w = int((h * sin_angle) + (w * cos_angle))
    new_h = int((h * cos_angle) + (w * sin_angle))
    
    # Adjust translation
    rotation_matrix[0, 2] += (new_w / 2) - center[0]
    rotation_matrix[1, 2] += (new_h / 2) - center[1]
    
    # Rotate image
    rotated = cv2.warpAffine(image, rotation_matrix, (new_w, new_h), flags=cv2.INTER_LINEAR)
    
    return rotated, rotation_matrix


def transform_face_coordinates(face_coords: np.ndarray, rotation_matrix: np.ndarray, original_size: Tuple[int, int]) -> np.ndarray:
    """Transform face coordinates back to original image coordinates"""
    # Extract face bounding box coordinates
    x, y, w, h = face_coords[:4]
    
    # Get the four corners of the bounding box
    corners = np.array([
        [x, y, 1],
        [x + w, y, 1],
        [x + w, y + h, 1],
        [x, y + h, 1]
    ]).T
    
    # Transform corners back to original coordinates
    inv_matrix = cv2.invertAffineTransform(rotation_matrix)
    transformed_corners = inv_matrix @ corners
    
    # Get new bounding box
    x_coords = transformed_corners[0]
    y_coords = transformed_corners[1]
    
    new_x = max(0, int(min(x_coords)))
    new_y = max(0, int(min(y_coords)))
    new_w = min(original_size[0] - new_x, int(max(x_coords) - new_x))
    new_h = min(original_size[1] - new_y, int(max(y_coords) - new_y))
    
    # Create new face coordinates array
    new_face = face_coords.copy()
    new_face[0] = new_x
    new_face[1] = new_y
    new_face[2] = new_w
    new_face[3] = new_h
    
    return new_face


def detect_faces_multi_angle(detector, image_bgr: np.ndarray, rotation_angles: List[float] = None) -> np.ndarray:
    """Detect faces in image with multiple rotation angles for sideways face detection"""
    if rotation_angles is None:
        rotation_angles = [0, -90, -45, 45, 90]  # Include original and common rotation angles
    
    h, w = image_bgr.shape[:2]
    original_size = (w, h)
    all_faces = []
    face_angles = []  # Track which angle each face came from
    
    for angle in rotation_angles:
        if angle == 0:
            # No rotation needed - prioritize this detection
            detector.setInputSize((w, h))
            faces = detector.detect(image_bgr)[1]
            if faces is not None:
                for face in faces:
                    # Boost confidence for original angle detection
                    face[4] = min(1.0, face[4] + 0.1)
                    all_faces.append(face)
                    face_angles.append(angle)
        else:
            # Rotate image and detect
            rotated_image, rotation_matrix = rotate_image(image_bgr, angle)
            rh, rw = rotated_image.shape[:2]
            detector.setInputSize((rw, rh))
            faces = detector.detect(rotated_image)[1]
            
            if faces is not None:
                # Transform coordinates back to original image
                for face in faces:
                    # Only keep high-confidence detections from rotated images
                    if face[4] > DEFAULTS["det_score_thresh"] + 0.1:  # Higher threshold for rotated
                        transformed_face = transform_face_coordinates(face, rotation_matrix, original_size)
                        # Reduce confidence slightly for rotated detections
                        transformed_face[4] = max(0.0, transformed_face[4] - 0.05)
                        all_faces.append(transformed_face)
                        face_angles.append(angle)
    
    if not all_faces:
        return np.empty((0, 15), dtype=np.float32)
    
    # Convert to numpy array and apply NMS to remove duplicates
    all_faces = np.array(all_faces)
    
    # Apply Non-Maximum Suppression to remove overlapping detections
    if len(all_faces) > 1:
        # Extract bounding boxes for NMS
        boxes = all_faces[:, :4]
        scores = all_faces[:, 4]
        
        # Use stricter NMS for sideways detection
        nms_thresh = DEFAULTS["det_nms_thresh"] * 0.7  # Stricter NMS
        indices = cv2.dnn.NMSBoxes(
            boxes.tolist(), 
            scores.tolist(), 
            DEFAULTS["det_score_thresh"], 
            nms_thresh
        )
        
        if len(indices) > 0:
            indices = indices.flatten()
            all_faces = all_faces[indices]
    
    return all_faces


def create_recognizer(sface_path: Path):
    recognizer = cv2.FaceRecognizerSF.create(str(sface_path), "")
    return recognizer


def detect_faces(detector, image_bgr: np.ndarray) -> np.ndarray:
    h, w = image_bgr.shape[:2]
    detector.setInputSize((w, h))
    faces = detector.detect(image_bgr)[1]
    if faces is None:
        return np.empty((0, 15), dtype=np.float32)
    return faces


def extract_feature_for_face(recognizer, image_bgr: np.ndarray, face_row: np.ndarray) -> np.ndarray:
    # face_row includes 4 bbox + score + 5 landmarks (x1,y1,...,x5,y5)
    # Align and extract feature using OpenCV helper
    aligned = recognizer.alignCrop(image_bgr, face_row)
    feature = recognizer.feature(aligned)
    return feature


def feature_cosine_score(recognizer, feat1: np.ndarray, feat2: np.ndarray) -> float:
    # Higher is better for cosine in OpenCV API
    return float(recognizer.match(feat1, feat2, cv2.FaceRecognizerSF_FR_COSINE))


def feature_l2_score(recognizer, feat1: np.ndarray, feat2: np.ndarray) -> float:
    # Lower is better for L2; we will invert to a similarity-like score
    dist = float(recognizer.match(feat1, feat2, cv2.FaceRecognizerSF_FR_NORM_L2))
    return 1.0 / (1e-6 + dist)


# -------------------------------
# Known database
# -------------------------------

def iter_known_images() -> List[Tuple[str, Path]]:
    pairs: List[Tuple[str, Path]] = []
    if not KNOWN_DIR.exists():
        return pairs

    # Supported extensions (case insensitive)
    valid_extensions = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".JPG", ".JPEG", ".PNG", ".BMP", ".WEBP"}

    # Prefer structure: known_person/<person_name>/*.jpg
    subdirs = [p for p in KNOWN_DIR.iterdir() if p.is_dir()]
    if subdirs:
        for sd in subdirs:
            name = sd.name
            for imgp in sd.rglob("*"):
                if imgp.suffix in valid_extensions:
                    pairs.append((name, imgp))
        return pairs

    # Fallback: files directly under known_person with name inference from filename
    for imgp in KNOWN_DIR.iterdir():
        if imgp.is_file() and imgp.suffix in valid_extensions:
            stem = imgp.stem
            # Use first token before _, -, or space as name; if none, use full stem
            for sep in ["_", "-", " "]:
                if sep in stem:
                    stem = stem.split(sep)[0]
                    break
            name = stem
            pairs.append((name, imgp))
    return pairs


def build_known_database(detector, recognizer, log: bool = True) -> Tuple[Dict[str, List[np.ndarray]], Dict[str, np.ndarray]]:
    name_to_features: Dict[str, List[np.ndarray]] = {}
    name_to_centroid: Dict[str, np.ndarray] = {}
    items = iter_known_images()
    if log:
        print(f"Scanning known faces in: {KNOWN_DIR} ...")
    for name, imgp in items:
        try:
            img = cv2.imread(str(imgp))
            if img is None:
                if log:
                    print(f"Skip unreadable image: {imgp}")
                continue
            
            # Resize very large images for better detection
            h, w = img.shape[:2]
            if w > 2000 or h > 2000:
                scale = min(2000/w, 2000/h)
                new_w, new_h = int(w * scale), int(h * scale)
                img = cv2.resize(img, (new_w, new_h))
                if log:
                    print(f"Resized {imgp.name} from {w}x{h} to {new_w}x{new_h}")
            
            # Try standard detection first for database building
            faces = detect_faces(detector, img)
            
            # If sideways detection is enabled and no faces found, try multi-angle detection
            if DEFAULTS["enable_sideways_detection"] and faces.shape[0] == 0:
                faces = detect_faces_multi_angle(detector, img, DEFAULTS["rotation_angles"])
            
            if faces.shape[0] == 0:
                if log:
                    print(f"No face detected in: {imgp}")
                continue
            # choose largest face by area
            def face_area(fr):
                x, y, w, h = fr[:4]
                return float(w * h)
            largest = max(faces, key=face_area)
            feat = extract_feature_for_face(recognizer, img, largest)
            name_to_features.setdefault(name, []).append(feat)
            if log:
                print(f"Added embedding for {name} from {imgp.name}")
        except Exception as e:
            if log:
                print(f"Failed processing {imgp}: {e}")

    # Compute centroids
    for name, feats in name_to_features.items():
        if len(feats) == 1:
            name_to_centroid[name] = feats[0]
        else:
            # Normalize then average then normalize again
            arr = np.stack(feats, axis=0)
            # Some OpenCV features are already L2-normalized; still safe to renorm
            mean = arr.mean(axis=0)
            # Ensure same shape as features
            name_to_centroid[name] = mean
    if log:
        print(f"Known identities: {list(name_to_features.keys())}")
    return name_to_features, name_to_centroid


# -------------------------------
# Recognition loop
# -------------------------------

def open_camera(index: int, width: int, height: int) -> cv2.VideoCapture:
    print(f"Attempting to open camera index {index}...")
    
    # Try different backends
    backends = [cv2.CAP_V4L2, cv2.CAP_ANY]
    
    for backend in backends:
        print(f"Trying backend {backend}...")
        cap = cv2.VideoCapture(index, backend)
        
        if cap.isOpened():
            print(f"Camera opened with backend {backend}")
            
            # Set properties
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
            cap.set(cv2.CAP_PROP_FPS, 15)
            
            # Test if we can read frames
            ret, frame = cap.read()
            if ret:
                print(f"Camera working! Frame shape: {frame.shape}")
                return cap
            else:
                print("Camera opened but cannot read frames, trying next backend...")
                cap.release()
        else:
            print(f"Failed to open camera with backend {backend}")
    
    # If all backends fail, try different camera indices
    print("Trying different camera indices...")
    for test_index in [8, 9, 0, 1, 2]:
        if test_index == index:
            continue
        print(f"Trying camera index {test_index}...")
        cap = cv2.VideoCapture(test_index)
        if cap.isOpened():
            ret, frame = cap.read()
            if ret:
                print(f"Found working camera at index {test_index}!")
                cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
                cap.set(cv2.CAP_PROP_FPS, 15)
                return cap
            cap.release()
    
    print("No working camera found!")
    return cv2.VideoCapture(index)  # Return the original attempt


def recognize_live(
    detector,
    recognizer,
    name_to_features: Dict[str, List[np.ndarray]],
    name_to_centroid: Dict[str, np.ndarray],
    metric: str,
    threshold: float,
    camera_index: int,
    width: int,
    height: int,
    cpu_target_percent: int,
    initial_frame_skip: int,
    show_preview: bool,
    play_greeting: bool,
) -> None:
    cap = open_camera(camera_index, width, height)
    if not cap.isOpened():
        print(f"ERROR: Could not open camera index {camera_index}")
        return

    # Initialize recognition cache for speed
    recognition_cache = RecognitionCache(DEFAULTS["recognition_cache_size"])
    
    # Maintain a lightweight seen cache to avoid spamming prints and audio
    last_print_time: Dict[str, float] = {}
    played_audio_this_session: Dict[str, bool] = {}  # Track if audio played this session
    frame_idx = 0
    frame_skip = max(1, int(initial_frame_skip))
    
    # Fast mode optimizations
    if DEFAULTS["fast_mode"]:
        print("🚀 Fast mode enabled - optimized for instant recognition")
        # Pre-allocate arrays for speed
        temp_feature = np.zeros((512,), dtype=np.float32)  # Typical feature size

    print("Starting recognition. Press Ctrl+C to stop.")
    if show_preview:
        print("Preview window enabled. Press 'q' in preview window to quit, or Ctrl+C in terminal.")
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                time.sleep(0.05)
                continue

            frame_idx += 1
            if frame_idx % frame_skip != 0:
                if show_preview:
                    cv2.imshow("Face Recognition", frame)
                    if cv2.waitKey(1) & 0xFF == ord('q'):
                        break
                continue

            # Try standard detection first
            faces = detect_faces(detector, frame)
            
            # If sideways detection is enabled and no faces found, try multi-angle detection
            if DEFAULTS["enable_sideways_detection"] and faces.shape[0] == 0:
                faces = detect_faces_multi_angle(detector, frame, DEFAULTS["rotation_angles"])
            
            now = time.time()

            # Create display frame for preview (mirrored for better user experience)
            display_frame = cv2.flip(frame, 1) if show_preview else None

            if faces.shape[0] > 0:
                # Limit faces processed per frame for speed
                max_faces = min(faces.shape[0], DEFAULTS["max_faces_per_frame"])
                
                for i in range(max_faces):
                    fr = faces[i]
                    # Confidence check
                    score = float(fr[4])
                    if score < DEFAULTS["det_score_thresh"]:
                        continue
                    
                    # Skip small faces for speed
                    x, y, w, h = map(int, fr[:4])
                    if w < DEFAULTS["min_face_size"] or h < DEFAULTS["min_face_size"]:
                        continue
                    
                    try:
                        feat = extract_feature_for_face(recognizer, frame, fr)
                    except Exception:
                        continue

                    # Check cache first for speed
                    cached_name, cached_score = recognition_cache.get(feat, threshold)
                    if cached_name is not None:
                        best_name = cached_name
                        best_score = cached_score
                    else:
                        best_name = None
                        best_score = -1.0

                        # Compare against centroids first for speed
                        for name, centroid in name_to_centroid.items():
                            if metric == "cosine":
                                s = feature_cosine_score(recognizer, feat, centroid)
                                passed = s >= threshold
                            else:
                                s = feature_l2_score(recognizer, feat, centroid)
                                passed = s >= (1.0 / max(1e-6, (1.0 / threshold)))  # approximate
                            
                            # Apply stricter threshold for sideways detection
                            if DEFAULTS["enable_sideways_detection"] and score < DEFAULTS["det_score_thresh"] + 0.1:
                                # This might be a sideways detection, use stricter threshold
                                adjusted_threshold = threshold + 0.1
                                passed = s >= adjusted_threshold
                            
                            if s > best_score:
                                best_score = s
                                best_name = name
                        
                        # Cache the result for future use
                        if best_name is not None and best_score >= threshold:
                            recognition_cache.put(feat, best_name, best_score)

                    # Optionally refine by checking all features for the best name
                    if best_name is not None and best_score >= threshold:
                        # Debounce prints to about once per second per name
                        last_t = last_print_time.get(best_name, 0.0)
                        if now - last_t > 1.0:
                            print(f"Recognized: {best_name} (score={best_score:.3f})")
                            last_print_time[best_name] = now
                        
                        # Play greeting audio (once per session) - optimized for speed
                        if play_greeting and not played_audio_this_session.get(best_name, False):
                            if not DEFAULTS["skip_audio_delay"]:
                                greeting_file = get_greeting_file(best_name)
                                if greeting_file:
                                    print(f"Playing greeting for {best_name}")
                                    play_audio_file(greeting_file)
                                    played_audio_this_session[best_name] = True
                                else:
                                    print(f"No greeting file found for {best_name}")
                                    played_audio_this_session[best_name] = True  # Mark as played even if no file
                            else:
                                # Skip audio processing for speed
                                played_audio_this_session[best_name] = True

                    # Draw bounding box and name on preview (mirror coordinates)
                    if show_preview and display_frame is not None:
                        x, y, w, h = map(int, fr[:4])
                        # Mirror the x coordinate for display
                        frame_width = display_frame.shape[1]
                        mirrored_x = frame_width - x - w
                        color = (0, 255, 0) if best_name and best_score >= threshold else (0, 0, 255)
                        cv2.rectangle(display_frame, (mirrored_x, y), (mirrored_x + w, y + h), color, 2)
                        
                        # Add sideways detection indicator
                        if DEFAULTS["enable_sideways_detection"]:
                            cv2.putText(display_frame, "Sideways Detection: ON", (10, 30), 
                                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)
                        
                        if best_name and best_score >= threshold:
                            label = f"{best_name} ({best_score:.2f})"
                            cv2.putText(display_frame, label, (mirrored_x, y - 10), 
                                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)

            # Show preview window
            if show_preview and display_frame is not None:
                cv2.imshow("Face Recognition", display_frame)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break

            # Optimized CPU governor for speed
            if DEFAULTS["fast_mode"]:
                # Less aggressive CPU limiting for speed
                cpu_percent = psutil.cpu_percent(interval=0.0)
                if cpu_percent > cpu_target_percent + 20:  # Higher threshold
                    frame_skip = min(4, frame_skip + 1)  # Less aggressive skipping
                elif cpu_percent < cpu_target_percent - 20 and frame_skip > 1:
                    frame_skip = max(1, frame_skip - 1)
            else:
                # Original CPU governor
                cpu_percent = psutil.cpu_percent(interval=0.0)
                if cpu_percent > cpu_target_percent + 10:
                    frame_skip = min(6, frame_skip + 1)
                    time.sleep(0.01)
                elif cpu_percent < cpu_target_percent - 10 and frame_skip > 1:
                    frame_skip = max(1, frame_skip - 1)

    except KeyboardInterrupt:
        print("Stopping.")
    finally:
        cap.release()
        if show_preview:
            cv2.destroyAllWindows()


# -------------------------------
# Testing utilities
# -------------------------------

def test_audio_system() -> None:
    """Test audio system functionality"""
    print("=== 🔊 Audio System Test ===")
    
    # Test pygame availability
    print(f"Pygame available: {PYGAME_AVAILABLE}")
    
    if PYGAME_AVAILABLE:
        # Test audio initialization
        if init_audio():
            print("✅ Pygame audio initialized successfully")
            
            # Test with a sample greeting file
            test_files = list(KNOWN_DIR.rglob("*.wav")) + list(KNOWN_DIR.rglob("*.WAV"))
            if test_files:
                test_file = test_files[0]
                print(f"Testing with file: {test_file}")
                play_audio_file(test_file)
                time.sleep(3)  # Wait for audio to play
            else:
                print("No WAV files found in known_person directory")
                print("Creating test beep...")
                try:
                    import winsound
                    winsound.Beep(1000, 500)
                    print("✅ System beep played successfully")
                except ImportError:
                    print("❌ No audio system available")
        else:
            print("❌ Failed to initialize pygame audio")
    else:
        print("❌ Pygame not available")
        print("Testing system beep...")
        try:
            import winsound
            winsound.Beep(1000, 500)
            print("✅ System beep played successfully")
        except ImportError:
            print("❌ No audio system available")

def test_sideways_detection(detector, test_image_path: str = None) -> None:
    """Test sideways face detection with a sample image"""
    if test_image_path is None:
        # Try to find a test image in the known_person directory
        test_images = list(KNOWN_DIR.rglob("*.jpg")) + list(KNOWN_DIR.rglob("*.png"))
        if not test_images:
            print("No test images found in known_person directory")
            return
        test_image_path = str(test_images[0])
    
    print(f"Testing sideways detection with: {test_image_path}")
    
    # Load test image
    img = cv2.imread(test_image_path)
    if img is None:
        print(f"Could not load image: {test_image_path}")
        return
    
    # Test with different detection methods
    print("\n=== Standard Detection ===")
    faces_standard = detect_faces(detector, img)
    print(f"Standard detection found {len(faces_standard)} faces")
    
    print("\n=== Multi-Angle Detection ===")
    faces_multi = detect_faces_multi_angle(detector, img, DEFAULTS["rotation_angles"])
    print(f"Multi-angle detection found {len(faces_multi)} faces")
    
    # Show results
    if len(faces_multi) > len(faces_standard):
        print("✅ Sideways detection found additional faces!")
    elif len(faces_multi) == len(faces_standard):
        print("ℹ️  Same number of faces detected")
    else:
        print("⚠️  Multi-angle detection found fewer faces (possible NMS filtering)")


# -------------------------------
# Main
# -------------------------------

def main() -> None:
    ensure_dirs()
    download_models_if_needed()

    yunet_path = MODELS_DIR / YUNET_FILENAME
    sface_path = MODELS_DIR / SFACE_FILENAME

    if not yunet_path.exists() or not sface_path.exists():
        print("Models missing. Please download the ONNX files as instructed.")
        sys.exit(1)

    limit_process_affinity_to_half_cores()
    set_opencv_threads()

    # Build detector and recognizer
    input_size = (DEFAULTS["frame_width"], DEFAULTS["frame_height"])  # dummy; will be set per-frame
    detector = create_detector(
        yunet_path,
        input_size,
        DEFAULTS["det_score_thresh"],
        DEFAULTS["det_nms_thresh"],
        DEFAULTS["det_top_k"],
    )
    recognizer = create_recognizer(sface_path)
    
    # Check for command line options
    if len(sys.argv) > 1:
        if sys.argv[1] == "test":
            test_sideways_detection(detector)
            return
        elif sys.argv[1] == "sideways":
            print("Enabling sideways detection...")
            DEFAULTS["enable_sideways_detection"] = True
        elif sys.argv[1] == "frontal":
            print("Using frontal face detection only...")
            DEFAULTS["enable_sideways_detection"] = False
        elif sys.argv[1] == "fast":
            print("🚀 Ultra-fast mode enabled!")
            DEFAULTS["fast_mode"] = True
            DEFAULTS["frame_width"] = 240
            DEFAULTS["frame_height"] = 180
            DEFAULTS["initial_frame_skip"] = 3
            DEFAULTS["max_faces_per_frame"] = 2
            DEFAULTS["skip_audio_delay"] = True
        elif sys.argv[1] == "instant":
            print("⚡ INSTANT recognition mode!")
            DEFAULTS["fast_mode"] = True
            DEFAULTS["frame_width"] = 160
            DEFAULTS["frame_height"] = 120
            DEFAULTS["initial_frame_skip"] = 4
            DEFAULTS["max_faces_per_frame"] = 1
            DEFAULTS["skip_audio_delay"] = True
            DEFAULTS["recognition_threshold"] = 0.3
        elif sys.argv[1] == "audio-test":
            print("🔊 Testing audio system...")
            test_audio_system()
            return
        elif sys.argv[1] == "fast-audio":
            print("🚀 Fast mode with audio enabled!")
            DEFAULTS["fast_mode"] = True
            DEFAULTS["frame_width"] = 240
            DEFAULTS["frame_height"] = 180
            DEFAULTS["initial_frame_skip"] = 3
            DEFAULTS["max_faces_per_frame"] = 2
            DEFAULTS["skip_audio_delay"] = False  # Keep audio
        elif sys.argv[1] == "instant-audio":
            print("⚡ INSTANT mode with audio enabled!")
            DEFAULTS["fast_mode"] = True
            DEFAULTS["frame_width"] = 160
            DEFAULTS["frame_height"] = 120
            DEFAULTS["initial_frame_skip"] = 4
            DEFAULTS["max_faces_per_frame"] = 1
            DEFAULTS["skip_audio_delay"] = False  # Keep audio
            DEFAULTS["recognition_threshold"] = 0.3

    # Build database
    name_to_features, name_to_centroid = build_known_database(detector, recognizer, log=True)
    if not name_to_centroid:
        print(
            f"No known faces found in {KNOWN_DIR}. Add images and rerun.\n"
            f"- Option A: {KNOWN_DIR}/<person_name>/*.jpg\n"
            f"- Option B: {KNOWN_DIR}/name1.jpg, name2_1.png, etc."
        )
        sys.exit(1)

    # Live recognition
    recognize_live(
        detector=detector,
        recognizer=recognizer,
        name_to_features=name_to_features,
        name_to_centroid=name_to_centroid,
        metric=DEFAULTS["recognition_metric"],
        threshold=float(DEFAULTS["recognition_threshold"]),
        camera_index=int(DEFAULTS["camera_index"]),
        width=int(DEFAULTS["frame_width"]),
        height=int(DEFAULTS["frame_height"]),
        cpu_target_percent=int(DEFAULTS["cpu_target_percent"]),
        initial_frame_skip=int(DEFAULTS["initial_frame_skip"]),
        show_preview=bool(DEFAULTS["show_preview"]),
        play_greeting=bool(DEFAULTS["play_greeting"]),
    )


if __name__ == "__main__":
    main()
