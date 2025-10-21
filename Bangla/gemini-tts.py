from google import genai
from google.genai import types
import wave, os
import logging

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
logger = logging.getLogger(__name__)

if not GOOGLE_API_KEY:
    raise RuntimeError("GOOGLE_API_KEY environment variable must be set")

client = genai.Client(api_key=GOOGLE_API_KEY)

# --- Helper to save wave files ---
def save_wave(filename, pcm, channels=1, rate=24000, sample_width=2):
    with wave.open(filename, "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(sample_width)
        wf.setframerate(rate)
        wf.writeframes(pcm)

def generate_gemini_tts(
    text: str,
    output_file: str = "bangla_out.wav",
    voice_name: str = "Kore",
    language_code: str = "bn-BD"
):
    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash-preview-tts",
            contents=text,
            config=types.GenerateContentConfig(
                response_modalities=["AUDIO"],
                speech_config=types.SpeechConfig(
                    voice_config=types.VoiceConfig(
                        prebuilt_voice_config=types.PrebuiltVoiceConfig(
                            voice_name=voice_name
                        )
                    ),
                    language_code=language_code
                ),
            ),
        )
        audio_data = response.candidates[0].content.parts[0].inline_data.data
        save_wave(output_file, audio_data)
        logger.info(f"Bangla Gemini TTS wrote '{output_file}'")
        return output_file
    except Exception as e:
        raise RuntimeError(f"Gemini TTS (Bangla) error: {e}")