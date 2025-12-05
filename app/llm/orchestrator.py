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
        
        # We need to accumulate the assistant's response to add to history for the next step
        # But since we are streaming, we build it up.
        
        while loop_active:
            loop_active = False # Default to stop unless function call happens
            
            tool_calls = []
            
            # Call LLM
            # We need to pass the updated history.
            # If this is the first iteration, `current_message` is the user message.
            # If this is subsequent iteration (after tool execution), `current_message` is the tool output?
            # No, in Gemini `send_message` handles the user message.
            # If we are sending tool outputs, we send them as a message with role 'function'?
            # The SDK `chat.send_message` handles this.
            
            # Wait, my `gemini_client` wrapper creates a NEW chat session every time.
            # This is inefficient and might break context if we don't pass the FULL history including the intermediate tool calls.
            # So `history` must be updated.
            
            # Let's assume `gemini_client.stream_chat` yields events.
            
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
                
                # Update history with the Assistant's Function Call and the Function Response
                # We need to construct the history objects correctly for Gemini.
                # This is getting complicated to do with a stateless wrapper.
                # It's better if `gemini_client` exposed a stateful chat session or if we manually constructed the Content objects.
                
                # For this task, I will simplify:
                # 1. Add User message to history.
                # 2. Add Model response (function call) to history.
                # 3. Add Function response to history.
                # 4. Call model again with empty text? Or with the function response?
                
                # In `google-generativeai`, `chat.send_message` returns a response.
                # If we use `chat.send_message(tool_outputs)`, it continues.
                
                # I should refactor `gemini_client` to return the `chat` object or handle the loop internally?
                # Or just pass the accumulated history.
                
                # Let's update history manually.
                # User message is already handled by `start_chat` if we pass it as history? No, `start_chat(history=...)` sets past history.
                # The `message` arg in `stream_chat` is the NEW message.
                
                # So:
                # 1. `history` has past turns.
                # 2. `stream_chat` sends `message` (User).
                # 3. We get `function_call`.
                # 4. We execute tools.
                # 5. We need to call `stream_chat` again.
                #    But `stream_chat` starts a NEW chat.
                #    So we must append (User: message), (Model: function_call), (Function: result) to `history`.
                #    And then call `stream_chat` with a dummy message or just the function result?
                
                # Actually, `chat.send_message` is what we want.
                # If I recreate `chat` every time, I must reconstruct the state.
                
                # Let's try to make `gemini_client` more flexible or just handle the history construction here.
                # Constructing `content_types.ContentDict` is verbose.
                
                # Alternative: Use a persistent `ChatSession` in `gemini_client`?
                # But this is a REST API, we don't keep state between requests easily unless we serialize it.
                # The user request `POST /chat` implies a single turn or sending full history.
                # Let's assume we send full history.
                
                # Update history:
                # User message
                history.append({"role": "user", "parts": [message]})
                
                # Model function call
                parts = []
                for fc in function_call_parts:
                    # Construct part for function call
                    # This is tricky without the SDK objects.
                    # The SDK expects `Part(function_call=FunctionCall(...))`
                    # We can use `genai.protos.Part` or dicts if supported.
                    # `content_types.to_content` handles dicts.
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
                
                # Prepare for next iteration
                # The next message to send is... nothing? We just want the model to continue.
                # But `chat.send_message` expects a message.
                # If we reconstructed the history, we can just call `chat.send_message` with the LAST part?
                # No, `start_chat(history=...)` initializes the state.
                # If the last item in history is `function_response`, the model should generate the next response automatically?
                # No, we need to trigger generation.
                # In the stateless approach:
                # We pass `history` (which now ends with function_response).
                # And we send an empty message? Or we don't send a message, just `model.generate_content(history)`?
                # `chat.send_message` adds to history.
                
                # Actually, if we use `model.generate_content(history)`, it generates the NEXT message.
                # So we don't use `chat` object, we just use `generate_content`.
                # But `generate_content` is not chat-aware unless we format history correctly.
                
                # Let's change `gemini_client.stream_chat` to accept `history` and `message` is optional?
                # Or just use `chat.send_message` but we need to be careful about what we send.
                
                # If I append everything to `history`, then I can start a chat with `history[:-1]` and send `history[-1]`?
                # That works.
                
                # So:
                # 1. Append User message to `history`.
                # 2. Call LLM (send `message`).
                # 3. Get Function Call.
                # 4. Append Model (FC) to `history`.
                # 5. Execute tools.
                # 6. Append Function (Response) to `history`.
                # 7. Loop: Call LLM (send... what?).
                #    If we start a new chat with `history` (including function response), we can send an empty message or prompt it to continue?
                #    Actually, if we use `chat.send_message`, we are sending a NEW user message.
                #    But here we are in the middle of a turn.
                #    The "Function" role is a user-side role in some APIs, but in Gemini it's distinct.
                
                # Correct flow with `chat` object:
                # chat = model.start_chat()
                # response = chat.send_message(user_msg)
                # if response.parts[0].function_call:
                #    tool_output = ...
                #    response = chat.send_message(tool_output) # Send function response
                
                # Since I am stateless, I need to simulate this.
                # I can reconstruct the `chat` object with history up to the user message.
                # Then `send_message` (User message).
                # Receive FC.
                # Then I have a problem: I can't easily "continue" the same `chat` object instance if I lost it.
                # But I can recreate it.
                # `chat = model.start_chat(history=history_with_user_and_fc)`
                # `response = chat.send_message(function_response)`
                
                # YES. This is the way.
                
                # So, in the loop:
                # `current_message` will be the content to send.
                # In first iteration: `current_message` = User text. `history` = past conversation.
                # In next iteration: `current_message` = Function Response part. `history` = past + User + Model(FC).
                
                # Update `current_message` to be the function response parts.
                # Note: `gemini_client.stream_chat` expects `message` as str?
                # I defined it as `str`. I should update it to accept `Union[str, List[Part]]`.
                
                # Let's update `gemini_client.py` first to be more flexible.
                
                # But wait, `gemini_client.stream_chat` takes `message: str`.
                # I should change it to `message: Union[str, Any]`.
                
                # Also, I need to handle the `history` update correctly in `Orchestrator`.
                
                # Let's modify `gemini_client.py` to allow sending non-string messages (like function responses).
                
                loop_active = True
                
                # Prepare the message for the next iteration (Function Response)
                # We need to construct the parts.
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
                loop_active = False

orchestrator = Orchestrator()
