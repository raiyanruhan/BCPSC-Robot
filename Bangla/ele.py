import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Prefer modern client with Voice/VoiceSettings if available
HAS_CLIENT_GENERATE = False
ELXClient = None  # type: ignore
ELVoice = None  # type: ignore
ELVoiceSettings = None  # type: ignore
try:
    from elevenlabs import ElevenLabs as _ELXClient, Voice as _ELVoice, VoiceSettings as _ELVoiceSettings  # type: ignore
    ELXClient = _ELXClient
    ELVoice = _ELVoice
    ELVoiceSettings = _ELVoiceSettings
    HAS_CLIENT_GENERATE = True
except Exception:
    HAS_CLIENT_GENERATE = False

# Attempt to support both legacy and new ElevenLabs SDKs.
EL_LEGACY_GENERATE = None
EL_LEGACY_SET_API_KEY = None
EL_CLIENT = None
try:
    from elevenlabs import generate as _gen  # type: ignore
    from elevenlabs import set_api_key as _set_key  # type: ignore
    EL_LEGACY_GENERATE = _gen
    EL_LEGACY_SET_API_KEY = _set_key
except Exception:
    try:
        from elevenlabs.client import ElevenLabs as _Client  # type: ignore
        EL_CLIENT = _Client
    except Exception:
        EL_CLIENT = None

# Fallback API key sources
def _get_api_key() -> str:
    # Get API key from environment variables
    api_key = os.getenv("ELEVENLABS_API_KEY") or os.getenv("XI_API_KEY")
    if not api_key:
        raise RuntimeError("ELEVENLABS_API_KEY or XI_API_KEY environment variable must be set")
    return api_key

# Default voice IDs per your guidance
_MALE_VOICE_ID = "onwK4e9ZLuTAKqWW03F9"     # Daniel
_FEMALE_VOICE_ID = "flq6f7g4wjgrpnKxnyAi"   # Jessica

def _resolve_voice_id(explicit: Optional[str]) -> str:
    if explicit:
        return explicit
    env_any = os.getenv("TTS_ELEVENLABS_VOICE_ID")
    if env_any:
        return env_any
    preset = (os.getenv("TTS_VOICE") or "").strip().lower()
    if preset == "female":
        return os.getenv("TTS_ELEVENLABS_VOICE_ID_FEMALE") or _FEMALE_VOICE_ID
    return os.getenv("TTS_ELEVENLABS_VOICE_ID_MALE") or _MALE_VOICE_ID

def _write_audio(output_file: str, audio) -> None:
    # audio can be bytes or an iterator of bytes depending on SDK
    with open(output_file, "wb") as f:
        if isinstance(audio, (bytes, bytearray)):
            f.write(audio)
        else:
            try:
                for chunk in audio:
                    if chunk:
                        f.write(chunk)
            except TypeError:
                # Not iterable and not bytes
                raise

def generate_elevenlabs_tts(
    text: str,
    output_file: str = "bangla_audio.mp3",
    voice_id: Optional[str] = None,
    model_id: Optional[str] = None,
    api_key: Optional[str] = None,
    stability: Optional[float] = None,
    similarity_boost: Optional[float] = None,
):
    api_key = api_key or _get_api_key()
    vid = _resolve_voice_id(voice_id)
    # Resolve model and settings from args or environment
    model_id = (
        model_id
        or os.getenv("TTS_ELEVENLABS_MODEL_ID")
        or os.getenv("ELEVENLABS_MODEL_ID")
        or "eleven_v3"
    )
    if stability is None:
        s = os.getenv("TTS_ELEVENLABS_STABILITY") or os.getenv("ELEVENLABS_STABILITY")
        if s:
            try:
                stability = float(s)
            except Exception:
                stability = 0.5
        else:
            stability = 0.5
    if similarity_boost is None:
        sb = os.getenv("TTS_ELEVENLABS_SIMILARITY") or os.getenv("ELEVENLABS_SIMILARITY")
        if sb:
            try:
                similarity_boost = float(sb)
            except Exception:
                similarity_boost = 0.75
        else:
            similarity_boost = 0.75

    # Preferred modern API: client.generate with Voice/VoiceSettings
    if HAS_CLIENT_GENERATE and ELXClient is not None and ELVoice is not None and ELVoiceSettings is not None:
        try:
            client = ELXClient(api_key=api_key if api_key else None)  # type: ignore[call-arg]
            audio = client.generate(
                text=text,
                voice=ELVoice(
                    voice_id=vid,
                    settings=ELVoiceSettings(stability=stability, similarity_boost=similarity_boost),
                ),
                model=model_id,
            )
            _write_audio(output_file, audio)
            logger.info(f"ElevenLabs wrote '{output_file}'")
            return output_file
        except Exception as e:
            logger.debug(f"Modern client.generate failed, falling back: {e}")

    # Legacy simple API
    if EL_LEGACY_GENERATE is not None:
        if api_key:
            try:
                EL_LEGACY_SET_API_KEY(api_key)  # type: ignore[misc]
            except Exception:
                pass
        try:
            audio = EL_LEGACY_GENERATE(text=text, voice=vid, model=model_id)
            _write_audio(output_file, audio)
            logger.info(f"ElevenLabs wrote '{output_file}'")
            return output_file
        except Exception as e:
            raise RuntimeError(f"ElevenLabs (legacy) error: {e}")

    # New client API
    if EL_CLIENT is None:
        raise RuntimeError("ElevenLabs SDK not available. Please install/upgrade the 'elevenlabs' package.")

    try:
        # Try multiple client class import styles
        client_cls = EL_CLIENT
        try:
            from elevenlabs import ElevenLabs as _Client2  # type: ignore
            client_cls = _Client2
        except Exception:
            pass

        client = client_cls(api_key=api_key if api_key else None)  # type: ignore[call-arg]
        audio = client.text_to_speech.convert(
            voice_id=vid,
            model_id=model_id,
            text=text,
        )
        _write_audio(output_file, audio)
        logger.info(f"ElevenLabs wrote '{output_file}'")
        return output_file
    except Exception as e:
        raise RuntimeError(f"ElevenLabs (client) error: {e}")
