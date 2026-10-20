/**
 * Stage: the cinematic wrapper used by every scene that has a background.
 *
 *   background layer  -> camera move (+ grade / blur filters, echo, halation…)
 *   scrim             -> darkening for readability
 *   foreground        -> children, with parallax-damped camera transform
 *   overlays          -> vignette, grain, light leaks, flare, letterbox…
 *
 * Everything is deterministic (no Math.random) so renders are repeatable.
 */
import React, { createContext, useContext, useId } from "react";
import { AbsoluteFill, Img, OffthreadVideo, interpolate, useCurrentFrame, useVideoConfig } from "remotion";
import { resolveAsset } from "./resolveAsset";
import { CameraInput, CameraSpec, evalCamera, resolveCamera } from "./motion";

// ---------------------------------------------------------------------------
// Scene timing context — useVideoConfig().durationInFrames is the composition
// length, so scenes get their own length through this context.
// ---------------------------------------------------------------------------
export const SceneTimingContext = createContext<number | null>(null);
export function useSceneFrames(): number {
  const ctx = useContext(SceneTimingContext);
  const { durationInFrames } = useVideoConfig();
  return ctx ?? durationInFrames;
}

// ---------------------------------------------------------------------------
// FX model
// ---------------------------------------------------------------------------
export type FxItem = string | ({ type: string } & Record<string, any>);
export interface NormalizedFx {
  type: string;
  [k: string]: any;
}
export function normalizeFx(list?: FxItem[] | FxItem): NormalizedFx[] {
  if (!list) return [];
  const arr = Array.isArray(list) ? list : [list];
  return arr.map((f) => (typeof f === "string" ? { type: f } : f)) as NormalizedFx[];
}
const find = (fx: NormalizedFx[], type: string) => fx.find((f) => f.type === type);

interface Grade {
  /** gradient-map stops (dark -> light) applied by luminance via an SVG filter */
  gmap?: string[];
  pre?: string;
  filter?: string;
  tints?: { background: string; blend: string; opacity?: number }[];
}
const GRADES: Record<string, (p: NormalizedFx) => Grade> = {
  grade_teal_orange: () => ({
    filter: "contrast(1.08) saturate(1.15)",
    tints: [{ background: "linear-gradient(180deg, rgba(20,110,140,.55) 0%, rgba(255,150,70,.5) 100%)", blend: "soft-light" }],
  }),
  grade_noir: () => ({ filter: "grayscale(1) contrast(1.35) brightness(0.95)" }),
  grade_sepia: () => ({ filter: "sepia(0.85) contrast(1.05)" }),
  grade_vintage: () => ({
    filter: "sepia(0.35) saturate(0.8) contrast(0.92) brightness(1.05)",
    tints: [{ background: "rgba(255,200,140,.22)", blend: "multiply" }],
  }),
  grade_cool: () => ({ tints: [{ background: "rgba(60,120,255,.28)", blend: "soft-light" }], filter: "saturate(1.05)" }),
  grade_warm: () => ({ tints: [{ background: "rgba(255,150,40,.28)", blend: "soft-light" }], filter: "saturate(1.05)" }),
  grade_bleach: () => ({ filter: "contrast(1.3) saturate(0.55) brightness(1.02)" }),
  grade_high_contrast: () => ({ filter: "contrast(1.3) saturate(1.05)" }),
  grade_desaturate: () => ({ filter: "saturate(0.55)" }),
  grade_vivid: () => ({ filter: "saturate(1.5) contrast(1.08)" }),
  grade_night: () => ({
    filter: "brightness(0.78) contrast(1.1) saturate(0.8)",
    tints: [{ background: "rgba(20,40,120,.45)", blend: "multiply" }],
  }),
  grade_golden_hour: () => ({ filter: "saturate(1.15)", tints: [{ background: "rgba(255,170,60,.32)", blend: "soft-light" }] }),
  grade_dream: () => ({
    filter: "saturate(1.1) brightness(1.08) contrast(0.92)",
    tints: [{ background: "rgba(255,190,220,.25)", blend: "screen" }],
  }),
  duotone: (p) => ({ gmap: [p.shadow ?? "#05070d", p.highlight ?? "#f5b544"], filter: "contrast(1.1)" }),
  invert: () => ({ filter: "invert(1)" }),
  night_vision: () => ({ gmap: ["#001a05", "#1aff4c", "#d8ffd8"], filter: "contrast(1.4) brightness(1.25)" }),
  thermal: () => ({ gmap: ["#0a0030", "#4b00b4", "#d01010", "#ff8c00", "#ffe14a", "#ffffff"], filter: "contrast(1.35) brightness(1.25)" }),
  x_ray: () => ({ gmap: ["#02080f", "#2d9cdb", "#e6f6ff"], pre: "invert(1)", filter: "contrast(1.3)" }),
  vhs: () => ({ filter: "blur(0.7px) saturate(1.25) contrast(0.95)" }),
  crt: () => ({ filter: "contrast(1.1) saturate(1.1)" }),
};

const hash = (n: number) => {
  const x = Math.sin(n * 127.1 + 311.7) * 43758.5453;
  return x - Math.floor(x);
};

// ---------------------------------------------------------------------------
// SVG filter definitions (chromatic aberration, glitch, wave, directional blur)
// ---------------------------------------------------------------------------
const SvgFilters: React.FC<{ id: string; fx: NormalizedFx[]; frame: number; blurDir?: { x: number; y: number } }> = ({ id, fx, frame, blurDir }) => {
  const ca = find(fx, "chromatic_aberration") ?? find(fx, "rgb_split") ?? find(fx, "vhs") ?? find(fx, "crt");
  const glitch = find(fx, "glitch");
  const wave = find(fx, "distortion_wave");
  const mb = find(fx, "motion_blur");
  if (!ca && !glitch && !wave && !mb && !(blurDir && (blurDir.x || blurDir.y))) return null;

  let amount = 0;
  if (ca) amount = ca.type === "vhs" ? 3 : ca.type === "crt" ? 2 : ca.amount ?? 4;
  let burst = 0;
  if (glitch) {
    const on = hash(Math.floor(frame / 3)) > (glitch.rate ?? 0.72);
    burst = on ? (glitch.amount ?? 38) * (0.4 + hash(frame) * 0.6) : 0;
    amount += burst * 0.25;
  }
  const bx = (mb?.x ?? 0) + (blurDir?.x ?? 0);
  const by = (mb?.y ?? 0) + (blurDir?.y ?? 0);
  const wf = 0.006 + 0.0006 * Math.sin(frame / 12);
  return (
    <svg width="0" height="0" style={{ position: "absolute" }} aria-hidden>
      <defs>
        <filter id={id} x="-8%" y="-8%" width="116%" height="116%" colorInterpolationFilters="sRGB">
          {wave ? (
            <>
              <feTurbulence type="fractalNoise" baseFrequency={`${wf} ${wf * 2.2}`} numOctaves="2" seed="4" result="t" />
              <feDisplacementMap in="SourceGraphic" in2="t" scale={wave.amount ?? 26} xChannelSelector="R" yChannelSelector="G" result="w" />
            </>
          ) : (
            <feOffset in="SourceGraphic" dx="0" dy="0" result="w" />
          )}
          {burst > 0 ? (
            <>
              <feTurbulence type="fractalNoise" baseFrequency="0.002 0.35" numOctaves="1" seed={String(1 + (Math.floor(frame / 3) % 17))} result="gt" />
              <feDisplacementMap in="w" in2="gt" scale={burst} xChannelSelector="R" yChannelSelector="G" result="w2" />
            </>
          ) : (
            <feOffset in="w" dx="0" dy="0" result="w2" />
          )}
          {amount > 0 ? (
            <>
              <feColorMatrix in="w2" type="matrix" values="1 0 0 0 0  0 0 0 0 0  0 0 0 0 0  0 0 0 1 0" result="r" />
              <feColorMatrix in="w2" type="matrix" values="0 0 0 0 0  0 1 0 0 0  0 0 0 0 0  0 0 0 1 0" result="g" />
              <feColorMatrix in="w2" type="matrix" values="0 0 0 0 0  0 0 0 0 0  0 0 1 0 0  0 0 0 1 0" result="b" />
              <feOffset in="r" dx={amount} dy="0" result="r2" />
              <feOffset in="b" dx={-amount} dy="0" result="b2" />
              <feBlend in="r2" in2="g" mode="screen" result="rg" />
              <feBlend in="rg" in2="b2" mode="screen" result="rgb" />
            </>
          ) : (
            <feOffset in="w2" dx="0" dy="0" result="rgb" />
          )}
          {bx || by ? <feGaussianBlur in="rgb" stdDeviation={`${bx} ${by}`} /> : <feOffset in="rgb" dx="0" dy="0" />}
        </filter>
      </defs>
    </svg>
  );
};

const hexRgb = (hex: string): [number, number, number] => {
  const c = hex.replace("#", "");
  const n = parseInt(c.length === 3 ? c.split("").map((x) => x + x).join("") : c, 16);
  return [((n >> 16) & 255) / 255, ((n >> 8) & 255) / 255, (n & 255) / 255];
};

/** Maps luminance onto a colour gradient (duotone, thermal, night vision, x-ray). */
const GradientMapFilter: React.FC<{ id: string; stops: string[] }> = ({ id, stops }) => {
  const rgb = stops.map(hexRgb);
  const table = (ch: number) => rgb.map((c) => c[ch].toFixed(3)).join(" ");
  return (
    <svg width="0" height="0" style={{ position: "absolute" }} aria-hidden>
      <defs>
        <filter id={id} colorInterpolationFilters="sRGB">
          <feColorMatrix type="matrix" values="0.2126 0.7152 0.0722 0 0  0.2126 0.7152 0.0722 0 0  0.2126 0.7152 0.0722 0 0  0 0 0 1 0" />
          <feComponentTransfer>
            <feFuncR type="table" tableValues={table(0)} />
            <feFuncG type="table" tableValues={table(1)} />
            <feFuncB type="table" tableValues={table(2)} />
          </feComponentTransfer>
        </filter>
      </defs>
    </svg>
  );
};

// ---------------------------------------------------------------------------
// Overlays
// ---------------------------------------------------------------------------
const Grain: React.FC<{ id: string; frame: number; intensity: number; freq?: number; colored?: boolean }> = ({ id, frame, intensity, freq = 0.85, colored }) => (
  <AbsoluteFill style={{ pointerEvents: "none", mixBlendMode: "overlay", opacity: intensity }}>
    <svg width="100%" height="100%">
      <filter id={id}>
        <feTurbulence type="fractalNoise" baseFrequency={freq} numOctaves="2" seed={String(1 + (frame % 53))} />
        {!colored && <feColorMatrix type="saturate" values="0" />}
      </filter>
      <rect width="100%" height="100%" filter={`url(#${id})`} />
    </svg>
  </AbsoluteFill>
);

const Overlays: React.FC<{ fx: NormalizedFx[]; frame: number; total: number; fps: number; uid: string }> = ({ fx, frame, total, fps, uid }) => {
  const t = frame / Math.max(1, total - 1);
  const out: React.ReactNode[] = [];
  const add = (key: string, node: React.ReactNode) => out.push(<React.Fragment key={key}>{node}</React.Fragment>);

  fx.forEach((f, i) => {
    switch (f.type) {
      case "vignette": {
        const s = f.strength ?? 0.6;
        add(`v${i}`, <AbsoluteFill style={{ background: `radial-gradient(ellipse at center, transparent ${Math.round((f.size ?? 52))}%, rgba(0,0,0,${s}) 100%)` }} />);
        break;
      }
      case "film_grain":
        add(`g${i}`, <Grain id={`${uid}g${i}`} frame={frame} intensity={f.intensity ?? 0.35} />);
        break;
      case "noise":
        add(`n${i}`, <Grain id={`${uid}n${i}`} frame={frame} intensity={f.intensity ?? 0.25} freq={1.6} colored />);
        break;
      case "scanlines":
      case "crt":
      case "night_vision":
      case "vhs":
        if (f.type === "vhs") add(`vh${i}`, <Grain id={`${uid}vh${i}`} frame={frame} intensity={0.3} freq={1.2} colored />);
        add(`s${i}`, <AbsoluteFill style={{ background: "repeating-linear-gradient(0deg, rgba(0,0,0,.28) 0px, rgba(0,0,0,.28) 1px, transparent 1px, transparent 3px)", opacity: f.intensity ?? 0.7 }} />);
        if (f.type === "crt") add(`cv${i}`, <AbsoluteFill style={{ background: "radial-gradient(ellipse at center, transparent 55%, rgba(0,0,0,.65) 100%)" }} />);
        break;
      case "haze":
        add(`h${i}`, <AbsoluteFill style={{ background: `linear-gradient(180deg, rgba(190,205,225,${f.intensity ?? 0.18}) 0%, rgba(190,205,225,${(f.intensity ?? 0.18) * 1.6}) 100%)`, mixBlendMode: "screen" }} />);
        break;
      case "fog":
        add(`f${i}`, <AbsoluteFill style={{ background: `linear-gradient(0deg, rgba(210,220,235,${f.intensity ?? 0.5}) 0%, transparent 55%)`, transform: `translateX(${Math.sin(frame / 60) * 2}%)` }} />);
        break;
      case "light_leak": {
        const a = (frame / total) * 100;
        add(`ll${i}`, <AbsoluteFill style={{ mixBlendMode: "screen", opacity: f.intensity ?? 0.55, background: `radial-gradient(circle at ${10 + a * 0.5}% ${20 + Math.sin(frame / 30) * 10}%, rgba(255,120,40,.85), transparent 45%), radial-gradient(circle at ${90 - a * 0.4}% 80%, rgba(255,60,120,.6), transparent 40%)` }} />);
        break;
      }
      case "lens_flare": {
        const x = Number(interpolate(t, [0, 1], [f.fromX ?? 15, f.toX ?? 70]));
        const y = Number(interpolate(t, [0, 1], [f.fromY ?? 25, f.toY ?? 45]));
        add(`lf${i}`, <AbsoluteFill style={{ mixBlendMode: "screen", opacity: f.intensity ?? 0.8, background: `radial-gradient(circle at ${x}% ${y}%, rgba(255,240,210,.95) 0, rgba(255,200,120,.45) 3%, transparent 12%), radial-gradient(circle at ${100 - x}% ${100 - y}%, rgba(120,170,255,.4) 0, transparent 7%), radial-gradient(circle at ${(x + (100 - x) * 0.5)}% ${(y + (100 - y) * 0.5)}%, rgba(255,150,90,.3) 0, transparent 5%)` }} />);
        break;
      }
      case "light_flash": {
        const at = f.at ?? 0.5;
        const d = (f.duration ?? 0.25) * fps;
        const o = interpolate(frame, [at * total - d * 0.2, at * total, at * total + d], [0, 1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
        add(`lfl${i}`, <AbsoluteFill style={{ background: f.color ?? "#fff", opacity: o * (f.intensity ?? 0.85) }} />);
        break;
      }
      case "light_sweep": {
        const x = interpolate(t, [0, 1], [-40, 140]);
        add(`ls${i}`, <AbsoluteFill style={{ mixBlendMode: "overlay", background: `linear-gradient(105deg, transparent ${x - 12}%, rgba(255,255,255,${f.intensity ?? 0.55}) ${x}%, transparent ${x + 12}%)` }} />);
        break;
      }
      case "spotlight": {
        const r = f.radius ?? 38;
        add(`sp${i}`, <AbsoluteFill style={{ background: `radial-gradient(circle at ${f.x ?? 50}% ${f.y ?? 50}%, transparent ${r * 0.55}%, rgba(0,0,0,${f.dark ?? 0.78}) ${r + 22}%)` }} />);
        break;
      }
      case "hard_light":
        add(`hl${i}`, <AbsoluteFill style={{ mixBlendMode: "overlay", background: "linear-gradient(120deg, rgba(255,255,255,.55), rgba(0,0,0,.65))" }} />);
        break;
      case "dust": {
        const dots = Array.from({ length: f.count ?? 36 }, (_, k) => {
          const x = (hash(k * 3.1) * 100 + frame * (0.05 + hash(k) * 0.12)) % 100;
          const y = (hash(k * 7.7) * 100 + Math.sin((frame + k * 9) / 40) * 2 + frame * 0.03) % 100;
          const s = 1 + hash(k * 2.2) * 3;
          return <div key={k} style={{ position: "absolute", left: `${x}%`, top: `${y}%`, width: s, height: s, borderRadius: "50%", background: "rgba(255,255,255,.7)", opacity: 0.25 + hash(k * 5) * 0.5, filter: "blur(0.5px)" }} />;
        });
        add(`d${i}`, <AbsoluteFill style={{ pointerEvents: "none" }}>{dots}</AbsoluteFill>);
        break;
      }
      case "dirty_lens":
        add(`dl${i}`, <AbsoluteFill style={{ mixBlendMode: "screen", opacity: f.intensity ?? 0.5, background: "radial-gradient(circle at 18% 70%, rgba(255,255,255,.35) 0, transparent 6%), radial-gradient(circle at 76% 28%, rgba(255,255,255,.28) 0, transparent 9%), radial-gradient(circle at 60% 82%, rgba(255,255,255,.22) 0, transparent 5%), radial-gradient(circle at 30% 20%, rgba(255,255,255,.2) 0, transparent 4%)", filter: "blur(2px)" }} />);
        break;
      case "silhouette":
        add(`si${i}`, <AbsoluteFill style={{ background: "rgba(0,0,0,.35)", mixBlendMode: "multiply" }} />);
        break;
      case "frame_border": {
        const w = f.width ?? 6;
        add(`fb${i}`, <AbsoluteFill style={{ boxShadow: `inset 0 0 0 ${w}px ${f.color ?? "#f5f5f5"}` }} />);
        break;
      }
      case "rounded_frame": {
        const r = f.radius ?? 44;
        const m = f.margin ?? 40;
        add(`rf${i}`, <AbsoluteFill style={{ boxShadow: `inset 0 0 0 ${m}px ${f.color ?? "#05070d"}`, borderRadius: r, outline: `${m}px solid ${f.color ?? "#05070d"}`, outlineOffset: -m }} />);
        break;
      }
      default:
        break;
    }
  });
  return <>{out}</>;
};

const Bars: React.FC<{ fx: NormalizedFx[]; frame: number; total: number; width: number; height: number }> = ({ fx, frame, total, width, height }) => {
  const lb = find(fx, "letterbox");
  const rs = find(fx, "ratio_switch");
  const pb = find(fx, "pillarbox");
  const nodes: React.ReactNode[] = [];
  const barsFor = (ratio: number, k: number) => {
    const target = width / ratio;
    const bar = Math.max(0, (height - target) / 2) * k;
    return (
      <>
        <div style={{ position: "absolute", left: 0, right: 0, top: 0, height: bar, background: "#000" }} />
        <div style={{ position: "absolute", left: 0, right: 0, bottom: 0, height: bar, background: "#000" }} />
      </>
    );
  };
  if (lb) nodes.push(<React.Fragment key="lb">{barsFor(lb.ratio ?? 2.39, interpolate(frame, [0, 10], [lb.animate ? 0 : 1, 1], { extrapolateRight: "clamp" }))}</React.Fragment>);
  if (rs) {
    const at = (rs.at ?? 0.5) * total;
    const k = interpolate(frame, [at - 6, at + 6], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
    nodes.push(<React.Fragment key="rs">{barsFor(rs.ratio ?? 2.39, k)}</React.Fragment>);
  }
  if (pb) {
    const target = height * (pb.ratio ?? 1);
    const bar = Math.max(0, (width - target) / 2);
    nodes.push(
      <React.Fragment key="pb">
        <div style={{ position: "absolute", top: 0, bottom: 0, left: 0, width: bar, background: "#000" }} />
        <div style={{ position: "absolute", top: 0, bottom: 0, right: 0, width: bar, background: "#000" }} />
      </React.Fragment>
    );
  }
  return <AbsoluteFill style={{ pointerEvents: "none" }}>{nodes}</AbsoluteFill>;
};

// ---------------------------------------------------------------------------
// Stage
// ---------------------------------------------------------------------------
export interface StageProps {
  /** background image */
  src?: string;
  /** background video */
  video?: { src: string; startFrom?: number; playbackRate?: number };
  /** second image for double_exposure */
  srcB?: string;
  camera?: CameraInput;
  legacyAnimation?: string;
  fx?: FxItem[];
  overlayOpacity?: number;
  backgroundColor?: string;
  /** Content that lives INSIDE the camera (moves/zooms with the background), e.g. a scale chart. */
  world?: React.ReactNode;
  children?: React.ReactNode;
}

export const Stage: React.FC<StageProps> = ({ src, video, srcB, camera, legacyAnimation, fx: fxIn, overlayOpacity = 0, backgroundColor, world, children }) => {
  const frame = useCurrentFrame();
  const { fps, width, height } = useVideoConfig();
  const total = useSceneFrames();
  const rawId = useId().replace(/[^a-zA-Z0-9]/g, "");
  const fx = normalizeFx(fxIn);

  // fx that act on the camera itself
  const frz = find(fx, "freeze");
  const stut = find(fx, "stutter");
  let spec: CameraSpec | undefined = resolveCamera(camera, legacyAnimation)?.spec;
  if (spec || frz || stut) {
    spec = { ...(spec ?? {}), ...(frz ? { freezeAt: frz.at ?? 0.5 } : {}), ...(stut ? { ease: "stutter" } : {}) };
  }
  const resolved = spec ? resolveCamera(spec) : undefined;
  const cam = evalCamera(resolved, frame, total, fps);

  // rack focus / focal shift blur
  const rack = find(fx, "rack_focus") ?? find(fx, "focal_shift");
  const t = frame / Math.max(1, total - 1);
  const rackBlur = rack ? interpolate(t, [0, 1], [rack.from ?? 14, rack.to ?? 0], { extrapolateRight: "clamp" }) : 0;
  const blurFx = find(fx, "blur")?.amount ?? 0;
  const camBlur = cam.blur;

  // directional motion blur from the camera when the move is horizontal/vertical dominant
  const dirBlur = camBlur > 0.5 && resolved?.def?.autoBlur ? { x: Math.abs(cam.raw.x) >= Math.abs(cam.raw.y) ? camBlur : 0, y: Math.abs(cam.raw.y) > Math.abs(cam.raw.x) ? camBlur : 0 } : undefined;
  const svgId = `f${rawId}`;
  const needsSvg = !!(find(fx, "chromatic_aberration") || find(fx, "rgb_split") || find(fx, "glitch") || find(fx, "distortion_wave") || find(fx, "motion_blur") || find(fx, "vhs") || find(fx, "crt") || dirBlur);

  // grade
  let gradeFilter = "";
  const tints: { background: string; blend: string; opacity?: number }[] = [];
  let gmap: string[] | undefined;
  let preFilter = "";
  fx.forEach((f) => {
    const g = GRADES[f.type]?.(f);
    if (g) {
      if (g.pre) preFilter += " " + g.pre;
      if (g.filter) gradeFilter += " " + g.filter;
      if (g.tints) tints.push(...g.tints);
      if (g.gmap) gmap = g.gmap;
    }
  });
  const gmId = `gm${rawId}`;
  const silh = find(fx, "silhouette") ? " brightness(0.6) contrast(1.5)" : "";
  const bgBlurPx = rackBlur + blurFx + (needsSvg ? 0 : camBlur);
  const filterParts = [needsSvg ? `url(#${svgId})` : "", bgBlurPx > 0.2 ? `blur(${bgBlurPx.toFixed(2)}px)` : "", preFilter.trim(), gmap ? `url(#${gmId})` : "", gradeFilter.trim(), silh.trim()].filter(Boolean).join(" ");

  const imgStyle: React.CSSProperties = { width: "100%", height: "100%", objectFit: "cover", position: "absolute", inset: 0 };
  const layerStyle = (camState = cam): React.CSSProperties => ({
    position: "absolute",
    inset: 0,
    transform: camState.bg,
    transformOrigin: camState.origin,
    // no will-change for vector worlds: keeps them re-rasterised (crisp) while zooming
    willChange: world ? undefined : "transform, filter",
  });
  const bgMedia = (extra?: React.CSSProperties) =>
    video ? (
      <OffthreadVideo src={resolveAsset(video.src)} startFrom={Math.round((video.startFrom ?? 0) * fps)} playbackRate={video.playbackRate ?? 1} muted style={{ ...imgStyle, ...extra }} />
    ) : src ? (
      <Img src={resolveAsset(src)} style={{ ...imgStyle, ...extra }} />
    ) : null;

  // extra background passes -------------------------------------------------
  const extras: React.ReactNode[] = [];
  const hal = find(fx, "halation");
  const bloom = find(fx, "bloom") ?? find(fx, "glow");
  if ((src || video) && hal)
    extras.push(<div key="hal" style={{ position: "absolute", inset: 0, mixBlendMode: "screen", opacity: hal.intensity ?? 0.45 }}>{bgMedia({ filter: "blur(22px) brightness(1.7) contrast(1.5) saturate(1.8) sepia(.6) hue-rotate(-18deg)" })}</div>);
  if ((src || video) && bloom)
    extras.push(<div key="bl" style={{ position: "absolute", inset: 0, mixBlendMode: "screen", opacity: bloom.intensity ?? 0.4 }}>{bgMedia({ filter: "blur(16px) brightness(1.5) contrast(1.3)" })}</div>);
  const ts = find(fx, "tilt_shift");
  if ((src || video) && ts)
    extras.push(<div key="ts" style={{ position: "absolute", inset: 0, WebkitMaskImage: `linear-gradient(180deg, #000 0%, transparent ${ts.top ?? 32}%, transparent ${ts.bottom ?? 66}%, #000 100%)`, maskImage: `linear-gradient(180deg, #000 0%, transparent ${ts.top ?? 32}%, transparent ${ts.bottom ?? 66}%, #000 100%)` }}>{bgMedia({ filter: `blur(${ts.blur ?? 9}px) saturate(1.3)` })}</div>);
  const db = find(fx, "depth_blur");
  if ((src || video) && db)
    extras.push(<div key="db" style={{ position: "absolute", inset: 0, WebkitMaskImage: "radial-gradient(circle at 50% 50%, transparent 25%, #000 80%)", maskImage: "radial-gradient(circle at 50% 50%, transparent 25%, #000 80%)" }}>{bgMedia({ filter: `blur(${db.blur ?? 12}px)` })}</div>);
  const ex = find(fx, "double_exposure");
  if (ex && (srcB || ex.src)) {
    const o = ex.opacity ?? interpolate(t, [0, 1], [0.15, 0.65]);
    extras.push(<div key="dx" style={{ position: "absolute", inset: 0, mixBlendMode: (ex.blend ?? "screen") as any, opacity: o }}><Img src={resolveAsset(srcB ?? ex.src)} style={imgStyle} /></div>);
  }
  const echo = find(fx, "echo");
  const ghosts: React.ReactNode[] = [];
  if ((src || video) && echo) {
    const n = echo.count ?? 3;
    for (let g = n; g >= 1; g--) {
      const gc = evalCamera(resolved, Math.max(0, frame - g * (echo.lag ?? 3)), total, fps);
      ghosts.push(<div key={`eg${g}`} style={{ position: "absolute", inset: 0, opacity: 0.28 / g, mixBlendMode: "screen", transform: gc.bg, transformOrigin: gc.origin }}>{bgMedia()}</div>);
    }
  }

  // mirror / kaleidoscope compose the layer several times ------------------
  const layerCore = (
    <div style={layerStyle()}>
      {bgMedia()}
      {world}
      {extras}
      {tints.map((tn, k) => (
        <div key={`t${k}`} style={{ position: "absolute", inset: 0, background: tn.background, mixBlendMode: tn.blend as any, opacity: tn.opacity ?? 1 }} />
      ))}
    </div>
  );
  const mirror = find(fx, "mirror");
  const kaleido = find(fx, "kaleidoscope");
  let bgLayer: React.ReactNode = layerCore;
  if (kaleido) {
    const q = (key: string, clip: string, tf: string) => (
      <div key={key} style={{ position: "absolute", inset: 0, clipPath: clip, transform: tf }}>{layerCore}</div>
    );
    bgLayer = (
      <>
        {q("a", "inset(0 50% 50% 0)", "none")}
        {q("b", "inset(0 0 50% 50%)", "scaleX(-1)")}
        {q("c", "inset(50% 50% 0 0)", "scaleY(-1)")}
        {q("d", "inset(50% 0 0 50%)", "scale(-1, -1)")}
      </>
    );
  } else if (mirror) {
    const vertical = mirror.axis === "horizontal";
    bgLayer = (
      <>
        <div style={{ position: "absolute", inset: 0, clipPath: vertical ? "inset(0 0 50% 0)" : "inset(0 50% 0 0)" }}>{layerCore}</div>
        <div style={{ position: "absolute", inset: 0, clipPath: vertical ? "inset(50% 0 0 0)" : "inset(0 0 0 50%)", transform: vertical ? "scaleY(-1)" : "scaleX(-1)" }}>{layerCore}</div>
      </>
    );
  }

  const uid = `o${rawId}`;
  const fgHasMove = cam.fg !== "none";

  return (
    <AbsoluteFill style={{ overflow: "hidden", background: backgroundColor ?? "transparent" }}>
      {needsSvg && <SvgFilters id={svgId} fx={fx} frame={frame} blurDir={dirBlur} />}
      {gmap && <GradientMapFilter id={gmId} stops={gmap} />}
      <AbsoluteFill style={{ filter: filterParts || undefined }}>
        {ghosts}
        {bgLayer}
      </AbsoluteFill>
      {overlayOpacity > 0 && <AbsoluteFill style={{ background: `rgba(15, 23, 42, ${overlayOpacity})` }} />}
      <AbsoluteFill style={{ transform: fgHasMove ? cam.fg : undefined, transformOrigin: "50% 50%" }}>{children}</AbsoluteFill>
      <Overlays fx={fx} frame={frame} total={total} fps={fps} uid={uid} />
      <Bars fx={fx} frame={frame} total={total} width={width} height={height} />
    </AbsoluteFill>
  );
};
