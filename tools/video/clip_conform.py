"""Conform clips from different sources to one timeline standard.

Clips from different video models arrive at 16, 24, 25 or 30 fps, sometimes
with variable frame rate, flicker, shake or a lower resolution than the
timeline. This tool brings each clip to the project standard before edit:

- **analyze** — fps (and VFR), size, codec, color tags and a flicker index
  (luma jitter that a camera move would not explain). Returns the steps it
  recommends; it changes nothing.
- **conform** — one pass (two with stabilization): deflicker → light denoise
  → stabilization (vidstab, or ``deshake`` when this FFmpeg lacks vidstab) →
  frame-rate conversion → resize → yuv420p. Upscaling with Real-ESRGAN (and
  GFPGAN faces) is delegated to the existing ``upscale`` tool.
- **slow_motion** — motion-interpolated slow motion (``minterpolate``).

Interpolation is used only to fill frames (source slower than the target) or
for slow motion, never on animation drawn on twos.
Policy: ``skills/creative/clip-conform.md``.
"""

from __future__ import annotations

import json
import re
import shutil
import tempfile
import time
from functools import lru_cache
from pathlib import Path
from typing import Any

from tools.base_tool import (
    BaseTool,
    Determinism,
    ExecutionMode,
    ResourceProfile,
    ToolResult,
    ToolStability,
    ToolStatus,
    ToolTier,
)

FPS_METHODS = ["auto", "none", "drop", "interpolate", "blend", "retime"]
CONTENT_TYPES = ["generated", "live_action", "animation"]
FLICKER_WARN = 0.012  # mean luma jitter / mean luma; above this flicker is visible


class ClipConform(BaseTool):
    name = "clip_conform"
    version = "0.1.0"
    tier = ToolTier.CORE
    capability = "video_post"
    provider = "ffmpeg"
    stability = ToolStability.EXPERIMENTAL
    execution_mode = ExecutionMode.SYNC
    determinism = Determinism.DETERMINISTIC

    dependencies = ["cmd:ffmpeg", "cmd:ffprobe"]
    install_instructions = (
        "Install FFmpeg: https://ffmpeg.org/download.html "
        "(a build with libvidstab is needed for two-pass stabilization; otherwise deshake is used)"
    )
    agent_skills = ["ffmpeg"]

    capabilities = ["fps_conform", "deflicker", "frame_interpolation", "slow_motion", "stabilization", "resize"]
    best_for = [
        "bringing AI clips from different models to one fps and size before edit",
        "removing luminance flicker from generated clips",
        "stabilizing handheld or jittery footage",
    ]

    input_schema = {
        "type": "object",
        "required": ["operation", "input_path"],
        "properties": {
            "operation": {"type": "string", "enum": ["analyze", "conform", "slow_motion"]},
            "input_path": {"type": "string"},
            "output_path": {"type": "string", "description": "Defaults to <input>_conform.<ext> or <input>_slowmo.<ext>."},
            "target_fps": {"type": "number", "default": 24, "description": "Timeline fps: 24 for cinematic, 30 for web/explainer."},
            "fps_method": {"type": "string", "enum": FPS_METHODS, "default": "auto"},
            "content_type": {
                "type": "string", "enum": CONTENT_TYPES, "default": "generated",
                "description": "animation never gets motion interpolation (it would smear drawings on twos).",
            },
            "deflicker": {"type": "boolean", "default": False},
            "deflicker_size": {"type": "integer", "minimum": 2, "maximum": 129, "default": 5},
            "denoise": {"type": "string", "enum": ["none", "light"], "default": "none"},
            "stabilize": {"type": "boolean", "default": False},
            "stabilize_smoothing": {"type": "integer", "minimum": 1, "maximum": 60, "default": 10},
            "target_width": {"type": "integer"},
            "target_height": {"type": "integer"},
            "resize_mode": {
                "type": "string", "enum": ["fill", "fit"], "default": "fill",
                "description": "fill: scale and center-crop to the exact size. fit: scale and pad with black.",
            },
            "upscale_method": {
                "type": "string", "enum": ["lanczos", "realesrgan"], "default": "lanczos",
                "description": "realesrgan delegates to the upscale tool when the clip is smaller than the target.",
            },
            "face_enhance": {"type": "boolean", "default": False, "description": "realesrgan only: GFPGAN on faces."},
            "slow_motion_factor": {"type": "number", "minimum": 1.25, "maximum": 8, "default": 2},
            "keep_audio": {"type": "boolean", "default": True},
            "crf": {"type": "integer", "default": 16},
        },
    }

    resource_profile = ResourceProfile(cpu_cores=4, ram_mb=2048, vram_mb=0, disk_mb=4000)
    idempotency_key_fields = [
        "operation", "input_path", "target_fps", "fps_method", "content_type", "deflicker", "denoise",
        "stabilize", "target_width", "target_height", "resize_mode", "upscale_method", "slow_motion_factor",
    ]
    side_effects = ["writes conformed video to output_path"]
    user_visible_verification = [
        "Scrub a pan or fast move for judder or interpolation warping",
        "Check stabilized clips for wobbling edges",
    ]

    def execute(self, inputs: dict[str, Any]) -> ToolResult:
        src = Path(inputs["input_path"])
        if not src.exists():
            return ToolResult(success=False, error=f"Input not found: {src}")
        start = time.time()
        try:
            op = inputs["operation"]
            if op == "analyze":
                data = self.analyze(src, inputs)
                artifacts: list[str] = []
            elif op == "slow_motion":
                data = self._slow_motion(src, inputs)
                artifacts = [data["output"]]
            else:
                data = self._conform(src, inputs)
                artifacts = [data["output"]]
        except Exception as exc:  # noqa: BLE001
            return ToolResult(success=False, error=str(exc))
        return ToolResult(success=True, data=data, artifacts=artifacts, duration_seconds=round(time.time() - start, 2))

    # ---- analyze ----

    def probe(self, path: Path) -> dict[str, Any]:
        cmd = ["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)]
        raw = json.loads(self.run_command(cmd, timeout=120).stdout)
        return summarize_probe(raw)

    def flicker_index(self, path: Path, max_seconds: float = 10.0) -> float:
        cmd = ["ffmpeg", "-hide_banner", "-nostats", "-t", str(max_seconds), "-i", str(path),
               "-vf", "signalstats,metadata=mode=print:key=lavfi.signalstats.YAVG", "-an", "-f", "null", "-"]
        values = [float(v) for v in re.findall(r"lavfi\.signalstats\.YAVG=([-\d.]+)", self.run_command(cmd, timeout=600).stderr)]
        return compute_flicker_index(values)

    def analyze(self, src: Path, inputs: dict[str, Any]) -> dict[str, Any]:
        info = self.probe(src)
        flicker = self.flicker_index(src) if info.get("has_video") else 0.0
        return {
            "operation": "analyze",
            "input": str(src),
            "probe": info,
            "flicker_index": flicker,
            "has_vidstab": has_filter("vidstabdetect"),
            "recommendations": recommend(info, flicker, inputs),
        }

    # ---- conform ----

    def _conform(self, src: Path, inputs: dict[str, Any]) -> dict[str, Any]:
        out = Path(inputs.get("output_path") or src.with_name(f"{src.stem}_conform{src.suffix}"))
        out.parent.mkdir(parents=True, exist_ok=True)
        warnings: list[str] = []
        info = self.probe(src)
        work_src = src

        th = inputs.get("target_height")
        if inputs.get("upscale_method") == "realesrgan" and th and info["height"] < int(th):
            work_src = self._realesrgan(src, info, int(th), bool(inputs.get("face_enhance")), out.parent)
            info = {**self.probe(work_src), "fps": info["fps"], "vfr": info["vfr"]}

        target = float(inputs.get("target_fps", 24))
        method = choose_fps_method(info["fps"], target, inputs.get("fps_method", "auto"), inputs.get("content_type", "generated"))
        if method == "interpolate" and inputs.get("content_type") == "animation":
            raise ValueError("Motion interpolation on animation smears drawings; use fps_method 'drop'.")
        pre = pre_filters(inputs)
        post = fps_filters(method, info["fps"], target) + resize_filters(inputs, info) + ["format=yuv420p"]

        stab_mode = None
        with tempfile.TemporaryDirectory() as tmp:
            if inputs.get("stabilize"):
                if has_filter("vidstabdetect"):
                    stab_mode = "vidstab"
                    detect = ",".join(pre + ["vidstabdetect=shakiness=5:accuracy=15:result=transforms.trf"])
                    self.run_command(["ffmpeg", "-hide_banner", "-y", "-i", str(work_src.resolve()), "-vf", detect,
                                      "-an", "-f", "null", "-"], timeout=7200, cwd=Path(tmp))
                    pre = pre + [f"vidstabtransform=input=transforms.trf:smoothing={int(inputs.get('stabilize_smoothing', 10))}"
                                 ":zoom=0:optzoom=1:interpol=bicubic", "unsharp=5:5:0.6:3:3:0.3"]
                else:
                    stab_mode = "deshake"
                    warnings.append("This FFmpeg has no libvidstab; used single-pass deshake (weaker).")
                    pre = pre + ["deshake"]

            vf = ",".join(pre + post)
            cmd = ["ffmpeg", "-hide_banner", "-y", "-i", str(work_src.resolve()), "-vf", vf,
                   "-c:v", "libx264", "-crf", str(inputs.get("crf", 16)), "-preset", "slow"]
            audio_note = None
            if inputs.get("keep_audio", True) and info.get("has_audio"):
                if method == "retime":
                    cmd += ["-af", f"atempo={target / info['fps']:.6f}"]
                    audio_note = "audio retimed with atempo (pitch kept)"
                cmd += ["-c:a", "aac", "-b:a", "256k", "-ar", "48000"]
            else:
                cmd += ["-an"]
            cmd += ["-r", fps_arg(target), "-movflags", "+faststart", str(out.resolve())]
            self.run_command(cmd, timeout=7200, cwd=Path(tmp))

        if work_src != src:
            work_src.unlink(missing_ok=True)
        result = self.probe(out)
        if method == "retime":
            warnings.append(f"Duration changed by {(info['fps'] / target - 1) * 100:+.1f}% (retime).")
        return {
            "operation": "conform",
            "input": str(src),
            "output": str(out),
            "source": {"fps": info["fps"], "vfr": info["vfr"], "width": info["width"], "height": info["height"]},
            "fps_method": method,
            "stabilization": stab_mode,
            "deflicker": bool(inputs.get("deflicker")),
            "upscaled_with": "realesrgan" if work_src != src else None,
            "filter": vf,
            "audio": audio_note,
            "result": {k: result.get(k) for k in ("fps", "width", "height", "duration")},
            "warnings": warnings,
        }

    def _realesrgan(self, src: Path, info: dict[str, Any], target_h: int, face: bool, out_dir: Path) -> Path:
        from tools.enhancement.upscale import Upscale

        tool = Upscale()
        if tool.get_status() != ToolStatus.AVAILABLE:
            raise RuntimeError("upscale_method 'realesrgan' needs the upscale tool (pip install realesrgan torch); "
                               "use upscale_method 'lanczos' or install it.")
        scale = 2 if info["height"] * 2 >= target_h else 4
        tmp_out = out_dir / f"{src.stem}_esrgan_tmp{src.suffix}"
        res = tool.execute({"input_path": str(src), "output_path": str(tmp_out), "scale": scale, "face_enhance": face})
        if not res.success:
            raise RuntimeError(f"upscale failed: {res.error}")
        return tmp_out

    # ---- slow motion ----

    def _slow_motion(self, src: Path, inputs: dict[str, Any]) -> dict[str, Any]:
        out = Path(inputs.get("output_path") or src.with_name(f"{src.stem}_slowmo{src.suffix}"))
        out.parent.mkdir(parents=True, exist_ok=True)
        info = self.probe(src)
        factor = float(inputs.get("slow_motion_factor", 2))
        target = float(inputs.get("target_fps", 24))
        warnings = []
        if inputs.get("content_type") == "animation":
            warnings.append("Interpolated slow motion on drawn animation can smear lines; check every frame.")
        vf = ",".join(pre_filters(inputs) + slow_motion_filters(info["fps"], factor, target)
                      + resize_filters(inputs, info) + ["format=yuv420p"])
        self.run_command(["ffmpeg", "-hide_banner", "-y", "-i", str(src), "-vf", vf, "-an",
                          "-c:v", "libx264", "-crf", str(inputs.get("crf", 16)), "-preset", "slow",
                          "-r", fps_arg(target), "-movflags", "+faststart", str(out)], timeout=7200)
        result = self.probe(out)
        return {
            "operation": "slow_motion",
            "input": str(src),
            "output": str(out),
            "factor": factor,
            "filter": vf,
            "audio": "dropped (slow motion); add sound design in the edit",
            "result": {k: result.get(k) for k in ("fps", "width", "height", "duration")},
            "warnings": warnings,
        }


# ---- pure helpers (tested without ffmpeg) ----

@lru_cache(maxsize=None)
def has_filter(name: str) -> bool:
    if not shutil.which("ffmpeg"):
        return False
    import subprocess

    out = subprocess.run(["ffmpeg", "-hide_banner", "-filters"], capture_output=True, text=True,
                         encoding="utf-8", errors="replace")
    return re.search(rf"^\s*\S+\s+{re.escape(name)}\s", out.stdout, flags=re.M) is not None


def parse_rate(value: str | None) -> float:
    if not value or value in ("0/0", "N/A"):
        return 0.0
    if "/" in value:
        num, den = value.split("/", 1)
        return float(num) / float(den) if float(den) else 0.0
    return float(value)


def summarize_probe(raw: dict[str, Any]) -> dict[str, Any]:
    streams = raw.get("streams", [])
    video = next((s for s in streams if s.get("codec_type") == "video"), None)
    audio = next((s for s in streams if s.get("codec_type") == "audio"), None)
    info: dict[str, Any] = {
        "has_video": video is not None,
        "has_audio": audio is not None,
        "duration": float(raw.get("format", {}).get("duration") or 0.0),
    }
    if video:
        r = parse_rate(video.get("r_frame_rate"))
        avg = parse_rate(video.get("avg_frame_rate")) or r
        info.update({
            "fps": round(avg or r, 3),
            "vfr": bool(r and avg and abs(r - avg) / r > 0.01),
            "width": int(video.get("width") or 0),
            "height": int(video.get("height") or 0),
            "codec": video.get("codec_name"),
            "pixel_format": video.get("pix_fmt"),
            "color_space": video.get("color_space", "unknown"),
            "color_primaries": video.get("color_primaries", "unknown"),
        })
    return info


def compute_flicker_index(yavg: list[float]) -> float:
    """Mean distance of each frame's luma from the line through its neighbours.

    A pan or fade changes luma smoothly and scores near zero; flicker
    alternates frame to frame and scores high.
    """
    if len(yavg) < 3:
        return 0.0
    mean = sum(yavg) / len(yavg) or 1.0
    jitter = [abs(yavg[i] - (yavg[i - 1] + yavg[i + 1]) / 2) for i in range(1, len(yavg) - 1)]
    return round(sum(jitter) / len(jitter) / mean, 5)


def choose_fps_method(src_fps: float, target: float, requested: str = "auto", content_type: str = "generated") -> str:
    if requested != "auto":
        return requested
    if not src_fps or abs(src_fps / target - 1) < 0.002:
        return "none"
    if src_fps < target:
        # Animation on twos (12→24, 15→30) duplicates frames; generated clips get new ones.
        return "drop" if content_type == "animation" else "interpolate"
    if src_fps / target <= 1.05 and content_type != "animation":
        return "retime"  # 25→24 or 30→29.97: no dropped-frame stutter
    return "drop"


def fps_arg(fps: float) -> str:
    for exact, label in ((23.976, "24000/1001"), (29.97, "30000/1001"), (59.94, "60000/1001")):
        if abs(fps - exact) < 0.01:
            return label
    return f"{fps:g}"


def fps_filters(method: str, src_fps: float, target: float) -> list[str]:
    t = fps_arg(target)
    if method == "interpolate":
        return [f"minterpolate=fps={t}:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1"]
    if method == "blend":
        return [f"framerate=fps={t}"]
    if method == "retime":
        return [f"setpts=PTS*{src_fps:.6f}/{target:.6f}", f"fps={t}"]
    return [f"fps={t}"]  # none (also fixes VFR) and drop


def slow_motion_filters(src_fps: float, factor: float, target: float) -> list[str]:
    dense = round(src_fps * factor, 3)
    return [f"minterpolate=fps={dense:g}:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1",
            f"setpts=PTS*{factor:g}", f"fps={fps_arg(target)}"]


def pre_filters(inputs: dict[str, Any]) -> list[str]:
    out: list[str] = []
    if inputs.get("deflicker"):
        out.append(f"deflicker=size={int(inputs.get('deflicker_size', 5))}:mode=pm")
    if inputs.get("denoise") == "light":
        out.append("hqdn3d=1.5:1.5:6:6")
    return out


def resize_filters(inputs: dict[str, Any], info: dict[str, Any]) -> list[str]:
    w, h = inputs.get("target_width"), inputs.get("target_height")
    if not w or not h or (int(w), int(h)) == (info.get("width"), info.get("height")):
        return []
    w, h = int(w), int(h)
    if inputs.get("resize_mode", "fill") == "fit":
        return [f"scale={w}:{h}:force_original_aspect_ratio=decrease:flags=lanczos",
                f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:color=black", "setsar=1"]
    return [f"scale={w}:{h}:force_original_aspect_ratio=increase:flags=lanczos", f"crop={w}:{h}", "setsar=1"]


def recommend(info: dict[str, Any], flicker: float, inputs: dict[str, Any]) -> list[dict[str, str]]:
    recs: list[dict[str, str]] = []
    if not info.get("has_video"):
        return [{"step": "none", "reason": "no video stream"}]
    target = float(inputs.get("target_fps", 24))
    content = inputs.get("content_type", "generated")
    method = choose_fps_method(info["fps"], target, "auto", content)
    if info.get("vfr"):
        recs.append({"step": "conform", "reason": "variable frame rate; conform to a constant rate before edit"})
    if method != "none":
        recs.append({"step": f"fps_method={method}", "reason": f"{info['fps']:g} fps source vs {target:g} fps timeline"})
    if flicker > FLICKER_WARN:
        recs.append({"step": "deflicker", "reason": f"flicker index {flicker:.4f} > {FLICKER_WARN}"})
    th = inputs.get("target_height")
    if th and info["height"] < int(th):
        how = "upscale_method=realesrgan" if info["height"] * 1.5 < int(th) else "lanczos resize"
        recs.append({"step": how, "reason": f"{info['height']}p source vs {th}p timeline"})
    if info.get("color_space") in (None, "unknown"):
        recs.append({"step": "film_look tagging", "reason": "untagged color; finish with film_look (BT.709 tags)"})
    return recs
