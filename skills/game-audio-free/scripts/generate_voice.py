# /// script
# requires-python = ">=3.11"
# dependencies = ["google-genai==3.6.1"]
# ///
"""Generate a single game character's line with Gemini TTS."""
import argparse

from assets import AudioError, event_args, publish, run_cli
from google_audio import cloud_errors, google_client, pcm_rate, pcm_wav


def write_voice(response, output):
    candidates = response.candidates or []
    content = candidates[0].content if candidates else None
    parts = [part.inline_data for part in (getattr(content, "parts", None) or ())
             if part.inline_data and part.inline_data.data]
    if not parts:
        raise AudioError("Gemini TTS returned no audio; check the text and model response")
    rate = pcm_rate(parts[0].mime_type, 24000)
    size = 0
    with pcm_wav(output, 1, rate) as wav:
        for part in parts:
            if pcm_rate(part.mime_type, rate) != rate:
                raise AudioError("TTS sample rate changed within the response")
            wav.writeframesraw(part.data)
            size += len(part.data)
    if size % 2:
        raise AudioError("truncated 16-bit TTS sample")


def generate(args):
    if not args.text.strip():
        raise AudioError("the spoken line is empty")

    def render(staging):
        output = staging / "voice.wav"
        with cloud_errors(), google_client("v1beta") as client:
            from google.genai import types
            directions = "Read the following dialogue verbatim"
            if args.language:
                directions += f" in {args.language}"
            if args.emotion:
                directions += f" with this delivery: {args.emotion}"
            speech = types.SpeechConfig(voice_config=types.VoiceConfig(
                prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=args.voice)))
            response = client.models.generate_content(
                model=args.model, contents=f"{directions}.\n\n{args.text}",
                config=types.GenerateContentConfig(response_modalities=["AUDIO"], speech_config=speech))
            write_voice(response, output)
        return output

    publish(args, "gemini-tts", [args.text, args.language, args.voice, args.emotion],
            render, {"model": args.model, "voice": args.voice})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    event_args(parser)
    parser.add_argument("--text", required=True)
    parser.add_argument("--language", default="")
    parser.add_argument("--voice", default="Kore")
    parser.add_argument("--emotion", default="")
    parser.add_argument("--model", default="gemini-2.5-flash-preview-tts")
    generate(parser.parse_args())


if __name__ == "__main__":
    run_cli(main)
