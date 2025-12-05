"""
World-Class Context Manager for BCPSC Robot
Implements advanced context awareness similar to enterprise AI systems.
Features: conversation summarization, semantic understanding, intelligent context injection
"""
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import json
import re

logger = logging.getLogger(__name__)

class ContextManager:
    """
    Advanced context manager with conversation summarization,
    semantic understanding, and intelligent context injection.
    """
    
    def __init__(self):
        self.conversation_summaries = {}
        self.max_history_items = 50  # Keep last 50 items for analysis
        self.summary_threshold = 20  # Summarize when history exceeds this
    
    def build_contextual_message(
        self,
        user_message: str,
        history: List[Dict[str, Any]],
        current_state: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Builds an enriched, intelligent contextual message.
        Uses conversation summarization and semantic understanding.
        """
        # Extract semantic information from user message
        message_intent = self._analyze_message_intent(user_message)
        
        # Check if this is the first message (no history or empty history)
        is_first_message = not history or len(history) == 0
        
        # Build context components
        context_components = []
        
        # 1. Temporal context
        temporal_context = self._get_temporal_context()
        context_components.append(temporal_context)
        
        # 2. First message indicator (for greeting)
        if is_first_message:
            context_components.append("IMPORTANT: This is the FIRST message in this conversation. Greet with 'Assalamu Alaikum' only this time.")
        else:
            context_components.append("IMPORTANT: This is NOT the first message. Do NOT greet - answer directly without 'Assalamu Alaikum'.")
        
        # 3. Conversation summary (intelligent compression)
        if history and not is_first_message:
            conversation_summary = self._build_conversation_summary(history, user_message)
            if conversation_summary:
                context_components.append(conversation_summary)
        
        # 4. Current state (fixed bug here)
        if current_state and not is_first_message:
            state_context = self._format_current_state(current_state)
            if state_context:
                context_components.append(state_context)
        
        # 5. Relevant history (semantic relevance) - only if not first message
        if not is_first_message:
            relevant_history = self._extract_relevant_history(history, user_message, message_intent)
            if relevant_history:
                context_components.append(relevant_history)
        
        # 6. Tool usage patterns - only if not first message
        if not is_first_message:
            tool_context = self._analyze_tool_usage(history)
            if tool_context:
                context_components.append(tool_context)
        
        # 7. Robot capabilities (condensed)
        capabilities = self._get_robot_capabilities()
        context_components.append(capabilities)
        
        # 8. STT/TTS reminder (important for response format)
        stt_reminder = self._get_stt_tts_reminder(message_intent)
        if stt_reminder:
            context_components.append(stt_reminder)
        
        # Build final contextual message with intelligent formatting
        # Only include non-empty components
        valid_components = [c for c in context_components if c and c.strip()]
        
        if valid_components:
            # Join with double newline for readability
            context_text = "\n\n".join(valid_components)
            # More natural, less verbose format
            enriched_message = f"""{context_text}

---

User: {user_message}

[Use context above to provide coherent response. Use tools when needed for current information.]"""
        else:
            enriched_message = f"{temporal_context}\n\nUser: {user_message}"
        
        return enriched_message
    
    def _get_stt_tts_reminder(self, intent: Dict[str, Any]) -> str:
        """Returns STT/TTS reminder if user is asking for code or formatted content."""
        intent_type = intent.get("type", "")
        message_keywords = intent.get("keywords", [])
        
        # Check if user is asking for code or formatted content
        code_indicators = ["code", "program", "script", "function", "write", "create", "generate", "python", "java", "javascript"]
        if any(keyword in code_indicators for keyword in message_keywords):
            return "REMINDER: Your responses are spoken via TTS. Do NOT write code - explain concepts verbally instead. Always use paragraph format, never markdown or lists."
        
        # Always remind about format
        return "REMINDER: Always respond in natural paragraph format with complete sentences. Never use bullet points, lists, markdown, or formatting symbols. Use appropriate emotions like 'haha', 'wow', 'great' when suitable."
    
    def _get_temporal_context(self) -> str:
        """Returns current date/time context."""
        now = datetime.now()
        day_name = now.strftime("%A")
        time_str = now.strftime("%H:%M")
        date_str = now.strftime("%Y-%m-%d")
        return f"Current Context: {day_name}, {date_str} at {time_str}"
    
    def _analyze_message_intent(self, message: str) -> Dict[str, Any]:
        """Analyzes user message to understand intent and extract key information."""
        message_lower = message.lower()
        
        intent = {
            "type": "general",
            "keywords": [],
            "entities": [],
            "requires_tool": False,
            "topic": "general"
        }
        
        # Detect intent types
        if any(word in message_lower for word in ["weather", "temperature", "forecast", "rain", "sunny"]):
            intent["type"] = "weather_query"
            intent["requires_tool"] = True
            intent["topic"] = "weather"
        elif any(word in message_lower for word in ["news", "headline", "article", "latest"]):
            intent["type"] = "news_query"
            intent["requires_tool"] = True
            intent["topic"] = "news"
        elif any(word in message_lower for word in ["who", "person", "teacher", "student", "principal"]):
            intent["type"] = "person_search"
            intent["requires_tool"] = True
            intent["topic"] = "person"
        elif any(word in message_lower for word in ["school", "bcpsc", "college", "institution"]):
            intent["type"] = "school_info"
            intent["requires_tool"] = True
            intent["topic"] = "school"
        elif any(word in message_lower for word in ["you", "yourself", "who are you", "what are you"]):
            intent["type"] = "robot_info"
            intent["requires_tool"] = True
            intent["topic"] = "robot"
        elif any(word in message_lower for word in ["search", "find", "look up", "google"]):
            intent["type"] = "web_search"
            intent["requires_tool"] = True
            intent["topic"] = "search"
        
        # Extract keywords (important words, excluding common stop words)
        stop_words = {"the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with", "is", "are", "was", "were", "be", "been", "have", "has", "had", "do", "does", "did", "will", "would", "could", "should", "may", "might", "can", "this", "that", "these", "those", "i", "you", "he", "she", "it", "we", "they", "what", "when", "where", "why", "how"}
        words = re.findall(r'\b\w+\b', message_lower)
        intent["keywords"] = [w for w in words if w not in stop_words and len(w) > 2][:5]
        
        return intent
    
    def _build_conversation_summary(self, history: List[Dict[str, Any]], current_message: str) -> str:
        """
        Builds an intelligent conversation summary.
        Uses compression and semantic understanding.
        """
        if not history:
            return ""
        
        # Analyze conversation structure
        total_turns = len(history)
        user_messages = [item for item in history if item.get("role") == "user"]
        model_responses = [item for item in history if item.get("role") == "model"]
        
        # Extract main topics discussed
        topics = self._extract_conversation_topics(history)
        
        # Extract key information shared (especially entities mentioned)
        key_info = self._extract_key_information(history)
        
        # Extract recent entities/names mentioned (critical for pronoun resolution)
        recent_entities = self._extract_recent_entities(history)
        
        # Extract entity mappings (e.g., "Raju Sir" -> "Brig Gen Md Raju Ahmed")
        entity_mappings = self._extract_entity_mappings(history)
        
        # Extract conversation flow (what user is currently asking about)
        conversation_flow = self._analyze_conversation_flow(history, current_message)
        
        # Build summary
        summary_parts = []
        
        if total_turns > 0:
            summary_parts.append(f"Conversation: {len(user_messages)} exchanges")
        
        # Most important: entity mappings for proper name resolution
        if entity_mappings:
            mapping_str = "; ".join([f"{k} = {v}" for k, v in entity_mappings.items()][:3])
            summary_parts.append(f"Name mappings: {mapping_str}")
        
        # Recent entities for pronoun resolution
        if recent_entities:
            summary_parts.append(f"Recent entities: {', '.join(recent_entities[:4])}")
        
        # Conversation flow - what user is asking about
        if conversation_flow:
            summary_parts.append(f"Current topic: {conversation_flow}")
        
        if topics:
            summary_parts.append(f"Topics discussed: {', '.join(topics[:3])}")
        
        if key_info:
            summary_parts.append(f"Key info: {key_info}")
        
        # Recent context (last 1-2 exchanges) - most important for immediate context
        recent_context = self._get_recent_context(history, limit=1)
        if recent_context:
            summary_parts.append(f"Last exchange: {recent_context}")
        
        if summary_parts:
            # More concise format
            return "Conversation Context:\n" + "\n".join(f"  • {part}" for part in summary_parts)
        
        return ""
    
    def _extract_conversation_topics(self, history: List[Dict[str, Any]]) -> List[str]:
        """Extracts main topics from conversation history."""
        topics = set()
        
        for item in history[-20:]:  # Last 20 items
            role = item.get("role", "")
            parts = item.get("parts", [])
            
            for part in parts:
                text = ""
                if isinstance(part, str):
                    text = part
                elif isinstance(part, dict):
                    text = part.get("text", "")
                
                if text:
                    # Extract potential topics (simple keyword extraction)
                    words = re.findall(r'\b[A-Z][a-z]+\b', text)  # Capitalized words often indicate entities
                    topics.update(words[:3])
                    
                    # Also check for common topic indicators
                    text_lower = text.lower()
                    if "weather" in text_lower:
                        topics.add("weather")
                    if "school" in text_lower or "bcpsc" in text_lower:
                        topics.add("school")
                    if "person" in text_lower or "teacher" in text_lower:
                        topics.add("people")
                    if "news" in text_lower:
                        topics.add("news")
        
        return list(topics)[:10]
    
    def _extract_key_information(self, history: List[Dict[str, Any]]) -> str:
        """Extracts key information that was shared in the conversation."""
        key_info = []
        
        for item in history[-10:]:
            role = item.get("role", "")
            parts = item.get("parts", [])
            
            if role == "function":
                # Tool results contain key information
                for part in parts:
                    if isinstance(part, dict) and "function_response" in part:
                        func_name = part["function_response"].get("name", "")
                        response = part["function_response"].get("response", {})
                        if isinstance(response, dict):
                            result = response.get("result", {})
                            if isinstance(result, dict):
                                # Extract key fields
                                if "location" in result:
                                    key_info.append(f"Location: {result.get('location')}")
                                if "name" in result:
                                    key_info.append(f"Person: {result.get('name')}")
                                if "temperature" in result:
                                    key_info.append(f"Weather: {result.get('temperature')}°")
        
        return "; ".join(key_info[:3]) if key_info else ""
    
    def _get_recent_context(self, history: List[Dict[str, Any]], limit: int = 3) -> str:
        """Gets the most recent context from conversation."""
        recent_items = []
        
        # Go through history in reverse to get most recent first
        for item in reversed(history[-limit*4:]):  # Check more items
            role = item.get("role", "")
            parts = item.get("parts", [])
            
            for part in parts:
                text = ""
                if isinstance(part, str):
                    text = part
                elif isinstance(part, dict):
                    text = part.get("text", "")
                
                if text and len(text) > 10:
                    if role == "user":
                        recent_items.insert(0, f"User: {text[:100]}")  # Insert at beginning to maintain order
                    elif role == "model":
                        recent_items.insert(0, f"Assistant: {text[:100]}")
                    if len(recent_items) >= limit * 2:  # Get user + assistant pairs
                        break
            
            if len(recent_items) >= limit * 2:
                break
        
        # Return in chronological order
        return " | ".join(recent_items) if recent_items else ""
    
    def _extract_recent_entities(self, history: List[Dict[str, Any]]) -> List[str]:
        """Extracts recently mentioned entities (names, places) for pronoun resolution."""
        entities = []
        
        # Also check tool results for names
        for item in reversed(history[-15:]):  # Last 15 items, most recent first
            role = item.get("role", "")
            parts = item.get("parts", [])
            
            # Check tool results for names
            if role == "function":
                for part in parts:
                    if isinstance(part, dict) and "function_response" in part:
                        response = part["function_response"].get("response", {})
                        if isinstance(response, dict):
                            result = response.get("result", {})
                            if isinstance(result, dict):
                                # Extract names from tool results
                                if "name" in result:
                                    name = result.get("name")
                                    if name and name not in entities:
                                        entities.append(name)
                                if "person_name" in result:
                                    name = result.get("person_name")
                                    if name and name not in entities:
                                        entities.append(name)
                                if "title" in result:
                                    title = result.get("title")
                                    # Extract name from title if it's a person
                                    if title and "Bill Gates" in title or "Gates" in title:
                                        entities.append("Bill Gates")
            
            # Extract from text
            for part in parts:
                text = ""
                if isinstance(part, str):
                    text = part
                elif isinstance(part, dict):
                    text = part.get("text", "")
                
                if text:
                    # Extract capitalized words (likely names/entities)
                    # Match full names (e.g., "Bill Gates", "William Henry Gates")
                    full_names = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+\b', text)
                    for entity in full_names:
                        # Filter out common phrases
                        if entity not in ["User", "Assistant", "Tool", "Result", "Call", "Brain", "Robot"] and len(entity) > 3:
                            if entity not in entities:
                                entities.append(entity)
                    
                    # Also extract single capitalized words that might be names
                    single_words = re.findall(r'\b[A-Z][a-z]{3,}\b', text)
                    for word in single_words:
                        # Common names or important entities
                        if word not in ["User", "Assistant", "Tool", "Result", "Call", "Brain", "Robot", "The", "This", "That"]:
                            if word not in entities and len(entities) < 8:  # Limit to avoid too many
                                entities.append(word)
                
                if len(entities) >= 8:  # Top 8 most recent entities
                    break
            
            if len(entities) >= 8:
                break
        
        return entities[:5]  # Return top 5
    
    def _extract_entity_mappings(self, history: List[Dict[str, Any]]) -> Dict[str, str]:
        """
        Extracts entity mappings from conversation.
        e.g., "Raju Sir" -> "Brig Gen Md Raju Ahmed"
        """
        mappings = {}
        
        # Look for patterns where user mentions a name and we respond with full name
        user_mentions = []
        model_responses = []
        
        for item in history[-10:]:
            role = item.get("role", "")
            parts = item.get("parts", [])
            
            for part in parts:
                text = ""
                if isinstance(part, str):
                    text = part
                elif isinstance(part, dict):
                    text = part.get("text", "")
                
                if text:
                    if role == "user":
                        user_mentions.append(text)
                    elif role == "model":
                        model_responses.append(text)
                    elif role == "function":
                        # Check tool results for name mappings
                        if isinstance(part, dict) and "function_response" in part:
                            response = part["function_response"].get("response", {})
                            if isinstance(response, dict):
                                result = response.get("result", {})
                                if isinstance(result, dict):
                                    # If we searched for a person and found a full name
                                    if "person_name" in result and "info" in result:
                                        info = result.get("info", {})
                                        if isinstance(info, dict) and "name" in info:
                                            # Map search query to found name
                                            search_query = result.get("person_name", "")
                                            found_name = info.get("name", "")
                                            if search_query and found_name and search_query.lower() != found_name.lower():
                                                mappings[search_query] = found_name
        
        # Also check for patterns in text where we mention "X refers to Y"
        for response in model_responses:
            # Pattern: "X refers to Y" or "X is Y"
            patterns = [
                r'"([^"]+)"\s+refers?\s+to\s+([A-Z][^,\.]+)',
                r'"([^"]+)"\s+is\s+([A-Z][^,\.]+)',
                r'([A-Z][a-z]+\s+Sir)\s+refers?\s+to\s+([A-Z][^,\.]+)',
            ]
            for pattern in patterns:
                matches = re.findall(pattern, response)
                for match in matches:
                    if len(match) == 2:
                        short_name, full_name = match
                        if short_name and full_name:
                            mappings[short_name.strip()] = full_name.strip()
        
        return mappings
    
    def _analyze_conversation_flow(self, history: List[Dict[str, Any]], current_message: str) -> str:
        """
        Analyzes what the user is currently asking about based on conversation flow.
        Helps distinguish between separate topics vs follow-ups.
        """
        if not history:
            return ""
        
        # Get last few user messages and model responses to understand the flow
        recent_exchanges = []
        for item in reversed(history[-8:]):
            role = item.get("role", "")
            parts = item.get("parts", [])
            
            for part in parts:
                text = ""
                if isinstance(part, str):
                    text = part
                elif isinstance(part, dict):
                    text = part.get("text", "")
                
                if text and len(text) > 5:
                    recent_exchanges.insert(0, (role, text))
                    if len(recent_exchanges) >= 4:  # Last 2 user-assistant pairs
                        break
            
            if len(recent_exchanges) >= 4:
                break
        
        # Analyze the flow
        flow_parts = []
        current_lower = current_message.lower()
        
        # Check if current message is a new topic or follow-up
        if recent_exchanges:
            # Get the most recent user message before current
            last_user_msg = None
            for role, text in reversed(recent_exchanges):
                if role == "user":
                    last_user_msg = text
                    break
            
            # Detect if this is a follow-up or new topic
            follow_up_indicators = ["more", "about", "tell", "explain", "who", "what", "how", "yes", "no", "him", "her", "it", "that", "this"]
            is_follow_up = any(word in current_lower for word in follow_up_indicators)
            
            if is_follow_up and last_user_msg:
                # This might be a follow-up - check if it references previous topic
                # Extract entities from last user message
                last_entities = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', last_user_msg)
                current_entities = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', current_message)
                
                # If current message has different entities, it's likely a new topic
                if current_entities and last_entities:
                    if not any(e in last_entities for e in current_entities):
                        # Different entities = new topic
                        flow_parts.append(f"New topic: {current_entities[0]}")
                    else:
                        # Same entities = follow-up
                        flow_parts.append(f"Follow-up about: {last_entities[0]}")
                elif last_entities:
                    # Current message has no entities but last did - likely follow-up
                    flow_parts.append(f"Follow-up about: {last_entities[0]}")
            else:
                # New topic - extract key terms
                key_terms = []
                # Extract important words (nouns, proper nouns)
                words = re.findall(r'\b[A-Z][a-z]+\b', current_message)
                if words:
                    key_terms.extend(words[:2])
                else:
                    # Fallback to important lowercase words
                    important_words = [w for w in current_message.split() if len(w) > 4 and w.lower() not in ["about", "tell", "explain"]][:2]
                    key_terms.extend(important_words)
                
                if key_terms:
                    flow_parts.append(f"New topic: {' '.join(key_terms)}")
        
        return " | ".join(flow_parts) if flow_parts else ""
    
    def _extract_relevant_history(
        self,
        history: List[Dict[str, Any]],
        current_message: str,
        intent: Dict[str, Any]
    ) -> str:
        """Extracts semantically relevant history based on current message intent."""
        if not history or not intent.get("keywords"):
            return ""
        
        relevant_items = []
        keywords = intent["keywords"]
        topic = intent.get("topic", "")
        
        # Score history items by relevance
        scored_items = []
        for item in history[-30:]:  # Check last 30 items
            parts = item.get("parts", [])
            relevance_score = 0
            
            for part in parts:
                text = ""
                if isinstance(part, str):
                    text = part
                elif isinstance(part, dict):
                    text = part.get("text", "")
                
                if text:
                    text_lower = text.lower()
                    # Score based on keyword matches
                    for keyword in keywords:
                        if keyword in text_lower:
                            relevance_score += 1
                    
                    # Score based on topic match
                    if topic and topic in text_lower:
                        relevance_score += 2
                    
                    if relevance_score > 0:
                        scored_items.append((relevance_score, text[:150]))
        
        # Get top 2 most relevant items
        scored_items.sort(reverse=True, key=lambda x: x[0])
        for score, text in scored_items[:2]:
            if score > 0:
                relevant_items.append(text)
        
        if relevant_items:
            return f"Relevant previous context: {' | '.join(relevant_items)}"
        
        return ""
    
    def _analyze_tool_usage(self, history: List[Dict[str, Any]]) -> str:
        """Analyzes tool usage patterns to provide context."""
        tools_used = []
        tool_results = {}
        
        for item in history[-20:]:
            role = item.get("role", "")
            parts = item.get("parts", [])
            
            if role == "model":
                for part in parts:
                    if isinstance(part, dict) and "function_call" in part:
                        func_name = part["function_call"].get("name", "")
                        if func_name:
                            tools_used.append(func_name)
            
            elif role == "function":
                for part in parts:
                    if isinstance(part, dict) and "function_response" in part:
                        func_name = part["function_response"].get("name", "")
                        response = part["function_response"].get("response", {})
                        if func_name:
                            tool_results[func_name] = response
        
        if tools_used:
            unique_tools = list(set(tools_used))
            tool_info = f"Tools used in conversation: {', '.join(unique_tools[-5:])}"
            
            # Add note about recent tool results if relevant
            if tool_results:
                tool_info += f" (Recent results available)"
            
            return tool_info
        
        return ""
    
    def _format_current_state(self, state: Dict[str, Any]) -> str:
        """Formats current system state information (FIXED BUG)."""
        state_parts = []
        
        if "pending_actions" in state:
            # FIX: pending_actions is already an integer (count), not a list
            pending_count = state["pending_actions"]
            if isinstance(pending_count, int) and pending_count > 0:
                state_parts.append(f"Pending device actions requiring confirmation: {pending_count}")
            elif not isinstance(pending_count, int):
                # Handle edge case where it might be a list
                count = len(pending_count) if hasattr(pending_count, '__len__') else 0
                if count > 0:
                    state_parts.append(f"Pending device actions: {count}")
        
        if "active_tools" in state:
            tools = state["active_tools"]
            if isinstance(tools, list) and tools:
                state_parts.append(f"Recently used tools: {', '.join(tools)}")
        
        if state_parts:
            return "Current System State:\n" + "\n".join(f"- {part}" for part in state_parts)
        
        return ""
    
    def _get_robot_capabilities(self) -> str:
        """Returns condensed robot capabilities."""
        return """Available Tools: getWeather, getWeatherForecast, getNews, webSearch, getSchoolInfo, searchPerson, getDeveloperInfo, getRobotInfo, controlDevice. Use tools when you need current, real-time information."""
    
    def enrich_history_with_context(
        self,
        history: List[Dict[str, Any]],
        user_message: str
    ) -> List[Dict[str, Any]]:
        """
        Enriches history with contextual information.
        Ensures proper format for Gemini with intelligent normalization.
        """
        enriched_history = []
        
        for item in history:
            if isinstance(item, dict):
                role = item.get("role", "user")
                parts = item.get("parts", [])
                
                # Normalize parts
                normalized_parts = []
                for part in parts:
                    if isinstance(part, str):
                        normalized_parts.append(part)
                    elif isinstance(part, dict):
                        normalized_parts.append(part)
                    else:
                        normalized_parts.append(str(part))
                
                if normalized_parts:  # Only add if has parts
                    enriched_history.append({
                        "role": role,
                        "parts": normalized_parts
                    })
            else:
                enriched_history.append({"role": "user", "parts": [str(item)]})
        
        return enriched_history

context_manager = ContextManager()
