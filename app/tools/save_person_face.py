"""
Save Person Face Tool
Allows LLM to capture and save a person's face for recognition
"""
from pydantic import BaseModel, Field
import logging
import os
import json
from pathlib import Path
from typing import Callable, Optional, Any
from datetime import datetime

logger = logging.getLogger(__name__)

class SavePersonFaceArgs(BaseModel):
    person_name: str = Field(..., description="Full name of the person")
    role: Optional[str] = Field(None, description="Role or position (e.g., 'Teacher', 'Student', 'Staff', 'Principal')")
    additional_info: Optional[str] = Field(None, description="Any additional information about the person")

# Callback function to be set by the main integration script
_face_service_callback: Optional[Callable[[], Optional[Any]]] = None

def set_face_service_callback(callback: Callable[[], Optional[Any]]):
    """Sets the callback function to get face service instance."""
    global _face_service_callback
    _face_service_callback = callback
    logger.info("Face service callback set.")

def _load_face_database(db_path: Path) -> list:
    """Load face database from JSON file."""
    if not db_path.exists():
        return []
    try:
        with open(db_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading face database: {e}")
        return []

def _save_face_database(db_path: Path, data: list):
    """Save face database to JSON file."""
    try:
        db_path.parent.mkdir(parents=True, exist_ok=True)
        with open(db_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Error saving face database: {e}")
        raise

async def save_person_face(args: SavePersonFaceArgs) -> dict:
    """
    Capture and save a person's face for recognition.
    The LLM should ask the user to look at the camera before calling this tool.
    """
    if not _face_service_callback:
        return {
            "status": "error",
            "message": "Face recognition service not initialized"
        }
    
    try:
        face_service = _face_service_callback()
        if not face_service:
            return {
                "status": "error",
                "message": "Face recognition service not available"
            }
        
        # Capture current frame
        success, frame, message = face_service.capture_current_frame()
        if not success or frame is None:
            return {
                "status": "error",
                "message": f"Failed to capture frame: {message}"
            }
        
        # Get detector
        detector = face_service.get_detector()
        if not detector:
            return {
                "status": "error",
                "message": "Face detector not available"
            }
        
        # Import cv2 and numpy for face detection
        try:
            import cv2
            import numpy as np
        except ImportError as e:
            return {
                "status": "error",
                "message": f"Required libraries not available: {e}"
            }
        
        h, w = frame.shape[:2]
        detector.setInputSize((w, h))
        faces = detector.detect(frame)[1]
        
        if faces is None or len(faces) == 0:
            return {
                "status": "error",
                "message": "No face detected in the captured frame. Please ensure the person is looking at the camera."
            }
        
        # Get the largest face (most likely the person we want)
        def face_area(fr):
            x, y, w, h = fr[:4]
            return float(w * h)
        
        largest_face = max(faces, key=face_area)
        score = float(largest_face[4])
        
        if score < 0.6:  # Confidence threshold
            return {
                "status": "error",
                "message": f"Face detected but confidence too low ({score:.2f}). Please try again with better lighting or closer to camera."
            }
        
        # Prepare person name for directory (sanitize)
        person_name_safe = "".join(c for c in args.person_name if c.isalnum() or c in (' ', '-', '_')).strip()
        person_name_safe = person_name_safe.replace(' ', '_')
        
        # Create person directory
        face_dir = Path(__file__).parent.parent.parent / "face" / "known_person" / person_name_safe
        face_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        image_filename = f"{person_name_safe}_{timestamp}.jpg"
        image_path = face_dir / image_filename
        
        # Extract face region and save
        x, y, w, h = map(int, largest_face[:4])
        # Add some padding
        padding = 20
        x = max(0, x - padding)
        y = max(0, y - padding)
        w = min(frame.shape[1] - x, w + 2 * padding)
        h = min(frame.shape[0] - y, h + 2 * padding)
        
        face_roi = frame[y:y+h, x:x+w]
        
        # Save image
        cv2.imwrite(str(image_path), face_roi)
        logger.info(f"Saved face image to: {image_path}")
        
        # Update face database
        db_path = Path(__file__).parent.parent.parent / "Data" / "Face" / "face_database.json"
        db_data = _load_face_database(db_path)
        
        # Find existing entry or create new
        person_entry = None
        for entry in db_data:
            if entry.get("name", "").lower() == args.person_name.lower():
                person_entry = entry
                break
        
        if person_entry:
            # Update existing entry
            if str(image_path) not in person_entry.get("images", []):
                person_entry["images"].append(str(image_path))
            if args.role:
                person_entry["role"] = args.role
            if args.additional_info:
                person_entry["additional_info"] = args.additional_info
            person_entry["updated_at"] = datetime.now().isoformat()
        else:
            # Create new entry
            person_entry = {
                "name": args.person_name,
                "role": args.role or "",
                "images": [str(image_path)],
                "additional_info": args.additional_info or "",
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }
            db_data.append(person_entry)
        
        # Save database
        _save_face_database(db_path, db_data)
        logger.info(f"Updated face database with entry for: {args.person_name}")
        
        return {
            "status": "success",
            "message": f"Successfully saved face for {args.person_name}",
            "person_name": args.person_name,
            "image_path": str(image_path),
            "role": args.role,
            "database_updated": True
        }
        
    except Exception as e:
        logger.error(f"Error saving person face: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return {
            "status": "error",
            "message": f"Failed to save person face: {str(e)}"
        }

definition = {
    "name": "savePersonFace",
    "description": "Capture and save a person's face for recognition. The LLM should first ask the user to look at the camera, then call this tool. The tool captures the current camera frame, detects the face, saves the image to the known_person directory, and creates/updates a database entry with the person's name, role, and metadata. Use this when the user wants to register a new person for face recognition or add more images of an existing person.",
    "parameters": {
        "type": "object",
        "properties": {
            "person_name": {
                "type": "string",
                "description": "Full name of the person to register"
            },
            "role": {
                "type": "string",
                "description": "Role or position (e.g., 'Teacher', 'Student', 'Staff', 'Principal', 'Guardian Member', etc.)"
            },
            "additional_info": {
                "type": "string",
                "description": "Any additional information about the person (e.g., department, class, contact info)"
            }
        },
        "required": ["person_name"]
    }
}

