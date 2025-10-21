import requests
import urllib.parse
import logging
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)
TOKEN = "JOsu1kGkR1HlzWSc"

def _session():
    sess = requests.Session()
    retries = Retry(total=3, backoff_factor=0.5, status_forcelist=[429, 500, 502, 503, 504], allowed_methods=["GET"])
    sess.mount("https://", HTTPAdapter(max_retries=retries))
    return sess

def text_to_speech(
    text: str,
    voice: str = "alloy",
    output_file: str = "output.mp3"
):
    prompt_text = f"Write this exact text as output: {text}"
    encoded_prompt = urllib.parse.quote(prompt_text)
    url = f"https://text.pollinations.ai/{encoded_prompt}"
    params = {"model": "openai-audio", "voice": voice}
    headers = {"Authorization": f"Bearer {TOKEN}", "Accept": "audio/mpeg"}
    sess = _session()
    resp = sess.get(url, params=params, headers=headers, timeout=30)
    resp.raise_for_status()
    content_type = resp.headers.get("content-type", "")
    if "audio" not in content_type:
        error_msg = resp.text[:300] if resp.text else "No response body"
        raise ValueError(f"Pollinations returned non-audio content: {error_msg}")
    with open(output_file, "wb") as f:
        f.write(resp.content)
    logger.info(f"Pollinations (Bangla) wrote '{output_file}'")
    return output_file