# Multi-Language Text-to-Speech System

A robust, multi-provider Text-to-Speech system supporting Bangla (Bengali) and English with intelligent fallback mechanisms.

## Features

- **Multi-language Support**: Automatic language detection for Bangla and English
- **Multiple TTS Providers**: ElevenLabs, Gemini, Pollinations, gTTS, KittenTTS, and more
- **Intelligent Fallback**: Automatic failover between providers
- **Voice Presets**: Male/Female voice options
- **Configurable**: Environment variables, YAML, or JSON configuration
- **Offline Support**: Local models available (KittenTTS, banglaTTS)

## Quick Start

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Set Environment Variables**:
   ```bash
   # Required API Keys
   export ELEVENLABS_API_KEY="your_elevenlabs_api_key"
   export GOOGLE_API_KEY="your_google_api_key"
   
   # Optional
   export TTS_VOICE="male"  # or "female"
   export TTS_MODE="normal"  # or "special"
   ```

3. **Run TTS**:
   ```bash
   python main.py "Hello, this is a test"
   ```

## Environment Variables

### Required
- `ELEVENLABS_API_KEY` - ElevenLabs API key for premium voices
- `GOOGLE_API_KEY` - Google API key for Gemini TTS

### Optional
- `TTS_VOICE` - Voice preset: "male" or "female" (default: "male")
- `TTS_MODE` - Mode: "normal" or "special" (default: "normal")
- `POLLINATIONS_TOKEN` - Pollinations API token (has default)
- `TTS_ELEVENLABS_VOICE_ID_MALE` - Custom male voice ID
- `TTS_ELEVENLABS_VOICE_ID_FEMALE` - Custom female voice ID
- `TTS_BN_CHAIN` - Bangla engine chain (comma-separated)
- `TTS_EN_CHAIN` - English engine chain (comma-separated)

## Supported TTS Providers

### Bangla
1. **Gemini TTS** - Google's Gemini 2.5 Flash with TTS
2. **Pollinations** - OpenAI audio model via API
3. **gTTS** - Google Text-to-Speech (free)
4. **banglaTTS** - Specialized Bangla library
5. **ElevenLabs** - Premium AI voices

### English
1. **Pollinations** - OpenAI audio model
2. **Gemini TTS** - Google Gemini
3. **Bytez TTS** - Alternative provider
4. **KittenTTS** - Local ONNX model (offline)
5. **gTTS** - Google Text-to-Speech
6. **ElevenLabs** - Premium voices

## Configuration

### Environment Variables
Set environment variables for runtime configuration.

### Config Files
Create `tts_config.yaml` or `tts_config.json`:
```yaml
voice: "male"
mode: "normal"
timeout_seconds: 30
max_retries: 2
backoff_factor: 0.5
bn_chain: ["gemini", "pollinations", "gtts", "banglatts", "elevenlabs"]
en_chain: ["pollinations", "gemini", "bytez", "kittentts", "gtts"]
elevenlabs:
  model_id: "eleven_v3"
  stability: 0.5
  similarity_boost: 0.75
```

## Usage Examples

```bash
# English text
python main.py "Hello, how are you today?"

# Bangla text
python main.py "আমি বাংলা ভাষায় কথা বলতে পারি"

# Interactive mode
python main.py
# Then enter text when prompted
```

## Project Structure

```
├── main.py              # Main orchestrator
├── Bangla/              # Bangla TTS implementations
│   ├── ele.py          # ElevenLabs
│   ├── gemini-tts.py   # Gemini
│   ├── banglaTTS.py    # Local Bangla library
│   └── ...
├── English/            # English TTS implementations
│   ├── pollinations-tts.py
│   ├── gemini-tts.py
│   ├── KittenTTS.py
│   └── ...
└── tests/              # Test suite
```

## Testing

Run the test suite:
```bash
python tests/smoke_tts.py
```

## License

This project is open source. Please ensure you have proper API keys for the services you use.
