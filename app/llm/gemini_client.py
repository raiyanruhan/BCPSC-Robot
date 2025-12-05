import google.generativeai as genai
from app.config import settings
from app.llm.personality import SYSTEM_INSTRUCTION
import logging
from typing import List, AsyncGenerator, Any, Dict, Union
from google.generativeai.types import content_types
from google.protobuf import struct_pb2
from google.protobuf.json_format import MessageToDict
import traceback

logger = logging.getLogger(__name__)

def _convert_args_to_dict(args) -> dict:
    """Convert function call args to a Python dict, handling protobuf Struct objects."""
    try:
        if isinstance(args, dict):
            return args
        elif hasattr(args, 'fields'):
            # It's a protobuf Struct - convert it
            return MessageToDict(args)
        elif hasattr(args, '__iter__') and not isinstance(args, (str, bytes)):
            # Try to convert iterable to dict
            return dict(args)
        else:
            logger.warning(f"Unexpected args type: {type(args)}, using empty dict")
            return {}
    except Exception as e:
        logger.warning(f"Error converting args to dict: {e}, using empty dict")
        return {}

class GeminiClient:
    def __init__(self):
        genai.configure(api_key=settings.GEMINI_API_KEY)
        self.model = genai.GenerativeModel(
            settings.GEMINI_MODEL,
            system_instruction=SYSTEM_INSTRUCTION
        )

    async def stream_chat(
        self,
        chat_history: List[content_types.ContentDict],
        message: Union[str, List[Any]],
        tools: List[Any] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Streams responses from Gemini, handling both text and function calls.
        Yields dictionaries with 'type' ('text' or 'function_call') and 'content'.
        """
        try:
            # Configure tools if provided
            model = self.model
            if tools:
                # Log tools for debugging
                import json
                logger.debug(f"Tools being passed to Gemini: {json.dumps(tools, indent=2)}")
                model = genai.GenerativeModel(
                    settings.GEMINI_MODEL,
                    tools=tools,
                    system_instruction=SYSTEM_INSTRUCTION
                )

            chat = model.start_chat(history=chat_history)
            
            # Send message with streaming
            response_stream = await chat.send_message_async(message, stream=True)
            
            async for chunk in response_stream:
                # Check for function calls
                for part in chunk.parts:
                    if part.function_call:
                        # Yield function call
                        fc = part.function_call
                        try:
                            args_dict = _convert_args_to_dict(fc.args)
                            yield {
                                "type": "function_call",
                                "function_name": fc.name,
                                "args": args_dict
                            }
                        except Exception as e:
                            logger.error(f"Error processing function call: {e}\n{traceback.format_exc()}")
                            yield {
                                "type": "error",
                                "content": f"Error processing function call: {str(e)}"
                            }
                    elif part.text:
                        # Yield text
                        yield {
                            "type": "text",
                            "content": part.text
                        }
                        
        except Exception as e:
            error_msg = str(e) if e else repr(e)
            full_traceback = traceback.format_exc()
            logger.error(f"Error in Gemini stream_chat: {error_msg}\n{full_traceback}")
            # Include more context in error message for debugging
            if "KeyError" in str(type(e).__name__) or "KeyError" in error_msg:
                error_msg = f"{error_msg} - This suggests a schema format issue. Check tool definitions."
            yield {"type": "error", "content": error_msg}

gemini_client = GeminiClient()
