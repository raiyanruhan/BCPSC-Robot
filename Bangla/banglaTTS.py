from banglatts import BanglaTTS
import logging

logger = logging.getLogger(__name__)
_cached_models = {}

def generate_bangla_library_tts(
    text: str,
    voice: str = 'male',
    filename: str = 'output.wav',
    save_location: str = "save_model_location"
):
    tts = _cached_models.get(save_location)
    if tts is None:
        logger.info("Loading BanglaTTS model...")
        tts = BanglaTTS(save_location=save_location)
        _cached_models[save_location] = tts

    path = tts(text, voice=voice, filename=filename)
    logger.info(f"banglaTTS wrote '{path}'")
    return path
