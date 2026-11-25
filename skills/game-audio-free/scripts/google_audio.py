"""Shared Google client and PCM handling for the optional cloud tools."""
import os
import wave
from contextlib import contextmanager
from email.message import Message
from assets import AudioError


def google_client(version):
    key = os.getenv("GEMINI_API_KEY")
    if not key:
        raise AudioError("GEMINI_API_KEY is missing; configure your Google AI Studio project key")
    try:
        from google import genai
    except ImportError as exc:
        raise AudioError("install google-genai or run this script with uv run --script") from exc
    return genai.Client(api_key=key, http_options={"api_version": version, "timeout": 90000})


@contextmanager
def cloud_errors():
    try:
        yield
    except AudioError:
        raise
    except Exception as exc:
        status = getattr(exc, "code", None)
        message = str(exc)
        upper = message.upper()
        if status == 429 or any(
                word in upper for word in ("RESOURCE_EXHAUSTED", "QUOTA", "RATE LIMIT", "429")):
            message = "quota exhausted or rate limited; check this project's quota and retry later"
        elif status in (401, 403) or any(word in upper for word in ("PERMISSION_DENIED", "API_KEY_INVALID", "403", "401")):
            message = "access denied; check the API key and this project's model permissions"
        elif status == 404 or "NOT_FOUND" in upper:
            message = "model unavailable for this project or API version"
        elif isinstance(exc, TimeoutError):
            message = "generation timed out before the requested audio was complete"
        key = os.getenv("GEMINI_API_KEY")
        if key:
            message = message.replace(key, "[redacted]")
        raise AudioError(f"Google audio: {message or type(exc).__name__}") from exc


def pcm_rate(mime, default):
    if not mime:
        return default
    header = Message()
    header["content-type"] = mime
    if header.get_content_type() not in ("audio/l16", "audio/pcm"):
        raise AudioError(f"expected 16-bit PCM, got {mime}")
    rate = int(header.get_param("rate") or default)
    if rate <= 0:
        raise AudioError("invalid PCM sample rate")
    return rate


@contextmanager
def pcm_wav(path, channels, rate):
    with wave.open(str(path), "wb") as wav:
        wav.setparams((channels, 2, rate, 0, "NONE", "not compressed"))
        yield wav
