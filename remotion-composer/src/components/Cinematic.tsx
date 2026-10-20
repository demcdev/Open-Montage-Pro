/**
 * Cinematic scene types and overlays:
 *   KineticText   - animated typography (12 modes)
 *   SplitScreen   - 2/3/4-up and picture-in-picture, each panel with its own camera
 *   Collage       - free-positioned pop-in tiles
 *   FocusRing / Arrow / LowerThird / HudFrame - overlays that point at things
 */
import React from "react";
import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { Stage, useSceneFrames, FxItem } from "../lib/stage";
import type { CameraInput } from "../lib/motion";
import { EASINGS } from "../lib/motion";

const clamp01 = (t: number) => Math.min(1, Math.max(0, t));
const hash = (n: number) => {
  const x = Math.sin(n * 91.7 + 17.3) * 43758.5453;
  return x - Math.floor(x);
};

// ---------------------------------------------------------------------------
// KineticText
// ---------------------------------------------------------------------------
export type TextMode =
  | "typewriter"
  | "word_pop"
  | "letter_cascade"
  | "slide_up"
  | "blur_in"
  | "scale_reveal"
  | "glitch_in"
  | "wave"
  | "mask_wipe"
  | "bounce_in"
  | "tracking_in"
  | "fade_words";

export const TEXT_MODES: TextMode[] = [
  "typewriter", "word_pop", "letter_cascade", "slide_up", "blur_in", "scale_reveal",
  "glitch_in", "wave", "mask_wipe", "bounce_in", "tracking_in", "fade_words",
];

export interface KineticTextProps {
  text: string;
  mode?: TextMode;
  fontSize?: number;
  color?: string;
  accentColor?: string;
  /** words to render in the accent colour */
  highlight?: string[];
  align?: "left" | "center" | "right";
  fontFamily?: string;
  fontWeight?: number;
  /** frames between units */
  stagger?: number;
  maxWidth?: string;
  uppercase?: boolean;
}

export const KineticText: React.FC<KineticTextProps> = ({
  text, mode = "word_pop", fontSize = 96, color = "#fff", accentColor = "#f5b544", highlight = [],
  align = "center", fontFamily, fontWeight = 700, stagger, maxWidth = "86%", uppercase,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const total = useSceneFrames();
  const words = text.split(/\s+/).filter(Boolean);
  const isChar = ["typewriter", "letter_cascade", "wave", "glitch_in", "tracking_in"].includes(mode);
  const hl = new Set(highlight.map((w) => w.toLowerCase().replace(/[.,;:!?]/g, "")));
  const colorFor = (w: string) => (hl.has(w.toLowerCase().replace(/[.,;:!?]/g, "")) ? accentColor : color);

  let idx = 0;
  const unitsTotal = isChar ? text.replace(/\s/g, "").length : words.length;
  const st = stagger ?? Math.max(1, Math.min(6, Math.floor((total * 0.55) / Math.max(1, unitsTotal))));

  const unitStyle = (i: number, w: string): React.CSSProperties => {
    const local = frame - i * st;
    const p = clamp01(local / (mode === "typewriter" ? 1 : 14));
    const s = spring({ frame: Math.max(0, local), fps, config: { damping: 11, stiffness: 140 } });
    switch (mode) {
      case "typewriter":
        return { opacity: p > 0 ? 1 : 0 };
      case "word_pop":
        return { opacity: clamp01(local / 4), transform: `scale(${0.4 + 0.6 * s})` };
      case "letter_cascade":
        return { opacity: p, transform: `translateY(${(1 - EASINGS.out_cubic(p)) * 40}px)` };
      case "slide_up":
        return { opacity: p, transform: `translateY(${(1 - EASINGS.out_expo(p)) * 70}px)` };
      case "blur_in":
        return { opacity: p, filter: `blur(${(1 - p) * 18}px)` };
      case "scale_reveal":
        return { opacity: p, transform: `scale(${2.2 - 1.2 * EASINGS.out_cubic(p)})` };
      case "glitch_in": {
        const on = local >= 0 && local < 10 && hash(frame + i) > 0.4;
        return { opacity: local < 0 ? 0 : 1, transform: on ? `translate(${(hash(frame + i * 3) - 0.5) * 22}px, ${(hash(frame * 2 + i) - 0.5) * 8}px)` : undefined, color: on ? accentColor : undefined };
      }
      case "wave":
        return { opacity: p, transform: `translateY(${Math.sin((frame - i * 2) / 6) * 14}px)` };
      case "bounce_in":
        return { opacity: clamp01(local / 3), transform: `translateY(${(1 - EASINGS.bounce_out(p)) * -90}px)` };
      case "tracking_in":
        return { opacity: p };
      case "fade_words":
        return { opacity: p };
      default:
        return { opacity: p };
    }
  };

  const wrap = (children: React.ReactNode, key: string) => (
    <span key={key} style={{ display: "inline-block", whiteSpace: "pre" }}>{children}</span>
  );

  const body = words.map((w, wi) => {
    const col = colorFor(w);
    const content = isChar
      ? wrap(
          w.split("").map((ch, ci) => {
            const i = idx++;
            return (
              <span key={ci} style={{ display: "inline-block", color: col, ...unitStyle(i, w) }}>{ch}</span>
            );
          }),
          `w${wi}`
        )
      : (() => {
          const i = idx++;
          return (
            <span key={`w${wi}`} style={{ display: "inline-block", color: col, ...unitStyle(i, w) }}>{w}</span>
          );
        })();
    return <React.Fragment key={wi}>{content}{wi < words.length - 1 ? <span style={{ display: "inline-block", width: "0.28em" }} /> : null}</React.Fragment>;
  });

  const wipe = mode === "mask_wipe" ? clamp01(frame / Math.max(8, total * 0.35)) : 1;
  const trackingExtra = mode === "tracking_in" ? `${(1 - EASINGS.out_expo(clamp01(frame / (total * 0.5)))) * 0.5}em` : undefined;

  return (
    <AbsoluteFill style={{ justifyContent: "center", alignItems: "center" }}>
      <div
        style={{
          maxWidth, textAlign: align, fontSize, fontWeight, color, lineHeight: 1.1, fontFamily,
          textTransform: uppercase ? "uppercase" : undefined,
          letterSpacing: trackingExtra,
          clipPath: mode === "mask_wipe" ? `inset(0 ${(1 - EASINGS.out_cubic(wipe)) * 100}% 0 0)` : undefined,
          textShadow: "0 4px 30px rgba(0,0,0,.55)",
        }}
      >
        {body}
      </div>
    </AbsoluteFill>
  );
};

// ---------------------------------------------------------------------------
// SplitScreen
// ---------------------------------------------------------------------------
export interface Panel {
  src: string;
  camera?: CameraInput;
  fx?: FxItem[];
  label?: string;
  overlayOpacity?: number;
}
export type SplitLayout = "2h" | "2v" | "3h" | "3v" | "4" | "pip" | "1+2";

function rects(layout: SplitLayout, n: number, gap: number): { l: number; t: number; w: number; h: number }[] {
  const g = gap;
  switch (layout) {
    case "2v": return [{ l: 0, t: 0, w: 100, h: 50 - g / 2 }, { l: 0, t: 50 + g / 2, w: 100, h: 50 - g / 2 }];
    case "3h": { const w = (100 - 2 * g) / 3; return [0, 1, 2].map((i) => ({ l: i * (w + g), t: 0, w, h: 100 })); }
    case "3v": { const h = (100 - 2 * g) / 3; return [0, 1, 2].map((i) => ({ l: 0, t: i * (h + g), w: 100, h })); }
    case "4": { const w = 50 - g / 2; const h = 50 - g / 2; return [{ l: 0, t: 0, w, h }, { l: w + g, t: 0, w, h }, { l: 0, t: h + g, w, h }, { l: w + g, t: h + g, w, h }]; }
    case "pip": return [{ l: 0, t: 0, w: 100, h: 100 }, { l: 62, t: 6, w: 32, h: 32 }];
    case "1+2": return [{ l: 0, t: 0, w: 60 - g / 2, h: 100 }, { l: 60 + g / 2, t: 0, w: 40 - g / 2, h: 50 - g / 2 }, { l: 60 + g / 2, t: 50 + g / 2, w: 40 - g / 2, h: 50 - g / 2 }];
    default: return [{ l: 0, t: 0, w: 50 - g / 2, h: 100 }, { l: 50 + g / 2, t: 0, w: 50 - g / 2, h: 100 }];
  }
}

export const SplitScreen: React.FC<{ panels: Panel[]; layout?: SplitLayout; gap?: number; background?: string; radius?: number; accentColor?: string }> = ({
  panels, layout = "2h", gap = 1.2, background = "#05070d", radius = 0, accentColor = "#f5b544",
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const rs = rects(layout, panels.length, gap);
  return (
    <AbsoluteFill style={{ background }}>
      {panels.slice(0, rs.length).map((p, i) => {
        const r = rs[i];
        const pop = spring({ frame: Math.max(0, frame - i * 4), fps, config: { damping: 16, stiffness: 120 } });
        return (
          <div key={i} style={{ position: "absolute", left: `${r.l}%`, top: `${r.t}%`, width: `${r.w}%`, height: `${r.h}%`, overflow: "hidden", borderRadius: layout === "pip" && i === 1 ? 22 : radius, opacity: pop, transform: `scale(${0.94 + 0.06 * pop})`, boxShadow: layout === "pip" && i === 1 ? "0 14px 40px rgba(0,0,0,.55)" : undefined, outline: layout === "pip" && i === 1 ? `3px solid ${accentColor}` : undefined }}>
            <Stage src={p.src} camera={p.camera ?? "ken_burns"} fx={p.fx} overlayOpacity={p.overlayOpacity ?? 0.2} />
            {p.label && (
              <div style={{ position: "absolute", left: 18, bottom: 16, fontSize: 28, fontWeight: 700, color: "#fff", textShadow: "0 2px 12px rgba(0,0,0,.7)", letterSpacing: 1, textTransform: "uppercase" }}>{p.label}</div>
            )}
          </div>
        );
      })}
    </AbsoluteFill>
  );
};

// ---------------------------------------------------------------------------
// Collage
// ---------------------------------------------------------------------------
export interface CollageItem {
  src: string;
  x: number; // percent of frame (left)
  y: number; // percent of frame (top)
  w: number; // percent width
  h: number; // percent height
  rotate?: number;
  delay?: number; // frames
  camera?: CameraInput;
  label?: string;
}

export const Collage: React.FC<{ items: CollageItem[]; background?: string; accentColor?: string }> = ({ items, background = "#05070d", accentColor = "#f5b544" }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  return (
    <AbsoluteFill style={{ background }}>
      {items.map((it, i) => {
        const s = spring({ frame: Math.max(0, frame - (it.delay ?? i * 6)), fps, config: { damping: 12, stiffness: 130 } });
        return (
          <div key={i} style={{ position: "absolute", left: `${it.x}%`, top: `${it.y}%`, width: `${it.w}%`, height: `${it.h}%`, transform: `rotate(${(it.rotate ?? 0) * s}deg) scale(${s})`, opacity: clamp01(s * 1.5), overflow: "hidden", borderRadius: 10, boxShadow: "0 12px 36px rgba(0,0,0,.55)", border: `3px solid ${accentColor}22` }}>
            <Stage src={it.src} camera={it.camera ?? "ken_burns"} overlayOpacity={0.1} />
            {it.label && <div style={{ position: "absolute", left: 12, bottom: 10, fontSize: 24, fontWeight: 700, color: "#fff", textShadow: "0 2px 10px rgba(0,0,0,.8)" }}>{it.label}</div>}
          </div>
        );
      })}
    </AbsoluteFill>
  );
};

// ---------------------------------------------------------------------------
// Overlays that point at things
// ---------------------------------------------------------------------------
export interface PointerProps {
  /** target position as a percent of the frame */
  x?: number;
  y?: number;
  /** ring radius in px (focus_ring) */
  radius?: number;
  label?: string;
  color?: string;
  shape?: "circle" | "square";
  /** where the label sits relative to the target */
  side?: "right" | "left" | "top" | "bottom";
}

export const FocusRing: React.FC<PointerProps> = ({ x = 50, y = 50, radius = 120, label, color = "#f5b544", shape = "circle", side = "right" }) => {
  const frame = useCurrentFrame();
  const { fps, width, height } = useVideoConfig();
  const s = spring({ frame, fps, config: { damping: 14, stiffness: 120 } });
  const pulse = 1 + Math.sin(frame / 8) * 0.025;
  const cx = (x / 100) * width;
  const cy = (y / 100) * height;
  const r = radius * s * pulse;
  const dx = side === "right" ? radius + 40 : side === "left" ? -(radius + 40) : 0;
  const dy = side === "top" ? -(radius + 40) : side === "bottom" ? radius + 40 : 0;
  return (
    <AbsoluteFill style={{ pointerEvents: "none" }}>
      <svg width={width} height={height} style={{ position: "absolute", inset: 0 }}>
        {shape === "circle" ? (
          <circle cx={cx} cy={cy} r={r} fill="none" stroke={color} strokeWidth={4} strokeDasharray={`${r * 1.4} ${r * 0.5}`} transform={`rotate(${frame * 1.6} ${cx} ${cy})`} />
        ) : (
          <rect x={cx - r} y={cy - r} width={r * 2} height={r * 2} fill="none" stroke={color} strokeWidth={4} rx={10} />
        )}
        {label && (
          <line x1={cx + (dx ? Math.sign(dx) * r : 0)} y1={cy + (dy ? Math.sign(dy) * r : 0)} x2={cx + dx * s} y2={cy + dy * s} stroke={color} strokeWidth={3} />
        )}
      </svg>
      {label && (
        <div style={{ position: "absolute", left: cx + dx * s + (side === "left" ? -10 : 10), top: cy + dy * s - 20, transform: side === "left" ? "translateX(-100%)" : side === "top" || side === "bottom" ? "translateX(-50%)" : undefined, opacity: s, fontSize: 36, fontWeight: 700, color: "#fff", textShadow: "0 2px 14px rgba(0,0,0,.8)", background: "rgba(5,7,13,.55)", padding: "6px 16px", borderRadius: 8, borderLeft: `4px solid ${color}`, whiteSpace: "nowrap" }}>{label}</div>
      )}
    </AbsoluteFill>
  );
};

export const Arrow: React.FC<PointerProps & { angle?: number }> = ({ x = 50, y = 50, label, color = "#f5b544", angle = 135 }) => {
  const frame = useCurrentFrame();
  const { fps, width, height } = useVideoConfig();
  const s = spring({ frame, fps, config: { damping: 12, stiffness: 140 } });
  const cx = (x / 100) * width;
  const cy = (y / 100) * height;
  const len = 150 * s;
  const a = (angle * Math.PI) / 180;
  const sx = cx - Math.cos(a) * len;
  const sy = cy - Math.sin(a) * len;
  const bob = Math.sin(frame / 6) * 6;
  return (
    <AbsoluteFill style={{ pointerEvents: "none" }}>
      <svg width={width} height={height} style={{ position: "absolute", inset: 0 }}>
        <g transform={`translate(${Math.cos(a) * bob} ${Math.sin(a) * bob})`}>
          <line x1={sx} y1={sy} x2={cx} y2={cy} stroke={color} strokeWidth={6} strokeLinecap="round" />
          <polygon points={`${cx},${cy} ${cx - Math.cos(a - 0.5) * 34},${cy - Math.sin(a - 0.5) * 34} ${cx - Math.cos(a + 0.5) * 34},${cy - Math.sin(a + 0.5) * 34}`} fill={color} />
        </g>
      </svg>
      {label && <div style={{ position: "absolute", left: sx, top: sy, transform: "translate(-50%, -110%)", opacity: s, fontSize: 36, fontWeight: 700, color: "#fff", textShadow: "0 2px 14px rgba(0,0,0,.8)", whiteSpace: "nowrap" }}>{label}</div>}
    </AbsoluteFill>
  );
};

export const LowerThird: React.FC<{ text: string; subtitle?: string; color?: string }> = ({ text, subtitle, color = "#f5b544" }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const s = spring({ frame, fps, config: { damping: 16, stiffness: 120 } });
  return (
    <AbsoluteFill style={{ justifyContent: "flex-end", alignItems: "flex-start", padding: "0 0 150px 90px", pointerEvents: "none" }}>
      <div style={{ transform: `translateX(${(1 - s) * -420}px)`, opacity: s, borderLeft: `6px solid ${color}`, background: "linear-gradient(90deg, rgba(5,7,13,.82), rgba(5,7,13,0))", padding: "12px 60px 12px 22px" }}>
        <div style={{ fontSize: 46, fontWeight: 700, color: "#fff" }}>{text}</div>
        {subtitle && <div style={{ fontSize: 28, color: "#c9d3e6", marginTop: 4 }}>{subtitle}</div>}
      </div>
    </AbsoluteFill>
  );
};

export const HudFrame: React.FC<{ label?: string; color?: string; rec?: boolean }> = ({ label, color = "#f5b544", rec = true }) => {
  const frame = useCurrentFrame();
  const { fps, width, height } = useVideoConfig();
  const m = 46;
  const L = 70;
  const sec = Math.floor(frame / fps);
  const tc = `00:${String(Math.floor(sec / 60)).padStart(2, "0")}:${String(sec % 60).padStart(2, "0")}:${String(frame % fps).padStart(2, "0")}`;
  const corner = (x: number, y: number, sx: number, sy: number) => (
    <path d={`M ${x + sx * L} ${y} L ${x} ${y} L ${x} ${y + sy * L}`} stroke={color} strokeWidth={4} fill="none" />
  );
  return (
    <AbsoluteFill style={{ pointerEvents: "none" }}>
      <svg width={width} height={height} style={{ position: "absolute", inset: 0 }}>
        {corner(m, m, 1, 1)}
        {corner(width - m, m, -1, 1)}
        {corner(m, height - m, 1, -1)}
        {corner(width - m, height - m, -1, -1)}
        <line x1={width / 2 - 20} y1={height / 2} x2={width / 2 + 20} y2={height / 2} stroke={color} strokeWidth={2} opacity={0.7} />
        <line x1={width / 2} y1={height / 2 - 20} x2={width / 2} y2={height / 2 + 20} stroke={color} strokeWidth={2} opacity={0.7} />
      </svg>
      <div style={{ position: "absolute", left: m + 14, top: m + 14, fontFamily: "monospace", fontSize: 26, color: "#fff", display: "flex", gap: 12, alignItems: "center" }}>
        {rec && <span style={{ width: 16, height: 16, borderRadius: "50%", background: "#ff3b30", opacity: Math.floor(frame / 15) % 2 === 0 ? 1 : 0.25 }} />}
        {label ?? "REC"}
      </div>
      <div style={{ position: "absolute", right: m + 14, bottom: m + 14, fontFamily: "monospace", fontSize: 24, color: "#fff", opacity: 0.85 }}>{tc}</div>
    </AbsoluteFill>
  );
};

