"""A download only takes its final name once the bytes check out.

A dropped connection used to leave a truncated clip under a finished-looking
name. These tests pin the contract: nothing at the final path or at ``.part``
after any failure, and a cut MP4 is caught even when ffprobe would accept it.
"""

from __future__ import annotations

import io
import shutil
import subprocess
from pathlib import Path

import pytest
import requests

from lib import media_download
from lib.media_download import MediaDownloadError, check_media, download_media
from tools.video.stock_sources.base import Candidate
from tools.video.stock_sources.pexels import PexelsSource

needs_ffmpeg = pytest.mark.skipif(not shutil.which("ffmpeg"), reason="ffmpeg not installed")


class _Response:
    def __init__(self, chunks, *, status_error=None, drop_after=None):
        self.chunks = chunks
        self.status_error = status_error
        self.drop_after = drop_after

    def raise_for_status(self):
        if self.status_error:
            raise self.status_error

    def iter_content(self, chunk_size=1):
        for index, chunk in enumerate(self.chunks):
            if self.drop_after is not None and index >= self.drop_after:
                raise requests.ConnectionError("connection dropped")
            yield chunk

    def __enter__(self):
        return self

    def __exit__(self, *_exc):
        return False


def _serve(monkeypatch, response):
    monkeypatch.setattr(requests, "get", lambda *args, **kwargs: response)


@pytest.fixture(scope="module")
def clip(tmp_path_factory) -> bytes:
    if not shutil.which("ffmpeg"):
        pytest.skip("ffmpeg not installed")
    path = tmp_path_factory.mktemp("media") / "clip.mp4"
    subprocess.run(
        [
            "ffmpeg", "-v", "error", "-y", "-f", "lavfi",
            "-i", "testsrc=size=320x240:rate=30", "-t", "4",
            "-c:v", "libx264", "-movflags", "+faststart", str(path),
        ],
        check=True,
    )
    return path.read_bytes()


def _png() -> bytes:
    from PIL import Image

    buffer = io.BytesIO()
    Image.new("RGB", (8, 8), "red").save(buffer, format="PNG")
    return buffer.getvalue()


def _leftovers(path: Path) -> list[str]:
    return sorted(p.name for p in path.parent.iterdir())


@needs_ffmpeg
def test_a_whole_clip_is_published_and_verified(monkeypatch, tmp_path, clip):
    _serve(monkeypatch, _Response([clip]))
    target = tmp_path / "out" / "clip.mp4"
    assert download_media("https://x/clip.mp4", target, kind="video") is True
    assert target.read_bytes() == clip
    assert _leftovers(target) == ["clip.mp4"]


@needs_ffmpeg
def test_a_cut_clip_that_ffprobe_accepts_is_rejected(monkeypatch, tmp_path, clip):
    cut = clip[: len(clip) * 6 // 10]
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-i", "pipe:0"], input=cut, capture_output=True, check=False
    )
    assert probe.returncode == 0, "the cut must fool ffprobe, or this test proves nothing"

    _serve(monkeypatch, _Response([cut]))
    target = tmp_path / "clip.mp4"
    with pytest.raises(MediaDownloadError, match="does not decode to the end"):
        download_media("https://x/clip.mp4", target, kind="video")
    assert _leftovers(target) == []


@needs_ffmpeg
def test_a_dropped_connection_keeps_the_previous_good_file(monkeypatch, tmp_path, clip):
    target = tmp_path / "clip.mp4"
    target.write_bytes(clip)
    half = len(clip) // 2
    _serve(monkeypatch, _Response([clip[:half], clip[half:]], drop_after=1))
    with pytest.raises(requests.ConnectionError):
        download_media("https://x/clip.mp4", target, kind="video")
    assert target.read_bytes() == clip
    assert _leftovers(target) == ["clip.mp4"]


def test_an_http_error_leaves_nothing(monkeypatch, tmp_path):
    _serve(monkeypatch, _Response([b"x"], status_error=requests.HTTPError("404")))
    target = tmp_path / "clip.mp4"
    with pytest.raises(requests.HTTPError):
        download_media("https://x/clip.mp4", target, kind="video")
    assert _leftovers(target) == []


def test_an_empty_body_is_rejected(monkeypatch, tmp_path):
    _serve(monkeypatch, _Response([]))
    target = tmp_path / "photo.jpg"
    with pytest.raises(MediaDownloadError, match="empty"):
        download_media("https://x/photo.jpg", target, kind="image")
    assert _leftovers(target) == []


def test_images_are_checked_with_pillow(monkeypatch, tmp_path):
    target = tmp_path / "photo.png"
    _serve(monkeypatch, _Response([_png()]))
    assert download_media("https://x/photo.png", target, kind="image") is True

    _serve(monkeypatch, _Response([b"<html>rate limited</html>"]))
    with pytest.raises(MediaDownloadError, match="not a readable image"):
        download_media("https://x/photo.png", target, kind="image")
    assert _leftovers(target) == ["photo.png"]


def test_without_ffmpeg_a_video_is_kept_but_unverified(monkeypatch, tmp_path):
    monkeypatch.setattr(media_download.shutil, "which", lambda _name: None)
    _serve(monkeypatch, _Response([b"not checked"]))
    target = tmp_path / "clip.mp4"
    assert download_media("https://x/clip.mp4", target, kind="video") is False
    assert target.read_bytes() == b"not checked"


def test_an_unknown_kind_is_a_caller_error(tmp_path):
    path = tmp_path / "a.bin"
    path.write_bytes(b"x")
    with pytest.raises(ValueError, match="Unknown media kind"):
        check_media(path, "audio")


@needs_ffmpeg
def test_a_stock_source_never_leaves_a_cut_clip(monkeypatch, tmp_path, clip):
    _serve(monkeypatch, _Response([clip[: len(clip) * 6 // 10]]))
    candidate = Candidate(
        source="pexels", source_id="1", source_url="https://x",
        download_url="https://x/1.mp4", kind="video",
    )
    target = tmp_path / "corpus" / "1.mp4"
    with pytest.raises(MediaDownloadError):
        PexelsSource().download(candidate, target)
    assert _leftovers(target) == []
