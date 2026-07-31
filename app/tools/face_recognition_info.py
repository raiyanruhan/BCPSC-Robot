"""
Face Recognition Info Tool
Allows LLM to get currently recognized person names from face recognition system
"""
from pydantic import BaseModel, Field
import logging
from typing import Callable, Optional

logger = logging.getLogger(__name__)

class GetFaceRecognitionInfoArgs(BaseModel):
    """No arguments needed for this tool"""
    pass

# Callback function to be set by the main integration script
_face_info_callback: Optional[Callable[[], dict]] = None

def set_face_info_callback(callback: Callable[[], dict]):
    """Sets the callback function to get face recognition info."""
    global _face_info_callback
    _face_info_callback = callback
    logger.info("Face recognition info callback set.")

async def get_face_recognition_info(args: GetFaceRecognitionInfoArgs) -> dict:
    """
    Gets currently recognized person names from the face recognition system.
    Returns who is currently visible to the camera.
    """
    if _face_info_callback:
        try:
            result = _face_info_callback()
            logger.info(f"Face recognition info retrieved: {result}")
            return {
                "status": "success",
                "recognized_persons": result.get("recognized", []),
                "unknown_count": result.get("unknown_count", 0),
                "message": f"Currently visible: {', '.join(result.get('recognized', [])) if result.get('recognized') else 'No recognized persons'}. Unknown persons: {result.get('unknown_count', 0)}"
            }
        except Exception as e:
            logger.error(f"Error getting face recognition info via callback: {e}")
            return {
                "status": "error",
                "message": f"Failed to get face recognition info: {e}"
            }
    else:
        logger.warning("Face recognition info callback not set.")
        return {
            "status": "error",
            "message": "Face recognition functionality not initialized.",
            "recognized_persons": [],
            "unknown_count": 0
        }

definition = {
    "name": "getFaceRecognitionInfo",
    "description": "Get currently recognized person names from face recognition system. Returns list of person names currently visible to the camera and count of unknown persons. Use this when you need to know who is present or when the user asks 'who is here' or 'who can you see'.",
    "parameters": {
        "type": "object",
        "properties": {},
        "required": []
    }
}




