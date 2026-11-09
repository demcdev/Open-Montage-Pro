"""Mixkit (by Envato) stock video source adapter.

Scrapes the Mixkit website (``mixkit.co``) for free stock video clips.
Mixkit offers curated, high-quality footage (HD and 4K) under a free
licence with no attribution required. The library is smaller than
Pixabay/Pexels but has higher average quality due to Envato's curation.

No API available — this adapter scrapes Mixkit search pages. Each result
card carries the clip id, and the files sit at a predictable address
(``assets.mixkit.co/videos/<id>/<id>-1080.mp4``, with ``-720`` for clips
that have no 1080p), so no detail page is fetched.

What Mixkit is good for
-----------------------
- High-quality curated B-roll (nature, business, technology, lifestyle)
- Clean, modern footage with consistent quality
- No-attribution-needed clips for quick gap-fills
- Nature and landscape establishing shots
"""
from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

from lib.media_download import download_media

from .base import Candidate, SearchFilters

_log = logging.getLogger(__name__)

# ``?q=`` on the listing page is ignored (it returns the same popular clips
# for any query); the real search lives under ``discover/<slug>/``.
_SEARCH_URL = "https://mixkit.co/free-stock-video/discover/{slug}/"
_ASSET_URL = "https://assets.mixkit.co/videos/{id}/{id}-{height}.mp4"
_HEADERS = {"User-Agent": "OpenMontage/1.0"}
_LICENSE = "Mixkit License (free for commercial and personal use, no attribution required)"


class MixkitSource:
    """Mixkit video adapter. Satisfies `StockSource`."""

    name = "mixkit"
    display_name = "Mixkit"
    provider = "envato"
    priority = 19
    install_instructions = (
        "Mixkit works without an API key. Scrapes the Mixkit website. "
        "Requires beautifulsoup4: pip install beautifulsoup4"
    )
    supports = {"video": True, "image": False}

    def is_available(self) -> bool:
        try:
            import bs4  # noqa: F401
            return True
        except ImportError:
            return False

    def search(self, query: str, filters: SearchFilters) -> list[Candidate]:
        import requests
        from bs4 import BeautifulSoup

        kind = (filters.kind or "video").lower()
        if kind == "image":
            return []

        slug = re.sub(r"[^a-z0-9]+", "-", query.lower()).strip("-")
        if not slug:
            return []

        try:
            r = requests.get(
                _SEARCH_URL.format(slug=slug),
                timeout=30,
                headers=_HEADERS,
            )
            r.raise_for_status()
        except Exception as e:
            # Contract: an empty list means "nothing matched", so a
            # transport failure has to propagate. See `base.StockSource`.
            _log.warning("Mixkit search failed: %s", e)
            raise

        soup = BeautifulSoup(r.text, "html.parser")
        out: list[Candidate] = []

        for card in soup.select(".item-grid-card"):
            if len(out) >= filters.per_page:
                break
            player = card.select_one("[data-item-grid--video-player-item-id-value]")
            link_el = card.select_one("a.item-grid-video-player__overlay-link[href]")
            if not player or not link_el:
                continue
            clip_id = player["data-item-grid--video-player-item-id-value"]
            if not clip_id.isdigit():
                continue

            href = link_el["href"]
            if not href.startswith("http"):
                href = f"https://mixkit.co{href}"

            title_el = card.select_one(".item-grid-video-player__overlay-video-title")
            title = title_el.get_text(strip=True) if title_el else link_el.get_text(strip=True)

            img_el = card.select_one("img")
            thumb = (img_el.get("src") or "") if img_el else ""
            video_el = card.select_one("video[src]")
            preview_url = (video_el.get("src") or "") if video_el else ""

            out.append(
                Candidate(
                    source=self.name,
                    source_id=f"mixkit_{clip_id}",
                    source_url=href,
                    download_url=_ASSET_URL.format(id=clip_id, height=1080),
                    kind="video",
                    width=0,
                    height=0,
                    duration=0.0,
                    creator="Mixkit",
                    license=_LICENSE,
                    source_tags=f"{title} {query}",
                    thumbnail_url=thumb,
                    extra={
                        "detail_url": href,
                        "preview_url": preview_url,
                        "fallback_url": _ASSET_URL.format(id=clip_id, height=720),
                    },
                )
            )

        return out

    def download(self, candidate: Candidate, out_path: Path) -> Path:
        """Download the 1080p file, or the 720p one when a clip has no 1080p."""
        import requests

        out_path = Path(out_path)
        fallback = candidate.extra.get("fallback_url")
        try:
            download_media(candidate.download_url, out_path, kind=candidate.kind,
                           timeout=120, headers=_HEADERS)
        except requests.HTTPError as e:
            status = getattr(e.response, "status_code", None)
            if not fallback or status not in (403, 404):
                raise
            download_media(fallback, out_path, kind=candidate.kind,
                           timeout=120, headers=_HEADERS)
        return out_path
