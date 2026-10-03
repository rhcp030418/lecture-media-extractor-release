"""Register the native host for the current Windows user; no admin needed."""
import base64
import hashlib
import json
import os
import sys
from pathlib import Path
from lecture_script import NATIVE_HOST_NAME

ROOT = Path(__file__).resolve().parent


def install():
    if os.name != "nt":
        raise RuntimeError("This installer supports Windows.")
    import winreg
    python = ROOT / ".venv" / "Scripts" / "python.exe"
    if not python.is_file():
        raise RuntimeError("Run setup.cmd first.")
    extension = json.loads((ROOT / "extension" / "manifest.json").read_text(encoding="utf-8"))
    digest = hashlib.sha256(base64.b64decode(extension["key"])).hexdigest()[:32]
    extension_id = "".join(chr(ord("a") + int(char, 16)) for char in digest)
    directory = ROOT / "data" / "chrome"
    directory.mkdir(parents=True, exist_ok=True)
    launcher = directory / "native-host.cmd"
    launcher.write_text(
        '@echo off\nchcp 65001 >nul\nsetlocal\n'
        f'cd /d "{ROOT}"\n"{python}" -u -m lecture_script.native_host %*\n', encoding="utf-8")
    manifest = directory / f"{NATIVE_HOST_NAME}.json"
    manifest.write_text(json.dumps({
        "name": NATIVE_HOST_NAME, "description": "Lecture Script selected MP4/MP3/transcript exports",
        "path": str(launcher), "type": "stdio", "allowed_origins": [f"chrome-extension://{extension_id}/"]
    }, indent=2), encoding="utf-8")
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, rf"Software\Google\Chrome\NativeMessagingHosts\{NATIVE_HOST_NAME}") as key:
        winreg.SetValueEx(key, "", 0, winreg.REG_SZ, str(manifest))
    print(f"Native host installed. Extension ID: {extension_id}")
    print(f"Chrome > chrome://extensions > Developer mode > Load unpacked > {ROOT / 'extension'}")
    if "--open-guide" in sys.argv:
        os.startfile(ROOT / "install-guide.html")
    return extension_id


if __name__ == "__main__":
    install()
