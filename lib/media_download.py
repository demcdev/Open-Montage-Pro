"""Download media without leaving a half-written file at its final path.

Stock downloads used to stream straight into their destination, so a dropped
connection left a truncated clip under a name that looked finished, and the
next step trusted it. Here the bytes land in ``<name>.part``, are checked, and
only then take the final name through ``os.replace``.

The check is cheap on purpose. ffprobe alone accepts a truncated MP4 whose
index sits at the front (the usual layout for web delivery), because the
index still describes the missing tail. Decoding the last two seconds reads
that tail, so it catches the cut without decoding the whole clip. Images go
through Pillow's ``verify``.

When ffmpeg is not installed the file is kept and reported as unverified,
rather than discarding media that may be fine.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

_CHUNK_BYTES = 1 << 16
_TAIL_SECONDS = 2
_CHECK_TIMEOUT_SECONDS = 60


class MediaDownloadError(RuntimeError):
    """The downloaded bytes are empty or do not decode as the expected media."""


def download_media(
    url: str,
    path: Path,
    *,
    kind: str,
    timeout: float = 120,
    headers: dict[str, str] | None = None,
) -> bool:
    """Stream ``url`` to ``path`` and publish it only once it checks out.

    ``kind`` is ``"video"`` or ``"image"``. Returns whether the content was
    verified: False only when ffmpeg is missing for a video. Raises on HTTP
    errors and on ``MediaDownloadError``; in both cases no file is left at
    ``path`` or at its ``.part`` name.
    """
    import requests  # looked up at call time so request wrappers still apply

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    part = path.with_name(path.name + ".part")
    try:
        with requests.get(url, stream=True, timeout=timeout, headers=headers) as response:
            response.raise_for_status()
            with open(part, "wb") as f:
                for chunk in response.iter_content(chunk_size=_CHUNK_BYTES):
                    if chunk:
                        f.write(chunk)
        verified = check_media(part, kind)
        part.replace(path)
    except BaseException:
        part.unlink(missing_ok=True)
        raise
    return verified


def check_media(path: Path, kind: str) -> bool:
    """Raise ``MediaDownloadError`` if ``path`` is not usable ``kind`` media.

    Returns False when the check could not run (no ffmpeg), True otherwise.
    """
    path = Path(path)
    if kind not in {"video", "image"}:
        raise ValueError(f"Unknown media kind: {kind!r}")
    if path.stat().st_size == 0:
        raise MediaDownloadError(f"{path.name} is empty")
    if kind == "image":
        _check_image(path)
        return True
    return _check_video(path)


def _check_image(path: Path) -> None:
    from PIL import Image

    try:
        with Image.open(path) as image:
            image.verify()
    except Exception as exc:
        raise MediaDownloadError(f"{path.name} is not a readable image: {exc}") from exc


def _check_video(path: Path) -> bool:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        return False
    try:
        proc = subprocess.run(
            [
                ffmpeg, "-v", "error", "-xerror",
                "-sseof", f"-{_TAIL_SECONDS}", "-i", str(path),
                "-f", "null", "-",
            ],
            capture_output=True,
            text=True,
            timeout=_CHECK_TIMEOUT_SECONDS,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise MediaDownloadError(f"{path.name} took too long to decode") from exc
    if proc.returncode != 0:
        detail = (proc.stderr.strip().splitlines() or ["no detail"])[-1]
        raise MediaDownloadError(f"{path.name} does not decode to the end: {detail}")
    return True
