from app.schemas import GetRobotInfoArgs
import logging

logger = logging.getLogger(__name__)

async def get_robot_info(args: GetRobotInfoArgs) -> dict:
    """
    Returns information about BCPSC Robot - the robot's own identity and capabilities.
    """
    query = args.query.lower().strip() if args.query else ""
    
    # Return comprehensive robot information
    robot_info = {
        "name": "BCPSC Robot",
        "type": "Humanoid Robot",
        "category": "First school-level humanoid robot in Bangladesh",
        "project_start": "September 2025",
        "developed_by": "BCPSC Robotics Team",
        "lead_software_developer": "Raiyan Bin Rashid",
        "origin": "BCPSC Robot was created entirely in-house by student developers at BCPSC. All hardware assembly, motor control, AI systems, and software pipelines were built from scratch within the team.",
        "software_components": {
            "operating_system": "Custom operating and control system made for BCPSC",
            "face_detection_model": "yunet_2023mar.onnx",
            "face_recognition_model": "sface_2021dec.onnx",
            "speech_modules": "Speech-to-Text and Text-to-Speech modules",
            "core_systems": [
                "Task manager",
                "Memory system",
                "Action engine",
                "Real-time motor controller for humanoid movement",
                "Multimodal AI processing pipeline"
            ]
        },
        "highlights": [
            "First humanoid robot built by a school team in Bangladesh",
            "Built using only internal talent, creativity, and engineering",
            "Capable of face recognition, conversation, and coordinated movement",
            "Acts as a symbol of innovation, robotics education, and future technology at BCPSC"
        ],
        "capabilities": [
            "Face detection and recognition",
            "Natural language conversation",
            "Coordinated humanoid movement",
            "Multimodal AI processing",
            "Real-time motor control"
        ],
        "institution": "Bogura Cantonment Public School & College (BCPSC)"
    }
    
    # If query is specific, return relevant subset
    if "software" in query or "system" in query or "model" in query:
        return {
            "query": args.query,
            "info": {
                "name": robot_info["name"],
                "software_components": robot_info["software_components"],
                "capabilities": robot_info["capabilities"]
            }
        }
    
    if "developer" in query or "created" in query or "built" in query or "made" in query:
        return {
            "query": args.query,
            "info": {
                "name": robot_info["name"],
                "developed_by": robot_info["developed_by"],
                "lead_software_developer": robot_info["lead_software_developer"],
                "project_start": robot_info["project_start"],
                "origin": robot_info["origin"]
            }
        }
    
    if "capability" in query or "can" in query or "ability" in query or "do" in query:
        return {
            "query": args.query,
            "info": {
                "name": robot_info["name"],
                "capabilities": robot_info["capabilities"],
                "highlights": robot_info["highlights"]
            }
        }
    
    # Return full info for general queries
    return {
        "query": args.query,
        "info": robot_info
    }

definition = {
    "name": "getRobotInfo",
    "description": "Get information about BCPSC Robot - the robot's own identity, capabilities, development history, and technical details. Use this when users ask 'Who are you?', 'What are you?', 'Tell me about yourself', 'What can you do?', or questions about the robot's systems, developers, or capabilities.",
    "parameters": {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Query about the robot (e.g., 'who are you', 'what are you', 'tell me about yourself', 'what can you do', 'your software', 'your developers', etc.). Can be empty for general info."}
        },
        "required": ["query"]
    }
}

