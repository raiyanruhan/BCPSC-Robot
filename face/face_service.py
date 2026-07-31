"""
Face Recognition Service for Voice Robot Integration
Wraps the face recognition system to run in background and provide callbacks
"""
import threading
import time
import logging
from typing import Dict, Set, Optional, Callable
from pathlib import Path
import sys

try:
    import cv2
except ImportError:
    cv2 = None
    logging.warning("OpenCV (cv2) not available - face recognition will not work")

# Import face recognition functions from main.py
# Use importlib to import from the specific file path
FACE_DIR = Path(__file__).parent
MAIN_PY_PATH = FACE_DIR / "main.py"

try:
    import importlib.util
    spec = importlib.util.spec_from_file_location("face_main", MAIN_PY_PATH)
    face_main = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(face_main)
    
    # Import specific functions and classes
    ensure_dirs = face_main.ensure_dirs
    download_models_if_needed = face_main.download_models_if_needed
    create_detector = face_main.create_detector
    create_recognizer = face_main.create_recognizer
    build_known_database = face_main.build_known_database
    detect_faces = face_main.detect_faces
    extract_feature_for_face = face_main.extract_feature_for_face
    feature_cosine_score = face_main.feature_cosine_score
    feature_l2_score = face_main.feature_l2_score
    RecognitionCache = face_main.RecognitionCache
    DEFAULTS = face_main.DEFAULTS
    MODELS_DIR = face_main.MODELS_DIR
    KNOWN_DIR = face_main.KNOWN_DIR
    YUNET_FILENAME = face_main.YUNET_FILENAME
    SFACE_FILENAME = face_main.SFACE_FILENAME
    limit_process_affinity_to_half_cores = face_main.limit_process_affinity_to_half_cores
    set_opencv_threads = face_main.set_opencv_threads
except (ImportError, AttributeError) as e:
    logging.error(f"Failed to import face recognition modules: {e}")
    raise

logger = logging.getLogger(__name__)


class FaceRecognitionService:
    """
    Service wrapper for face recognition that runs in a background thread.
    Provides callbacks for recognition events and tracks recognized/unknown persons.
    """
    
    def __init__(self, callback: Optional[Callable] = None):
        """
        Initialize face recognition service.
        
        Args:
            callback: Function to call when recognition events occur.
                     Signature: callback(recognized_names: Set[str], unknown_count: int)
        """
        self.callback = callback
        self.recognized_persons: Set[str] = set()  # Currently recognized persons
        self.unknown_count: int = 0  # Count of unknown faces
        self.running: bool = False
        self.thread: Optional[threading.Thread] = None
        self.lock = threading.Lock()  # Thread-safe access to state
        
        # Recognition state tracking
        self.last_recognition_time: Dict[str, float] = {}  # Debounce per person
        self.recognition_debounce_seconds = 1.0  # Update at most once per second per person
        
        # Face recognition components
        self.detector = None
        self.recognizer = None
        self.name_to_features = None
        self.name_to_centroid = None
        self.recognition_cache = None
        
        # Camera
        self.cap = None
        
    def _recognition_loop(self):
        """Main recognition loop running in background thread"""
        if cv2 is None:
            logger.error("OpenCV not available, cannot run face recognition")
            return
        
        try:
            # Initialize camera
            camera_index = DEFAULTS.get("camera_index", 8)
            width = DEFAULTS.get("frame_width", 320)
            height = DEFAULTS.get("frame_height", 240)
            
            self.cap = self._open_camera(camera_index, width, height)
            if not self.cap or not self.cap.isOpened():
                logger.error(f"Could not open camera index {camera_index}")
                return
            
            frame_idx = 0
            frame_skip = max(1, int(DEFAULTS.get("initial_frame_skip", 2)))
            metric = DEFAULTS.get("recognition_metric", "cosine")
            threshold = float(DEFAULTS.get("recognition_threshold", 0.4))
            
            logger.info("Face recognition service started")
            
            while self.running:
                ret, frame = self.cap.read()
                if not ret:
                    time.sleep(0.05)
                    continue
                
                frame_idx += 1
                if frame_idx % frame_skip != 0:
                    continue
                
                # Detect faces
                faces = detect_faces(self.detector, frame)
                
                now = time.time()
                current_recognized = set()
                current_unknown = 0
                
                if faces.shape[0] > 0:
                    max_faces = min(faces.shape[0], DEFAULTS.get("max_faces_per_frame", 3))
                    
                    for i in range(max_faces):
                        fr = faces[i]
                        score = float(fr[4])
                        if score < DEFAULTS.get("det_score_thresh", 0.6):
                            continue
                        
                        # Skip small faces
                        x, y, w, h = map(int, fr[:4])
                        if w < DEFAULTS.get("min_face_size", 30) or h < DEFAULTS.get("min_face_size", 30):
                            continue
                        
                        try:
                            feat = extract_feature_for_face(self.recognizer, frame, fr)
                        except Exception:
                            continue
                        
                        # Check cache first
                        cached_name, cached_score = self.recognition_cache.get(feat, threshold)
                        if cached_name is not None:
                            best_name = cached_name
                            best_score = cached_score
                        else:
                            best_name = None
                            best_score = -1.0
                            
                            # Compare against centroids
                            for name, centroid in self.name_to_centroid.items():
                                if metric == "cosine":
                                    s = feature_cosine_score(self.recognizer, feat, centroid)
                                    passed = s >= threshold
                                else:
                                    s = feature_l2_score(self.recognizer, feat, centroid)
                                    passed = s >= (1.0 / max(1e-6, (1.0 / threshold)))
                                
                                if s > best_score:
                                    best_score = s
                                    best_name = name
                            
                            # Cache result
                            if best_name is not None and best_score >= threshold:
                                self.recognition_cache.put(feat, best_name, best_score)
                        
                        # Process recognition result
                        if best_name is not None and best_score >= threshold:
                            # Debounce: only update if enough time has passed
                            last_t = self.last_recognition_time.get(best_name, 0.0)
                            if now - last_t >= self.recognition_debounce_seconds:
                                current_recognized.add(best_name)
                                self.last_recognition_time[best_name] = now
                        else:
                            # Unknown face
                            current_unknown += 1
                
                # Update state and call callback if changed
                with self.lock:
                    state_changed = False
                    if current_recognized != self.recognized_persons:
                        self.recognized_persons = current_recognized.copy()
                        state_changed = True
                    if current_unknown != self.unknown_count:
                        self.unknown_count = current_unknown
                        state_changed = True
                    
                    if state_changed and self.callback:
                        # Call callback with current state
                        try:
                            self.callback(
                                self.recognized_persons.copy(),
                                self.unknown_count
                            )
                        except Exception as e:
                            logger.error(f"Error in face recognition callback: {e}")
                
                # Small sleep to prevent CPU spinning
                time.sleep(0.01)
                
        except Exception as e:
            logger.error(f"Error in face recognition loop: {e}")
            import traceback
            logger.error(traceback.format_exc())
        finally:
            if self.cap:
                self.cap.release()
            logger.info("Face recognition service stopped")
    
    def _open_camera(self, index: int, width: int, height: int):
        """Open camera with fallback logic"""
        if cv2 is None:
            return None
        
        backends = [cv2.CAP_V4L2, cv2.CAP_ANY]
        for backend in backends:
            cap = cv2.VideoCapture(index, backend)
            if cap.isOpened():
                ret, frame = cap.read()
                if ret:
                    cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
                    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
                    cap.set(cv2.CAP_PROP_FPS, 15)
                    return cap
                cap.release()
        
        # Try different indices
        for test_index in [8, 9, 0, 1, 2]:
            if test_index == index:
                continue
            cap = cv2.VideoCapture(test_index)
            if cap.isOpened():
                ret, frame = cap.read()
                if ret:
                    cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
                    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
                    cap.set(cv2.CAP_PROP_FPS, 15)
                    return cap
                cap.release()
        
        return None
    
    def start(self):
        """Start face recognition service in background thread"""
        if self.running:
            logger.warning("Face recognition service already running")
            return
        
        try:
            # Ensure directories and models
            ensure_dirs()
            download_models_if_needed()
            
            yunet_path = MODELS_DIR / YUNET_FILENAME
            sface_path = MODELS_DIR / SFACE_FILENAME
            
            if not yunet_path.exists() or not sface_path.exists():
                logger.error("Face recognition models missing. Please download ONNX files.")
                return
            
            # Limit CPU affinity for performance
            limit_process_affinity_to_half_cores()
            set_opencv_threads()
            
            # Build detector and recognizer
            input_size = (DEFAULTS.get("frame_width", 320), DEFAULTS.get("frame_height", 240))
            self.detector = create_detector(
                yunet_path,
                input_size,
                DEFAULTS.get("det_score_thresh", 0.6),
                DEFAULTS.get("det_nms_thresh", 0.4),
                DEFAULTS.get("det_top_k", 1000),
            )
            self.recognizer = create_recognizer(sface_path)
            
            # Build known database
            self.name_to_features, self.name_to_centroid = build_known_database(
                self.detector, self.recognizer, log=True
            )
            
            if not self.name_to_centroid:
                logger.warning(f"No known faces found in {KNOWN_DIR}")
                return
            
            # Initialize recognition cache
            cache_size = DEFAULTS.get("recognition_cache_size", 10)
            self.recognition_cache = RecognitionCache(cache_size)
            
            # Start recognition thread
            self.running = True
            self.thread = threading.Thread(target=self._recognition_loop, daemon=True)
            self.thread.start()
            logger.info("Face recognition service started in background thread")
            
        except Exception as e:
            logger.error(f"Failed to start face recognition service: {e}")
            import traceback
            logger.error(traceback.format_exc())
            self.running = False
    
    def stop(self):
        """Stop face recognition service"""
        if not self.running:
            return
        
        self.running = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=2.0)
        logger.info("Face recognition service stopped")
    
    def get_current_state(self) -> Dict:
        """
        Get current recognition state (thread-safe).
        
        Returns:
            Dict with 'recognized' (list of names) and 'unknown_count' (int)
        """
        with self.lock:
            return {
                "recognized": list(self.recognized_persons),
                "unknown_count": self.unknown_count
            }
    
    def is_running(self) -> bool:
        """Check if service is running"""
        return self.running
    
    def get_camera_access(self):
        """
        Get access to the camera for capturing frames.
        Returns the camera object if available, None otherwise.
        """
        if not self.running or not self.cap:
            # Try to open camera temporarily if service not running
            if cv2 is None:
                return None
            camera_index = DEFAULTS.get("camera_index", 8)
            width = DEFAULTS.get("frame_width", 320)
            height = DEFAULTS.get("frame_height", 240)
            return self._open_camera(camera_index, width, height)
        return self.cap
    
    def capture_current_frame(self, max_attempts: int = 5):
        """
        Capture current frame from camera.
        
        Args:
            max_attempts: Maximum number of attempts to capture a frame
            
        Returns:
            Tuple of (success: bool, frame: np.ndarray or None, message: str)
        """
        if cv2 is None:
            return False, None, "OpenCV not available"
        
        cap = self.get_camera_access()
        if not cap or not cap.isOpened():
            return False, None, "Camera not available"
        
        # Try to capture a frame
        for attempt in range(max_attempts):
            ret, frame = cap.read()
            if ret and frame is not None:
                return True, frame, "Frame captured successfully"
            time.sleep(0.1)
        
        # If using temporary camera, release it
        if not self.running and cap:
            cap.release()
        
        return False, None, "Failed to capture frame after multiple attempts"
    
    def get_detector(self):
        """Get the face detector (for use in save_person_face tool)"""
        return self.detector
    
    def get_recognizer(self):
        """Get the face recognizer (for use in save_person_face tool)"""
        return self.recognizer

