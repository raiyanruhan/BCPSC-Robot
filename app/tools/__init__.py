from .weather import definition as weather_def, get_weather
from .weather_forecast import definition as weather_forecast_def, get_weather_forecast
from .news import definition as news_def, get_news
from .web_search import definition as search_def, web_search
from .school_info import definition as school_def, get_school_info
from .developer_info import definition as dev_def, get_developer_info
from .person_search import definition as person_search_def, search_person
from .robot_info import definition as robot_info_def, get_robot_info
from .device_control import definition as device_def, control_device
import copy

def _convert_schema_for_gemini(schema, is_top_level=False):
    """Convert JSON Schema to Gemini-compatible format.
    
    CRITICAL: Gemini's Schema protobuf REQUIRES "type": "OBJECT" (uppercase enum)
    when the schema has "properties"! The error "properties: only allowed for OBJECT type"
    means we MUST set type to "OBJECT" for schemas with properties.
    
    It does NOT support:
    - "minimum", "maximum" (validation constraints)
    - "default" values
    - "enum" (use description instead)
    - "type" in nested property definitions (only top-level needs it)
    
    It supports:
    - "type": "OBJECT" (required for schemas with properties)
    - "properties" (for object schemas)
    - "items" (for array schemas)
    - "description"
    - "required"
    - "additionalProperties"
    """
    if not isinstance(schema, dict):
        return schema
    
    schema = copy.deepcopy(schema)
    
    # For top-level schema with properties, MUST set type to "OBJECT"
    if is_top_level and "properties" in schema:
        schema["type"] = "OBJECT"
    
    # Remove unsupported validation fields (but keep "type" for top-level)
    unsupported_fields = ["minimum", "maximum", "default", "enum"]
    if not is_top_level:
        # Remove "type" from nested schemas (only top-level needs it)
        unsupported_fields.append("type")
    
    for field in unsupported_fields:
        schema.pop(field, None)
    
    # Process properties - keep "type" for primitive types (string, integer, etc.) but remove from nested objects
    if "properties" in schema:
        for prop_name, prop_def in list(schema["properties"].items()):
            if isinstance(prop_def, dict):
                # Keep "type" for primitive types (string, integer, number, boolean, array)
                # Only remove "type" if it's "object" (nested object schema)
                prop_type = prop_def.get("type")
                if prop_type == "object":
                    prop_def.pop("type", None)
                # Remove unsupported validation fields (but keep "type" for primitives)
                for field in ["minimum", "maximum", "default", "enum"]:
                    prop_def.pop(field, None)
                # Recursively process nested structures (not top-level)
                prop_def = _convert_schema_for_gemini(prop_def, is_top_level=False)
                schema["properties"][prop_name] = prop_def
    
    # Handle "items" for array types (not top-level)
    if "items" in schema and isinstance(schema["items"], dict):
        schema["items"] = _convert_schema_for_gemini(schema["items"], is_top_level=False)
    
    # Handle "additionalProperties" (not top-level)
    if "additionalProperties" in schema and isinstance(schema["additionalProperties"], dict):
        schema["additionalProperties"] = _convert_schema_for_gemini(schema["additionalProperties"], is_top_level=False)
    
    return schema

def _convert_tool_for_gemini(tool_def):
    """Convert a tool definition to Gemini-compatible format."""
    converted = copy.deepcopy(tool_def)
    if "parameters" in converted:
        # Convert schema - top-level MUST have "type": "OBJECT" if it has properties
        converted["parameters"] = _convert_schema_for_gemini(converted["parameters"], is_top_level=True)
    return converted

# List of tool definitions for Gemini (converted format)
TOOL_DEFINITIONS = [
    _convert_tool_for_gemini(weather_def),
    _convert_tool_for_gemini(weather_forecast_def),
    _convert_tool_for_gemini(news_def),
    _convert_tool_for_gemini(search_def),
    _convert_tool_for_gemini(school_def),
    _convert_tool_for_gemini(dev_def),
    _convert_tool_for_gemini(person_search_def),
    _convert_tool_for_gemini(robot_info_def),
    _convert_tool_for_gemini(device_def)
]

# Map function names to callables
TOOL_FUNCTIONS = {
    "getWeather": get_weather,
    "getWeatherForecast": get_weather_forecast,
    "getNews": get_news,
    "webSearch": web_search,
    "getSchoolInfo": get_school_info,
    "getDeveloperInfo": get_developer_info,
    "searchPerson": search_person,
    "getRobotInfo": get_robot_info,
    "controlDevice": control_device
}
