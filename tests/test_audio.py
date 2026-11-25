"""Offline regression checks. Run: python3 -m unittest discover -s tests"""
import asyncio
from contextlib import redirect_stdout
import io
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace as NS
import unittest
from unittest.mock import patch
import wave

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "skills/game-audio-free/scripts"))
import assets
import game_audio_free
import generate_music
import generate_voice


class MusicSession:
    def __init__(self, chunks):
        self.chunks = chunks

    async def receive(self):
        yield NS(server_content=None)
        for group in self.chunks:
            yield NS(server_content=NS(audio_chunks=[NS(data=b, mime_type="audio/pcm;rate=48000")
                                                      for b in group]))


def voice_response(*chunks):
    return NS(candidates=[NS(content=NS(parts=[NS(inline_data=NS(data=b, mime_type="audio/L16;rate=24000"))
                                               for b in chunks]))])


class AudioTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.output = self.root / "game audio"
        self.args = NS(event="claw.test", out_dir=self.output, loop=False)
        self.stdout = io.StringIO()
        console = redirect_stdout(self.stdout)
        console.__enter__()
        self.addCleanup(console.__exit__, None, None, None)

    def seed(self, content=b"\x00\x01" * 4):
        source = self.root / "original.wav"
        generate_voice.write_voice(voice_response(content), source)
        return source

    def test_music_crosses_chunk_boundaries_and_trims_exactly(self):
        source = bytes(range(32))
        stream = MusicSession([[source[:3], source[3:10]], [source[10:]]])
        output = self.root / "music.wav"
        asyncio.run(generate_music.capture(stream, output, 5))
        with wave.open(str(output)) as wav:
            self.assertEqual((wav.getnchannels(), wav.getframerate(), wav.getnframes()), (2, 48000, 5))
            self.assertEqual(wav.readframes(5), source[:20])

    def test_short_stream_preserves_last_good_asset(self):
        source = self.seed()
        assets.publish(self.args, "existing", "original", lambda _: source)
        manifest = self.output / "audio-manifest.json"
        old = manifest.read_bytes()

        def interrupted(tmp):
            asyncio.run(generate_music.capture(MusicSession([[b"1234"]]), tmp / "partial.wav", 30))
        with self.assertRaisesRegex(assets.AudioError, "ended before"):
            assets.publish(self.args, "lyria-realtime", "revision", interrupted)
        self.assertEqual(manifest.read_bytes(), old)
        self.assertEqual((self.output / "claw-test.wav").read_bytes(), source.read_bytes())
        self.assertEqual(len(list(self.output.iterdir())), 2)

    def test_voice_payload_and_incomplete_sample(self):
        output = self.root / "voice.wav"
        generate_voice.write_voice(voice_response(b"abc", b"def"), output)
        with wave.open(str(output)) as wav:
            self.assertEqual((wav.getnchannels(), wav.getframerate(), wav.getnframes()), (1, 24000, 3))
            self.assertEqual(wav.readframes(3), b"abcdef")
        with self.assertRaisesRegex(assets.AudioError, "truncated"):
            generate_voice.write_voice(voice_response(b"x"), output)
        with self.assertRaisesRegex(assets.AudioError, "no audio"):
            generate_voice.write_voice(NS(candidates=[]), output)

    def test_quota_and_permissions_return_actionable_errors(self):
        args = NS(**vars(self.args), style="jazz", mood="", instruments="bass", bpm=100, duration=2)
        for code, message in ((429, "quota exhausted"), (403, "access denied")):
            error = RuntimeError("simulated service error")
            error.code = code
            with patch.object(generate_music, "google_client", side_effect=error):
                with self.assertRaisesRegex(assets.AudioError, message):
                    generate_music.generate(args)
            self.assertFalse((self.output / "audio-manifest.json").exists())

    def test_stable_adapter_and_missing_cli(self):
        args = NS(**vars(self.args), prompt="arcade motor", duration=3.0)
        with patch.object(game_audio_free.shutil, "which", return_value=None):
            with self.assertRaisesRegex(assets.AudioError, "CLI missing"):
                game_audio_free.custom(args)
        def simulate(argv, **options):
            self.assertEqual(argv[:-1], ["stable-audio", "--model", "small-sfx", "-p", "arcade motor",
                                         "--duration", "3.0", "-o"])
            Path(argv[-1]).write_bytes(self.seed().read_bytes())
            return subprocess.CompletedProcess(argv, 0)
        with patch.object(game_audio_free.shutil, "which", return_value="stable-audio"), \
                patch.object(game_audio_free.subprocess, "run", side_effect=simulate) as cli:
            game_audio_free.custom(args)
            game_audio_free.custom(args)
            cli.assert_called_once()
        self.assertEqual(assets.read_manifest(self.output)["events"]["claw.test"]["model"], "small-sfx")

    def test_attribution_and_loop_verification_follow_actual_content(self):
        source = self.seed()
        self.args.loop = True
        credit = {"source_url": "https://example.com/clip", "license": "CC BY 4.0", "credit": "Foley by A"}
        assets.publish(self.args, "sfx-sources", "id", lambda _: source, credit)
        assets.confirm_loop(self.args)
        saved = assets.read_manifest(self.output)["events"]["claw.test"]
        self.assertTrue(saved["loop_verified"])
        self.args.event = "claw.second"
        existing = NS(**vars(self.args), file=self.output / saved["file"], source_url=None, license=None, credit=None)
        game_audio_free.existing(existing)
        second = assets.read_manifest(self.output)["events"]["claw.second"]
        self.assertEqual((second["file"], second["credit"]), (saved["file"], credit["credit"]))
        self.args.event = "claw.test"
        assets.publish(self.args, "plinkfx", "revision", lambda _: self.seed(b"abcd"))
        revised = assets.read_manifest(self.output)["events"]["claw.test"]
        self.assertFalse(revised["loop_verified"])
        self.assertNotEqual(revised["file"], second["file"])
        self.assertTrue((self.output / second["file"]).exists())


if __name__ == "__main__":
    unittest.main()
