import asyncio
import httpx
import json
import sys

async def chat():
    print("Robot Brain Interactive Chat (type 'quit' to exit)")
    url = "http://localhost:8000/api/v1/chat"
    
    # Maintain conversation history
    conversation_history = []
    
    async with httpx.AsyncClient() as client:
        while True:
            try:
                user_input = input("\nYou: ")
                if user_input.lower() in ['quit', 'exit']:
                    break
            except EOFError:
                break
                
            try:
                # Add user message to history
                conversation_history.append({
                    "role": "user",
                    "parts": [user_input]
                })
                
                # Send request with history
                async with client.stream(
                    "POST", 
                    url, 
                    json={
                        "message": user_input,
                        "history": conversation_history[:-1]  # Send history without current message
                    }, 
                    timeout=None
                ) as response:
                    print("Brain: ", end="", flush=True)
                    
                    # Collect assistant response for history
                    assistant_response_parts = []
                    full_text_response = ""
                    tool_calls_in_turn = []
                    tool_results_in_turn = []
                    
                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            data_str = line[6:]
                            if data_str == "[DONE]":
                                break
                            try:
                                data = json.loads(data_str)
                                if data['event'] == 'token':
                                    token = data['data']
                                    print(token, end="", flush=True)
                                    full_text_response += token
                                elif data['event'] == 'tool_call':
                                    tool_name = data['data']['name']
                                    tool_args = data['data'].get('args', {})
                                    print(f"\n[Tool Call: {tool_name}]", end="", flush=True)
                                    tool_calls_in_turn.append({
                                        "function_call": {
                                            "name": tool_name,
                                            "args": tool_args
                                        }
                                    })
                                elif data['event'] == 'tool_result':
                                    tool_name = data['data']['name']
                                    tool_result = data['data'].get('result', {})
                                    print(f"\n[Tool Result: {tool_name}]", end="", flush=True)
                                    tool_results_in_turn.append({
                                        "function_response": {
                                            "name": tool_name,
                                            "response": {"result": tool_result}
                                        }
                                    })
                                elif data['event'] == 'error':
                                    print(f"\n[Error: {data['data']}]")
                            except json.JSONDecodeError:
                                pass
                    
                    print()
                    
                    # Update history with assistant response
                    # Handle different response types
                    if tool_calls_in_turn:
                        # Model made function calls
                        function_call_parts = []
                        for tool_call in tool_calls_in_turn:
                            function_call_parts.append(tool_call)
                        
                        conversation_history.append({
                            "role": "model",
                            "parts": function_call_parts
                        })
                        
                        # Add tool results
                        if tool_results_in_turn:
                            for tool_result in tool_results_in_turn:
                                conversation_history.append({
                                    "role": "function",
                                    "parts": [tool_result]
                                })
                        
                        # If there's also text after tool calls, add it
                        if full_text_response:
                            conversation_history.append({
                                "role": "model",
                                "parts": [full_text_response]
                            })
                    elif full_text_response:
                        # Only text response, no tool calls
                        conversation_history.append({
                            "role": "model",
                            "parts": [full_text_response]
                        })
                    
            except Exception as e:
                print(f"\nError connecting to server: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(chat())
    except KeyboardInterrupt:
        pass
