import os
import soundfile as sf
from kittentts import KittenTTS
import logging

logger = logging.getLogger(__name__)

# Optional: path to eSpeak-NG for phonemizer (Windows). Safe to keep as-is.
os.environ.setdefault("PHONEMIZER_ESPEAK_LIBRARY", r"C:\\Program Files\\eSpeak NG\\libespeak-ng.dll")

_cached_models = {}

def _default_model_path() -> str:
    base_dir = os.path.dirname(__file__)
    return os.path.join(base_dir, "kitten-tts-nano-0.1", "kitten_tts_nano_v0_1.onnx")

def generate_kitten_tts(
    text: str,
    output_file: str = "output.wav",
    model_path: str | None = None,
    sample_rate: int = 24000,
):
    mp = model_path or _default_model_path()
    tts = _cached_models.get(mp)
    if tts is None:
        logger.info("Loading KittenTTS model...")
        tts = KittenTTS(mp)
        _cached_models[mp] = tts
    audio = tts.generate(text)
    sf.write(output_file, audio, sample_rate)
    logger.info(f"KittenTTS wrote '{output_file}'")
    return output_file

