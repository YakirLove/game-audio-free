"""Publish audio and event mappings together. Python 3.10+."""
import argparse
import errno
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import wave
from contextlib import contextmanager
from pathlib import Path


class AudioError(Exception):
    """A failure that the agent can report to the game developer."""


def event_id(value):
    if not re.fullmatch(r"[a-z0-9]+(?:[._-][a-z0-9]+)*", value):
        raise argparse.ArgumentTypeError("use lowercase words separated by dots, underscores or hyphens")
    return value


def event_args(parser):
    parser.add_argument("event", type=event_id, help="game event, e.g. claw.coin.insert")
    parser.add_argument("--out-dir", type=Path, default=Path("assets/audio"))
    parser.add_argument("--loop", action="store_true", help="mark this asset for loop testing")


def run_cli(main):
    try:
        main()
    except (AudioError, OSError, ValueError, subprocess.CalledProcessError) as exc:
        sys.exit(f"game-audio-free: {exc}")


def file_hash(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def validate_audio(path):
    if not path.is_file() or path.stat().st_size == 0:
        raise AudioError("the provider returned no audio file")
    if path.suffix.lower() == ".wav":
        try:
            with wave.open(str(path), "rb") as wav:
                frames = wav.getnframes()
                if frames < 1:
                    raise AudioError("empty WAV")
                wav.setpos(frames - 1)
                if len(wav.readframes(1)) != wav.getnchannels() * wav.getsampwidth():
                    raise AudioError("truncated WAV")
                return
        except (EOFError, wave.Error):
            pass  # Float WAV and other codecs also work with ffmpeg.
    decoder = shutil.which("ffmpeg")
    if not decoder:
        raise AudioError("install ffmpeg to validate compressed or non-PCM audio")
    result = subprocess.run(
        [decoder, "-v", "error", "-xerror", "-nostdin", "-i", str(path),
         "-map", "0:a:0", "-f", "framemd5", "-"],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    if result.returncode or not any(line.startswith(b"0,") for line in result.stdout.splitlines()):
        raise AudioError(f"could not decode audio from {path.name}")


@contextmanager
def manifest_lock(root):
    # Lock a stable file outside the game's assets. The manifest inode changes on replace.
    key = hashlib.sha256(os.fsencode(os.path.normcase(str(root)))).hexdigest()
    locks = Path(tempfile.gettempdir()) / "game-audio-free-locks"
    locks.mkdir(mode=0o700, exist_ok=True)
    with (locks / key).open("a+b") as lock:
        if os.name == "nt":
            import msvcrt
            if not lock.tell():
                lock.write(b"0")
                lock.flush()
            lock.seek(0)
            while True:
                try:
                    msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
                    break
                except OSError as exc:
                    if exc.errno not in (errno.EACCES, errno.EDEADLK):
                        raise
                    time.sleep(0.1)
        else:
            import fcntl
            fcntl.flock(lock, fcntl.LOCK_EX)
        yield  # Closing the handle releases the lock, including on failure.


def read_manifest(root):
    path = root / "audio-manifest.json"
    if not path.exists():
        return {"version": 1, "events": {}}
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("version") != 1 or not isinstance(data.get("events"), dict):
        raise AudioError("unsupported audio-manifest.json structure")
    return data


def save_manifest(root, manifest, staging):
    pending = staging / "audio-manifest.json"
    pending.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    pending.replace(root / pending.name)


def existing_audio(root, entry):
    if not entry:
        return None
    path = (root / entry["file"]).resolve()
    if path.is_relative_to(root) and path.is_file() and file_hash(path) == entry["sha256"]:
        return path
    return None


def report(status, event, root, entry):
    print(json.dumps({"status": status, "event": event, "path": str(root / entry["file"]),
                      **entry}, ensure_ascii=False))


def publish(args, tool, inputs, produce, metadata=None):
    """produce(staging) returns a file. Keep old mappings valid until the final replace."""
    root = args.out_dir.resolve()
    root.mkdir(parents=True, exist_ok=True)
    with manifest_lock(root), tempfile.TemporaryDirectory(prefix=".game-audio-free-", dir=root) as tmp:
        staging = Path(tmp)
        manifest = read_manifest(root)
        old = manifest["events"].get(args.event)
        if tool == "existing":
            # Carry credits forward when the same clip is assigned to a second event.
            for prior in manifest["events"].values():
                if prior.get("sha256") == inputs:
                    inherited = {k: prior[k] for k in ("source_url", "source_id", "license", "credit") if k in prior}
                    metadata = {**inherited, **(metadata or {})}
                    if inherited:
                        break
        encoded = json.dumps([tool, inputs, metadata], sort_keys=True, ensure_ascii=False).encode()
        request = hashlib.sha256(encoded).hexdigest()
        if old and old["request"] == request and existing_audio(root, old):
            if old["loop_requested"] != args.loop:
                old.update(loop_requested=args.loop, loop_verified=False)
                save_manifest(root, manifest, staging)
            report("reused", args.event, root, old)
            return
        source = produce(staging).resolve()
        validate_audio(source)
        digest = file_hash(source)
        if source.is_relative_to(root) and not source.is_relative_to(staging):
            target = source  # An existing game asset can serve multiple events.
        else:
            name = args.event.replace(".", "-")
            suffix = source.suffix.lower()
            target = root / (name + suffix)
            if target.exists() and (target.is_symlink() or file_hash(target) != digest):
                target = root / f"{name}-{digest[:16]}{suffix}"
            if target.is_symlink() or (target.exists() and file_hash(target) != digest):
                raise AudioError(f"output name already occupied: {target.name}")
            if not target.exists():
                if not source.is_relative_to(staging):
                    source = Path(shutil.copyfile(source, staging / ("import" + suffix)))
                source.replace(target)
        entry = {"file": target.relative_to(root).as_posix(), "tool": tool, "request": request,
                 "sha256": digest, "loop_requested": args.loop,
                 "loop_verified": bool(args.loop and old and old["sha256"] == digest and old["loop_verified"])}
        if metadata:
            entry.update(metadata)
        manifest["events"][args.event] = entry
        save_manifest(root, manifest, staging)
        report("ready", args.event, root, entry)


def confirm_loop(args):
    root = args.out_dir.resolve()
    with manifest_lock(root):
        manifest = read_manifest(root)
        entry = manifest["events"].get(args.event)
        if not entry or not entry["loop_requested"] or not existing_audio(root, entry):
            raise AudioError("need a current, unchanged audio file with loop_requested=true")
        entry["loop_verified"] = True
        with tempfile.TemporaryDirectory(dir=root) as tmp:
            save_manifest(root, manifest, Path(tmp))
        report("loop_verified", args.event, root, entry)
