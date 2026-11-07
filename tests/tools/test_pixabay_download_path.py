"""A Pixabay download must never land in the working directory.

With no output_path, these tools used to write to the repo root, where the files
looked like project work and could end up in a commit.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from lib import paths
from tools.graphics.pixabay_image import PixabayImage
from tools.video.pixabay_video import PixabayVideo

VIDEO_HIT = {"id": 7, "videos": {"large": {"url": "https://x/v", "width": 1, "height": 1}}}
IMAGE_HIT = {"id": 7, "largeImageURL": "https://x/i", "webformatURL": "https://x/i", "imageWidth": 1, "imageHeight": 1}


class _Response:
    def __init__(self, hit):
        self.hit = hit
        self.content = b"file"

    def raise_for_status(self):
        pass

    def json(self):
        return {"hits": [self.hit], "total": 1}


@pytest.fixture
def scratch(monkeypatch, tmp_path) -> Path:
    monkeypatch.setenv("PIXABAY_API_KEY", "test-key")
    monkeypatch.chdir(tmp_path)
    folder = tmp_path / "scratch"
    monkeypatch.setattr(paths, "SCRATCH_DIR", folder)
    return folder


@pytest.mark.parametrize(
    ("tool", "hit", "name"),
    [(PixabayVideo, VIDEO_HIT, "pixabay_video_7.mp4"), (PixabayImage, IMAGE_HIT, "pixabay_7.jpg")],
)
def test_without_a_path_the_file_goes_to_scratch(monkeypatch, scratch, tool, hit, name):
    import requests

    monkeypatch.setattr(requests, "get", lambda *args, **kwargs: _Response(hit))
    result = tool().execute({"query": "sky"})
    assert result.success, result.error
    assert (scratch / name).is_file()
    assert list(Path.cwd().glob("pixabay*")) == []


@pytest.mark.parametrize(("tool", "hit"), [(PixabayVideo, VIDEO_HIT), (PixabayImage, IMAGE_HIT)])
def test_an_explicit_path_is_respected(monkeypatch, scratch, tmp_path, tool, hit):
    import requests

    monkeypatch.setattr(requests, "get", lambda *args, **kwargs: _Response(hit))
    target = tmp_path / "project" / "clip.bin"
    assert tool().execute({"query": "sky", "output_path": str(target)}).success
    assert target.is_file() and not scratch.exists()


def test_scratch_is_ignored_by_git():
    gitignore = (paths.REPO_ROOT / ".gitignore").read_text(encoding="utf-8")
    assert paths.SCRATCH_DIR.relative_to(paths.REPO_ROOT).parts[0] == "output"
    assert "output/" in gitignore.splitlines()
