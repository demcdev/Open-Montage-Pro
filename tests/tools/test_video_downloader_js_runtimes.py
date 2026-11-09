"""Every yt-dlp call lets YouTube's challenges run on Node, not only Deno.

yt-dlp enables only Deno by default. Without a runtime it still lists
YouTube formats but warns that some are missing, and downloads can fail.
"""

from __future__ import annotations

import sys
import types

import pytest

from tools.analysis.video_downloader import VideoDownloader


@pytest.fixture
def seen_opts(monkeypatch):
    opts_seen: list[dict] = []

    class FakeYoutubeDL:
        def __init__(self, opts):
            opts_seen.append(opts)

        def __enter__(self):
            return self

        def __exit__(self, *_exc):
            return False

        def extract_info(self, url, download=False):
            return {"title": "t", "duration": 1}

        def download(self, urls):
            return 0

    monkeypatch.setitem(sys.modules, "yt_dlp", types.SimpleNamespace(YoutubeDL=FakeYoutubeDL))
    return opts_seen


@pytest.mark.parametrize("fmt", ["metadata_only", "video", "audio_only", "subtitles_only"])
def test_every_call_enables_node_and_deno(seen_opts, tmp_path, fmt):
    VideoDownloader().execute({"url": "https://example.com/v", "output_dir": str(tmp_path), "format": fmt})
    assert seen_opts
    assert all(opts["js_runtimes"] == {"deno": {}, "node": {}} for opts in seen_opts)


def test_each_call_gets_its_own_runtimes_dict(seen_opts, tmp_path):
    # yt-dlp normalises the dict in place; a shared one would leak between calls.
    VideoDownloader().execute({"url": "https://example.com/v", "output_dir": str(tmp_path), "format": "video"})
    dicts = [opts["js_runtimes"] for opts in seen_opts]
    assert len(dicts) == 2
    assert dicts[0] is not dicts[1]
