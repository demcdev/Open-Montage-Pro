"""Dareful stock video source adapter.

Scrapes the Dareful website (``dareful.com``, formerly
StockFootageForFree.com) for free 4K nature footage. Dareful is a
boutique collection curated by a single creator (Joel Holland) offering
high-quality landscape, forest, mountain, waterfall, and time-lapse
footage.

Licensed under CC BY 4.0 (attribution required). No API available.
Clips are hosted on Mux: each search card's ``contentURL`` names the Mux
playback id, and ``stream.mux.com/<id>/high.mp4`` is the full-resolution MP4.

What Dareful is good for
------------------------
- 4K nature B-roll (mountains, forests, waterfalls, oceans)
- Aerial landscape footage
- Time-lapse sequences (sunrise, clouds, stars)
- Consistent visual style (single creator)
"""
from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

from lib.media_download import download_media

from .base import Candidate, SearchFilters

_log = logging.getLogger(__name__)

_BASE_URL = "https://www.dareful.com"
_HEADERS = {"User-Agent": "OpenMontage/1.0"}
_LICENSE = "Creative Commons Attribution 4.0 (CC BY 4.0, attribution required)"
_MUX_STREAM = re.compile(r"https://stream\.mux\.com/([A-Za-z0-9]+)\.m3u8")
_MUX_MP4 = "https://stream.mux.com/{id}/high.mp4"
_ISO_DURATION = re.compile(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:([\d.]+)S)?")


def _mux_mp4(text: str) -> str | None:
    match = _MUX_STREAM.search(text)
    return _MUX_MP4.format(id=match.group(1)) if match else None


def _seconds(iso: str) -> float:
    match = _ISO_DURATION.fullmatch(iso or "")
    if not match:
        return 0.0
    hours, minutes, seconds = (float(g or 0) for g in match.groups())
    return hours * 3600 + minutes * 60 + seconds


class DarefulSource:
    """Dareful nature footage adapter. Satisfies `StockSource`."""

    name = "dareful"
    display_name = "Dareful"
    provider = "dareful"
    priority = 50
    install_instructions = (
        "Dareful works without an API key. Scrapes the Dareful website. "
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

        try:
            r = requests.get(
                _BASE_URL,
                params={"s": query},
                timeout=30,
                headers=_HEADERS,
            )
            r.raise_for_status()
        except Exception as e:
            # Contract: an empty list means "nothing matched", so a
            # transport failure has to propagate. See `base.StockSource`.
            _log.warning("Dareful search failed: %s", e)
            raise

        soup = BeautifulSoup(r.text, "html.parser")
        out: list[Candidate] = []

        def meta(card, prop: str) -> str:
            el = card.select_one(f"meta[itemprop={prop}]")
            return (el.get("content") or "") if el else ""

        for card in soup.select("article[itemtype$='VideoObject']"):
            if len(out) >= filters.per_page:
                break
            link_el = card.select_one("a.grid-link[href]")
            download_url = _mux_mp4(meta(card, "contentURL"))
            if not link_el or not download_url:
                continue

            href = link_el["href"]
            if not href.startswith("http"):
                href = f"{_BASE_URL}{href}"
            title = link_el.get("title") or card.get("aria-label") or ""
            duration = _seconds(meta(card, "duration"))
            if filters.min_duration is not None and duration < filters.min_duration:
                continue
            if filters.max_duration is not None and duration > filters.max_duration:
                continue

            clip_id = href.rstrip("/").rsplit("/", 1)[-1]

            out.append(
                Candidate(
                    source=self.name,
                    source_id=f"dareful_{clip_id}",
                    source_url=href,
                    download_url=download_url,
                    kind="video",
                    width=int(meta(card, "width") or 1920),
                    height=int(meta(card, "height") or 1080),
                    duration=duration,
                    creator="Joel Holland (Dareful)",
                    license=_LICENSE,
                    source_tags=f"{title} nature landscape {query}",
                    thumbnail_url=meta(card, "thumbnailUrl"),
                    extra={"detail_url": href},
                )
            )

        return out

    def download(self, candidate: Candidate, out_path: Path) -> Path:
        """Download the Mux MP4; a candidate that only has the page URL is resolved first."""
        import requests

        out_path = Path(out_path)
        download_url = candidate.download_url
        if not download_url.startswith("https://stream.mux.com/"):
            # The detail page also links Shutterstock previews, so only the
            # Mux stream counts as the clip.
            r = requests.get(candidate.extra.get("detail_url", download_url),
                             timeout=30, headers=_HEADERS)
            r.raise_for_status()
            download_url = _mux_mp4(r.text)
            if not download_url:
                raise ValueError(f"No Mux stream on Dareful page: {candidate.source_url}")

        download_media(download_url, out_path, kind=candidate.kind,
                       timeout=180, headers=_HEADERS)
        return out_path
