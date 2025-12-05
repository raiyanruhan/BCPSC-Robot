import uuid
import logging
import json
from app.schemas import ControlDeviceArgs

logger = logging.getLogger(__name__)

# In-memory store for pending actions (in a real app, use Redis)
PENDING_ACTIONS = {}

async def control_device(args: ControlDeviceArgs) -> dict:
    """
    Request a control action. Returns an intent requiring confirmation.
    """
    request_id = str(uuid.uuid4())
    
    # Params is already parsed by Pydantic validator
    params = args.params if args.params else {}
    
    action_record = {
        "request_id": request_id,
        "device_id": args.device_id,
        "action": args.action,
        "params": params,
        "status": "pending_confirmation"
    }
    
    PENDING_ACTIONS[request_id] = action_record
    
    logger.info(f"Device control requested: {action_record}")
    
    return {
        "status": "pending_confirmation",
        "request_id": request_id,
        "message": f"Action '{args.action}' on device '{args.device_id}' requires admin confirmation. Request ID: {request_id}"
    }

definition = {
    "name": "controlDevice",
    "description": "Request a control action for a robot actuator. This MUST only return an intent; actual execution requires human confirmation via the admin endpoint.",
    "parameters": {
        "type": "object",
        "properties": {
            "device_id": {"type": "string", "description": "Device ID"},
            "action": {"type": "string", "description": "Action to perform"},
            "params": {
                "type": "string",
                "description": "Optional action parameters as a JSON string. Example: '{\"speed\": 50, \"direction\": \"forward\"}'"
            }
        },
        "required": ["device_id", "action"]
    }
}
