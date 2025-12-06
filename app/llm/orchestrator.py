import asyncio
import logging
import json
from typing import AsyncGenerator, List, Dict, Any
from app.llm.gemini_client import gemini_client
from app.llm.context_manager import context_manager
from app.tools import TOOL_DEFINITIONS, TOOL_FUNCTIONS
from app.cache.redis_cache import cache
from app.config import settings
import google.generativeai as genai

logger = logging.getLogger(__name__)

class Orchestrator:
    async def execute_tool(self, name: str, args: dict) -> dict:
        """
        Executes a single tool with caching and error handling.
        """
        if name not in TOOL_FUNCTIONS:
            return {"error": f"Tool {name} not found"}
        
        # Check cache
        # Cache key based on tool name and sorted args
        cache_key = f"tool:{name}:{json.dumps(args, sort_keys=True)}"
        cached_result = await cache.get(cache_key)
        if cached_result:
            logger.info(f"Cache hit for {name}")
            return cached_result
        
        # Execute tool
        try:
            func = TOOL_FUNCTIONS[name]
            # Validate args using Pydantic models? 
            # The tools themselves use Pydantic models in their signatures, 
            # but we need to convert the dict args to the model.
            # However, our tool functions take the Pydantic model as argument.
            # We can inspect the type hint or just let pydantic validation happen inside the tool if we wrapped it?
            # In my implementation, tools take `args: Model`.
            # I need to instantiate the model.
            
            # Get the type hint for the first argument
            import inspect
            sig = inspect.signature(func)
            param = list(sig.parameters.values())[0]
            model_class = param.annotation
            
            model_instance = model_class(**args)
            result = await func(model_instance)
            
            # Cache result if successful and not an error
            if "error" not in result:
                ttl = settings.DEFAULT_CACHE_TTL_SECONDS.get(name, 60)
                await cache.set(cache_key, result, ttl)
            
            return result
        except Exception as e:
            logger.error(f"Error executing tool {name}: {e}")
            return {"error": str(e)}

    async def process_chat(self, message: str, history: List[Dict[str, Any]]) -> AsyncGenerator[str, None]:
        """
        Main loop: User -> LLM -> [Tools] -> LLM -> User
        Yields SSE events as JSON strings.
        """
        
        # Enrich history with context awareness
        enriched_history = context_manager.enrich_history_with_context(history, message)
        
        # Build contextual message with awareness of what's happening
        from app.tools.device_control import PENDING_ACTIONS
        pending_count = len([a for a in PENDING_ACTIONS.values() if a.get("status") == "pending_confirmation"])
        
        # Extract recently used tools from history
        recent_tools = []
        for item in enriched_history[-10:]:
            if item.get("role") == "model":
                parts = item.get("parts", [])
                for part in parts:
                    if isinstance(part, dict) and "function_call" in part:
                        func_name = part["function_call"].get("name")
                        if func_name:
                            recent_tools.append(func_name)
        
        current_state = {
            "pending_actions": pending_count,
            "active_tools": list(set(recent_tools[-5:]))  # Last 5 unique tools
        }
        
        contextual_message = context_manager.build_contextual_message(
            message,
            enriched_history,
            current_state
        )
        
        # First call to LLM with enriched context
        async for event in self._run_llm_step(enriched_history, contextual_message):
            yield event
            
    async def _run_llm_step(self, history: List[Any], message: str) -> AsyncGenerator[str, None]:
        # This function handles one turn of LLM generation, potentially recursing if tools are called.
        # Actually, recursion is tricky with generators. Iteration is better.
        
        # We need to keep track of the conversation within this turn
        # The user message is added to history by the caller or `start_chat`.
        # Here we just pass the message.
        
        # But wait, if we call tools, we need to send the tool outputs back to the LLM *as part of the same turn* 
        # or as a new message in the chat session?
        # In Gemini, it's a multi-turn chat.
        # User: "What's the weather?"
        # Model: FunctionCall(getWeather)
        # User (Role: Function): {weather data}
        # Model: "It's sunny."
        
        # So we need to maintain a local history of this interaction if we want to support multiple tool calls in a chain?
        # Or just rely on the `chat` object in `gemini_client`?
        # `gemini_client` creates a new chat session each time in my implementation: `chat = model.start_chat(history=chat_history)`.
        # So we need to update `chat_history` and pass it back.
        
        # Let's refine `gemini_client` usage.
        # We should probably instantiate `gemini_client` once or pass the chat object?
        # But `gemini_client` is stateless in my wrapper.
        
        # Loop for tool calls
        loop_active = True
        current_message = message
        user_message_added = False  # Track if user message has been added to history
        
        # We need to accumulate the assistant's response to add to history for the next step
        # But since we are streaming, we build it up.
        
        while loop_active:
            loop_active = False # Default to stop unless function call happens
            
            tool_calls = []
            
            # Call LLM
            # We need to pass the updated history.
            # If this is the first iteration, `current_message` is the user message.
            # If this is subsequent iteration (after tool execution), `current_message` is the tool output.
            
            # We need to capture the full response to update history.
            full_response_text = ""
            function_call_parts = []
            
            async for chunk in gemini_client.stream_chat(history, current_message, tools=TOOL_DEFINITIONS):
                if chunk["type"] == "text":
                    full_response_text += chunk["content"]
                    yield json.dumps({"event": "token", "data": chunk["content"]})
                elif chunk["type"] == "function_call":
                    function_call_parts.append(chunk)
                    # Notify client of tool call
                    yield json.dumps({"event": "tool_call", "data": {"name": chunk["function_name"], "args": chunk["args"]}})
                elif chunk["type"] == "error":
                    error_data = chunk.get("content", "Unknown error")
                    if not isinstance(error_data, str):
                        error_data = str(error_data) if error_data else repr(error_data)
                    yield json.dumps({"event": "error", "data": error_data})
            
            # If we had function calls
            if function_call_parts:
                # Execute tools in parallel
                tasks = []
                for fc in function_call_parts:
                    tasks.append(self.execute_tool(fc["function_name"], fc["args"]))
                
                results = await asyncio.gather(*tasks)
                
                # Yield progress
                for fc, res in zip(function_call_parts, results):
                    yield json.dumps({"event": "tool_result", "data": {"name": fc["function_name"], "result": res}})
                
                # Update history with the User message (only once), Model function call, and Function response
                # User message (only add once, on first iteration)
                if not user_message_added:
                    history.append({"role": "user", "parts": [message]})
                    user_message_added = True
                
                # Model function call
                parts = []
                for fc in function_call_parts:
                    parts.append({
                        "function_call": {
                            "name": fc["function_name"],
                            "args": fc["args"]
                        }
                    })
                history.append({"role": "model", "parts": parts})
                
                # Function response
                parts = []
                for fc, res in zip(function_call_parts, results):
                    parts.append({
                        "function_response": {
                            "name": fc["function_name"],
                            "response": {"result": res} # Response must be a dict
                        }
                    })
                history.append({"role": "function", "parts": parts})
                
                # Prepare for next iteration - send function response as message
                loop_active = True
                
                # Prepare the message for the next iteration (Function Response)
                # Construct as list of parts that can be sent to the model
                response_parts = []
                for fc, res in zip(function_call_parts, results):
                    response_parts.append(
                        genai.protos.Part(
                            function_response=genai.protos.FunctionResponse(
                                name=fc["function_name"],
                                response={"result": res}
                            )
                        )
                    )
                current_message = response_parts
                
            else:
                # No function calls, we are done.
                # If we had text response, add it to history
                if full_response_text and not user_message_added:
                    # This shouldn't happen normally, but handle it
                    history.append({"role": "user", "parts": [message]})
                    user_message_added = True
                if full_response_text:
                    history.append({"role": "model", "parts": [full_response_text]})
                loop_active = False

orchestrator = Orchestrator()
