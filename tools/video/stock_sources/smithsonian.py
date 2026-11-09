"""Smithsonian Open Access image source adapter.

Wraps the Smithsonian Open Access API (``api.si.edu/openaccess``) behind
the `StockSource` protocol. Every result is filtered to CC0 images, so it
can be used for anything without credit.

Needs a free api.data.gov key in ``SMITHSONIAN_API_KEY``
(https://api.data.gov/signup/, 1,000 requests per hour). The key travels
in the ``X-Api-Key`` header rather than the URL, so it stays out of logs.

Images come from the Smithsonian's IDS server, which takes the longest
side in pixels either as a path suffix (``.../deliveryService/id/<ark>/3000``)
or, for links of the ``deliveryService?id=<id>`` form, as ``&max=3000``.

What the Smithsonian is good for
--------------------------------
- Museum objects: aircraft, spacecraft, locomotives, tools, coins
- Natural-history specimens and scientific illustration
- Paintings, prints and design drawings (Cooper Hewitt)
It is not stock photography: results are objects and specimens, not
scenes. Expect museum-catalogue framing.
"""
from __future__ import annotations

import logging
import os
import re
from pathlib import Path
from typing import Any

from lib.media_download import download_media

from .base import Candidate, SearchFilters

_log = logging.getLogger(__name__)

_SEARCH_URL = "https://api.si.edu/openaccess/api/v1.0/search"
_USER_AGENT = "OpenMontageBot/0.1 (https://github.com/calesthio/OpenMontage)"
_LICENSE = "CC0 (Smithsonian Open Access)"
_MAX_SIDE = 3000
_CREATOR_LABELS = {"artist", "maker", "creator", "designer", "photographer", "author", "manufacturer"}
_QUERY_SYNTAX = re.compile(r'["():]')
_UNSAFE_ID_CHARS = re.compile(r"[^A-Za-z0-9._\-]+")


class SmithsonianSource:
    """Smithsonian Open Access adapter. Satisfies `StockSource`."""

    name = "smithsonian"
    display_name = "Smithsonian Open Access"
    provider = "smithsonian"
    priority = 46
    install_instructions = (
        "Set SMITHSONIAN_API_KEY in .env (free api.data.gov key: https://api.data.gov/signup/)."
    )
    supports = {"video": False, "image": True}

    def is_available(self) -> bool:
        return bool(os.environ.get("SMITHSONIAN_API_KEY"))

    def search(self, query: str, filters: SearchFilters) -> list[Candidate]:
        import requests

        kind = (filters.kind or "video").lower()
        if kind == "video":
            return []

        words = _QUERY_SYNTAX.sub(" ", query).strip()
        if not words:
            return []
        rows = max(1, min(filters.per_page, 100))
        params: dict[str, Any] = {
            "q": f'({words}) AND online_media_type:"Images" AND media_usage:"CC0"',
            "rows": rows,
            "start": (max(1, filters.page) - 1) * rows,
        }
        headers = {
            "X-Api-Key": os.environ.get("SMITHSONIAN_API_KEY", ""),
            "User-Agent": _USER_AGENT,
        }

        try:
            r = requests.get(_SEARCH_URL, params=params, timeout=30, headers=headers)
            r.raise_for_status()
            data = r.json()
        except Exception as e:
            # Contract: an empty list means "nothing matched", so a
            # transport failure has to propagate. See `base.StockSource`.
            _log.warning("Smithsonian search failed: %s", e)
            raise

        out: list[Candidate] = []
        for row in (data.get("response") or {}).get("rows") or []:
            cand = _row_to_candidate(row, filters)
            if cand is not None:
                out.append(cand)
        return out

    def download(self, candidate: Candidate, out_path: Path) -> Path:
        out_path = Path(out_path)
        download_media(candidate.download_url, out_path, kind=candidate.kind,
                       timeout=120, headers={"User-Agent": _USER_AGENT})
        return out_path


def _sized(ids_url: str, side: int) -> str:
    """Ask IDS for an image whose longest side is `side` pixels."""
    if "?" in ids_url:
        return f"{ids_url}&max={side}"
    return f"{ids_url}/{side}"


def _row_to_candidate(row: dict[str, Any], filters: SearchFilters) -> Candidate | None:
    content = row.get("content") or {}
    descriptive = content.get("descriptiveNonRepeating") or {}
    media = next(
        (m for m in (descriptive.get("online_media") or {}).get("media") or []
         if m.get("type") == "Images"
         and (m.get("usage") or {}).get("access") == "CC0"
         and m.get("content")),
        None,
    )
    if media is None:
        return None

    full_w = int(media.get("width") or 0)
    full_h = int(media.get("height") or 0)
    longest = max(full_w, full_h)
    side = min(longest, _MAX_SIDE) if longest else _MAX_SIDE
    scale = side / longest if longest else 0
    width, height = round(full_w * scale), round(full_h * scale)
    if filters.min_width and width and width < filters.min_width:
        return None

    freetext = content.get("freetext") or {}
    names = freetext.get("name") or []
    creator = next(
        (n.get("content", "") for n in names
         if (n.get("label") or "").lower() in _CREATOR_LABELS),
        "",
    )
    indexed = content.get("indexedStructured") or {}
    topics = " ".join(t for t in (indexed.get("topic") or []) if isinstance(t, str))
    title = row.get("title") or ""

    media_id = str(media.get("id") or row.get("id") or "").removeprefix("media:")
    source_id = _UNSAFE_ID_CHARS.sub("_", media_id).strip("_")[:120]
    if not source_id:
        return None

    return Candidate(
        source=SmithsonianSource.name,
        source_id=source_id,
        source_url=descriptive.get("record_link") or "",
        download_url=_sized(media["content"], side),
        kind="image",
        width=width,
        height=height,
        creator=creator or "Smithsonian Institution",
        license=_LICENSE,
        source_tags=f"{title} {topics}".strip()[:500],
        thumbnail_url=media.get("thumbnail") or "",
        extra={"unit": row.get("unitCode"), "record_id": row.get("id")},
    )
