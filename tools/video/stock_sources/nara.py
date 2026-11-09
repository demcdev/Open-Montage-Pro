"""U.S. National Archives (NARA) stock source adapter.

Wraps the NARA Catalog API (``catalog.archives.gov/api/v2``) behind the
unified `StockSource` protocol. NARA holds billions of records including
significant film and video holdings — all U.S. federal government work
and therefore public domain.

Every request needs an API key (free, read-only, 10,000 queries per
month): email Catalog_API@nara.gov with your email address. Without one
the API answers with the catalog's web page instead of JSON.

TODO: ``_extract_candidates`` still reads the pre-2026 response shape. It
has not been checked against ``/records/search``; verify it with a real
key before trusting an empty result.

Fetch pattern
-------------
Two-stage like NASA. The search endpoint returns metadata records. Each
record may contain digital objects (files) in ``objects``. We follow
those to find downloadable video files.

What NARA is good for
---------------------
- U.S. historical footage (military, presidential, space, civil rights)
- WWII, Cold War, Apollo era footage
- Government program footage and newsreels
- Any "march of history" documentary sequence
"""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

from lib.media_download import download_media

from .base import Candidate, SearchFilters

_log = logging.getLogger(__name__)

_SEARCH_URL = "https://catalog.archives.gov/api/v2/records/search"
_LICENSE = "Public domain (U.S. federal government work)"


class NARASource:
    """U.S. National Archives adapter. Satisfies `StockSource`."""

    name = "nara"
    display_name = "U.S. National Archives"
    provider = "nara"
    priority = 35
    install_instructions = (
        "Set NARA_API_KEY in .env. The key is free: email Catalog_API@nara.gov "
        "with your email address to request a read-only key."
    )
    supports = {"video": True, "image": True}

    def is_available(self) -> bool:
        return bool(os.environ.get("NARA_API_KEY"))

    def search(self, query: str, filters: SearchFilters) -> list[Candidate]:
        import requests

        kind = (filters.kind or "video").lower()

        # Parameter names from the v2 docs (archives.gov, "Getting Started").
        params: dict[str, Any] = {
            "q": query,
            "limit": max(1, min(filters.per_page, 50)),
            "page": max(1, filters.page),
            "availableOnline": "true",
        }
        if kind == "video":
            params["typeOfMaterials"] = "Moving Images"
        elif kind == "image":
            params["typeOfMaterials"] = "Photographs and other Graphic Materials"

        headers = {
            "Content-Type": "application/json",
            "x-api-key": os.environ.get("NARA_API_KEY", ""),
        }

        try:
            r = requests.get(
                _SEARCH_URL,
                headers=headers,
                params=params,
                timeout=30,
            )
            r.raise_for_status()
            try:
                data = r.json()
            except ValueError:
                raise RuntimeError(
                    "NARA answered with a web page instead of JSON; "
                    "check NARA_API_KEY."
                ) from None
        except Exception as e:
            # Contract: an empty list means "nothing matched", so a
            # transport failure has to propagate. See `base.StockSource`.
            _log.warning("NARA search failed: %s", e)
            raise

        results = data.get("results", []) or []
        out: list[Candidate] = []

        for item in results:
            candidates = self._extract_candidates(item, kind, filters)
            out.extend(candidates)

        return out

    def _extract_candidates(
        self, item: dict, kind: str, filters: SearchFilters
    ) -> list[Candidate]:
        """Extract downloadable candidates from a NARA catalog record."""
        naid = str(item.get("naId", "") or "")
        if not naid:
            return []

        title = item.get("title", "") or ""
        description = item.get("scopeAndContentNote", "") or ""
        source_tags = f"{title} {description}".strip()
        source_url = f"https://catalog.archives.gov/id/{naid}"

        # Look for digital objects
        objects = item.get("objects", []) or []
        if not objects:
            # Try alternate field names
            digital = item.get("digitalObjects", []) or []
            objects = digital

        out: list[Candidate] = []
        for obj in objects:
            file_url = obj.get("url") or obj.get("fileUrl") or ""
            if not file_url:
                continue

            # Determine kind from mime type or file extension
            mime = (obj.get("mimeType", "") or "").lower()
            ext = file_url.rsplit(".", 1)[-1].lower() if "." in file_url else ""

            is_video = (
                "video" in mime
                or ext in ("mp4", "mov", "avi", "wmv", "mkv", "webm")
            )
            is_image = (
                "image" in mime
                or ext in ("jpg", "jpeg", "png", "tif", "tiff", "gif")
            )

            if kind == "video" and not is_video:
                continue
            if kind == "image" and not is_image:
                continue
            if not is_video and not is_image:
                continue

            candidate_kind = "video" if is_video else "image"
            width = int(obj.get("width") or 0)
            height = int(obj.get("height") or 0)
            duration = float(obj.get("duration") or 0)

            # Duration filters (client-side)
            if candidate_kind == "video":
                if filters.min_duration and duration and duration < filters.min_duration:
                    continue
                if filters.max_duration and duration and duration > filters.max_duration:
                    continue

            out.append(
                Candidate(
                    source=self.name,
                    source_id=f"{naid}_{obj.get('objectId', len(out))}",
                    source_url=source_url,
                    download_url=file_url,
                    kind=candidate_kind,
                    width=width,
                    height=height,
                    duration=duration,
                    creator="U.S. National Archives",
                    license=_LICENSE,
                    source_tags=source_tags,
                    thumbnail_url=obj.get("thumbnailUrl", "") or "",
                    extra={
                        "naId": naid,
                        "mime": mime,
                        "fileSize": obj.get("fileSize"),
                    },
                )
            )

        return out

    def download(self, candidate: Candidate, out_path: Path) -> Path:
        out_path = Path(out_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)

        download_media(candidate.download_url, out_path, kind=candidate.kind, timeout=180)
        return out_path
