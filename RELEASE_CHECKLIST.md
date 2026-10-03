# Release Checklist

Before publishing:

- Confirm no real lecture URLs, cookies, tokens, model files, ffmpeg binaries, transcripts, or logs are staged.
- Run tests from `m3u8`.
- Run `python -m unittest discover -s tests -v` from the root after installing `requirements.txt` and the Playwright Chromium test browser.
- Check `extension/*.js` syntax and load the automatic extension from `extension`.
- On Windows, verify `setup.cmd` installs dependencies and registers the native host, then check automatic processing in Chrome.
- Load the browser extension once from `m3u8-sniffer-extension`.
- Remove generated caches such as `__pycache__` if creating a manual zip.
- Create the zip from a clean git checkout or GitHub release archive.

Suggested local checks:

```powershell
rg -n "PRIVATE_CDN|YOUR_LOCAL_PATH|sk-|BEGIN PRIVATE|Bearer [A-Za-z0-9._-]{20,}" . --glob "!RELEASE_CHECKLIST.md"
git status
```
