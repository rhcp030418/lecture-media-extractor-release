import io
import json
import struct
import tempfile
import threading
import time
import unittest
import wave
from pathlib import Path
from unittest.mock import patch

from lecture_script.browser import Source
from lecture_script.native_host import Host, read_message, source_from_message, write_message
from lecture_script.pipeline import Cancelled, Options, job_identity, process_source
from lecture_script.storage import JobStore
from lecture_script.text import Segment


class Engine:
    actual_device = "cpu"
    compute_type = "int8"
    def transcribe(self, audio, work, options, cancel, progress):
        assert audio.is_file()
        return [Segment(0, 0.8, "파이프라인 시험입니다.")]


class UnifiedTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.original = self.root / "input.wav"
        with wave.open(str(self.original), "wb") as out:
            out.setparams((1, 2, 16000, 0, "NONE", "not compressed"))
            out.writeframes(b"\0\0" * 16000)
        self.options = Options(self.root / "lecture", prefer_subtitles=False)
        self.store = JobStore(self.root / "jobs.db")

    def test_full_flow_keeps_media_audio_and_script_in_course_folders(self):
        source = Source(str(self.original), "local", "1주차", course="네트워크")
        before = self.original.read_bytes()
        stages = []
        result = process_source(source, self.options, Engine(), threading.Event(), lambda _, s: stages.append(s), self.store)
        course = self.options.output / "네트워크"
        self.assertEqual({p.name for p in course.iterdir()}, {"video", "audio", "script"})
        meta = result["payload"]["metadata"]
        self.assertEqual(Path(meta["media_path"]).parent, course / "video")
        self.assertEqual(Path(meta["audio_path"]).parent, course / "audio")
        self.assertEqual(Path(result["directory"]).parent, course / "script")
        self.assertEqual(self.original.read_bytes(), before)
        self.assertEqual(self.store.recent()[0]["status"], "complete")
        self.assertTrue(any("2/3" in s for s in stages))
        self.assertTrue((Path(result["directory"]) / "subtitles.srt").is_file())

    def test_failed_transcription_retains_download_and_retry_skips_network(self):
        source = Source("https://cdn.example.edu/a.mp4?token=secret", "media", "Lecture", course="Course")
        def download(_source, work, *args):
            target = work / "source.wav"
            target.write_bytes(self.original.read_bytes())
            return target
        engine = Engine()
        with patch("lecture_script.pipeline.download_media", side_effect=download) as downloader:
            with patch.object(engine, "transcribe", side_effect=ValueError("model failed")):
                with self.assertRaises(ValueError):
                    process_source(source, self.options, engine, threading.Event(), lambda *_: None, self.store)
            self.assertEqual(self.store.recent()[0]["status"], "failed")
            self.assertEqual(len(list(self.options.output.glob("Course/video/*"))), 1)
            self.assertEqual(len(list(self.options.output.glob("Course/audio/*"))), 1)
            with patch("lecture_script.pipeline.extract_audio", side_effect=AssertionError("Must reuse audio")):
                result = process_source(source, self.options, engine, threading.Event(), lambda *_: None, self.store)
            self.assertEqual(downloader.call_count, 1)
            self.assertNotIn("secret", (Path(result["directory"]) / "pipeline.json").read_text())

    def test_subtitle_preference_still_performs_first_two_stages(self):
        self.original.with_suffix(".srt").write_text("1\n00:00:00,000 --> 00:00:00,800\n기존 자막\n", encoding="utf-8")
        self.options.prefer_subtitles = True
        with patch.object(Engine, "transcribe", side_effect=AssertionError("Use captions")):
            result = process_source(Source(str(self.original), "local"), self.options, Engine(), threading.Event(), lambda *_: None)
        self.assertTrue(Path(result["payload"]["metadata"]["audio_path"]).is_file())

    def test_course_name_cannot_escape_download_folder(self):
        result = process_source(Source(str(self.original), "local", course="../../outside"), self.options, Engine(), threading.Event(), lambda *_: None)
        self.assertTrue(Path(result["directory"]).resolve().is_relative_to(self.options.output.resolve()))

    def test_stream_variants_of_same_hansung_lecture_have_same_identity(self):
        page = "https://learn.hansung.ac.kr/mod/vod/viewer.php?id=55"
        self.assertEqual(job_identity(Source("https://cdn/a.m3u8", page_url=page)),
                         job_identity(Source("https://cdn/720.m3u8", page_url=page)))


class ProtocolTests(unittest.TestCase):
    def test_native_framing_and_korean_roundtrip(self):
        stream = io.BytesIO()
        value = {"title": "네트워크", "command": "hello"}
        write_message(stream, value)
        stream.seek(0)
        self.assertEqual(read_message(stream), value)
        self.assertIsNone(read_message(stream))
        for raw in (b"\x01", struct.pack("=I", 2000000), struct.pack("=I", 4) + b"{}"):
            with self.assertRaises(ValueError): read_message(io.BytesIO(raw))

    def test_reject_local_url_and_header_injection_scope_cookies(self):
        raw = {"url": "file:///C:/Windows/win.ini", "page_url": "https://school.test/viewer", "kind": "media"}
        with self.assertRaises(ValueError): source_from_message({"source": raw})
        raw["url"] = "https://cdn.test/video.mp4"
        raw["headers"] = {"Referer": "https://school.test/\r\nInjected: bad"}
        with self.assertRaises(ValueError): source_from_message({"source": raw})
        raw["headers"] = {}
        raw["cookies"] = [{"name": "session", "value": "secret", "domain": "other.test"},
                          {"name": "session", "value": "allowed", "domain": "school.test"}]
        source = source_from_message({"source": raw})
        self.assertEqual(len(source.cookies), 1)
        self.assertEqual(source.cookies[0]["domain"], "school.test")

    def test_native_queue_deduplicates_and_cancels_queued_job(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first_started, release = threading.Event(), threading.Event()
            messages, calls = [], []
            def process(source, *_args):
                calls.append(source.title)
                first_started.set()
                release.wait(5)
                return {"directory": str(root)}
            def command(name):
                return {"command": "start", "request_id": name, "source": {
                    "url": f"https://cdn.test/{name}.mp4", "page_url": "https://school.test/viewer",
                    "kind": "media", "title": name, "course": "course"}}
            with patch("lecture_script.native_host.process_source", side_effect=process):
                host = Host(messages.append, root, JobStore(root / "jobs.db"))
                try:
                    host.handle(command("first"))
                    self.assertTrue(first_started.wait(2))
                    host.handle(command("first"))
                    host.handle(command("second"))
                    second = next(m for m in messages if m.get("request_id") == "second")
                    host.handle({"command": "cancel", "job_id": second["job_id"]})
                    release.set()
                    deadline = time.monotonic() + 3
                    while time.monotonic() < deadline and not any(m["type"] == "cancelled" for m in messages):
                        time.sleep(0.01)
                    self.assertEqual(calls, ["first"])
                    self.assertTrue(any(m["type"] == "duplicate" for m in messages))
                    self.assertTrue(any(m["type"] == "cancelled" for m in messages))
                finally:
                    release.set()
                    host.close()


if __name__ == "__main__":
    unittest.main()
