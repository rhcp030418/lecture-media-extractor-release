"""Make this app's optional NVIDIA DLLs visible to CTranslate2 on Windows."""
import os
from importlib.metadata import PackageNotFoundError, distribution

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
