"""CI smoke test on real macOS/Linux runners; no school login or private media."""
import io
import json
import subprocess
import sys
import tempfile
import threading
from pathlib import Path
from urllib.request import urlretrieve

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import install_chrome
from lecture_script import NATIVE_HOST_NAME
from lecture_script.browser import Source
from lecture_script.native_host import read_message, write_message
from lecture_script.pipeline import Options, Transcriber, process_source
from lecture_script.whisper_cpp import SOURCE_COMMIT, available_devices, executable


def main():
    cli = executable()
    assert cli and cli.is_file(), "Platform GPU engine was not installed/built"
    subprocess.run([str(cli), "--help"], check=True, capture_output=True, timeout=30)
    manifest_path = install_chrome.manifest_directory() / f"{NATIVE_HOST_NAME}.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    request = io.BytesIO()
    write_message(request, {"command": "hello"})
    result = subprocess.run([manifest["path"]], input=request.getvalue(), capture_output=True, timeout=30)
    assert result.returncode == 0, result.stderr.decode("utf-8", "replace")
    assert read_message(io.BytesIO(result.stdout))["type"] == "ready"
    print("Installed Chrome native host handshake passed", flush=True)

    devices = available_devices()
    print("Detected GPU backends:", devices, flush=True)
    with tempfile.TemporaryDirectory(prefix="lecture platform ") as temporary:
        root = Path(temporary)
        audio = root / "sample.wav"
        urlretrieve(f"https://raw.githubusercontent.com/ggml-org/whisper.cpp/{SOURCE_COMMIT}/samples/jfk.wav", audio)
        engine = Transcriber()
        options = Options(root / "output", model="tiny", language="en", prefer_subtitles=False)
        result = process_source(Source(str(audio), "local", "Public speech fixture"), options, engine,
                                threading.Event(), lambda n, text: print(n, text, flush=True))
        text = " ".join(segment["text"] for segment in result["payload"]["segments"]).lower()
        assert "country" in text, text
        if devices:
            assert engine.actual_device in {device["backend"] for device in devices}, engine.actual_device
        else:
            assert engine.actual_device == "cpu"
        print(f"Real transcription/export passed: {engine.actual_device}", flush=True)
        if not devices:
            print("This runner exposes no GPU; hardware GPU execution was not tested.", flush=True)


if __name__ == "__main__":
    main()
