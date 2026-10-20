"""Film-look finishing: grain, halation, bloom, vignette, .cube LUTs, shot
color matching and correct BT.709 tagging.

``color_grade`` picks one of seven grade profiles. This tool is the finishing
pass that sits after it (or after compose): texture and light response that
make a clip read as photographed, with intensities set by the visual style so
flat vector animation stays clean.

Operations:

- **apply** — one FFmpeg pass. Order: shot color match (YUV) → LUT (RGB,
  blendable) → halation and bloom (screen blends of blurred highlights) →
  vignette → convert to yuv420p with an explicit BT.709 matrix → luma-only
  temporal grain → BT.709 tags on the frames and the container.
- **measure** — average luma/chroma/saturation statistics (``signalstats``),
  used to compare shots from different models.
- **preview** — one frame, original | finished side by side, as a PNG. Lets
  the look be approved on a still before any clip is processed.

Policy and per-style intensities: ``skills/creative/film-look-finishing.md``.
"""

from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Any

from tools.base_tool import (
    BaseTool,
    Determinism,
    ExecutionMode,
    ResourceProfile,
    ToolResult,
    ToolStability,
    ToolTier,
)

LUT_DIR = Path(__file__).resolve().parents[2] / "assets" / "luts"

# Intensities in 0..1 per finishing layer. Flat vector stays almost untouched:
# a trace of grain only breaks gradient banding after YouTube's re-encode.
STYLE_PRESETS: dict[str, dict[str, float]] = {
    "none": {"grain": 0.0, "halation": 0.0, "bloom": 0.0, "vignette": 0.0},
    "flat_vector": {"grain": 0.03, "halation": 0.0, "bloom": 0.0, "vignette": 0.0},
    "anime": {"grain": 0.08, "halation": 0.0, "bloom": 0.2, "vignette": 0.1},
    "stylized_2d": {"grain": 0.12, "halation": 0.0, "bloom": 0.1, "vignette": 0.15},
    "live_action": {"grain": 0.25, "halation": 0.2, "bloom": 0.1, "vignette": 0.2},
    "cinematic_ai": {"grain": 0.35, "halation": 0.3, "bloom": 0.15, "vignette": 0.25},
    "archival": {"grain": 0.6, "halation": 0.15, "bloom": 0.0, "vignette": 0.4},
}

LAYERS = ("grain", "halation", "bloom", "vignette")
STAT_KEYS = ("YAVG", "YLOW", "YHIGH", "UAVG", "VAVG", "SATAVG")
BT709_TAGS = ["-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709", "-color_range", "tv"]


class FilmLook(BaseTool):
    name = "film_look"
    version = "0.1.0"
    tier = ToolTier.ENHANCE
    capability = "enhancement"
    provider = "ffmpeg"
    stability = ToolStability.EXPERIMENTAL
    execution_mode = ExecutionMode.SYNC
    determinism = Determinism.SEEDED

    dependencies = ["cmd:ffmpeg", "cmd:ffprobe"]
    install_instructions = "Install FFmpeg: https://ffmpeg.org/download.html"
    agent_skills = ["ffmpeg"]

    capabilities = ["film_grain", "halation", "bloom", "vignette", "lut_apply", "shot_color_match", "bt709_tagging"]
    best_for = [
        "finishing AI-generated or live-action clips so they read as photographed",
        "matching color between shots from different video models",
        "fixing untagged or mis-tagged color metadata before delivery",
    ]

    input_schema = {
        "type": "object",
        "required": ["operation", "input_path"],
        "properties": {
            "operation": {
                "type": "string",
                "enum": ["apply", "measure", "preview"],
                "description": "apply: finish the clip. measure: color stats. preview: one before|after frame.",
            },
            "input_path": {"type": "string"},
            "output_path": {
                "type": "string",
                "description": "apply: defaults to <input>_film.<ext>. preview: defaults to <input>_look_preview.png.",
            },
            "style": {
                "type": "string",
                "enum": list(STYLE_PRESETS.keys()),
                "default": "flat_vector",
                "description": "Sets default intensities; explicit layer values override it.",
            },
            "grain": {"type": "number", "minimum": 0, "maximum": 1},
            "halation": {"type": "number", "minimum": 0, "maximum": 1},
            "bloom": {"type": "number", "minimum": 0, "maximum": 1},
            "vignette": {"type": "number", "minimum": 0, "maximum": 1},
            "lut_path": {
                "type": "string",
                "description": ".cube file. A bare name (e.g. 'warm_film') resolves to assets/luts/<name>.cube.",
            },
            "lut_intensity": {"type": "number", "minimum": 0, "maximum": 1, "default": 1.0},
            "match_reference_path": {
                "type": "string",
                "description": "Clip or still whose levels and chroma this clip should match (the hero shot).",
            },
            "input_matrix": {
                "type": "string",
                "enum": ["bt709", "bt601"],
                "default": "bt709",
                "description": "Matrix to assume when converting the source to RGB. Untagged HD AI clips are bt709.",
            },
            "preview_at_seconds": {"type": "number", "minimum": 0, "default": 1.0},
            "seed": {"type": "integer", "default": 7, "description": "Grain seed (keeps renders reproducible)."},
            "crf": {"type": "integer", "default": 16},
            "codec": {"type": "string", "default": "libx264"},
        },
    }

    resource_profile = ResourceProfile(cpu_cores=2, ram_mb=1024, vram_mb=0, disk_mb=2000)
    idempotency_key_fields = [
        "operation", "input_path", "style", "grain", "halation", "bloom", "vignette",
        "lut_path", "lut_intensity", "match_reference_path", "seed",
    ]
    side_effects = ["writes finished video (apply) or a PNG (preview) to output_path"]
    user_visible_verification = [
        "Approve the preview still before finishing every clip",
        "Check skin, sky and flat color areas for banding or crawling grain after upload",
    ]

    def execute(self, inputs: dict[str, Any]) -> ToolResult:
        src = Path(inputs["input_path"])
        if not src.exists():
            return ToolResult(success=False, error=f"Input not found: {src}")
        start = time.time()
        try:
            op = inputs["operation"]
            if op == "measure":
                data: dict[str, Any] = {"operation": "measure", "input": str(src), "stats": self.measure(src)}
                artifacts: list[str] = []
            else:
                data = self._finish(src, inputs, preview=(op == "preview"))
                artifacts = [data["output"]]
        except Exception as exc:  # noqa: BLE001
            return ToolResult(success=False, error=str(exc))
        return ToolResult(success=True, data=data, artifacts=artifacts, duration_seconds=round(time.time() - start, 2))

    # ---- operations ----

    def measure(self, path: Path, max_seconds: float = 20.0) -> dict[str, float]:
        cmd = [
            "ffmpeg", "-hide_banner", "-nostats", "-t", str(max_seconds), "-i", str(path),
            "-vf", "fps=2,signalstats,metadata=mode=print", "-an", "-f", "null", "-",
        ]
        return parse_signalstats(self.run_command(cmd, timeout=1800).stderr)

    def _finish(self, src: Path, inputs: dict[str, Any], preview: bool) -> dict[str, Any]:
        layers = resolve_layers(inputs)
        lut = resolve_lut(inputs.get("lut_path"))
        match = None
        if inputs.get("match_reference_path"):
            ref = Path(inputs["match_reference_path"])
            if not ref.exists():
                raise FileNotFoundError(f"Match reference not found: {ref}")
            match = compute_match(self.measure(src), self.measure(ref))
        height = self._probe_height(src)
        chain = build_chain(
            layers, height=height, lut_path=lut, lut_intensity=float(inputs.get("lut_intensity", 1.0)),
            match=match, input_matrix=inputs.get("input_matrix", "bt709"), seed=int(inputs.get("seed", 7)),
        )

        if preview:
            out = Path(inputs.get("output_path") or src.with_name(f"{src.stem}_look_preview.png"))
            graph = (
                "[0:v]split=2[orig][work];"
                f"[orig]scale=in_color_matrix={inputs.get('input_matrix', 'bt709')}:out_color_matrix=bt709,format=yuv420p[a];"
                f"[work]{chain}[b];[a][b]hstack=inputs=2[out]"
            )
            cmd = ["ffmpeg", "-hide_banner", "-y", "-ss", str(inputs.get("preview_at_seconds", 1.0)),
                   "-i", str(src), "-filter_complex", graph, "-map", "[out]", "-frames:v", "1", str(out)]
        else:
            out = Path(inputs.get("output_path") or src.with_name(f"{src.stem}_film{src.suffix}"))
            cmd = ["ffmpeg", "-hide_banner", "-y", "-i", str(src), "-filter_complex", f"[0:v]{chain}[out]",
                   "-map", "[out]", "-map", "0:a?", "-c:v", inputs.get("codec", "libx264"),
                   "-crf", str(inputs.get("crf", 16)), "-preset", "slow", *BT709_TAGS,
                   "-c:a", "copy", "-movflags", "+faststart", str(out)]
        out.parent.mkdir(parents=True, exist_ok=True)
        self.run_command(cmd, timeout=7200)
        return {
            "operation": "preview" if preview else "apply",
            "input": str(src),
            "output": str(out),
            "style": inputs.get("style", "flat_vector"),
            "layers": layers,
            "lut": str(lut) if lut else None,
            "match": match,
            "filter": chain,
            "color_tags": "bt709/bt709/bt709/tv",
        }

    def _probe_height(self, path: Path) -> int:
        cmd = ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=height", "-of", "json", str(path)]
        try:
            streams = json.loads(self.run_command(cmd, timeout=60).stdout).get("streams") or [{}]
            return int(streams[0].get("height") or 1080)
        except Exception:  # noqa: BLE001
            return 1080


# ---- pure helpers (tested without ffmpeg) ----

def resolve_layers(inputs: dict[str, Any]) -> dict[str, float]:
    layers = dict(STYLE_PRESETS.get(inputs.get("style", "flat_vector"), STYLE_PRESETS["flat_vector"]))
    for key in LAYERS:
        if inputs.get(key) is not None:
            layers[key] = max(0.0, min(1.0, float(inputs[key])))
    return layers


def resolve_lut(value: str | None) -> Path | None:
    if not value:
        return None
    path = Path(value)
    if not path.suffix:
        path = LUT_DIR / f"{value}.cube"
    if not path.exists():
        raise FileNotFoundError(f"LUT not found: {path}")
    if path.suffix.lower() != ".cube":
        raise ValueError(f"Only .cube LUTs are supported: {path}")
    return path


def ffmpeg_filter_path(path: Path) -> str:
    # Inside a filtergraph the drive colon must be escaped and quotes wrap the path.
    return "'" + str(path.resolve()).replace("\\", "/").replace(":", "\\:") + "'"


def parse_signalstats(stderr: str) -> dict[str, float]:
    sums: dict[str, float] = {k: 0.0 for k in STAT_KEYS}
    counts: dict[str, int] = {k: 0 for k in STAT_KEYS}
    for key, value in re.findall(r"lavfi\.signalstats\.([A-Z]+)=([-\d.]+)", stderr):
        if key in sums:
            sums[key] += float(value)
            counts[key] += 1
    if not counts["YAVG"]:
        raise RuntimeError("signalstats reported nothing (no video stream?)")
    return {k: round(sums[k] / counts[k], 3) for k in STAT_KEYS if counts[k]}


def compute_match(src: dict[str, float], ref: dict[str, float]) -> dict[str, float]:
    """Affine luma map on the 10th/90th percentiles, chroma offsets, saturation ratio."""
    src_span = max(1.0, src["YHIGH"] - src["YLOW"])
    gain = max(0.6, min(1.6, (ref["YHIGH"] - ref["YLOW"]) / src_span))
    sat = 1.0
    if src.get("SATAVG") and ref.get("SATAVG"):
        sat = max(0.7, min(1.3, ref["SATAVG"] / src["SATAVG"]))
    return {
        "src_low": round(src["YLOW"], 2),
        "ref_low": round(ref["YLOW"], 2),
        "luma_gain": round(gain, 4),
        "u_offset": round(max(-20.0, min(20.0, ref["UAVG"] - src["UAVG"])), 2),
        "v_offset": round(max(-20.0, min(20.0, ref["VAVG"] - src["VAVG"])), 2),
        "saturation": round(sat, 4),
    }


def build_chain(
    layers: dict[str, float],
    *,
    height: int = 1080,
    lut_path: Path | None = None,
    lut_intensity: float = 1.0,
    match: dict[str, float] | None = None,
    input_matrix: str = "bt709",
    seed: int = 7,
) -> str:
    """Filter chain from one input pad to one output pad (labels added by the caller)."""
    scale = max(0.25, height / 1080.0)
    parts: list[str] = []
    if match:
        parts.append(
            "lutyuv="
            f"y='clip((val-{match['src_low']})*{match['luma_gain']}+{match['ref_low']},16,235)':"
            f"u='clip(val+{match['u_offset']},16,240)':v='clip(val+{match['v_offset']},16,240)'"
        )
        if abs(match["saturation"] - 1.0) > 0.01:
            parts.append(f"eq=saturation={match['saturation']}")
    parts.append(f"scale=in_color_matrix={input_matrix}:flags=bicubic,format=gbrp")
    chain = ",".join(parts)

    # Branching layers are written as filtergraph segments joined with ';'.
    segments: list[str] = []
    label = 0

    def nxt() -> str:
        nonlocal label
        label += 1
        return f"fl{label}"

    cur = nxt()
    segments.append(f"{chain}[{cur}]")

    if lut_path and lut_intensity > 0:
        a, b, lut, out = nxt(), nxt(), nxt(), nxt()
        segments.append(f"[{cur}]split=2[{a}][{b}]")
        segments.append(f"[{b}]lut3d=file={ffmpeg_filter_path(lut_path)}[{lut}]")
        segments.append(f"[{lut}][{a}]blend=all_mode=normal:all_opacity={min(1.0, lut_intensity):.3f}[{out}]")
        cur = out

    for layer, threshold, sigma, tint, weight in (
        ("halation", 200, 12.0, "colorchannelmixer=rr=1:rg=0:rb=0:gr=0:gg=0.35:gb=0:br=0:bg=0:bb=0.1", 0.6),
        ("bloom", 180, 30.0, "", 0.5),
    ):
        amount = layers.get(layer, 0.0)
        if amount <= 0:
            continue
        base, hi, glow, out = nxt(), nxt(), nxt(), nxt()
        knee = f"if(gt(val,{threshold}),(val-{threshold})*255/{255 - threshold},0)"
        treat = f"lut=c0='{knee}':c1='{knee}':c2='{knee}',gblur=sigma={sigma * scale:.1f}"
        if tint:
            treat += f",{tint}"
        segments.append(f"[{cur}]split=2[{base}][{hi}]")
        segments.append(f"[{hi}]{treat}[{glow}]")
        segments.append(f"[{base}][{glow}]blend=all_mode=screen:all_opacity={amount * weight:.3f}[{out}]")
        cur = out

    tail: list[str] = []
    if layers.get("vignette", 0.0) > 0:
        tail.append(f"vignette=angle={layers['vignette'] * 0.7:.3f}")
    tail.append("scale=out_color_matrix=bt709:out_range=tv,format=yuv420p")
    if layers.get("grain", 0.0) > 0:
        tail.append(f"noise=c0s={max(1, round(layers['grain'] * 24))}:c0f=t+u:all_seed={seed}")
    tail.append("setparams=color_primaries=bt709:color_trc=bt709:colorspace=bt709:range=tv")
    segments.append(f"[{cur}]{','.join(tail)}")
    return ";".join(segments)
