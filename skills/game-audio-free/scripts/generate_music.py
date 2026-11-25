# /// script
# requires-python = ">=3.11"
# dependencies = ["google-genai==3.6.1"]
# ///
"""Generate instrumental game music with Lyria RealTime."""
import argparse
import asyncio
import math

from assets import AudioError, event_args, publish, run_cli
from google_audio import cloud_errors, google_client, pcm_rate, pcm_wav


MODEL = "models/lyria-realtime-exp"
RATE = 48000


async def capture(session, output, frames):
    remaining = frames * 4  # signed 16-bit stereo
    with pcm_wav(output, 2, RATE) as wav:
        async for message in session.receive():
            if getattr(message, "filtered_prompt", None):
                raise AudioError("Google filtered the music prompt")
            content = getattr(message, "server_content", None)
            for chunk in getattr(content, "audio_chunks", None) or ():
                if not chunk.data:
                    continue
                if pcm_rate(chunk.mime_type, RATE) != RATE:
                    raise AudioError("unexpected Lyria sample rate")
                data = chunk.data[:remaining]
                wav.writeframesraw(data)
                remaining -= len(data)
                if not remaining:
                    return
    raise AudioError("music stream ended before the target duration")


async def stream(client, args, output, frames):
    from google.genai import types
    prompt = ", ".join(filter(None, [args.style, args.mood, args.instruments]))
    async with client.aio as api:
        async with api.live.music.connect(model=MODEL) as session:
            await session.set_weighted_prompts(prompts=[types.WeightedPrompt(text=prompt, weight=1.0)])
            if args.bpm is not None:
                await session.set_music_generation_config(config=types.LiveMusicGenerationConfig(bpm=args.bpm))
            await session.play()
            await capture(session, output, frames)


def generate(args):
    if not math.isfinite(args.duration) or args.duration <= 0 or round(args.duration * RATE) < 1:
        raise AudioError("duration must be positive and at least one audio frame")
    if args.bpm is not None and not 60 <= args.bpm <= 200:
        raise AudioError("Lyria accepts a tempo of 60–200 BPM")
    frames = round(args.duration * RATE)

    def render(staging):
        output = staging / "music.wav"
        with cloud_errors(), google_client("v1alpha") as client:
            asyncio.run(asyncio.wait_for(stream(client, args, output, frames), timeout=90 + 2 * args.duration))
        return output

    publish(args, "lyria-realtime", [args.style, args.mood, args.instruments, args.bpm, frames],
            render, {"model": MODEL})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    event_args(parser)
    parser.add_argument("--style", required=True)
    parser.add_argument("--mood", default="")
    parser.add_argument("--instruments", default="")
    parser.add_argument("--bpm", type=int)
    parser.add_argument("--duration", type=float, required=True, help="seconds")
    generate(parser.parse_args())


if __name__ == "__main__":
    run_cli(main)
