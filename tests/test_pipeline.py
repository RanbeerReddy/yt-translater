import builtins
from pathlib import Path
from unittest.mock import MagicMock, patch

from app.main import (
    build_output_path,
    chunk_text_for_tts,
    process_video,
    sanitize_output_name,
)


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


@patch("app.main.download_youtube_video")
@patch("app.main.extract_audio")
@patch("app.main.transcribe_audio")
@patch("app.main.translate_to_english")
@patch("app.main.synthesize_english_audio")
@patch("app.main.merge_audio_and_video")
def test_process_video_mocked(
    mock_merge,
    mock_synthesize,
    mock_translate,
    mock_transcribe,
    mock_extract,
    mock_download,
    tmp_path: Path,
):
    # Setup mocks
    mock_download.return_value = tmp_path / "video.mp4"
    mock_extract.return_value = tmp_path / "audio.wav"
    mock_transcribe.return_value = "Hola mundo"
    mock_translate.return_value = "Hello world"
    mock_synthesize.return_value = tmp_path / "english.wav"
    mock_merge.return_value = tmp_path / "video-dubbed.mp4"

    # Run
    result = process_video("http://youtube.com/watch?v=123", tmp_path)

    # Asserts
    mock_download.assert_called_once_with("http://youtube.com/watch?v=123", tmp_path)
    mock_extract.assert_called_once_with(mock_download.return_value, tmp_path)
    mock_transcribe.assert_called_once_with(mock_extract.return_value)
    mock_translate.assert_called_once_with("Hola mundo")
    mock_synthesize.assert_called_once_with("Hello world", tmp_path / "video-dubbed.wav")
    mock_merge.assert_called_once_with(mock_download.return_value, tmp_path / "video-dubbed.wav", tmp_path / "video-dubbed.mp4")

    assert result == mock_merge.return_value
