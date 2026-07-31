"""
Describe Circumstances Tool
Captures a photo from camera and uses Gemini vision to describe the current circumstances
"""
from pydantic import BaseModel
import logging
from typing import Callable, Optional, Any
import base64
import io

logger = logging.getLogger(__name__)

class DescribeCircumstancesArgs(BaseModel):
    """No arguments needed for this tool"""
    pass

# Callback function to be set by the main integration script
_face_service_callback: Optional[Callable[[], Optional[Any]]] = None

def set_face_service_callback_for_vision(callback: Callable[[], Optional[Any]]):
    """Sets the callback function to get face service instance for vision tool."""
    global _face_service_callback
    _face_service_callback = callback
    logger.info("Face service callback set for describe circumstances tool.")

async def describe_circumstances(args: DescribeCircumstancesArgs) -> dict:
    """
    Captures a photo from the camera and uses Gemini vision to describe the current circumstances.
    Returns a detailed description of what is visible in the captured image.
    """
    if not _face_service_callback:
        return {
            "status": "error",
            "message": "Face recognition service not initialized",
            "description": ""
        }
    
    try:
        face_service = _face_service_callback()
        if not face_service:
            return {
                "status": "error",
                "message": "Face recognition service not available",
                "description": ""
            }
        
        # Capture current frame
        success, frame, message = face_service.capture_current_frame(max_attempts=10)
        if not success or frame is None:
            return {
                "status": "error",
                "message": f"Failed to capture frame: {message}",
                "description": ""
            }
        
        # Convert frame to image format for Gemini
        try:
            import cv2
            from PIL import Image
            import numpy as np
        except ImportError as e:
            return {
                "status": "error",
                "message": f"Required libraries not available: {e}",
                "description": ""
            }
        
        # Convert BGR to RGB for PIL
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        pil_image = Image.fromarray(frame_rgb)
        
        # Convert to base64 or use PIL Image directly
        # Gemini can accept PIL Image objects
        
        # Call Gemini vision API
        try:
            from app.config import settings
            import google.generativeai as genai
            
            # Configure Gemini
            genai.configure(api_key=settings.GEMINI_API_KEY)
            
            # Use Gemini 2.5 Pro for vision (or fallback to available model)
            # Try gemini-2.5-pro first, then fallback to other models
            vision_model = None
            model_names = ["gemini-2.5-pro", "gemini-2.0-flash-exp", "gemini-1.5-pro", "gemini-1.5-flash"]
            for model_name in model_names:
                try:
                    vision_model = genai.GenerativeModel(model_name)
                    logger.info(f"Using Gemini vision model: {model_name}")
                    break
                except Exception as e:
                    logger.debug(f"Model {model_name} not available: {e}")
                    continue
            
            if not vision_model:
                return {
                    "status": "error",
                    "message": "No suitable Gemini vision model available",
                    "description": ""
                }
            
            # Create prompt for describing circumstances
            prompt = """Describe the current circumstances visible in this image. Include:
- What is happening in the scene
- Who is present (if any people are visible)
- The environment and setting
- Any notable objects, activities, or situations
- The overall context and atmosphere

Provide a clear, detailed description that would help someone understand what is happening in this moment."""
            
            # Generate description
            response = vision_model.generate_content([prompt, pil_image])
            
            description = response.text if hasattr(response, 'text') else str(response)
            
            logger.info("Circumstances description generated successfully")
            
            return {
                "status": "success",
                "message": "Circumstances described successfully",
                "description": description,
                "image_captured": True
            }
            
        except Exception as e:
            logger.error(f"Error calling Gemini vision API: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return {
                "status": "error",
                "message": f"Failed to generate description: {str(e)}",
                "description": ""
            }
        
    except Exception as e:
        logger.error(f"Error in describe_circumstances: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return {
            "status": "error",
            "message": f"Failed to describe circumstances: {str(e)}",
            "description": ""
        }

definition = {
    "name": "describeCircumstances",
    "description": "CRITICAL VISION TOOL: Capture a photo from the camera and get a detailed description of the current circumstances using Gemini vision AI. This tool takes a photo, analyzes it with Gemini vision, and returns a description of what is happening, who is present, the environment, and the overall context. ALWAYS use this tool when the user asks about: 'circumstances', 'what's happening', 'what do you see', 'what's in front of you', 'describe the situation', 'tell me about the scene', 'what's around you', 'what can you see', 'describe what you see', or any variation asking about visual surroundings or current situation. This tool uses the robot's camera to see and understand the environment.",
    "parameters": {
        "type": "object",
        "properties": {},
        "required": []
    }
}

