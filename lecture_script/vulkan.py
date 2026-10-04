"""Cross-vendor Windows GPU transcription using a pinned whisper.cpp Vulkan build."""
import hashlib
import json
import os
import re
import subprocess
import tempfile
import wave
import zipfile
from pathlib import Path
from types import SimpleNamespace
from urllib.request import urlopen

from .storage import DATA

# Community build of upstream whisper.cpp v1.8.4; source/build provenance is in README.
RUNTIME_URL = ("https://github.com/jiang1997/whisper.cpp-release/releases/download/v1.8.4.1/"
               "whisper-1.8.4-windows-x64.zip")
RUNTIME_SHA256 = "4b1b36343feb55ec3deace6a7dd18cc217f43a55e4ecce76ccd4ee3595c0b642"
RUNTIME_MEMBER = "whisper-1.8.4-windows-x64/whisper-cli.exe"
RUNTIME_DIRECTORY = DATA / "tools" / "whisper-vulkan"
MODEL_NAMES = {"tiny": "tiny", "small": "small", "medium": "medium",
               "large-v3": "large-v3", "turbo": "large-v3-turbo"}
CREATE_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def executable():
    return RUNTIME_DIRECTORY / RUNTIME_MEMBER


def install_runtime():
    """Download only the pinned CLI, checking its archive before extraction."""
    if executable().is_file():
        return
    RUNTIME_DIRECTORY.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryFile() as archive:
        with urlopen(RUNTIME_URL, timeout=60) as response:
            digest = hashlib.sha256()
            while block := response.read(1024 * 1024):
                archive.write(block)
                digest.update(block)
        if digest.hexdigest() != RUNTIME_SHA256:
            raise RuntimeError("Vulkan runtime checksum mismatch")
        archive.seek(0)
        with zipfile.ZipFile(archive) as zipped:
            # Extract one known member; do not trust arbitrary archive paths.
            target = executable()
            target.parent.mkdir(parents=True, exist_ok=True)
            partial = target.with_suffix(".partial")
            partial.write_bytes(zipped.read(RUNTIME_MEMBER))
            partial.replace(target)


def parse_devices(log):
    devices = []
    for match in re.finditer(r"ggml_vulkan:\s*(\d+) = ([^\r\n|]+)\| uma: ([01])", log):
        name = match[2].strip()
        if any(software in name.lower() for software in ("llvmpipe", "lavapipe", "swiftshader", "software")):
            continue
        devices.append({"index": int(match[1]), "name": name, "integrated": match[3] == "1"})
    # Prefer dedicated graphics, irrespective of vendor. Keep the CLI's device IDs.
    return sorted(devices, key=lambda device: (device["integrated"], device["index"]))


def available_devices():
    if os.name != "nt" or not executable().is_file():
        return []
    try:
        with tempfile.TemporaryDirectory(prefix="lecture-gpu-probe-") as directory:
            root = Path(directory)
            # This pinned CLI enumerates its actual backends before reading model data.
            # An empty model intentionally stops the probe before loading any weights.
            model = root / "probe.bin"
            model.touch()
            audio = root / "probe.wav"
            with wave.open(str(audio), "wb") as output:
                output.setparams((1, 2, 16000, 0, "NONE", "not compressed"))
                output.writeframes(b"\0\0" * 160)
            result = subprocess.run([str(executable()), "-m", str(model), "-f", str(audio)],
                                    capture_output=True, timeout=20, creationflags=CREATE_NO_WINDOW)
            return parse_devices(result.stderr.decode("utf-8", "replace"))
    except (OSError, subprocess.TimeoutExpired):
        return []


class VulkanModel:
    def __init__(self, model, device):
        from huggingface_hub import hf_hub_download
        self.device = device
        self.path = hf_hub_download("ggerganov/whisper.cpp", f"ggml-{MODEL_NAMES[model]}.bin",
                                    cache_dir=str(DATA / "models"))
        self.vad_path = hf_hub_download("ggml-org/whisper-vad", "ggml-silero-v5.1.2.bin",
                                       cache_dir=str(DATA / "models"))

    def transcribe(self, audio, *, language="ko", initial_prompt=None, beam_size=5,
                   vad_filter=True, cancel=None, **_kwargs):
        """Match the segment interface used by the shared checkpoint/export pipeline."""
        def segments():
            from .pipeline import Cancelled
            with tempfile.TemporaryDirectory(prefix="lecture-vulkan-") as directory:
                root = Path(directory)
                if not isinstance(audio, (str, Path)):
                    import numpy as np
                    samples = (np.clip(audio, -1, 1) * 32767).astype("<i2")
                    audio_path = root / "probe.wav"
                    with wave.open(str(audio_path), "wb") as output:
                        output.setparams((1, 2, 16000, 0, "NONE", "not compressed"))
                        output.writeframes(samples.tobytes())
                else:
                    audio_path = Path(audio)
                output_path = root / "transcript"
                command = [str(executable()), "-m", str(self.path), "-f", str(audio_path),
                           "-dev", str(self.device["index"]), "-l", language or "auto",
                           "-bs", str(beam_size), "-t", str(min(8, os.cpu_count() or 4)),
                           "-mc", "0", "-sow", "-ml", "1", "-oj", "-of", str(output_path)]
                if vad_filter:
                    command += ["--vad", "-vm", str(self.vad_path)]
                if initial_prompt:
                    command += ["--prompt", initial_prompt]
                if cancel and cancel.is_set():
                    raise Cancelled()
                process = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
                                           creationflags=CREATE_NO_WINDOW)
                try:
                    while True:
                        if cancel and cancel.is_set():
                            raise Cancelled()
                        try:
                            _, stderr = process.communicate(timeout=0.2)
                            break
                        except subprocess.TimeoutExpired:
                            continue
                finally:
                    if process.poll() is None:
                        process.kill()
                        process.communicate()
                log = stderr.decode("utf-8", "replace")
                if process.returncode:
                    raise RuntimeError("Vulkan 전사 실패: " + log[-1000:])
                if f"using Vulkan{self.device['index']} backend" not in log:
                    raise RuntimeError("Vulkan GPU가 실제로 활성화되지 않았습니다.")
                payload = json.loads(output_path.with_suffix(".json").read_text(encoding="utf-8"))
                words = []
                for item in payload["transcription"]:
                    start, end = item["offsets"]["from"] / 1000, item["offsets"]["to"] / 1000
                    if end > start and item["text"].strip():
                        words.append(SimpleNamespace(start=start, end=end, word=item["text"]))
                        text = "".join(word.word for word in words)
                        if len(text) >= 80 or text.rstrip().endswith((".", "?", "!", "。")):
                            yield SimpleNamespace(start=words[0].start, end=end, text=text, words=words)
                            words = []
                if words:
                    yield SimpleNamespace(start=words[0].start, end=words[-1].end,
                                          text="".join(word.word for word in words), words=words)
        return segments(), None
