# yt-translater

A fully automated Python pipeline that downloads YouTube videos, transcribes and translates the spoken audio to English, synthesizes an English speech dub, and remuxes it perfectly back into the original video.

## Features
- **Downloads** high quality YouTube videos using `yt-dlp`
- **Extracts** audio tracks seamlessly via `ffmpeg`
- **Transcribes** audio securely and locally using OpenAI's `whisper` with auto-language detection
- **Translates** transcripts directly to English via `deep-translator`
- **Synthesizes** the translated text into natural audio chunks using `pyttsx3`
- **Merges** synthetic audio flawlessly onto the original video sequence using native `wave` module concatenation and `ffmpeg`

## Requirements

- Python 3.11+
- [FFmpeg](https://ffmpeg.org/download.html) installed and available on your system `PATH`
- Internet access for downloading the video and querying translation services

## Installation

```bash
# Clone the repository
git clone https://github.com/RanbeerReddy/yt-translater.git
cd yt-translater

# Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows use: .venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt
```

## Usage

Run the module with the YouTube URL:

```bash
python -m app.main "https://www.youtube.com/watch?v=VIDEO_ID" --output-dir output
```

The dubbed video will be generated and saved in the specified `output` directory.

## Testing

You can verify the pipeline is functioning properly using `pytest`:

```bash
python -m pytest tests/
```

## Notes

- The current implementation uses local transcription and a local text-to-speech engine. 
- For production-quality speech dubbing, you can swap in stronger ASR backends (like the Whisper large model) or premium voice-cloning backends (like ElevenLabs) later!
