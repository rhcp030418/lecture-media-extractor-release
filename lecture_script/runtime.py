"""Make this app's optional NVIDIA DLLs visible to CTranslate2 on Windows."""
import os
import subprocess
import sys
from importlib.metadata import PackageNotFoundError, distribution
from pathlib import Path

_DLL_HANDLES = []
_CONFIGURED = False


def configure_gpu_runtime():
    global _CONFIGURED
    if _CONFIGURED or os.name != "nt":
        return
    directories = set()
    for package in ("nvidia-cublas-cu12", "nvidia-cudnn-cu12", "nvidia-cuda-runtime-cu12", "nvidia-cuda-nvrtc-cu12"):
        try:
            installed = distribution(package)
        except PackageNotFoundError:
            continue
        for file in installed.files or []:
            if str(file).lower().endswith(".dll"):
                directories.add(str(installed.locate_file(file).resolve().parent))
    for directory in sorted(directories):
        _DLL_HANDLES.append(os.add_dll_directory(directory))
    if directories:
        # Process-local only; LoadLibrary calls in native libraries also consult PATH.
        os.environ["PATH"] = os.pathsep.join(sorted(directories)) + os.pathsep + os.environ.get("PATH", "")
    _CONFIGURED = True


def install_gpu_runtime():
    """Provision cross-vendor Vulkan and, where supported, the CUDA fast path."""
    if os.name != "nt":
        return False
    from .vulkan import install_runtime, available_devices
    print("Installing cross-vendor Vulkan runtime (AMD / Intel / NVIDIA)...", flush=True)
    install_runtime()
    devices = available_devices()
    for device in devices:
        print(f"Vulkan GPU: {device['name']}")
    import ctranslate2
    try:
        count = ctranslate2.get_cuda_device_count()
    except RuntimeError as error:
        print(f"CUDA unavailable; Vulkan and CPU remain available: {error}")
        count = 0
    if not count:
        print("Using Vulkan GPU automatically." if devices else "No supported GPU detected. Using CPU.")
        return bool(devices)
    print(f"Detected {count} NVIDIA CUDA GPU(s). Installing GPU runtime...", flush=True)
    requirements = Path(__file__).resolve().parents[1] / "requirements-gpu.txt"
    subprocess.run([sys.executable, "-m", "pip", "install", "-r", str(requirements),
                    "--disable-pip-version-check"], check=True)
    print("GPU runtimes installed. Transcription selects an available GPU automatically.")
    return True


if __name__ == "__main__":
    install_gpu_runtime()
