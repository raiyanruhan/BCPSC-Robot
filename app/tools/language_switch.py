from app.schemas import SwitchLanguageArgs
import logging

logger = logging.getLogger(__name__)

# Global callback for language switching (set by voice_robot)
_language_switch_callback = None

def set_language_switch_callback(callback):
    """Set the callback function to switch STT language. Called by voice_robot."""
    global _language_switch_callback
    _language_switch_callback = callback

async def switch_stt_language(args: SwitchLanguageArgs) -> dict:
    """
    Switches the Speech-to-Text (STT) language for the voice robot.
    This allows the robot to understand speech in the specified language.
    
    Args:
        language: Target language code - "en-US" for English, "bn-BD" for Bangla
        reason: Optional reason for the switch (for logging/debugging)
    
    Returns:
        dict with status and current language
    """
    global _language_switch_callback
    
    # Call the callback if it's set (by voice_robot)
    if _language_switch_callback:
        try:
            _language_switch_callback(args.language)
            logger.info(f"STT language switched to {args.language} via callback")
        except Exception as e:
            logger.error(f"Error switching language via callback: {e}")
            return {
                "status": "error",
                "language": args.language,
                "message": f"Failed to switch language: {str(e)}"
            }
    
    return {
        "status": "success",
        "language": args.language,
        "message": f"STT language switched to {args.language}",
        "reason": args.reason
    }

definition = {
    "name": "switchSTTLanguage",
    "description": "Switch the Speech-to-Text (STT) language to match the user's preferred language. Use this when the user explicitly asks to speak in a different language (e.g., 'talk with me in bangla', 'speak in English', 'ইংরেজিতে কথা বলো'), or when you detect the user wants to switch languages. This tool changes what language the robot listens for, allowing it to understand speech in that language. Call this BEFORE responding in the new language.",
    "parameters": {
        "type": "object",
        "properties": {
            "language": {
                "type": "string",
                "enum": ["en-US", "bn-BD"],
                "description": "Target language: 'en-US' for English, 'bn-BD' for Bangla (Bengali)"
            },
            "reason": {
                "type": "string",
                "description": "Reason for switching (e.g., 'User requested Bangla', 'User asked to speak in English')"
            }
        },
        "required": ["language"]
    }
}

