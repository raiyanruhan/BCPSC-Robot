import os
import base64
import logging
from bytez import Bytez

logger = logging.getLogger(__name__)

def _get_api_key() -> str:
    # Prefer environment variable to avoid hard-coding
    key = os.getenv("BYTEZ_API_KEY")
    if key:
        return key
    # Fallback to placeholder for development; replace externally via env var
    return "REPLACE_WITH_API_KEY"

def _extract_audio_base64(result) -> str | None:
    if isinstance(result, str):
        return result
    if isinstance(result, list):
        if result and isinstance(result[0], str):
            return result[0]
        if result and isinstance(result[0], dict) and "output" in result[0]:
            return result[0]["output"].get("audio_base64")
    if isinstance(result, dict) and "output" in result:
        return result["output"].get("audio_base64")
    return None

def generate_bytez_tts(text: str, output_file: str = "output.wav"):
    client = Bytez(_get_api_key())
    model = client.model("suno/bark")
    result = model.run(text)
    audio_b64 = _extract_audio_base64(result)
    if not audio_b64:
        raise RuntimeError("Bytez TTS did not return base64 audio data")
    decoded = base64.b64decode(audio_b64)
    with open(output_file, "wb") as f:
        f.write(decoded)
    logger.info(f"Bytez TTS wrote '{output_file}'")
    return output_file
