import sys
import types

import pytest

from tools.video.stock_sources import SearchFilters, all_sources, get_source
from tools.video.stock_sources.unsplash import _build_download_url, _orientation_for_unsplash
from tools.video.stock_sources.wikimedia import (
    _build_search_queries,
    _kind_from_mime,
    _meta_value,
)


def test_stock_source_autodiscovery_includes_new_sources():
    names = {source.name for source in all_sources()}
    assert "wikimedia" in names
    assert "unsplash" in names


def test_wikimedia_search_query_respects_kind():
    # The cascade's first ("full") query should always carry the
    # filetype filter for video/image kinds. "any" drops the prefix.
    video_cascade = _build_search_queries("rain city", "video")
    assert video_cascade[0][0] == "full"
    assert video_cascade[0][1].startswith("filetype:video")

    image_cascade = _build_search_queries("rain city", "image")
    assert image_cascade[0][0] == "full"
    assert image_cascade[0][1].startswith("filetype:image")

    any_cascade = _build_search_queries("rain city", "any")
    assert any_cascade[0][0] == "full"
    assert any_cascade[0][1] == "rain city"


def test_wikimedia_cascade_falls_back_on_multi_word():
    # Multi-word query should produce a 3-stage cascade: full, top2_or,
    # single_best. Tokens are picked by length, so "television" beats
    # "family" and "watching".
    cascade = _build_search_queries(
        "1950s family watching television", "video"
    )
    labels = [label for label, _ in cascade]
    assert labels == ["full", "top2_or", "single_best"]
    assert cascade[1][1] == "filetype:video television watching"
    assert cascade[2][1] == "filetype:video television"


def test_wikimedia_cascade_strips_source_hints_and_years():
    # "prelinger" is a source hint (redundant on Commons) and "1955" is
    # a year — both are excluded from distinctive-token picks.
    cascade = _build_search_queries(
        "Prelinger 1955 housewife kitchen", "video"
    )
    # Full query keeps the source hint + year (first attempt is strict).
    assert cascade[0][1] == "filetype:video Prelinger 1955 housewife kitchen"
    # Distinctive picks do NOT include prelinger or 1955.
    joined = " ".join(sq for _, sq in cascade[1:])
    assert "housewife" in joined
    assert "kitchen" in joined
    assert "prelinger" not in joined.lower()
    assert "1955" not in joined


def test_wikimedia_kind_and_metadata_helpers():
    assert _kind_from_mime("video/webm", "File:foo.webm") == "video"
    assert _kind_from_mime("image/jpeg", "File:foo.jpg") == "image"
    assert _meta_value({"Artist": {"value": "<a href='/wiki/User:Test'>Test User</a>"}}, "Artist") == "Test User"


def test_unsplash_helpers_preserve_query_params():
    assert _orientation_for_unsplash("square") == "squarish"
    url = _build_download_url("https://images.unsplash.com/photo-123?ixid=abc", 1920)
    assert "ixid=abc" in url
    assert "w=1920" in url
    assert "fm=jpg" in url


# ---------------------------------------------------------------------
# Transport-error contract (issue #511)
#
# `base.StockSource.search` states the rule: "Network errors should be
# raised — the corpus builder catches and logs per-source so one flaky
# API doesn't poison the whole run." An adapter that swallows the error
# and returns `[]` is indistinguishable from a source that genuinely has
# nothing to offer, so `direct_clip_search` reports `success: True,
# clips_downloaded: 0, errors: []` on a run where every request failed.
#
# The two tests below pin both halves of the contract across *every*
# registered adapter, so a new source cannot quietly reintroduce the bug.
# ---------------------------------------------------------------------

# Adapters that gate on a key before they reach the network. Without
# these the key-gated sources would return early and the test would
# assert nothing.
_SOURCE_CREDENTIALS = {
    "COVERR_API_KEY": "test-coverr",
    "NARA_API_KEY": "test-nara",
    "NASA_API_KEY": "test-nasa",
    "PEXELS_API_KEY": "test-pexels",
    "PIXABAY_API_KEY": "test-pixabay",
    "POND5_API_KEY": "test-pond5",
    "UNSPLASH_ACCESS_KEY": "test-unsplash",
    "VIDEVO_API_KEY": "test-videvo",
}

# Adapters that still swallow transport failures, recorded as known
# defects rather than encoded as expected behavior. `strict=True` means
# the suite fails the moment one of them is fixed and left in this map.
_STILL_SWALLOWS_TRANSPORT_ERRORS = {
    "archive_org": "#511 follow-up: query cascade continues past a failed strategy",
    "wikimedia": "#511 follow-up: query cascade continues past a failed strategy",
    "pond5_pd": "#511 follow-up: API failure falls through to the web fallback",
}


class TransportError(Exception):
    """Distinct failure type so the assertion cannot pass by accident."""


class _EmptyOkResponse:
    """A genuine 200 that simply carries no results."""

    status_code = 200
    text = "<html><body></body></html>"
    content = b""

    def raise_for_status(self):
        return None

    def json(self):
        return {}

    def __enter__(self):
        return self

    def __exit__(self, *_exc):
        return False


class _EmptySoup:
    """Stand-in for `BeautifulSoup`: parses anything, finds nothing."""

    def __init__(self, *_args, **_kwargs):
        pass

    def select(self, *_args, **_kwargs):
        return []

    def select_one(self, *_args, **_kwargs):
        return None

    def find_all(self, *_args, **_kwargs):
        return []

    def find(self, *_args, **_kwargs):
        return None


def _install_fake_transport(monkeypatch, fake_get):
    """Point every adapter's lazy `import requests` at `fake_get`.

    `bs4` is stubbed alongside it: it is an optional dependency (the
    scraping adapters report `is_available() is False` without it), and
    they import it at the top of `search()`. Left alone, those adapters
    would fail on the import rather than on the request, and the test
    would pass for the wrong reason wherever bs4 is not installed.
    """
    requests_stub = types.ModuleType("requests")
    requests_stub.get = fake_get
    monkeypatch.setitem(sys.modules, "requests", requests_stub)

    bs4_stub = types.ModuleType("bs4")
    bs4_stub.BeautifulSoup = _EmptySoup
    monkeypatch.setitem(sys.modules, "bs4", bs4_stub)

    for var, value in _SOURCE_CREDENTIALS.items():
        monkeypatch.setenv(var, value)


def _adapter_names():
    return [source.name for source in all_sources()]


def _transport_error_params():
    params = []
    for name in _adapter_names():
        reason = _STILL_SWALLOWS_TRANSPORT_ERRORS.get(name)
        marks = [pytest.mark.xfail(strict=True, reason=reason)] if reason else []
        params.append(pytest.param(name, marks=marks, id=name))
    return params


@pytest.mark.parametrize("source_name", _transport_error_params())
def test_search_propagates_transport_errors(source_name, monkeypatch):
    def boom(*_args, **_kwargs):
        raise TransportError("simulated connection reset")

    _install_fake_transport(monkeypatch, boom)

    with pytest.raises(TransportError):
        get_source(source_name).search(
            "ocean waves", SearchFilters(kind="any", per_page=5)
        )


@pytest.mark.parametrize("source_name", _adapter_names(), ids=_adapter_names())
def test_search_returns_empty_when_the_source_has_no_results(
    source_name, monkeypatch
):
    # The other half of the contract: `[]` still has to mean "nothing
    # matched". A 200 with an empty payload must not raise.
    _install_fake_transport(monkeypatch, lambda *_a, **_k: _EmptyOkResponse())

    assert (
        get_source(source_name).search(
            "ocean waves", SearchFilters(kind="any", per_page=5)
        )
        == []
    )


class _JsonResponse(_EmptyOkResponse):
    def __init__(self, payload):
        self.payload = payload

    def json(self):
        return self.payload


def _coverr_hit(slug, *, premium=False):
    # Field names and types as api.coverr.co/videos returns them with urls=true.
    return {
        "id": f"id-{slug}",
        "slug": slug,
        "title": "Ocean waves",
        "tags": ["ocean", "waves"],
        "duration": "10.510500",
        "max_width": 3840,
        "max_height": 2160,
        "is_premium": premium,
        "poster": f"https://cdn.coverr.co/{slug}/poster.jpg",
        "urls": {
            "mp4": f"https://cdn.coverr.co/{slug}/1080p.mp4",
            "mp4_preview": f"https://cdn.coverr.co/{slug}/preview.mp4",
            "mp4_download": f"https://cdn.coverr.co/{slug}/download.mp4",
        },
    }


def test_coverr_asks_for_download_links_and_reads_the_real_fields(monkeypatch):
    calls = []

    def fake_get(url, **kwargs):
        calls.append(kwargs)
        return _JsonResponse({"hits": [_coverr_hit("free"), _coverr_hit("paid", premium=True)]})

    _install_fake_transport(monkeypatch, fake_get)
    found = get_source("coverr").search("ocean", SearchFilters(kind="video", per_page=5))

    assert calls[0]["params"]["urls"] == "true"
    assert calls[0]["headers"]["Authorization"] == "Bearer test-coverr"
    assert [c.source_id for c in found] == ["id-free"]
    clip = found[0]
    assert clip.download_url == "https://cdn.coverr.co/free/download.mp4"
    assert (clip.width, clip.height, clip.duration) == (3840, 2160, 10.5105)
    assert clip.thumbnail_url == "https://cdn.coverr.co/free/poster.jpg"
    assert clip.source_tags == "Ocean waves ocean waves"


def test_coverr_needs_a_key(monkeypatch):
    monkeypatch.delenv("COVERR_API_KEY", raising=False)
    assert get_source("coverr").is_available() is False


# Scraper fixtures are cut from the live pages (November 2026), keeping only
# the markup each adapter reads. When a site changes, refresh them from a
# real page rather than editing them to fit the parser.

class _HtmlResponse(_EmptyOkResponse):
    def __init__(self, text):
        self.text = text


def _serve_html(monkeypatch, fake_get):
    """Fake transport, but with the real HTML parser behind `bs4`."""
    bs4 = pytest.importorskip("bs4")
    _install_fake_transport(monkeypatch, fake_get)
    monkeypatch.setitem(sys.modules, "bs4", bs4)


_MIXKIT_SEARCH = """
<div class="item-grid-card" data-algolia-analytics-object-id="video-2168">
 <div class="item-grid-video-player" data-item-grid--video-player-item-id-value="2168"
      data-item-grid--video-player-item-type-value="Video">
  <picture><img alt="Bright orange sunset on beach." src="https://assets.mixkit.co/videos/2168/2168-thumb-360-0.jpg"/></picture>
  <video class="item-grid-video-player__video" src="https://assets.mixkit.co/videos/2168/2168-360.mp4"></video>
  <span class="item-grid-video-player__overlay-video-title"> Bright orange sunset on beach </span>
  <a class="item-grid-video-player__overlay-link" href="/free-stock-video/bright-orange-sunset-on-beach-2168/">Bright orange sunset on beach</a>
 </div>
</div>
"""

_DAREFUL_SEARCH = """
<article class="post-ad entry">
 <a href="https://shutterstock.7eer.net/c/489458/1422653/1305" title="Try Shutterstock"><img src="https://dareful.com/sstk-inline-ad.jpg"/></a>
</article>
<article aria-label="Winter Forest Hike" class="post-2277 entry" itemprop="video" itemscope="" itemtype="http://schema.org/VideoObject">
 <a class="grid-link" data-video="2277" href="https://dareful.com/winter-forest-hike/" title="Winter Forest Hike">
  <div class="video-title" itemprop="name">00:16 | Winter Forest Hike</div></a>
 <div class="video_info">
  <meta content="PT16.649967S" itemprop="duration"/>
  <meta content="https://dareful.com/wp-content/uploads/2024/10/thumbnail-2-590x332.png" itemprop="thumbnailUrl"/>
  <meta content="https://stream.mux.com/HAOWt8ZRHuXVBLRbBQlR64cKmYz0002fBrUuSITWg1154.m3u8" itemprop="contentURL"/>
  <meta content="1920" itemprop="width"/><meta content="1080" itemprop="height"/>
 </div>
</article>
"""


def test_mixkit_reads_the_result_cards_and_points_at_the_1080p_file(monkeypatch):
    calls = []

    def fake_get(url, **kwargs):
        calls.append((url, kwargs))
        return _HtmlResponse(_MIXKIT_SEARCH)

    _serve_html(monkeypatch, fake_get)
    found = get_source("mixkit").search("sunset beach", SearchFilters(kind="video", per_page=5))

    assert calls[0][0] == "https://mixkit.co/free-stock-video/discover/sunset-beach/"
    assert len(found) == 1
    clip = found[0]
    assert clip.source_id == "mixkit_2168"
    assert clip.source_url == "https://mixkit.co/free-stock-video/bright-orange-sunset-on-beach-2168/"
    assert clip.download_url == "https://assets.mixkit.co/videos/2168/2168-1080.mp4"
    assert clip.extra["fallback_url"] == "https://assets.mixkit.co/videos/2168/2168-720.mp4"
    assert clip.extra["preview_url"].endswith("2168-360.mp4")
    assert clip.source_tags.startswith("Bright orange sunset on beach")


def test_mixkit_falls_back_to_720p_when_a_clip_has_no_1080p(monkeypatch, tmp_path):
    import requests

    from tools.video.stock_sources import mixkit
    from tools.video.stock_sources.base import Candidate

    fetched = []

    def fake_download(url, path, **_kwargs):
        fetched.append(url)
        if url.endswith("-1080.mp4"):
            response = requests.Response()
            response.status_code = 403
            raise requests.HTTPError("403 Forbidden", response=response)
        return True

    monkeypatch.setattr(mixkit, "download_media", fake_download)
    candidate = Candidate(
        source="mixkit", source_id="mixkit_7", source_url="https://mixkit.co/x",
        download_url="https://assets.mixkit.co/videos/7/7-1080.mp4", kind="video",
        extra={"fallback_url": "https://assets.mixkit.co/videos/7/7-720.mp4"},
    )
    mixkit.MixkitSource().download(candidate, tmp_path / "7.mp4")
    assert fetched == [candidate.download_url, candidate.extra["fallback_url"]]


def test_dareful_skips_ads_and_downloads_the_mux_mp4(monkeypatch):
    _serve_html(monkeypatch, lambda *_a, **_k: _HtmlResponse(_DAREFUL_SEARCH))
    found = get_source("dareful").search("forest", SearchFilters(kind="video", per_page=5))

    assert [c.source_id for c in found] == ["dareful_winter-forest-hike"]
    clip = found[0]
    assert clip.download_url == (
        "https://stream.mux.com/HAOWt8ZRHuXVBLRbBQlR64cKmYz0002fBrUuSITWg1154/high.mp4"
    )
    assert (clip.width, clip.height, clip.duration) == (1920, 1080, 16.649967)
    assert clip.thumbnail_url.endswith("thumbnail-2-590x332.png")


def test_dareful_resolves_a_page_url_to_the_mux_stream_not_an_ad(monkeypatch, tmp_path):
    import requests

    from tools.video.stock_sources import dareful
    from tools.video.stock_sources.base import Candidate

    page = (
        '<a href="https://ak.picdn.net/shutterstock/videos/1/thumb/stock-footage.mp4">ad</a>'
        '<a href="https://stream.mux.com/AbC123.m3u8">Download Video</a>'
    )
    monkeypatch.setattr(requests, "get", lambda *_a, **_k: _HtmlResponse(page))
    fetched = []
    monkeypatch.setattr(dareful, "download_media", lambda url, *_a, **_k: fetched.append(url))

    candidate = Candidate(
        source="dareful", source_id="dareful_x", source_url="https://dareful.com/x/",
        download_url="https://dareful.com/x/", kind="video",
        extra={"detail_url": "https://dareful.com/x/"},
    )
    dareful.DarefulSource().download(candidate, tmp_path / "x.mp4")
    assert fetched == ["https://stream.mux.com/AbC123/high.mp4"]


def _unsplash_candidate():
    from tools.video.stock_sources.base import Candidate

    return Candidate(
        source="unsplash", source_id="abc", source_url="https://unsplash.com/photos/abc",
        download_url="https://images.unsplash.com/photo-abc?w=1920", kind="image",
        extra={"download_location": "https://api.unsplash.com/photos/abc/download?ixid=x"},
    )


def test_unsplash_reports_each_download_as_its_guidelines_require(monkeypatch, tmp_path):
    import requests

    from tools.video.stock_sources import unsplash

    monkeypatch.setenv("UNSPLASH_ACCESS_KEY", "test-unsplash")
    pings = []
    monkeypatch.setattr(unsplash, "download_media", lambda *_a, **_k: True)
    monkeypatch.setattr(
        requests, "get", lambda url, **kw: pings.append((url, kw["headers"])) or _EmptyOkResponse()
    )

    unsplash.UnsplashSource().download(_unsplash_candidate(), tmp_path / "abc.jpg")
    assert pings == [(
        "https://api.unsplash.com/photos/abc/download?ixid=x",
        {"Authorization": "Client-ID test-unsplash", "Accept-Version": "v1",
         "User-Agent": unsplash._USER_AGENT},
    )]


def test_unsplash_does_not_report_a_failed_download(monkeypatch, tmp_path):
    import requests

    from tools.video.stock_sources import unsplash

    monkeypatch.setenv("UNSPLASH_ACCESS_KEY", "test-unsplash")
    pings = []
    monkeypatch.setattr(requests, "get", lambda url, **_kw: pings.append(url))

    def broken(*_a, **_k):
        raise requests.ConnectionError("dropped")

    monkeypatch.setattr(unsplash, "download_media", broken)
    with pytest.raises(requests.ConnectionError):
        unsplash.UnsplashSource().download(_unsplash_candidate(), tmp_path / "abc.jpg")
    assert pings == []


def test_a_failed_unsplash_ping_keeps_the_saved_photo(monkeypatch, tmp_path):
    import requests

    from tools.video.stock_sources import unsplash

    monkeypatch.setenv("UNSPLASH_ACCESS_KEY", "test-unsplash")
    monkeypatch.setattr(unsplash, "download_media", lambda *_a, **_k: True)

    def offline(*_a, **_k):
        raise requests.ConnectionError("api down")

    monkeypatch.setattr(requests, "get", offline)
    target = tmp_path / "abc.jpg"
    assert unsplash.UnsplashSource().download(_unsplash_candidate(), target) == target
