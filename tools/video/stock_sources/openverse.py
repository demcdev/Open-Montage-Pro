"""Openverse image source adapter.

Wraps the Openverse API (``api.openverse.org``) behind the `StockSource`
protocol. Openverse indexes hundreds of millions of openly licensed
images from Flickr, NASA, museums and Wikimedia, among others.

No API key required. Anonymous requests may ask for at most 20 results
per page.

Licences
--------
Only CC0, public-domain marks and CC BY are requested: all of them allow
commercial use and modification. CC BY-SA is left out on purpose, since
share-alike would bind the finished video to the same licence. CC BY
still requires crediting the author, so every candidate carries
Openverse's ready-made credit line in ``extra["attribution"]``; whoever
publishes the video must copy it into the credits or the description.

What Openverse is good for
--------------------------
- Stills for almost any topic, including niche science and places
- Satellite and space imagery mirrored from agency Flickr accounts
- Gap-fills when the video sources have nothing
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from lib.media_download import download_media

from .base import Candidate, SearchFilters

_log = logging.getLogger(__name__)

_SEARCH_URL = "https://api.openverse.org/v1/images/"
# Many files live on upload.wikimedia.org, which answers 429 to agents
# that do not name themselves with a contact URL.
_HEADERS = {"User-Agent": "OpenMontageBot/0.1 (https://github.com/calesthio/OpenMontage)"}
_LICENSES = "cc0,pdm,by"
_ANONYMOUS_PAGE_SIZE = 20
_ASPECT_RATIO = {"landscape": "wide", "portrait": "tall", "square": "square"}


class OpenverseSource:
    """Openverse image adapter. Satisfies `StockSource`."""

    name = "openverse"
    display_name = "Openverse"
    provider = "openverse"
    priority = 45
    install_instructions = "Openverse works without an API key. No setup needed."
    supports = {"video": False, "image": True}

    def is_available(self) -> bool:
        return True

    def search(self, query: str, filters: SearchFilters) -> list[Candidate]:
        import requests

        kind = (filters.kind or "video").lower()
        if kind == "video":
            return []

        params: dict[str, Any] = {
            "q": query,
            "license": _LICENSES,
            "page": max(1, filters.page),
            "page_size": max(1, min(filters.per_page, _ANONYMOUS_PAGE_SIZE)),
        }
        aspect = _ASPECT_RATIO.get(filters.orientation or "")
        if aspect:
            params["aspect_ratio"] = aspect

        try:
            r = requests.get(_SEARCH_URL, params=params, timeout=30, headers=_HEADERS)
            r.raise_for_status()
            data = r.json()
        except Exception as e:
            # Contract: an empty list means "nothing matched", so a
            # transport failure has to propagate. See `base.StockSource`.
            _log.warning("Openverse search failed: %s", e)
            raise

        out: list[Candidate] = []
        for item in data.get("results") or []:
            cand = _item_to_candidate(item, filters)
            if cand is not None:
                out.append(cand)
        return out

    def download(self, candidate: Candidate, out_path: Path) -> Path:
        out_path = Path(out_path)
        download_media(candidate.download_url, out_path, kind=candidate.kind,
                       timeout=120, headers=_HEADERS)
        return out_path


def _item_to_candidate(item: dict[str, Any], filters: SearchFilters) -> Candidate | None:
    url = item.get("url") or ""
    if not item.get("id") or not url or item.get("mature"):
        return None

    width = int(item.get("width") or 0)
    height = int(item.get("height") or 0)
    if filters.min_width and width and width < filters.min_width:
        return None

    code = (item.get("license") or "").upper()
    version = item.get("license_version") or ""
    if code == "PDM":
        licence = "Public Domain Mark"
    elif code == "CC0":
        licence = f"CC0 {version}".strip()
    else:
        licence = f"CC {code} {version}".strip()

    title = item.get("title") or ""
    tags = " ".join(t.get("name", "") for t in item.get("tags") or [] if isinstance(t, dict))

    return Candidate(
        source=OpenverseSource.name,
        source_id=str(item["id"]),
        source_url=item.get("foreign_landing_url") or "",
        download_url=url,
        kind="image",
        width=width,
        height=height,
        creator=item.get("creator") or "",
        license=licence,
        source_tags=f"{title} {tags}".strip()[:500],
        thumbnail_url=item.get("thumbnail") or "",
        extra={
            "attribution": item.get("attribution") or "",
            "license_url": item.get("license_url") or "",
            "provider": item.get("provider"),
            "origin": item.get("source"),
        },
    )
