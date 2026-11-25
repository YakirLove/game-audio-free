# Provider commands

Run from the game project with `S` set to the installed skill's absolute `scripts` directory. Asset commands accept `--out-dir DIR`. Diagnostics go to stderr, and success prints one JSON object with the event and file path. Repeating a command with the same inputs reuses the verified file.

## Existing or synthesized sounds

```sh
python3 "$S/game_audio_free.py" existing ui.confirm assets/sounds/confirm.wav
python3 "$S/game_audio_free.py" synth claw.coin.insert coin
python3 "$S/game_audio_free.py" synth claw.grab.success victory
```

For an existing third-party asset, pass `--source-url`, `--license` and any required `--credit`. A file already inside the output directory can be referenced in place. Files elsewhere are copied. Presets use Node 18+ and fetch the pinned plinkfx npm CLI on first use. To find or design a different cue, use `npx --yes plinkfx@0.3.0 list` and the upstream recipe instructions, then pass the recipe's JSON path in place of `coin`. [plinkfx Skill](https://github.com/maximilianfeix/plinkfx/tree/main/skills/plinkfx)

## Recorded sounds

```sh
python3 "$S/game_audio_free.py" search mixkit metal -n 5 --urls
python3 "$S/game_audio_free.py" fetch claw.gear.lock mk:2858 \
  --source-url https://mixkit.co/free-sound-effects/metal/ \
  --license "Mixkit Sound Effects Free License"
python3 "$S/game_audio_free.py" search freesound "cloth drop" --license cc0 -n 5 --urls
```

Use the key returned by the search. Check the title and license against the source or pack page. Freesound downloads are MP3 previews. For CC BY, record the license version and put the title, creator, license link, and any changes in `--credit`. For Mixkit, a collection page together with the exact item ID identifies the clip. If a library returns no result or its download is unavailable, try another listed source. Keep its file format; compressed audio validation uses ffmpeg.

On first search the wrapper caches a checksum-verified version of the upstream Python helper under `~/.cache/game-audio-free/` (or `XDG_CACHE_HOME`). To use an existing installation, set `GAME_AUDIO_FREE_SFX_SCRIPT` to the path of its `scripts/sfx.py`. Upstream search results and downloaded packs have their own cache. [sfx-sources](https://github.com/sxhzju/sfx) · [Mixkit license](https://mixkit.co/license/#sfxFree)

## Custom effects

For first use, follow the upstream installation instructions in a separate checkout. Use its supported Python version and `uv sync`, then activate that checkout's environment so `stable-audio` is on PATH. Request access to the Small-SFX weights on Hugging Face and sign in with `hf auth login` if required. This route downloads the model on first inference. Commercial use under the free Community License is subject to Stability AI's annual revenue threshold (USD 1 million). [Community license terms](https://stability.ai/license) [Stable Audio 3 CLI and installation](https://github.com/Stability-AI/stable-audio-3#installation) · [Small-SFX weights and terms](https://huggingface.co/stabilityai/stable-audio-3-small-sfx)

```sh
python3 "$S/game_audio_free.py" custom claw.motor.start \
  --prompt "Arcade claw motor starting, short gear rattle, no music" --duration 3
```

## Google music and voice

Use the user's `GEMINI_API_KEY` from the environment. Use a free-tier project for requests with a free-only budget. A billing-enabled project can incur usage charges. Lyria RealTime is experimental and its preview pricing and quotas may change. The default Flash TTS model has a free tier. If access is denied, the model is unavailable, or quota is exhausted, report the specific status. Do not switch to a paid model automatically. [AI Studio keys](https://aistudio.google.com/apikey) · [API pricing](https://ai.google.dev/gemini-api/docs/pricing) · [Lyria cookbook](https://github.com/google-gemini/cookbook/blob/main/quickstarts/Get_started_LyriaRealTime.ipynb)

```sh
uv run --script "$S/generate_music.py" claw.arcade.bgm \
  --style "instrumental arcade jazz" --mood playful --instruments "bass, vibraphone" \
  --bpm 108 --duration 20 --loop
uv run --script "$S/generate_voice.py" claw.guide.move \
  --text "请移动摇杆。" --language zh-CN --voice Kore --emotion cheerful
```

`uv run --script` prepares the pinned Google SDK in an isolated environment. Alternatively, install `google-genai==3.6.1` in a Python 3.11+ virtual environment and run the scripts with that Python. Voice accepts an optional `--model`; the default is `gemini-2.5-flash-preview-tts`. The music script counts PCM frames to write the requested duration. Voice preserves the sample rate reported by the service. [RealTime music](https://ai.google.dev/gemini-api/docs/realtime-music-generation) · [Gemini speech](https://ai.google.dev/gemini-api/docs/speech-generation)

After verifying a clean loop at the actual playback boundary:

```sh
python3 "$S/game_audio_free.py" confirm-loop claw.arcade.bgm
```
