/**
 * Scale comparison scenes: silhouettes drawn at true relative size on a metric
 * ruler, with dimension brackets, range bands and dashed marks. The visible
 * width (in metres) can animate, so the scene "zooms out" from a turkey to a
 * 37 m titanosaur on the same ruler. Also a schematic bone cross-section.
 *
 * Positions are in METRES from the world origin; vertical positions are
 * measured up from the ground line.
 */
import React from "react";
import { AbsoluteFill, Img, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { EASINGS } from "../lib/motion";
import { useSceneFrames } from "../lib/stage";
import { resolveAsset } from "../lib/resolveAsset";

const clamp01 = (t: number) => Math.min(1, Math.max(0, t));
const smooth01 = (t: number) => {
  const u = clamp01(t);
  return u * u * (3 - 2 * u);
};
/** gentle, overshoot-free entrance 0 -> 1 over `frames` frames starting at `delay` */
const enter = (frame: number, delay: number, frames = 22) => smooth01((frame - delay) / frames);

export interface ScaleItem {
  src: string;
  /** width of the silhouette bounding box in metres (animal length) */
  lengthM?: number;
  /** alternative: height in metres (people, tall animals); needs aspect */
  heightM?: number;
  /** bounding-box width / height of the silhouette image */
  aspect: number;
  /** left edge position along the ruler (metres) */
  xM: number;
  flip?: boolean;
  label?: string;
  sublabel?: string;
  /** dimension bracket above the animal: true = "<length> m", string = custom text */
  bracket?: boolean | string;
  /** frames to wait before appearing */
  delay?: number;
  opacity?: number;
  color?: string;
  /** vertical dashed marks at heights above ground (metres) with labels */
  marksY?: { m: number; label: string }[];
}

export interface ScaleBand {
  fromM: number;
  toM: number;
  label: string;
}
export interface ScaleMark {
  m: number;
  label: string;
}

export interface ScaleWorldProps {
  items: ScaleItem[];
  /** visible width in metres at start / end of the scene */
  viewFrom: number;
  viewTo?: number;
  /** world x of the left edge at start / end (metres) */
  leftFromM?: number;
  leftToM?: number;
  /** ground line, percent of frame height from the top */
  groundY?: number;
  bands?: ScaleBand[];
  marks?: ScaleMark[];
  color?: string;
  accentColor?: string;
  mutedColor?: string;
  fontFamily?: string;
  viewEase?: string;
}

// Nested steps only (each divides the next): mixed grids like 2 m and 5 m put labels on top of each other.
const STEPS = [0.1, 0.5, 1, 5, 10, 50];
const fmt = (n: number) => (Math.abs(n - Math.round(n)) < 1e-6 ? String(Math.round(n)) : n.toFixed(1).replace(".", ","));

export const ScaleWorld: React.FC<ScaleWorldProps> = ({
  items, viewFrom, viewTo, leftFromM = 0, leftToM, groundY = 74, bands = [], marks = [],
  color = "#F3E9D8", accentColor = "#E0A33A", mutedColor = "#B8A98A", fontFamily, viewEase = "in_out_cubic",
}) => {
  const frame = useCurrentFrame();
  const { fps, width, height } = useVideoConfig();
  const total = useSceneFrames();
  const t = clamp01(frame / Math.max(1, total - 1));
  const p = EASINGS[viewEase] ? EASINGS[viewEase](t) : t;
  // Geometric interpolation: a constant ratio per frame reads as a smooth, even zoom.
  const viewM = viewFrom * Math.pow((viewTo ?? viewFrom) / viewFrom, p);
  const leftM = leftFromM + ((leftToM ?? leftFromM) - leftFromM) * p;
  const ppm = width / viewM;
  const gy = (groundY / 100) * height;
  const X = (m: number) => (m - leftM) * ppm;

  // Ruler: every step level fades in/out with its on-screen spacing, so ticks and
  // numbers never pop when the zoom changes.
  const fade = (spacingPx: number) => smooth01((spacingPx - 56) / 90);
  const levels = STEPS.filter((st) => st * ppm >= 40 && st * ppm <= 1400);
  // tick marks fade in early; their NUMBERS only when there is room for them
  const labelFade = (spacingPx: number) => smooth01((spacingPx - 104) / 70);
  const tickMap = new Map<number, { op: number; lab: number }>();
  for (const st of levels) {
    const op = fade(st * ppm);
    if (op <= 0.01) continue;
    const lab = labelFade(st * ppm);
    const first = Math.floor(leftM / st) * st;
    for (let m = first; m <= leftM + viewM + st; m += st) {
      const key = Math.round(m * 1000) / 1000;
      const cur = tickMap.get(key);
      tickMap.set(key, { op: Math.max(cur?.op ?? 0, op), lab: Math.max(cur?.lab ?? 0, lab) });
    }
  }
  const ticks = Array.from(tickMap.entries());

  const font = { fontFamily, color } as React.CSSProperties;
  return (
    <AbsoluteFill style={{ pointerEvents: "none" }}>
      {/* faint graph-paper grid, one line per metre when it is readable */}
      {ppm > 40 && (
        <AbsoluteFill style={{ opacity: 0.07, backgroundImage: `linear-gradient(90deg, ${color} 1px, transparent 1px)`, backgroundSize: `${ppm}px 100%`, backgroundPosition: `${X(0) % ppm}px 0` }} />
      )}
      {/* ground */}
      <div style={{ position: "absolute", left: 0, right: 0, top: gy, height: 3, background: color, opacity: 0.85 }} />
      {/* ruler */}
      {ticks.map(([m, { op, lab }]) => {
        const x = X(m);
        if (x < -80 || x > width + 80) return null;
        return (
          <React.Fragment key={m}>
            <div style={{ position: "absolute", left: x - 1, top: gy, width: 2, height: 8 + 8 * op, background: color, opacity: 0.85 * op }} />
            <div style={{ position: "absolute", left: x - 60, width: 120, top: gy + 22, textAlign: "center", fontSize: 26, opacity: 0.8 * lab, ...font }}>{fmt(m)} m</div>
          </React.Fragment>
        );
      })}
      {/* range bands on the ruler */}
      {bands.map((b, i) => {
        const x0 = X(b.fromM);
        const x1 = X(b.toM);
        const s = enter(frame, 10, 30);
        return (
          <React.Fragment key={`b${i}`}>
            <div style={{ position: "absolute", left: x0, top: gy - 10, width: (x1 - x0) * s, height: 10, background: accentColor, opacity: 0.9, borderRadius: 3 }} />
            <div style={{ position: "absolute", left: x0, top: gy + 62, width: Math.max(300, x1 - x0), fontSize: 30, fontWeight: 700, color: accentColor, opacity: s, fontFamily }}>{b.label}</div>
          </React.Fragment>
        );
      })}
      {/* vertical dashed marks (e.g. alternative estimate) */}
      {marks.map((m, i) => {
        const x = X(m.m);
        const s = enter(frame, 20, 28);
        return (
          <React.Fragment key={`m${i}`}>
            <div style={{ position: "absolute", left: x - 1.5, top: gy - 360 * s, height: 360 * s, width: 0, borderLeft: `3px dashed ${accentColor}`, opacity: 0.9 }} />
            <div style={{ position: "absolute", left: x - 260, width: 252, top: gy - 360 - 8, textAlign: "right", fontSize: 28, color: accentColor, fontWeight: 700, opacity: s, fontFamily }}>{m.label}</div>
          </React.Fragment>
        );
      })}
      {/* silhouettes */}
      {items.map((it, i) => {
        const wM = it.lengthM ?? (it.heightM ?? 1) * it.aspect;
        const hM = wM / it.aspect;
        const w = wM * ppm;
        const h = hM * ppm;
        const x = X(it.xM);
        const appear = enter(frame, it.delay ?? i * 5, 26);
        if (x > width + 50 || x + w < -50) return null;
        const bracketTop = gy - h - 40;
        const bracketText = typeof it.bracket === "string" ? it.bracket : `${fmt(wM)} m`;
        return (
          <React.Fragment key={i}>
            <div style={{ position: "absolute", left: x, top: gy - h, width: w, height: h, opacity: (it.opacity ?? 1) * appear, transform: `translateY(${(1 - appear) * 28}px)` }}>
              <Img
                src={resolveAsset(it.src)}
                style={{ width: "100%", height: "100%", transform: it.flip ? "scaleX(-1)" : undefined, filter: it.color ? undefined : "invert(0.93) sepia(0.3) brightness(1.02)" }}
              />
            </div>
            {it.bracket && h > 12 && (
              <div style={{ position: "absolute", left: x, top: bracketTop, width: w * appear, opacity: appear }}>
                <div style={{ height: 3, background: accentColor }} />
                <div style={{ position: "absolute", left: 0, top: -9, width: 3, height: 21, background: accentColor }} />
                <div style={{ position: "absolute", right: 0, top: -9, width: 3, height: 21, background: accentColor }} />
                <div style={{ position: "absolute", left: "50%", top: -50, transform: "translateX(-50%)", whiteSpace: "nowrap", textAlign: "center", fontSize: 40, fontWeight: 700, color: accentColor, fontFamily }}>{bracketText}</div>
              </div>
            )}
            {(it.marksY ?? []).map((my, k) => {
              const yy = gy - my.m * ppm;
              return (
                <React.Fragment key={`my${k}`}>
                  <div style={{ position: "absolute", left: x - 30, top: yy, width: w + 60, height: 0, borderTop: `3px dashed ${accentColor}`, opacity: 0.85 * appear }} />
                  <div style={{ position: "absolute", left: x - 30, top: yy - 46, fontSize: 28, fontWeight: 700, color: accentColor, opacity: appear, fontFamily, background: "rgba(20,16,11,.82)", padding: "2px 12px", borderRadius: 6 }}>{my.label}</div>
                </React.Fragment>
              );
            })}
            {it.label && (
              <div style={{ position: "absolute", left: Math.max(12, Math.min(x, width - Math.max(w, 260) - 12)), width: Math.max(w, 260), top: gy + 62, textAlign: w < 260 ? "left" : "center", opacity: appear * clamp01((w - 55) / 70), fontFamily, color: it.color ?? color }}>
                <div style={{ fontSize: 34, fontWeight: 700 }}>{it.label}</div>
                {it.sublabel && <div style={{ fontSize: 24, opacity: 0.75, color: mutedColor }}>{it.sublabel}</div>}
              </div>
            )}
          </React.Fragment>
        );
      })}
    </AbsoluteFill>
  );
};

// ---------------------------------------------------------------------------
// Schematic bone cross-section: ring of dense bone around many air cells
// ---------------------------------------------------------------------------
const h = (n: number) => {
  const x = Math.sin(n * 91.7 + 17.3) * 43758.5453;
  return x - Math.floor(x);
};

export const BoneSection: React.FC<{ color?: string; accentColor?: string; label?: string; sublabel?: string; fontFamily?: string }> = ({
  color = "#F3E9D8", accentColor = "#E0A33A", label, sublabel, fontFamily,
}) => {
  const frame = useCurrentFrame();
  const { fps, width, height } = useVideoConfig();
  const cx = width / 2;
  const cy = height * 0.37;
  const R = height * 0.27;
  const cells: { x: number; y: number; r: number }[] = [];
  for (let i = 0; i < 160; i++) {
    const a = h(i) * Math.PI * 2;
    const rr = Math.sqrt(h(i + 400)) * (R * 0.86);
    cells.push({ x: Math.cos(a) * rr, y: Math.sin(a) * rr, r: 10 + h(i + 900) * 22 });
  }
  const s = enter(frame, 0, 34);
  return (
    <AbsoluteFill>
      <svg width={width} height={height}>
        <ellipse cx={cx} cy={cy} rx={R * 1.12} ry={R} fill={color} opacity={0.92 * s} />
        {cells.map((c, i) => {
          const pop = clamp01((frame - 8 - i * 0.35) / 14);
          return <circle key={i} cx={cx + c.x * 1.12} cy={cy + c.y} r={c.r * pop} fill="#14100B" opacity={0.88} />;
        })}
        <ellipse cx={cx} cy={cy} rx={R * 1.12} ry={R} fill="none" stroke={accentColor} strokeWidth={5} opacity={s} />
      </svg>
      {label && (
        <div style={{ position: "absolute", left: 0, right: 0, top: height * 0.67, textAlign: "center", fontFamily, color, opacity: interpolate(frame, [20, 40], [0, 1], { extrapolateRight: "clamp" }) }}>
          <div style={{ fontSize: 44, fontWeight: 700, color: accentColor }}>{label}</div>
          {sublabel && <div style={{ fontSize: 28, opacity: 0.8 }}>{sublabel}</div>}
        </div>
      )}
    </AbsoluteFill>
  );
};
