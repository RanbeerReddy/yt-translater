# yt-translater

A small Python project that accepts a YouTube URL, downloads the video, transcribes the audio, translates the transcript to English, synthesizes an English dub, and remuxes it into a new video file.

## Requirements

- Python 3.11+
- FFmpeg installed and available on your PATH
- Internet access for downloading the video and using the translation service

## Installation

```bash
pip install -r requirements.txt
```

## Usage

```bash
python -m app.main "https://www.youtube.com/watch?v=VIDEO_ID" --output-dir output
```

## Notes

- The current implementation uses local transcription and a text-to-speech fallback for the dub.
- For production-quality dubbing, you can swap in stronger ASR, translation, and voice-cloning backends later.
