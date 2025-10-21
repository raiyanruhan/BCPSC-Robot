import os
import sys

# Import main.py as a module
sys.path.insert(0, os.path.dirname(__file__))
import importlib.util

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

spec = importlib.util.spec_from_file_location("main", os.path.join(BASE_DIR, "main.py"))
main = importlib.util.module_from_spec(spec)
spec.loader.exec_module(main)  # type: ignore

def assert_valid(path, min_size=1024):
    assert os.path.isfile(path), f"Missing output file: {path}"
    size = os.path.getsize(path)
    assert size >= min_size, f"Output too small ({size} bytes): {path}"

def test_english_fallback():
    text = "Although the sky was overcast, the explorers pressed forward."
    # First engine is a deliberate failure (missing module), then real providers
    engines = [
        ("Missing Provider", os.path.join(BASE_DIR, "missing.py"), "missing_fn", {}),
        ("Pollinations (English)", os.path.join(BASE_DIR, "English", "pollinations-tts.py"), "text_to_speech", {"output_file": os.path.join(BASE_DIR, "en_pollinations.mp3")}),
        ("Gemini TTS (English)", os.path.join(BASE_DIR, "English", "gemini-tts.py"), "generate_gemini_tts", {"output_file": os.path.join(BASE_DIR, "en_gemini.wav")}),
        ("gTTS (English)", os.path.join(BASE_DIR, "English", "gTTS.py"), "generate_gtts", {"lang": "en", "output_file": os.path.join(BASE_DIR, "en_gtts.mp3")}),
    ]
    out = main.run_engines(text, engines, timeout_seconds=30, max_retries=2, backoff_factor=0.5, min_size_bytes=1024)
    assert_valid(out)
    print("English fallback test passed:", out)

def test_bangla_fallback():
    text = "আমি বাংলা ভাষায় কথা বলতে পারি"
    engines = [
        ("Missing Provider", os.path.join(BASE_DIR, "missing.py"), "missing_fn", {}),
        ("ElevenLabs (Bangla)", os.path.join(BASE_DIR, "Bangla", "ele.py"), "generate_elevenlabs_tts", {"output_file": os.path.join(BASE_DIR, "bn_elevenlabs.mp3")}),
        ("Gemini TTS (Bangla)", os.path.join(BASE_DIR, "Bangla", "gemini-tts.py"), "generate_gemini_tts", {"output_file": os.path.join(BASE_DIR, "bn_gemini.wav")}),
        ("gTTS (Bangla)", os.path.join(BASE_DIR, "English", "gTTS.py"), "generate_gtts", {"lang": "bn", "output_file": os.path.join(BASE_DIR, "bn_gtts.mp3")}),
    ]
    out = main.run_engines(text, engines, timeout_seconds=30, max_retries=2, backoff_factor=0.5, min_size_bytes=1024)
    assert_valid(out)
    print("Bangla fallback test passed:", out)

if __name__ == "__main__":
    test_english_fallback()
    test_bangla_fallback()