"""Find the beat of a music track and move cuts onto it.

Runs on ffmpeg and numpy alone. An onset envelope comes from spectral flux on log
bands, autocorrelation gives the tempo, and dynamic programming places each beat
where onsets and a steady pulse agree (Ellis, 2007). Bars assume 4/4: the downbeat
is the position of the four with the strongest low end.

Music without a clear pulse has no honest grid, so ``usable`` turns false below
``MIN_CONFIDENCE`` and nothing is snapped: that music is cut by phrases instead.
Tracks change between sections, so analyze only the stretch that plays, with
``offset_seconds`` and ``duration_seconds``: a track can fail whole and pass in part.
"""

from __future__ import annotations

import json
import subprocess
import time
from pathlib import Path
from typing import Any

import numpy as np

from tools.base_tool import (
    BaseTool,
    Determinism,
    ExecutionMode,
    ResourceProfile,
    ToolResult,
    ToolStability,
    ToolTier,
)

SAMPLE_RATE = 22050
FRAME_SIZE = 2048
HOP_SIZE = 512
FRAMES_PER_SECOND = SAMPLE_RATE / HOP_SIZE
BANDS = 40
LOW_BANDS = 8
MIN_FREQUENCY = 40.0
TEMPO_CENTER_BPM = 110.0
TEMPO_SPREAD_OCTAVES = 1.0
TIGHTNESS = 100.0
MIN_CONFIDENCE = 0.2
MIN_ONSET_FLUX = 0.05
MIN_DOWNBEAT_CONFIDENCE = 0.5
BEATS_PER_BAR = 4
# An onset registers about 4.5 frames after the window reaches it: measured on click tracks.
ONSET_LAG_FRAMES = FRAME_SIZE / HOP_SIZE / 2 + 1
DEFAULT_TOLERANCE = 0.25


def load_audio(path: str) -> np.ndarray:
    """Decode any audio or video file to mono samples."""
    proc = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", path, "-vn", "-ac", "1", "-ar", str(SAMPLE_RATE), "-f", "f32le", "-"],
        capture_output=True,
        check=True,
    )
    return np.frombuffer(proc.stdout, dtype=np.float32)


def band_edges() -> np.ndarray:
    """Log-spaced bins, so a kick drum weighs as much as all the treble."""
    top = SAMPLE_RATE / 2
    edges = MIN_FREQUENCY * (top / MIN_FREQUENCY) ** (np.arange(BANDS + 1) / BANDS)
    return np.unique((edges * FRAME_SIZE / SAMPLE_RATE).astype(int))


def band_energies(samples: np.ndarray) -> np.ndarray:
    """Return log energy per band and frame."""
    count = (len(samples) - FRAME_SIZE) // HOP_SIZE + 1
    if count < 2:
        return np.zeros((0, BANDS))
    window = np.hanning(FRAME_SIZE)
    edges = band_edges()
    energies = np.empty((count, len(edges) - 1))
    # By blocks: a whole track as one array would need gigabytes.
    for start in range(0, count, 2048):
        indices = np.arange(start, min(start + 2048, count))
        frames = np.stack([samples[i * HOP_SIZE : i * HOP_SIZE + FRAME_SIZE] for i in indices])
        power = np.abs(np.fft.rfft(frames * window, axis=1)) ** 2
        cumulative = np.cumsum(power, axis=1)
        energies[indices] = (cumulative[:, edges[1:]] - cumulative[:, edges[:-1]]) / np.diff(edges)
    return np.log1p(energies * 1000)


def onset_envelope(bands: np.ndarray) -> np.ndarray:
    """Rise in energy per frame, normalized so the DP weights do not depend on level."""
    if len(bands) < 2:
        return np.zeros(len(bands))
    flux = np.maximum(np.diff(bands, axis=0, prepend=bands[:1]), 0).mean(axis=1)
    # A held tone has almost no onsets, and normalizing would inflate its numeric noise.
    if np.percentile(flux, 95) < MIN_ONSET_FLUX:
        return np.zeros(len(flux))
    width = int(FRAMES_PER_SECOND)
    flux = np.maximum(flux - np.convolve(flux, np.ones(width) / width, mode="same"), 0)
    spread = flux.std()
    return flux / spread if spread > 0 else flux


def estimate_tempo(envelope: np.ndarray, min_bpm: float, max_bpm: float) -> tuple[float, float]:
    """Return (bpm, confidence). Confidence is the pulse's share of the envelope's energy."""
    length = len(envelope)
    if length < FRAMES_PER_SECOND * 4 or not envelope.any():
        return 0.0, 0.0
    centered = envelope - envelope.mean()
    spectrum = np.fft.rfft(centered, 2 * length)
    autocorrelation = np.fft.irfft(np.abs(spectrum) ** 2)[:length]
    if autocorrelation[0] <= 0:
        return 0.0, 0.0
    autocorrelation = autocorrelation / autocorrelation[0]

    low = int(60 * FRAMES_PER_SECOND / max_bpm)
    high = min(int(60 * FRAMES_PER_SECOND / min_bpm), length - 1)
    lags = np.arange(max(low, 1), high + 1)
    bpms = 60 * FRAMES_PER_SECOND / lags
    preference = np.exp(-0.5 * (np.log2(bpms / TEMPO_CENTER_BPM) / TEMPO_SPREAD_OCTAVES) ** 2)
    best = int(np.argmax(autocorrelation[lags] * preference))
    lag = lags[best]

    # Parabolic refinement: a whole-frame lag is 2 BPM off at fast tempos.
    if 0 < best < len(lags) - 1:
        before, peak, after = autocorrelation[lags[best - 1 : best + 2]]
        denominator = before - 2 * peak + after
        lag = lag + (0.5 * (before - after) / denominator if denominator else 0)
    return float(60 * FRAMES_PER_SECOND / lag), float(max(autocorrelation[lags[best]], 0))


def track_beats(envelope: np.ndarray, bpm: float) -> np.ndarray:
    """Return beat frames by dynamic programming over a steady pulse."""
    period = 60 * FRAMES_PER_SECOND / bpm
    window = np.arange(-int(round(2 * period)), -int(round(period / 2)) + 1)
    penalty = -TIGHTNESS * np.log(-window / period) ** 2

    score = envelope.astype(float).copy()
    previous = np.full(len(envelope), -1)
    for frame in range(len(envelope)):
        reachable = window >= -frame
        if not reachable.any():
            continue
        steps = window[reachable]
        candidates = score[frame + steps] + penalty[reachable]
        best = int(np.argmax(candidates))
        if candidates[best] > 0:
            score[frame] += candidates[best]
            previous[frame] = frame + steps[best]

    tail = len(envelope) - int(round(period * 2))
    frame = tail + int(np.argmax(score[max(tail, 0) :])) if tail > 0 else int(np.argmax(score))
    beats = []
    while frame >= 0:
        beats.append(frame)
        frame = previous[frame]
    return np.array(beats[::-1])


def find_downbeat_phase(bands: np.ndarray, beats: np.ndarray) -> tuple[int, float]:
    """Return (phase, confidence) of the bar start among the first beats."""
    if len(beats) < BEATS_PER_BAR * 2:
        return 0, 0.0
    low_end = bands[:, :LOW_BANDS].mean(axis=1)
    strength = np.array([low_end[max(frame - 1, 0) : frame + 3].max() for frame in beats])
    by_phase = np.array([strength[phase::BEATS_PER_BAR].mean() for phase in range(BEATS_PER_BAR)])
    phase = int(np.argmax(by_phase))
    others = np.delete(by_phase, phase)
    spread = strength.std()
    return phase, float((by_phase[phase] - others.mean()) / spread) if spread else 0.0


def analyze(samples: np.ndarray, min_bpm: float = 60.0, max_bpm: float = 180.0) -> dict[str, Any]:
    """Return tempo, beats and downbeats of a track, in seconds from its start."""
    bands = band_energies(samples)
    envelope = onset_envelope(bands)
    bpm, confidence = estimate_tempo(envelope, min_bpm, max_bpm)
    result: dict[str, Any] = {
        "duration_seconds": round(len(samples) / SAMPLE_RATE, 3),
        "bpm": round(bpm, 2),
        "confidence": round(confidence, 3),
        "usable": bool(bpm and confidence >= MIN_CONFIDENCE),
        "beats": [],
        "downbeats": [],
        "downbeat_confidence": 0.0,
        "downbeats_reliable": False,
    }
    if not result["usable"]:
        return result

    frames = track_beats(envelope, bpm)
    seconds = (frames + ONSET_LAG_FRAMES) / FRAMES_PER_SECOND
    phase, downbeat_confidence = find_downbeat_phase(bands, frames)
    result["beats"] = [round(float(value), 3) for value in seconds]
    result["downbeats"] = [round(float(value), 3) for value in seconds[phase::BEATS_PER_BAR]]
    result["downbeat_confidence"] = round(downbeat_confidence, 3)
    result["downbeats_reliable"] = downbeat_confidence >= MIN_DOWNBEAT_CONFIDENCE
    return result


def playing_stretch(samples: np.ndarray, offset: float, duration: float | None) -> np.ndarray:
    start = int(offset * SAMPLE_RATE)
    return samples[start:] if duration is None else samples[start : start + int(float(duration) * SAMPLE_RATE)]


def to_timeline(grid: dict[str, Any], offset: float, music_start: float) -> dict[str, list[float]]:
    """Move the grid from track time to video time, keeping what plays."""
    moved = {}
    for key in ("beats", "downbeats"):
        moved[key] = [round(t - offset + music_start, 3) for t in grid[key] if t >= offset]
    return moved


def snap_cuts(
    cuts: list[float],
    beats: list[float],
    tolerance: float = DEFAULT_TOLERANCE,
    min_gap: float = 0.0,
) -> list[dict[str, Any]]:
    """Move each cut to the nearest beat within tolerance, keeping their order.

    A cut stays put, and says so, rather than move further than the tolerance or
    land on top of the previous one, since that would change the edit's content.
    """
    grid = np.array(sorted(beats))
    results: list[dict[str, Any]] = []
    previous = -np.inf
    for cut in cuts:
        target = float(cut)
        snapped = False
        if len(grid):
            nearest = float(grid[int(np.argmin(np.abs(grid - cut)))])
            if abs(nearest - cut) <= tolerance and nearest - previous > min_gap:
                target, snapped = nearest, True
        results.append(
            {
                "from": round(float(cut), 3),
                "to": round(target, 3),
                "moved": round(target - float(cut), 3),
                "snapped": snapped,
            }
        )
        previous = target
    return results


class BeatGrid(BaseTool):
    name = "beat_grid"
    version = "0.1.0"
    tier = ToolTier.CORE
    capability = "analysis"
    provider = "numpy"
    stability = ToolStability.EXPERIMENTAL
    execution_mode = ExecutionMode.SYNC
    determinism = Determinism.DETERMINISTIC

    dependencies = ["cmd:ffmpeg"]
    install_instructions = "Install FFmpeg: https://ffmpeg.org/download.html"
    agent_skills = ["ffmpeg"]
    usage_skills = ["core/beat-sync"]

    capabilities = ["detect_tempo", "detect_beats", "detect_downbeats", "snap_cuts_to_beats"]

    input_schema = {
        "type": "object",
        "required": ["audio_path"],
        "properties": {
            "audio_path": {"type": "string", "description": "Music track, on its own, not the final mix."},
            "min_bpm": {"type": "number", "default": 60},
            "max_bpm": {"type": "number", "default": 180},
            "offset_seconds": {
                "type": "number",
                "default": 0,
                "description": "Second of the track where playback starts.",
            },
            "duration_seconds": {
                "type": "number",
                "description": "How long the track plays. Leave it out to analyze to the end.",
            },
            "music_start_seconds": {
                "type": "number",
                "default": 0,
                "description": "Second of the video where the track enters.",
            },
            "cut_times": {
                "type": "array",
                "items": {"type": "number"},
                "description": "Cuts to snap, in seconds of the video timeline.",
            },
            "snap_to": {
                "type": "string",
                "enum": ["beats", "downbeats"],
                "default": "beats",
                "description": "Downbeats only for hero cuts: there are four times fewer.",
            },
            "tolerance_seconds": {
                "type": "number",
                "default": DEFAULT_TOLERANCE,
                "description": "Furthest a cut may move.",
            },
            "min_gap_seconds": {
                "type": "number",
                "default": 0,
                "description": "Shortest shot allowed after snapping.",
            },
            "report_path": {
                "type": "string",
                "description": "Where to write the JSON grid. Defaults to <audio>.beats.json.",
            },
        },
    }

    resource_profile = ResourceProfile(cpu_cores=1, ram_mb=1024, vram_mb=0, disk_mb=5)
    idempotency_key_fields = ["audio_path", "min_bpm", "max_bpm", "offset_seconds", "duration_seconds", "music_start_seconds"]
    side_effects = ["writes the grid as JSON next to the audio (or report_path)"]
    user_visible_verification = ["Watch the cuts against the music: a tempo at half or double speed is common"]

    def execute(self, inputs: dict[str, Any]) -> ToolResult:
        audio_path = Path(inputs["audio_path"])
        if not audio_path.exists():
            return ToolResult(success=False, error=f"Audio not found: {audio_path}")
        start = time.time()
        offset = float(inputs.get("offset_seconds", 0))
        try:
            grid = analyze(
                playing_stretch(load_audio(str(audio_path)), offset, inputs.get("duration_seconds")),
                float(inputs.get("min_bpm", 60)),
                float(inputs.get("max_bpm", 180)),
            )
        except Exception as exc:  # noqa: BLE001 - surface ffmpeg decode failures
            return ToolResult(success=False, error=f"Beat analysis failed: {exc}")

        # Beats come back relative to the stretch, which already starts at the offset.
        report = dict(grid)
        report["audio"] = str(audio_path)
        report["offset_seconds"] = offset
        report["timeline"] = to_timeline(grid, 0.0, float(inputs.get("music_start_seconds", 0)))
        cuts = inputs.get("cut_times")
        if cuts and grid["usable"]:
            wanted = inputs.get("snap_to", "beats")
            # Guessed bars would put hero cuts on weak beats, so plain beats are the honest fallback.
            used = wanted if wanted == "beats" or grid["downbeats_reliable"] else "beats"
            report["snap_target"] = used
            report["snapped_cuts"] = snap_cuts(
                cuts,
                report["timeline"][used],
                float(inputs.get("tolerance_seconds", DEFAULT_TOLERANCE)),
                float(inputs.get("min_gap_seconds", 0)),
            )

        report_path = Path(inputs.get("report_path") or audio_path.with_suffix(".beats.json"))
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        return ToolResult(
            success=True,
            data={**report, "report_path": str(report_path)},
            artifacts=[str(report_path)],
            duration_seconds=round(time.time() - start, 2),
        )
