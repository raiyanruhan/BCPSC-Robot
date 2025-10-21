import os
import sys
import re
import importlib.util
import logging
import concurrent.futures
import time
import subprocess

BASE_DIR = os.path.dirname(__file__)
LOG_LEVEL = logging.INFO
logger = logging.getLogger("tts_main")
logging.basicConfig(
    level=LOG_LEVEL,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(os.path.join(BASE_DIR, "tts.log"), encoding="utf-8"),
    ],
)

BN_REGEX = re.compile(r'[\u0980-\u09FF]')

# Defaults for orchestration
DEFAULT_TIMEOUT_SECONDS = 30
DEFAULT_MAX_RETRIES = 2
DEFAULT_BACKOFF_FACTOR = 0.5
DEFAULT_BN_CHAIN = ["gemini", "pollinations", "gtts", "banglatts", "elevenlabs"]
DEFAULT_EN_CHAIN = ["pollinations", "gemini", "bytez", "kittentts", "gtts"]
DEFAULT_VOICE_PRESET = "male"  # set to "female" to switch globally
DEFAULT_MODE = "normal"  # set to "special" or "normal"

def import_func(module_path: str, func_name: str):
    if not os.path.exists(module_path):
        logger.warning(f"Skip: module not found at {module_path}")
        return None
    try:
        spec = importlib.util.spec_from_file_location(func_name, module_path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)  # type: ignore
        fn = getattr(mod, func_name, None)
        if fn is None:
            logger.warning(f"Skip: '{func_name}' not found in {module_path}")
        return fn
    except Exception as e:
        logger.error(f"Skip: failed to load {module_path}: {e}")
        return None

def detect_language(text: str) -> str:
    # bn if any Bengali chars present
    if BN_REGEX.search(text):
        return 'bn'
    # classify 'en' only if all letters are plain ASCII A-Z/a-z
    letters = [c for c in text if c.isalpha()]
    if not letters:
        return 'en'
    if all(('A' <= c <= 'Z') or ('a' <= c <= 'z') for c in letters):
        return 'en'
    return 'other'

def _load_config_if_any(base_dir: str):
    """Load a simple JSON or YAML config if present. Returns dict or None."""
    candidates = [
        os.path.join(base_dir, "tts_config.yaml"),
        os.path.join(base_dir, "tts_config.json"),
    ]
    for path in candidates:
        if not os.path.exists(path):
            continue
        try:
            if path.endswith((".yaml", ".yml")):
                try:
                    import yaml  # type: ignore
                except Exception:
                    logger.warning("YAML config found but PyYAML not installed; skipping.")
                    continue
                with open(path, "r", encoding="utf-8") as f:
                    return yaml.safe_load(f) or {}
            else:
                import json
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception as e:
            logger.warning(f"Config load failed ({os.path.basename(path)}): {e}")
    return None

def _parse_chain_env(var_name: str):
    v = os.getenv(var_name)
    if not v:
        return None
    return [x.strip().lower() for x in v.split(",") if x.strip()]

def _is_true_env(name: str) -> bool:
    v = os.getenv(name)
    if not v:
        return False
    return v.strip().lower() in ("1", "true", "yes", "on")

def _other_engines(base_dir: str, voice_preset: str):
    # Build a simple two-step fallback: Pollinations -> Gemini (English module)
    poll_voice = _env_or(
        ("onyx" if voice_preset == "male" else "alloy"),
        "TTS_POLLINATIONS_VOICE",
        f"TTS_POLLINATIONS_VOICE_{voice_preset.upper()}"
    )
    gem_voice = _env_or(
        ("Orus" if voice_preset == "male" else "Kore"),
        "TTS_GEMINI_VOICE",
        f"TTS_GEMINI_VOICE_{voice_preset.upper()}"
    )
    return [
        (
            "Pollinations (Other)",
            os.path.join(base_dir, "English", "pollinations-tts.py"),
            "text_to_speech",
            {"voice": poll_voice, "output_file": os.path.join(base_dir, "other_pollinations.mp3")},
        ),
        (
            "Gemini TTS (Other)",
            os.path.join(base_dir, "English", "gemini-tts.py"),
            "generate_gemini_tts",
            {"output_file": os.path.join(base_dir, "other_gemini.wav"), "voice_name": gem_voice, "language_code": "en-US"},
        ),
    ]

def _special_chain(default_chain: list, registry: dict) -> list:
    preferred = ["elevenlabs", "gemini"]
    rest = [k for k in default_chain if k not in preferred and k in registry]
    for k in registry.keys():
        if k not in preferred and k not in rest:
            rest.append(k)
    return [k for k in preferred if k in registry] + rest
def _assemble_engines_v2(chain_keys, registry: dict):
    engines = []
    for key in chain_keys:
        item = registry.get(key)
        if not item:
            logger.warning(f"Unknown engine key '{key}' — skipping.")
            continue
        engines.append(item)
    return engines

def _env_or(default: str | None, *names: str) -> str | None:
    for n in names:
        v = os.getenv(n)
        if v:
            return v
    return default

def _bn_registry(base_dir: str, voice_preset: str, conf: dict | None = None, el_api_key: str | None = None):
    return {
        "pollinations": (
            "Pollinations (Bangla)",
            os.path.join(base_dir, "Bangla", "pollinations-tts.py"),
            "text_to_speech",
            {
                # Use stronger male voice for male preset; same for BN/EN
                "voice": _env_or(
                    ("onyx" if voice_preset == "male" else "alloy"),
                    "TTS_POLLINATIONS_VOICE",
                    f"TTS_POLLINATIONS_VOICE_{voice_preset.upper()}"
                ),
                "output_file": os.path.join(base_dir, "bn_pollinations.mp3"),
            },
        ),
        "gemini": (
            "Gemini TTS (Bangla)",
            os.path.join(base_dir, "Bangla", "gemini-tts.py"),
            "generate_gemini_tts",
            {
                "output_file": os.path.join(base_dir, "bn_gemini.wav"),
                # Male preset: use 'Orus' (or 'Puck'); default to Orus
                "voice_name": _env_or(
                    ("Orus" if voice_preset == "male" else "Kore"),
                    "TTS_GEMINI_VOICE",
                    f"TTS_GEMINI_VOICE_{voice_preset.upper()}"
                ),
                "language_code": "bn-BD",
            },
        ),
        **({} if voice_preset == "male" else {
            "gtts": (
                "gTTS (Bangla)",
                os.path.join(base_dir, "English", "gTTS.py"),
                "generate_gtts",
                {"lang": "bn", "output_file": os.path.join(base_dir, "bn_gtts.mp3")},
            )
        }),
        "banglatts": (
            "banglaTTS library",
            os.path.join(base_dir, "Bangla", "banglaTTS.py"),
            "generate_bangla_library_tts",
            {
                # Switch between 'male' and 'female' directly
                "voice": ("male" if voice_preset == "male" else "female"),
                "filename": os.path.join(base_dir, "bn_banglaTTS.wav"),
            },
        ),
        "elevenlabs": (
            "ElevenLabs (Bangla)",
            os.path.join(base_dir, "Bangla", "ele.py"),
            "generate_elevenlabs_tts",
            (lambda: (
                {
                    "output_file": os.path.join(base_dir, "bn_elevenlabs.mp3"),
                    "voice_id": (
                        _env_or(None, f"TTS_ELEVENLABS_VOICE_ID_{voice_preset.upper()}", "TTS_ELEVENLABS_VOICE_ID")
                        or ("onwK4e9ZLuTAKqWW03F9" if voice_preset == "male" else "flq6f7g4wjgrpnKxnyAi")
                    ),
                    "model_id": (
                        os.getenv("TTS_ELEVENLABS_MODEL_ID")
                        or (conf.get("elevenlabs", {}).get("model_id") if isinstance(conf, dict) else None)
                        or "eleven_v3"
                    ),
                    **({
                        "stability": float(conf.get("elevenlabs", {}).get("stability"))
                    } if isinstance(conf, dict) and conf.get("elevenlabs", {}).get("stability") is not None else {}),
                    **({
                        "similarity_boost": float(conf.get("elevenlabs", {}).get("similarity_boost"))
                    } if isinstance(conf, dict) and conf.get("elevenlabs", {}).get("similarity_boost") is not None else {}),
                    **({"api_key": el_api_key} if el_api_key else {}),
                }
            ))(),
        ),
    }

def _en_registry(base_dir: str, voice_preset: str, conf: dict | None = None, el_api_key: str | None = None):
    return {
        "pollinations": (
            "Pollinations (English)",
            os.path.join(base_dir, "English", "pollinations-tts.py"),
            "text_to_speech",
            {
                # Use stronger male voice for male preset; same for BN/EN
                "voice": _env_or(
                    ("onyx" if voice_preset == "male" else "alloy"),
                    "TTS_POLLINATIONS_VOICE",
                    f"TTS_POLLINATIONS_VOICE_{voice_preset.upper()}"
                ),
                "output_file": os.path.join(base_dir, "en_pollinations.mp3"),
            },
        ),
        "elevenlabs": (
            "ElevenLabs (English)",
            os.path.join(base_dir, "Bangla", "ele.py"),
            "generate_elevenlabs_tts",
            (lambda: (
                {
                    "output_file": os.path.join(base_dir, "en_elevenlabs.mp3"),
                    "voice_id": (
                        _env_or(None, f"TTS_ELEVENLABS_VOICE_ID_{voice_preset.upper()}", "TTS_ELEVENLABS_VOICE_ID")
                        or ("onwK4e9ZLuTAKqWW03F9" if voice_preset == "male" else "flq6f7g4wjgrpnKxnyAi")
                    ),
                    "model_id": (
                        os.getenv("TTS_ELEVENLABS_MODEL_ID")
                        or (conf.get("elevenlabs", {}).get("model_id") if isinstance(conf, dict) else None)
                        or "eleven_v3"
                    ),
                    **({
                        "stability": float(conf.get("elevenlabs", {}).get("stability"))
                    } if isinstance(conf, dict) and conf.get("elevenlabs", {}).get("stability") is not None else {}),
                    **({
                        "similarity_boost": float(conf.get("elevenlabs", {}).get("similarity_boost"))
                    } if isinstance(conf, dict) and conf.get("elevenlabs", {}).get("similarity_boost") is not None else {}),
                    **({"api_key": el_api_key} if el_api_key else {}),
                }
            ))(),
        ),
        "gemini": (
            "Gemini TTS (English)",
            os.path.join(base_dir, "English", "gemini-tts.py"),
            "generate_gemini_tts",
            {
                "output_file": os.path.join(base_dir, "en_gemini.wav"),
                # Male preset: 'Orus' (or 'Puck'); default 'Orus'
                "voice_name": _env_or(
                    ("Orus" if voice_preset == "male" else "Kore"),
                    "TTS_GEMINI_VOICE",
                    f"TTS_GEMINI_VOICE_{voice_preset.upper()}"
                ),
                "language_code": "en-US",
            },
        ),
        **({} if voice_preset == "female" else {
            "bytez": (
                "Bytez TTS",
                os.path.join(base_dir, "English", "bytez-tts.py"),
                "generate_bytez_tts",
                {"output_file": os.path.join(base_dir, "en_bytez.wav")},
            )
        }),
        "kittentts": (
            "KittenTTS",
            os.path.join(base_dir, "English", "KittenTTS.py"),
            "generate_kitten_tts",
            {"output_file": os.path.join(base_dir, "en_kitten.wav")},
        ),
        **({} if voice_preset == "male" else {
            "gtts": (
                "gTTS (English)",
                os.path.join(base_dir, "English", "gTTS.py"),
                "generate_gtts",
                {"lang": "en", "output_file": os.path.join(base_dir, "en_gtts.mp3")},
            )
        }),
    }

def _assemble_engines(chain_keys, registry: dict):
    engines = []
    for key in chain_keys:
        item = registry.get(key)
        if not item:
            logger.warning(f"Unknown engine key '{key}' — skipping.")
            continue
        engines.append(item)
    return engines

def _call_with_timeout(fn, text, kwargs, timeout_seconds: int):
    """Run a single engine call with a soft timeout."""
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(fn, text, **kwargs)
        return future.result(timeout=timeout_seconds)

def _is_valid_output(path: str, min_size_bytes: int) -> bool:
    try:
        return os.path.isfile(path) and os.path.getsize(path) >= min_size_bytes
    except Exception:
        return False

def _play_audio(file_path: str):
    """Attempt to play the generated audio using the OS default player."""
    try:
        if sys.platform.startswith("win"):
            os.startfile(file_path)  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.run(["open", file_path], check=False)
        else:
            subprocess.run(["xdg-open", file_path], check=False)
        logger.info(f"Playing audio: {file_path}")
    except Exception as e:
        logger.warning(f"Could not auto-play audio: {e}")

def run_engines(
    text: str,
    engines: list,
    timeout_seconds: int = 30,
    max_retries: int = 1,
    backoff_factor: float = 0.0,
    min_size_bytes: int = 1024
):
    """Try engines in order with retries, timeout, and output validation."""
    for name, path, func_name, kwargs in engines:
        logger.info(f"Trying engine: {name}")
        fn = import_func(path, func_name)
        if not fn:
            continue

        attempt = 0
        while attempt < max_retries:
            try:
                out = _call_with_timeout(fn, text, kwargs, timeout_seconds)
                if not out or not isinstance(out, str):
                    raise RuntimeError("Engine did not return an output file path.")
                if not _is_valid_output(out, min_size_bytes):
                    raise RuntimeError(f"Output invalid or too small: {out}")
                logger.info(f"{name} succeeded -> {out}")
                return out
            except concurrent.futures.TimeoutError:
                logger.warning(f"{name} timed out after {timeout_seconds}s (attempt {attempt+1}/{max_retries}).")
            except Exception as e:
                logger.warning(f"{name} failed (attempt {attempt+1}/{max_retries}): {e}")

            attempt += 1
            if attempt < max_retries and backoff_factor > 0:
                sleep_s = backoff_factor * (2 ** (attempt - 1))
                time.sleep(sleep_s)

    raise RuntimeError("All TTS engines failed.")

def main():
    if len(sys.argv) > 1:
        input_text = " ".join(sys.argv[1:])
    else:
        print("Enter text:")
        input_text = sys.stdin.readline().strip()

    if not input_text:
        logger.error("No input text provided.")
        sys.exit(1)

    language = detect_language(input_text)
    logger.info(f"Detected language: {'Bangla' if language == 'bn' else 'English'}")

    # Resolve orchestration settings (defaults, overridable via optional config)
    timeout_seconds = DEFAULT_TIMEOUT_SECONDS
    max_retries = DEFAULT_MAX_RETRIES
    backoff_factor = DEFAULT_BACKOFF_FACTOR

    conf = _load_config_if_any(BASE_DIR)
    if isinstance(conf, dict):
        timeout_seconds = int(conf.get("timeout_seconds", timeout_seconds))
        max_retries = int(conf.get("max_retries", max_retries))
        backoff_factor = float(conf.get("backoff_factor", backoff_factor))

    # Resolve voice preset globally (env -> config -> default)
    vp = os.getenv("TTS_VOICE") or (conf.get("voice") if isinstance(conf, dict) else None) or DEFAULT_VOICE_PRESET
    voice_preset = str(vp).strip().lower()
    if voice_preset not in ("male", "female"):
        logger.warning(f"Unknown voice preset '{voice_preset}', falling back to '{DEFAULT_VOICE_PRESET}'.")
        voice_preset = DEFAULT_VOICE_PRESET

    # Build engine registries and resolve chains
    el_api_key = os.getenv("ELEVENLABS_API_KEY") or os.getenv("XI_API_KEY") or (conf.get("elevenlabs_api_key") if isinstance(conf, dict) else None)
    bn_reg = _bn_registry(BASE_DIR, voice_preset, conf, el_api_key)
    en_reg = _en_registry(BASE_DIR, voice_preset, conf, el_api_key)

    # Special mode toggle (env/config)
    mode = (os.getenv("TTS_MODE") or (conf.get("mode") if isinstance(conf, dict) else None) or DEFAULT_MODE)
    mode = str(mode).strip().lower()
    special = _is_true_env("TTS_SPECIAL") or (mode == "special") or bool(conf.get("special_mode") if isinstance(conf, dict) else False)

    env_bn = _parse_chain_env("TTS_BN_CHAIN")
    env_en = _parse_chain_env("TTS_EN_CHAIN")

    if env_bn:
        bn_chain = env_bn
    elif special:
        bn_chain = _special_chain(DEFAULT_BN_CHAIN, bn_reg)
    elif isinstance(conf, dict) and conf.get("bn_chain"):
        bn_chain = conf.get("bn_chain")
    else:
        bn_chain = DEFAULT_BN_CHAIN

    if env_en:
        en_chain = env_en
    elif special:
        en_chain = _special_chain(DEFAULT_EN_CHAIN, en_reg)
    elif isinstance(conf, dict) and conf.get("en_chain"):
        en_chain = conf.get("en_chain")
    else:
        en_chain = DEFAULT_EN_CHAIN

    bn_engines = _assemble_engines_v2(bn_chain, bn_reg)
    en_engines = _assemble_engines_v2(en_chain, en_reg)

    if language == 'bn':
        engines = bn_engines
    elif language == 'en':
        engines = en_engines
    else:
        engines = _other_engines(BASE_DIR, voice_preset)
    try:
        out_file = run_engines(
            input_text,
            engines,
            timeout_seconds=timeout_seconds,
            max_retries=max_retries,
            backoff_factor=backoff_factor,
            min_size_bytes=1024
        )
        logger.info(f"Done. Output written to '{out_file}'.")
        _play_audio(out_file)
    except Exception as e:
        logger.error(f"TTS failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()


