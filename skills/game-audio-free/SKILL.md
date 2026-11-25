---
name: game-audio-free
description: Make, find, or reuse game audio with local tools, free-to-use recordings, and cloud models with free tiers. Use for game SFX, foley, music, dialogue or an event-to-file manifest (免费游戏音效、环境音、配乐、角色配音).
---

# Game Audio Free

Work from the game project directory. Resolve `scripts/` relative to **this SKILL.md**. In the shell examples below set `S` to that absolute scripts directory. The default output is the game's `assets/audio/`; pass `--out-dir` to use a different directory.

1. Identify the game event, sound, style, target duration or exact spoken line. Infer sensible event IDs from the game's existing naming. A countdown beep is an interaction cue; a spoken countdown is dialogue.
2. Inspect the output directory's `audio-manifest.json`, existing project audio, and any accompanying credits first. If an existing mapping fits, return its file and tool. Use `existing` to map a suitable unregistered file to an event. Preserve known source and attribution. Generate only missing or deliberately revised cues.
3. Choose the tool below. Run each event independently so a missing key, quota limit, or unavailable sound library leaves completed events available. Prepare only the selected tool. For cloud generation use the developer's own free-tier project and a model with a current free tier. A key alone does not identify its billing tier. If the free quota runs out, return that event's status.

| Request | Action |
| --- | --- |
| Short interaction, reward or arcade action | `python3 "$S/game_audio_free.py" synth claw.coin.insert coin`. Pick an upstream plinkfx preset, or pass a JSON recipe for a tailored sound. |
| Recorded object, action or environment | `python3 "$S/game_audio_free.py" search mixkit metal`, then `fetch` a matching key with its source page and license. |
| Original or otherwise unavailable effect | Use `game_audio_free.py custom` with a prompt and duration; the local Stable Audio CLI and model access are optional. |
| Instrumental background music | Run `generate_music.py` with style, duration, and optional mood, instruments and BPM. |
| A line of dialogue or an announcement | Run `generate_voice.py` with the exact text, language, voice and delivery. |

See [provider commands and setup](references/providers.md) when the selected route needs dependencies, a custom recipe, source metadata or cloud access.

4. For a loop request, pass `--loop`. It marks the event for review. Use `confirm-loop` only after the developer listens across multiple repetitions or equivalent boundary verification confirms a clean join for that exact file.
5. Return the event, playable file path and actual tool from the CLI's JSON result. Include credits for downloaded audio and the status of any unfinished events. Reads of the manifest alone do not establish that its files still exist.
