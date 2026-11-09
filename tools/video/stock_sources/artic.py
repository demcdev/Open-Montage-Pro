"""Art Institute of Chicago image source adapter.

Wraps the Art Institute of Chicago API (``api.artic.edu``) behind the
`StockSource` protocol. Only public-domain artworks with an image are
requested, so every result is CC0 and needs no credit (the museum
appreciates one).

No API key required. Images are served over IIIF; that server answers
403 unless the request carries an ``AIC-User-Agent`` header naming the
application, as the museum's API docs ask.

What the Art Institute is good for
----------------------------------
- Paintings, prints and drawings for history and culture topics
- Period illustrations of events, places and people before photography
- Maps, scientific plates and natural-history drawings
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from lib.media_download import download_media

from .base import Candidate, SearchFilters

_log = logging.getLogger(__name__)

_SEARCH_URL = "https://api.artic.edu/api/v1/artworks/search"
_IIIF_URL = "https://www.artic.edu/iiif/2/{image_id}/full/{width},/0/default.jpg"
_HEADERS = {
    "User-Agent": "OpenMontage/1.0 (stock source adapter)",
    "AIC-User-Agent": "OpenMontage (https://github.com/calesthio/OpenMontage)",
}
_LICENSE = "Public domain (CC0, Art Institute of Chicago)"
_FIELDS = "id,title,artist_display,date_display,image_id,thumbnail,term_titles"
_MATCH_FIELDS = ["title", "term_titles", "subject_titles", "classification_titles", "description"]
_MAX_WIDTH = 3000


def _search_body(query: str) -> str:
    """The search as the JSON ``params`` value.

    A bare ``q`` next to a ``query`` only reorders results, so a nonsense
    word still returned every public-domain work; the words have to be a
    ``must`` clause to filter.
    """
    return json.dumps({"query": {"bool": {
        "must": [{"multi_match": {"query": query, "fields": _MATCH_FIELDS}}],
        # Public domain only, and only records that actually have an image.
        "filter": [
            {"term": {"is_public_domain": True}},
            {"exists": {"field": "image_id"}},
        ],
    }}})
_DEFAULT_WIDTH = 1686


class ArticSource:
    """Art Institute of Chicago adapter. Satisfies `StockSource`."""

    name = "artic"
    display_name = "Art Institute of Chicago"
    provider = "artic"
    priority = 47
    install_instructions = "The Art Institute of Chicago works without an API key. No setup needed."
    supports = {"video": False, "image": True}

    def is_available(self) -> bool:
        return True

    def search(self, query: str, filters: SearchFilters) -> list[Candidate]:
        import requests

        kind = (filters.kind or "video").lower()
        if kind == "video":
            return []

        params: dict[str, Any] = {
            "limit": max(1, min(filters.per_page, 100)),
            "page": max(1, filters.page),
            "fields": _FIELDS,
            "params": _search_body(query),
        }

        try:
            r = requests.get(_SEARCH_URL, params=params, timeout=30, headers=_HEADERS)
            r.raise_for_status()
            data = r.json()
        except Exception as e:
            # Contract: an empty list means "nothing matched", so a
            # transport failure has to propagate. See `base.StockSource`.
            _log.warning("Art Institute of Chicago search failed: %s", e)
            raise

        out: list[Candidate] = []
        for item in data.get("data") or []:
            cand = _artwork_to_candidate(item, filters)
            if cand is not None:
                out.append(cand)
        return out

    def download(self, candidate: Candidate, out_path: Path) -> Path:
        out_path = Path(out_path)
        download_media(candidate.download_url, out_path, kind=candidate.kind,
                       timeout=120, headers=_HEADERS)
        return out_path


def _artwork_to_candidate(item: dict[str, Any], filters: SearchFilters) -> Candidate | None:
    image_id = item.get("image_id")
    if not item.get("id") or not image_id:
        return None

    thumb = item.get("thumbnail") or {}
    full_width = int(thumb.get("width") or 0)
    full_height = int(thumb.get("height") or 0)
    # IIIF does not upscale: never ask for more pixels than the original has.
    width = min(full_width, _MAX_WIDTH) if full_width else _DEFAULT_WIDTH
    height = round(full_height * width / full_width) if full_width and full_height else 0
    if filters.min_width and width < filters.min_width:
        return None

    title = item.get("title") or ""
    terms = " ".join(t for t in item.get("term_titles") or [] if isinstance(t, str))
    artist = item.get("artist_display") or ""

    return Candidate(
        source=ArticSource.name,
        source_id=str(item["id"]),
        source_url=f"https://www.artic.edu/artworks/{item['id']}",
        download_url=_IIIF_URL.format(image_id=image_id, width=width),
        kind="image",
        width=width,
        height=height,
        creator=artist.split("\n")[0],
        license=_LICENSE,
        source_tags=f"{title} {item.get('date_display') or ''} {terms}".strip()[:500],
        thumbnail_url=_IIIF_URL.format(image_id=image_id, width=400),
        extra={"image_id": image_id, "date": item.get("date_display")},
    )
