# Lecture Media Extractor

Lecture Media Extractor saves your choice of MP4 video, MP3 audio, and transcripts. Select one or more formats in the Chrome extension; selected files are kept and only temporary processing files are removed. The automatic Windows/Chrome workflow is based on Lecture Script 0.3. The existing URL sniffer and Python CLI are also available.

## 자동 처리: MP4 · MP3 · 스크립트 선택 다운로드

Windows와 Chrome에서 한성 eClass 강의 창을 열면 확장에서 체크한 **MP4 영상·MP3 음성·스크립트**를 자동으로 저장합니다. 기본값은 세 항목 모두 선택이며, 필요한 항목만 체크할 수 있습니다.

### 처음 설치

1. **Python 3.12 (64비트)**를 Python 실행기(`py`)와 함께 설치합니다.
2. 이 저장소를 내려받아 압축을 풀고, 루트 폴더의 **`setup.cmd`**를 실행합니다. Python 패키지 설치와 현재 Windows 사용자의 Chrome Native Messaging 등록을 진행합니다.
3. Chrome에서 `chrome://extensions`를 열고 **개발자 모드 → 압축해제된 확장 프로그램을 로드합니다**를 누릅니다.
4. 이 저장소의 **`extension`** 폴더를 선택합니다.
5. 이미 열려 있던 eClass 과목 페이지를 새로고침하고, 강의 동영상 창을 엽니다. 영상 주소가 재생 후에 제공되면 재생을 한 번 누릅니다.

설치 화면 안내: [install-guide.html](install-guide.html). 관리자 권한은 필요하지 않습니다. 프로젝트 폴더를 옮기면 `install-chrome.cmd`를 실행하고 확장도 새 경로에서 다시 로드합니다.

**이전 버전에서 업데이트할 때도 이 폴더의 `install-chrome.cmd`를 한 번 실행하세요.** 0.4의 선택 다운로드는 새 로컬 처리기 연결을 사용하므로 확장 새로고침만으로는 적용되지 않습니다. 이 폴더에 처음 설치한다면 `setup.cmd`를 실행합니다.

자동 처리 확장은 `extension`입니다. 아래의 `m3u8-sniffer-extension`은 주소 복사와 과목 목록 수집을 위한 별도 확장입니다. 자동 처리에는 설치하지 않아도 됩니다.

### 사용 및 저장 위치

- 확장 아이콘의 **다운로드할 파일**에서 MP4 영상, MP3 음성, 스크립트를 선택하고 **선택한 파일 다운로드 / 재시도**를 누릅니다. 자동 시작에도 같은 선택을 사용합니다.
- 선택은 확장 팝업을 닫아도 유지되고 다음 작업부터 적용됩니다. 하나도 선택하지 않으면 작업을 시작하지 않습니다.
- 결과는 Windows에 등록된 **다운로드 폴더/lecture/과목명/** 아래의 `video/*.mp4`, `audio/*.mp3`, `script/강의명/`에 저장됩니다.
- **선택한 결과물은 삭제하지 않습니다.** 선택한 출력이 모두 완료되면 임시 영상·WAV·작업 파일만 정리합니다. 이후 선택을 바꿔도 앞서 저장한 결과와 로컬 원본은 보존합니다.
- MP4와 MP3는 실제 해당 형식으로 저장합니다. 스크립트를 해제하면 음성 인식을 실행하지 않고 모델도 내려받지 않습니다. MP4만 선택하면 음성 추출도 생략합니다.
- 대본 폴더에는 `transcript.txt`, `transcript.md`, `subtitles.srt`, `subtitles.vtt`, JSON 메타데이터가 생성됩니다.
- 과목명은 강의 창 또는 그 창을 연 과목 페이지에서 읽습니다. 찾지 못하면 `과목 미지정`에 저장하며, 확장 팝업에서 과목명을 입력하고 재시도할 수 있습니다.
- 완료된 강의를 다시 열면 현재 선택한 파일이 모두 있을 때 기존 결과를 사용합니다. 선택을 추가하거나 파일이 누락되면 다시 처리합니다. 저장된 MP4가 있으면 재사용하며, 실패·중단된 작업의 임시 파일과 완료한 전사 구간도 재시도에 사용합니다.
- **처리 중에는 Chrome을 켜두세요.** 강의 탭이나 확장 팝업은 닫아도 됩니다. Chrome을 완전히 종료하면 처리가 중단됩니다.
- `start.cmd`로 저장 기록을 확인하거나 내 파일을 스크립트로 변환할 수 있습니다. MP4·MP3 선택 다운로드는 크롬 확장에서 설정합니다. 자동 처리에는 관리 화면을 켜둘 필요가 없습니다.

자동 시작은 `https://learn.hansung.ac.kr/mod/vod/viewer.php?id=...`에 적용됩니다. 다른 사이트에서는 확장의 **선택한 파일 다운로드 / 재시도**를 사용할 수 있습니다. MP4, HLS, DASH 감지는 플레이어 방식에 따라 달라집니다. 자동 처리 확장은 다른 강의를 직접 열거나 과목 목록을 순회하지 않습니다.

음성 인식은 로컬에서 실행하고, 모델은 처음 사용할 때 내려받습니다. 기본 설치는 CPU에서 사용할 수 있습니다. NVIDIA GPU용 선택 패키지는 다음 명령으로 설치합니다. GPU 초기화에 실패하면 자동 모드에서 CPU로 전환합니다.

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-gpu.txt
```

영상 다운로드에 필요한 로그인 쿠키와 요청 헤더는 해당 영상·페이지 범위에서 로컬 처리기로 전달합니다. 인증 정보는 디스크에 저장하지 않습니다. 모델·다운로드 결과·작업 기록은 Git에 포함하지 않습니다.

### 문제 해결

- **로컬 처리기 연결 오류:** `install-chrome.cmd` 실행 → 확장 새로고침 → 강의 창에서 재시도.
- **영상 감지 대기:** 과목 페이지와 강의 창을 새로고침하고 필요하면 재생을 누릅니다.
- **주소 만료 / 403:** 로그인 상태에서 강의 창을 새로 열고 재시도합니다.
- **전사 실패:** 확장에 표시된 오류를 확인합니다. 완료된 영상과 음성은 보존되므로 재시도할 수 있습니다.

### 자동 처리 개발 검증

```powershell
.\.venv\Scripts\python.exe -m playwright install chromium
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
node --check extension/background.js
node --check extension/content.js
node --check extension/popup.js
```

테스트는 로컬 서버와 모의 학교 페이지를 사용합니다. 실제 학교 로그인·플레이어 및 모델 추론은 별도 확인이 필요합니다.

## Manual URL Sniffer And CLI

Use it only with lectures or media you are allowed to access and process. DRM-protected streams are not supported.

The manual workflow has two parts:

- `m3u8-sniffer-extension`: Chrome/Edge extension that detects lecture `.m3u8` playlist and subtitle URLs.
- `m3u8`: Python CLI pipeline that uses subtitles when available, or extracts audio with ffmpeg and transcribes it with faster-whisper.

The release folder intentionally excludes Whisper models, virtual environments, ffmpeg binaries, logs, generated transcripts, and private/signed lecture URLs.

## Folder Layout

```text
lecture-media-extractor-release/
  lecture_script/             Automatic pipeline and local file manager
  extension/                  Automatic Chrome extension
  tests/                      Automatic pipeline regression tests
  m3u8/                       Python transcript CLI
  m3u8-sniffer-extension/     Chrome/Edge Manifest V3 extension
  examples/                   Safe placeholder examples
  scripts/                    Convenience scripts
  tools/                      Optional local tools, not committed
```

## Requirements

- Python 3.11 or newer
- ffmpeg and ffprobe on `PATH`, or explicit paths passed with `--ffmpeg` and `--ffprobe`
- Chrome or Edge for the URL sniffer extension
- Enough disk space for model cache and transcript outputs

CPU transcription works by default. CUDA/GPU transcription can be faster, but it depends on local NVIDIA driver/CUDA/cuDNN compatibility.

## Install Python App

From the repository root:

```powershell
cd .\m3u8
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
python -m app.main --check-ffmpeg
```

After installation, the CLI is also available as:

```powershell
m3u8-transcript --check-ffmpeg
```

If ffmpeg is not on `PATH`, install it separately and pass the binary paths:

```powershell
python -m app.main --check-ffmpeg --ffmpeg "C:\path\to\ffmpeg.exe" --ffprobe "C:\path\to\ffprobe.exe"
```

## Install Browser Extension

1. Open `chrome://extensions` or `edge://extensions`.
2. Enable developer mode.
3. Click `Load unpacked`.
4. Select `m3u8-sniffer-extension`.

Open a lecture page, start playback, then use the extension popup to copy a media URL or scan a supported course page queue.

## Run One URL

```powershell
cd .\m3u8
.\.venv\Scripts\Activate.ps1
python -m app.main --run-url "https://example.com/path/index.m3u8" --out ..\outputs\one --whisper-model medium
```

Useful options:

```powershell
python -m app.main --run-url "https://example.com/path/index.m3u8" `
  --out ..\outputs\one `
  --whisper-model large-v3 `
  --whisper-device cuda `
  --whisper-compute-type int8_float16 `
  --whisper-beam-size 5 `
  --language ko
```

## Run Batch

Put one m3u8 URL per line in a text file. Lines starting with `#` are ignored.

```powershell
.\scripts\run-batch.ps1 -Urls .\examples\urls.example.txt -Out .\outputs\course -Model medium
```

For CUDA:

```powershell
.\scripts\run-batch.ps1 -Urls .\examples\urls.example.txt -Out .\outputs\course -Model large-v3 -Device cuda -ComputeType int8_float16 -BeamSize 5
```

Each item writes:

- `transcript.txt`
- `transcript.md`
- `transcript.srt`
- `transcript.json`

The batch summary is written to `batch_summary.json`.

## Model Notes

Models are not included in this release. faster-whisper downloads or uses the requested model under `m3u8/model-cache/whisper-models` by default.

Common choices:

- `tiny`: very fast, useful for smoke tests
- `medium`: balanced
- `large-v3`: better quality, heavier

For Korean technical lectures, `large-v3` with later LLM cleanup usually gives the best study notes, especially for domain terms.

## Privacy And Sharing

Do not commit:

- real signed CDN URLs
- cookies or authorization headers
- generated transcripts from private lectures
- downloaded models
- local ffmpeg binaries

Generated metadata redacts common signed URL query parameters, but private transcripts and raw captured manifests should still be treated as private.

The browser extension uses broad `<all_urls>` permissions because lecture players and CDN hosts vary. It stores detections in browser session storage and does not send them to a remote server.

Before publishing to GitHub, run:

```powershell
git status
git diff --stat
```

Then check that only source, docs, examples, and scripts are staged.

## License

MIT. See `LICENSE`.
