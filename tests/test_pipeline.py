from pathlib import Path

from app.main import build_output_path, chunk_text_for_tts, sanitize_output_name


def test_sanitize_output_name():
    assert sanitize_output_name("My Video: 2024") == "my-video-2024"


def test_chunk_text_for_tts():
    text = "one two three four five six seven eight nine ten"
    chunks = chunk_text_for_tts(text, max_chars=20)

    assert len(chunks) >= 2
    assert all(len(chunk) <= 20 for chunk in chunks)


def test_build_output_path(tmp_path: Path):
    output_path = build_output_path(tmp_path, "demo-video")

    assert output_path.parent == tmp_path
    assert output_path.suffix == ".mp4"
