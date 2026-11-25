"""Local game audio commands. Run from the game project."""
import argparse
import math
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import sys
import tempfile
from urllib.request import urlopen
from urllib.parse import urlsplit

from assets import AudioError, confirm_loop, event_args, event_id, file_hash, publish, run_cli


SFX_COMMIT = "fb4ae3c44078dcc014c42adf1a7623e8a8758467"
SFX_SHA256 = "2aa9642865420eea3a6e03ce8517f1d3fe2e2c0d04e94a01097c7ffbf7878dad"


def upstream_sfx():
    override = os.getenv("GAME_AUDIO_FREE_SFX_SCRIPT")
    if override:
        path = Path(override).expanduser().resolve(strict=True)
        return [sys.executable, str(path)]
    cache = Path(os.getenv("XDG_CACHE_HOME") or Path.home() / ".cache")
    directory = cache / "game-audio-free" / SFX_COMMIT
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / "sfx.py"
    if not path.is_file() or file_hash(path) != SFX_SHA256:
        url = f"https://raw.githubusercontent.com/sxhzju/sfx/{SFX_COMMIT}/skills/sfx-sources/scripts/sfx.py"
        with tempfile.TemporaryDirectory(dir=directory) as tmp:
            candidate = Path(tmp) / "sfx.py"
            with urlopen(url, timeout=45) as response:
                candidate.write_bytes(response.read())
            if file_hash(candidate) != SFX_SHA256:
                raise AudioError("sfx-sources download failed its SHA-256 check")
            candidate.replace(path)
    return [sys.executable, str(path)]


def synth(args):
    recipe = Path(args.sound)
    if recipe.suffix.lower() == ".json":
        sound = str(recipe.resolve(strict=True))
        identity = {"recipe": file_hash(recipe)}
    elif re.fullmatch(r"[a-z0-9][a-z0-9-]*", args.sound):
        sound = args.sound
        identity = {"preset": sound}
    else:
        raise AudioError("supply a plinkfx preset name or a .json recipe")

    def render(staging):
        exe = shutil.which("npx")
        if not exe:
            raise AudioError("install Node.js 18+ with npm/npx for plinkfx")
        output = staging / "sound.wav"
        subprocess.run([exe, "--yes", "plinkfx@0.3.0", "render", sound, "-o", str(output)], check=True,
                       stdout=sys.stderr)
        return output

    publish(args, "plinkfx", {"version": "0.3.0", **identity}, render, {"license": "CC0-1.0"} if "preset" in identity else None)


def source_key(value):
    if re.fullmatch(r"(mk|fs|px):[0-9]+", value):
        return value
    if value.startswith("kn:"):
        parts = value[3:].split("/")
        if (len(parts) >= 2 and all(part not in ("", ".", "..") for part in parts)
                and all(re.fullmatch(r"[\w .()-]+", part) for part in parts)
                and PurePosixPath(parts[-1]).suffix.lower() in (".wav", ".mp3", ".ogg")):
            return value
    raise argparse.ArgumentTypeError("expected a downloaded search key such as fs:123 or kn:pack/Audio/file.ogg")


def provenance(args, parser_required=False):
    if not (args.source_url or args.license or args.credit or parser_required):
        return {}
    if not args.source_url or urlsplit(args.source_url).scheme not in ("https", "http") or not urlsplit(args.source_url).netloc:
        raise AudioError("supply a source page with --source-url")
    if not args.license or args.license.strip().lower() in ("", "?", "unknown"):
        raise AudioError("supply the license shown on the source page")
    if re.search(r"\b(by|attribution)\b", args.license, flags=re.I) and not (args.credit or "").strip():
        raise AudioError("this license needs an attribution; supply --credit")
    fields = {"source_url": args.source_url, "license": args.license}
    if args.credit:
        fields["credit"] = args.credit
    return fields


def fetch(args):
    fields = provenance(args, parser_required=True)
    fields["source_id"] = args.key

    def download(staging):
        subprocess.run([*upstream_sfx(), "get", str(staging), args.key], check=True, stdout=sys.stderr)
        files = [p for p in staging.iterdir() if p.suffix.lower() in (".ogg", ".wav", ".mp3") and p.is_file()]
        if len(files) != 1:
            raise AudioError("sfx-sources returned no complete audio file; check its output and search the source again")
        return files[0]

    publish(args, "sfx-sources", args.key, download, fields)


def existing(args):
    source = args.file.resolve(strict=True)
    if source.suffix.lower() not in {".wav", ".ogg", ".mp3", ".flac", ".m4a", ".aif", ".aiff", ".aac", ".opus"}:
        raise AudioError("expected an existing audio file")
    publish(args, "existing", file_hash(source), lambda _: source, provenance(args))


def custom(args):
    if not math.isfinite(args.duration) or not 0 < args.duration <= 120:
        raise AudioError("small-sfx duration must be greater than 0 and at most 120 seconds")

    def render(staging):
        exe = shutil.which("stable-audio")
        if not exe:
            raise AudioError("stable-audio CLI missing; see the Stable Audio setup in references/providers.md")
        output = staging / "custom.wav"
        subprocess.run([exe, "--model", "small-sfx", "-p", args.prompt, "--duration", str(args.duration),
                        "-o", str(output)], check=True, stdout=sys.stderr)
        return output

    publish(args, "stable-audio", [args.prompt, args.duration], render, {"model": "small-sfx"})


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    commands = cli.add_subparsers(dest="command", required=True)
    synth_cli = commands.add_parser("synth", help="render a plinkfx preset or recipe")
    event_args(synth_cli)
    synth_cli.add_argument("sound")
    synth_cli.set_defaults(run=synth)
    search = commands.add_parser("search", help="search the upstream sound library")
    search.add_argument("source", choices=["kenney", "mixkit", "freesound", "pixabay"])
    search.add_argument("options", nargs=argparse.REMAINDER)
    search.set_defaults(run=lambda a: subprocess.run([*upstream_sfx(), a.source, *a.options], check=True))
    get = commands.add_parser("fetch", help="download one search result and preserve its source details")
    reuse = commands.add_parser("existing", help="map an existing audio file to an event")
    for parser in (get, reuse):
        event_args(parser)
        parser.add_argument("--source-url", required=parser is get)
        parser.add_argument("--license", required=parser is get)
        parser.add_argument("--credit")
    get.add_argument("key", type=source_key)
    get.set_defaults(run=fetch)
    reuse.add_argument("file", type=Path)
    reuse.set_defaults(run=existing)
    special = commands.add_parser("custom", help="generate a custom sound with Stable Audio 3 Small-SFX")
    event_args(special)
    special.add_argument("--prompt", required=True)
    special.add_argument("--duration", type=float, required=True)
    special.set_defaults(run=custom)
    verify = commands.add_parser("confirm-loop", help="record a completed seamless-loop listening check")
    verify.add_argument("event", type=event_id)
    verify.add_argument("--out-dir", type=Path, default=Path("assets/audio"))
    verify.set_defaults(run=confirm_loop)
    args = cli.parse_args()
    args.run(args)


if __name__ == "__main__":
    run_cli(main)
