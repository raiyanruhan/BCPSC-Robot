from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from app.schemas import BaseModel
from typing import List, Optional, Dict, Any
from app.llm.orchestrator import orchestrator
from app.tools.device_control import control_device, PENDING_ACTIONS
from app.schemas import ControlDeviceArgs
import logging
import json
import traceback

router = APIRouter()
logger = logging.getLogger(__name__)

class ChatRequest(BaseModel):
    message: str
    history: Optional[List[Dict[str, Any]]] = []

@router.post("/chat")
async def chat_endpoint(request: ChatRequest):
    """
    Chat endpoint that streams SSE events.
    """
    async def event_generator():
        try:
            async for event in orchestrator.process_chat(request.message, request.history):
                yield f"data: {event}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as e:
            error_msg = str(e) if e else repr(e)
            logger.error(f"Error in chat stream: {error_msg}\n{traceback.format_exc()}")
            yield f"data: {json.dumps({'event': 'error', 'data': error_msg})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

@router.post("/admin/confirm")
async def admin_confirm(request_id: str, admin_token: str):
    """
    Confirms a pending device control action.
    """
    from app.config import settings
    
    if admin_token != settings.ADMIN_TOKEN:
        raise HTTPException(status_code=403, detail="Invalid admin token")
    
    action = PENDING_ACTIONS.get(request_id)
    if not action:
        raise HTTPException(status_code=404, detail="Request ID not found")
    
    if action["status"] != "pending_confirmation":
        raise HTTPException(status_code=400, detail="Action already processed")
    
    # Execute the action (Stub)
    action["status"] = "confirmed"
    logger.info(f"Action confirmed and executed: {action}")
    
    return {"status": "success", "message": "Action confirmed and executed", "action": action}

@router.get("/health")
async def api_health():
    return {"status": "ok", "component": "api"}
