from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import List

import yt_dlp


def sanitize_output_name(value: str) -> str:
    cleaned = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return cleaned or "dubbed-video"


def chunk_text_for_tts(text: str, max_chars: int = 180) -> List[str]:
    words = text.split()
    chunks: List[str] = []
    current = ""

    for word in words:
        if len(current) + len(word) + 1 <= max_chars:
            current = f"{current} {word}".strip()
        else:
            if current:
                chunks.append(current)
            current = word

    if current:
        chunks.append(current)

    return chunks or [text]


def build_output_path(output_dir: Path, video_title: str) -> Path:
    return output_dir / f"{sanitize_output_name(video_title)}-dubbed.mp4"


def download_youtube_video(url: str, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    temp_path = output_dir / "source_video.%(ext)s"

    ydl_opts = {
        "format": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        "outtmpl": str(temp_path),
        "quiet": True,
        "noplaylist": True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)

    title = info.get("title", "youtube-video")
    downloaded_files = sorted(output_dir.glob("source_video.*"))
    if not downloaded_files:
        raise FileNotFoundError("The download did not create a media file")

    source_path = downloaded_files[0]
    final_path = output_dir / f"{sanitize_output_name(title)}.mp4"
    if source_path != final_path:
        source_path.rename(final_path)
    return final_path


def extract_audio(video_path: Path, output_dir: Path) -> Path:
    audio_path = output_dir / f"{video_path.stem}.wav"
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(video_path),
        "-vn",
        "-acodec",
        "pcm_s16le",
        "-ar",
        "16000",
        str(audio_path),
    ]
    subprocess.run(cmd, check=True, capture_output=True, text=True)
    return audio_path


def transcribe_audio(audio_path: Path) -> str:
    try:
        import whisper
    except ImportError as exc:  # pragma: no cover - runtime dependency path
        raise RuntimeError("Install openai-whisper to enable transcription") from exc

    model = whisper.load_model("tiny")
    result = model.transcribe(str(audio_path))
    return result.get("text", "")


def translate_to_english(text: str) -> str:
    try:
        from deep_translator import GoogleTranslator
    except ImportError as exc:  # pragma: no cover - runtime dependency path
        raise RuntimeError("Install deep-translator to enable translation") from exc

    translator = GoogleTranslator(source="auto", target="en")
    return translator.translate(text)


def synthesize_english_audio(text: str, output_path: Path) -> Path:
    try:
        from pydub import AudioSegment
        import pyttsx3
    except ImportError as exc:  # pragma: no cover - runtime dependency path
        raise RuntimeError("Install pyttsx3 and pydub to enable English speech synthesis") from exc

    chunks = chunk_text_for_tts(text)
    combined = AudioSegment.silent(duration=0)
    for idx, chunk in enumerate(chunks):
        temp_path = output_path.parent / f"chunk_{idx}.wav"
        subprocess.run(
            [
                sys.executable,
                "-c",
                "import pyttsx3,sys; t=pyttsx3.init(); t.setProperty('rate', 140); t.save_to_file(sys.argv[1], sys.argv[2]); t.runAndWait()",
                chunk,
                str(temp_path),
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        combined += AudioSegment.from_file(temp_path)
        temp_path.unlink(missing_ok=True)

    combined.export(str(output_path), format="wav")
    return output_path


def merge_audio_and_video(video_path: Path, audio_path: Path, output_path: Path) -> Path:
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(video_path),
        "-i",
        str(audio_path),
        "-c:v",
        "copy",
        "-map",
        "0:v:0",
        "-map",
        "1:a:0",
        "-shortest",
        str(output_path),
    ]
    subprocess.run(cmd, check=True, capture_output=True, text=True)
    return output_path


def process_video(url: str, output_dir: Path) -> Path:
    video_path = download_youtube_video(url, output_dir)
    audio_path = extract_audio(video_path, output_dir)
    transcript = transcribe_audio(audio_path)
    if not transcript.strip():
        raise ValueError("The source audio did not produce a readable transcript")

    english_text = translate_to_english(transcript)
    dubbed_audio_path = output_dir / f"{video_path.stem}-dubbed.wav"
    synthesize_english_audio(english_text, dubbed_audio_path)
    output_path = build_output_path(output_dir, video_path.stem)
    merge_audio_and_video(video_path, dubbed_audio_path, output_path)
    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Dub a YouTube video into English")
    parser.add_argument("url", help="YouTube URL to process")
    parser.add_argument("--output-dir", default="output", help="Directory to store generated files")
    args = parser.parse_args()

    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        result = process_video(args.url, output_dir)
    except Exception as exc:  # pragma: no cover - CLI error path
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)

    print(f"Created {result}")


if __name__ == "__main__":
    main()
