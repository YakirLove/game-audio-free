# game-audio-free

[简体中文](README.md) · MIT

An Agent Skill for Codex and Claude Code that brings together free game audio tools: local synthesizers, free-to-use recordings, and cloud models with a free tier.

## Copy this message to your agent

Open your game project in Codex or Claude Code and send this message.

```text
Install the skill from https://github.com/YakirLove/game-audio-free in this game project.
Then use it to make a coin sound, save it in assets/audio/, and give me the WAV file path so I can listen.
```

The coin sound is generated locally and needs no API key. Replace “a coin sound” with another sound your game needs.

<details>
<summary>Manual installation and terminal example</summary>

Run this in the root of your game project and select your agent in the installer. Basic effects require Python 3.10+, Node.js 18+ and npm.

```sh
npx skills add YakirLove/game-audio-free
```

To generate a coin sound and a victory cue for a claw machine, use the project-local Codex path below. For Claude Code, set `S` to `.claude/skills/game-audio-free/scripts`.

```sh
S=".agents/skills/game-audio-free/scripts"
python3 "$S/game_audio_free.py" synth claw.coin.insert coin
python3 "$S/game_audio_free.py" synth claw.grab.success victory
```

Play `assets/audio/claw-coin-insert.wav` or `assets/audio/claw-grab-success.wav`. The first render fetches the plinkfx CLI on demand. Repeating a matching request reuses the verified asset.

</details>

## Choose a sound

| Game event or scene | Provider | Google key required? | Requirements and output |
| --- | --- | --- | --- |
| Button, coin, jump, victory | [plinkfx](https://github.com/maximilianfeix/plinkfx) | No | Local synthesis to WAV, CC0 presets |
| Footsteps, gears, collisions, rain | [sfx-sources](https://github.com/sxhzju/sfx) | No | Online search, original file format and source-specific license; ffmpeg for compressed audio validation |
| Custom mechanical, creature or magical effect | [Stable Audio 3 Small-SFX](https://github.com/Stability-AI/stable-audio-3) | No | Optional local CLI and model access; Small runs on CPU, with [community license conditions for free commercial use](https://stability.ai/license) |
| Menu, exploration or battle music | [Google Lyria RealTime](https://ai.google.dev/gemini-api/docs/realtime-music-generation) | **Yes** | Instrumental stereo WAV trimmed to the requested duration |
| Dialogue, tutorial or countdown voice | [Gemini TTS](https://ai.google.dev/gemini-api/docs/speech-generation) | **Yes** | Voice WAV from the exact line, language, voice and delivery |

## Get a Google API key

**Background music and character voices share one Gemini API key.** Get yours at [https://aistudio.google.com/apikey](https://aistudio.google.com/apikey).

1. Sign in with your Google account. If a key is already listed for your default project, you can copy it.
2. To make a new key, click **Create API key**, select a project, create the key and copy it. If your existing Google Cloud project is missing, import it under **Dashboard → Projects → Import projects**, then return to the keys page. Choose a free-tier project for a free-only budget. [Google’s setup guide](https://ai.google.dev/gemini-api/docs/api-key)
3. Set the local environment variable `GEMINI_API_KEY`. On macOS or Linux, run the line below in Bash or Zsh, paste the key at the hidden prompt and press Enter. Launch your agent from that terminal. On Windows, add `GEMINI_API_KEY` to your user environment variables, save it and reopen your agent.

```sh
read -rs GEMINI_API_KEY && export GEMINI_API_KEY
```

Run the Google scripts with `uv` to prepare Python 3.11+ and the SDK on demand. Lyria RealTime is a quota-limited experimental preview whose pricing can change. The default Flash TTS model has a free tier; billing-enabled projects can incur charges. The scripts surface quota or access failures and keep completed cues. [Provider commands](skills/game-audio-free/references/providers.md) · [Google pricing](https://ai.google.dev/gemini-api/docs/pricing) · [Lyria preview notes](https://github.com/google-gemini/cookbook/blob/main/quickstarts/Get_started_LyriaRealTime.ipynb)

## Use the results

In `assets/audio/audio-manifest.json`, read `events["claw.coin.insert"].file` for the filename relative to the manifest, and `tool` for the provider. Each asset command also prints JSON with the absolute path. Pass `--out-dir` to choose a different destination.

Downloaded clips carry a source URL, item ID, license and any required credit. Pass `--loop` to mark an asset for loop testing. After verifying the actual playback boundary, run `confirm-loop` to record that the current file loops cleanly.

## First-release checks and license

The coin, victory cue and a downloaded Mixkit gear lock were decoded in a clean game project. A repeated render reused the original coin file. Music and voice output and error handling were exercised with simulated responses. The Stable Audio adapter's arguments and missing-CLI handling were checked offline; actual inference requires model access.

The Skill and scripts in this repository use the [MIT License](LICENSE). Upstream tools, models and downloaded sounds have their own terms.
