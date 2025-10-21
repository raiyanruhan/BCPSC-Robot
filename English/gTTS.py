from gtts import gTTS
import logging

logger = logging.getLogger(__name__)
def generate_gtts(text: str, lang: str = 'en', output_file: str = 'output.mp3', slow: bool = False):
    tts = gTTS(text=text, lang=lang, slow=slow)
    tts.save(output_file)
    logger.info(f"gTTS wrote '{output_file}'")
    return output_file