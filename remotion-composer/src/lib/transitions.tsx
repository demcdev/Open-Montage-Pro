/**
 * Scene transitions between cuts.
 *
 * A boundary between two cuts has a style + duration. The incoming Sequence
 * starts half a transition early and the outgoing one ends half a transition
 * late, so both are on screen while TransitionShell animates them:
 *   outgoing -> exit(q)   incoming -> enter(p)   (p and q run over the same wall-clock window)
 */
import React from "react";
import { AbsoluteFill, interpolate, useCurrentFrame } from "remotion";
import { EASINGS } from "./motion";

export interface TransitionSpec {
  style: string;
  frames: number;
}

const clamp01 = (t: number) => Math.min(1, Math.max(0, t));
const bell = (t: number) => Math.sin(Math.PI * clamp01(t));
const e = (t: number) => EASINGS.in_out_cubic(clamp01(t));
const h = (n: number) => {
  const x = Math.sin(n * 91.7 + 17.3) * 43758.5453;
  return x - Math.floor(x);
};

interface Look {
  opacity?: number;
  transform?: string;
  filter?: string;
  clipPath?: string;
  mask?: string;
  z?: number;
}

type Fn = (t: number, frame: number) => Look;
interface Pair {
  enter: Fn;
  exit: Fn;
  /** colour of an overlay flash that peaks mid-transition */
  flash?: string;
}

const none: Fn = () => ({});
const slide = (dx: number, dy: number, blur = 0): Pair => ({
  enter: (p) => ({ transform: `translate(${dx * (1 - e(p))}%, ${dy * (1 - e(p))}%)`, filter: blur ? `blur(${(bell(p) * blur).toFixed(1)}px)` : undefined }),
  exit: (q) => ({ transform: `translate(${-dx * e(q)}%, ${-dy * e(q)}%)`, filter: blur ? `blur(${(bell(q) * blur).toFixed(1)}px)` : undefined }),
});
const cover = (dx: number): Pair => ({
  enter: (p) => ({ transform: `translateX(${dx * (1 - e(p))}%)` }),
  exit: (q) => ({ transform: `translateX(${-dx * 0.25 * e(q)}%)`, filter: `brightness(${1 - 0.4 * e(q)})` }),
});
const wipe = (inset: (p: number) => string): Pair => ({ enter: (p) => ({ clipPath: inset(e(p)) }), exit: none });

const PAIRS: Record<string, Pair> = {
  cut: { enter: () => ({}), exit: none },
  dissolve: { enter: (p) => ({ opacity: e(p) }), exit: none },
  blur_dissolve: {
    enter: (p) => ({ opacity: e(p), filter: `blur(${((1 - e(p)) * 16).toFixed(1)}px)` }),
    exit: (q) => ({ filter: `blur(${(e(q) * 16).toFixed(1)}px)`, opacity: 1 - 0.3 * e(q) }),
  },
  dip_black: { enter: (p) => ({ opacity: clamp01((p - 0.5) * 2) }), exit: (q) => ({ opacity: 1 - clamp01(q * 2) }) },
  dip_white: { enter: (p) => ({ opacity: clamp01((p - 0.5) * 2) }), exit: (q) => ({ opacity: 1 - clamp01(q * 2) }), flash: "#ffffff" },
  flash: { enter: (p) => ({ opacity: p < 0.5 ? 0 : 1 }), exit: none, flash: "#ffffff" },
  flash_cut: { enter: (p) => ({ opacity: p < 0.5 ? 0 : 1 }), exit: none, flash: "#ffffff" },
  film_burn: { enter: (p) => ({ opacity: p < 0.5 ? 0 : 1 }), exit: none, flash: "#ff8a2b" },
  whip_pan_left: slide(-100, 0, 22),
  whip_pan_right: slide(100, 0, 22),
  whip_pan_up: slide(0, -100, 22),
  whip_pan_down: slide(0, 100, 22),
  slide_left: slide(100, 0),
  slide_right: slide(-100, 0),
  slide_up: slide(0, 100),
  slide_down: slide(0, -100),
  cover_left: cover(100),
  cover_right: cover(-100),
  wipe_left: wipe((p) => `inset(0 0 0 ${(1 - p) * 100}%)`),
  wipe_right: wipe((p) => `inset(0 ${(1 - p) * 100}% 0 0)`),
  wipe_up: wipe((p) => `inset(${(1 - p) * 100}% 0 0 0)`),
  wipe_down: wipe((p) => `inset(0 0 ${(1 - p) * 100}% 0)`),
  wipe_diagonal: wipe((p) => `polygon(0 0, ${p * 140}% 0, ${p * 140 - 40}% 100%, 0 100%)`),
  iris_in: wipe((p) => `circle(${p * 78}% at 50% 50%)`),
  iris_out: {
    enter: (p) => ({ opacity: p > 0 ? 1 : 0 }),
    exit: (q) => ({ clipPath: `circle(${(1 - e(q)) * 78}% at 50% 50%)`, z: 2 }),
  },
  zoom_through: {
    enter: (p) => ({ transform: `scale(${0.55 + 0.45 * e(p)})`, opacity: e(p) }),
    exit: (q) => ({ transform: `scale(${1 + 1.6 * e(q)})`, opacity: 1 - e(q), filter: `blur(${(bell(q) * 8).toFixed(1)}px)` }),
  },
  zoom_out_through: {
    enter: (p) => ({ transform: `scale(${1.6 - 0.6 * e(p)})`, opacity: e(p) }),
    exit: (q) => ({ transform: `scale(${1 - 0.35 * e(q)})`, opacity: 1 - e(q) }),
  },
  crash_zoom: {
    enter: (p) => ({ transform: `scale(${1.7 - 0.7 * EASINGS.out_expo(p)})`, opacity: clamp01(p * 3), filter: `blur(${((1 - p) * 14).toFixed(1)}px)` }),
    exit: (q) => ({ transform: `scale(${1 + 0.9 * EASINGS.in_expo(q)})`, opacity: 1 - clamp01((q - 0.5) * 2), filter: `blur(${(q * 14).toFixed(1)}px)` }),
  },
  spin: {
    enter: (p) => ({ transform: `rotate(${-(1 - e(p)) * 90}deg) scale(${0.5 + 0.5 * e(p)})`, opacity: e(p) }),
    exit: (q) => ({ transform: `rotate(${e(q) * 90}deg) scale(${1 - 0.5 * e(q)})`, opacity: 1 - e(q) }),
  },
  scale_shift: {
    enter: (p) => ({ transform: `scale(${1.8 - 0.8 * EASINGS.out_expo(p)})`, opacity: e(p) }),
    exit: (q) => ({ transform: `scale(${1 + 0.8 * e(q)})`, opacity: 1 - e(q) }),
  },
  match_cut: {
    enter: (p) => ({ transform: `scale(${1.25 - 0.25 * e(p)})`, opacity: e(p) }),
    exit: (q) => ({ transform: `scale(${1 + 0.25 * e(q)})`, opacity: 1 - 0.0 * q }),
  },
  glitch: {
    enter: (p, f) => {
      const on = h(Math.floor(f / 2)) > 0.35;
      const a = Math.floor(h(f) * 60);
      return {
        opacity: p < 0.5 ? 0 : 1,
        transform: on ? `translate(${(h(f + 3) - 0.5) * 8}%, 0) skewX(${(h(f + 5) - 0.5) * 8}deg)` : undefined,
        clipPath: on ? `inset(${a}% 0 ${Math.max(0, 60 - a)}% 0)` : undefined,
        filter: on ? `hue-rotate(${Math.floor(h(f + 9) * 90)}deg) saturate(1.6) contrast(1.2)` : undefined,
      };
    },
    exit: (q, f) => {
      const on = h(Math.floor(f / 2) + 11) > 0.35;
      return {
        transform: on ? `translate(${(h(f + 13) - 0.5) * 8}%, 0)` : undefined,
        filter: on ? `hue-rotate(${Math.floor(h(f + 2) * 90)}deg) saturate(1.8)` : undefined,
      };
    },
  },
  rgb_split: {
    enter: (p) => ({ opacity: e(p), filter: `hue-rotate(${((1 - p) * 70).toFixed(0)}deg) saturate(${(1 + (1 - p) * 1.2).toFixed(2)})` }),
    exit: (q) => ({ filter: `hue-rotate(${(q * -70).toFixed(0)}deg) saturate(${(1 + q * 1.2).toFixed(2)})`, opacity: 1 - 0.3 * q }),
  },
  shutter: {
    enter: (p) => {
      const m = `repeating-linear-gradient(0deg, #000 0px, #000 ${(e(p) * 120).toFixed(1)}px, transparent ${(e(p) * 120).toFixed(1)}px, transparent 120px)`;
      return { mask: p >= 0.98 ? undefined : m };
    },
    exit: none,
  },
};

export function transitionStyles(): string[] {
  return Object.keys(PAIRS);
}
export function isKnownTransition(s?: string) {
  return !!s && s.toLowerCase() in PAIRS;
}
const ALIAS: Record<string, string> = {
  fade: "dissolve",
  crossfade: "dissolve",
  cross_dissolve: "dissolve",
  none: "cut",
  fade_black: "dip_black",
  fade_white: "dip_white",
  "dip-to-black": "dip_black",
  whip: "whip_pan_right",
  wipe: "wipe_left",
  slide: "slide_left",
  zoom: "zoom_through",
  push: "slide_left",
};
export function normalizeTransition(s?: string): string {
  if (!s) return "cut";
  const k = s.toLowerCase().replace(/[\s-]+/g, "_");
  return PAIRS[k] ? k : ALIAS[k] ?? ALIAS[s.toLowerCase()] ?? "dissolve";
}

export const TransitionShell: React.FC<{
  inT?: TransitionSpec;
  outT?: TransitionSpec;
  seqFrames: number;
  children: React.ReactNode;
}> = ({ inT, outT, seqFrames, children }) => {
  const frame = useCurrentFrame();
  const looks: Look[] = [];
  let flash: { color: string; o: number } | undefined;

  if (inT && inT.style !== "cut") {
    const p = clamp01(frame / Math.max(1, inT.frames));
    if (p < 1) {
      const pair = PAIRS[inT.style] ?? PAIRS.dissolve;
      looks.push(pair.enter(p, frame));
      if (pair.flash) flash = { color: pair.flash, o: bell(p) };
    }
  }
  if (outT && outT.style !== "cut") {
    const q = clamp01((frame - (seqFrames - outT.frames)) / Math.max(1, outT.frames));
    if (q > 0) {
      const pair = PAIRS[outT.style] ?? PAIRS.dissolve;
      looks.push(pair.exit(q, frame));
      if (pair.flash) flash = { color: pair.flash, o: bell(q) };
    }
  }
  const merged: Look = {};
  for (const l of looks) {
    if (l.opacity !== undefined) merged.opacity = (merged.opacity ?? 1) * l.opacity;
    if (l.transform) merged.transform = [merged.transform, l.transform].filter(Boolean).join(" ");
    if (l.filter) merged.filter = [merged.filter, l.filter].filter(Boolean).join(" ");
    if (l.clipPath) merged.clipPath = l.clipPath;
    if (l.mask) merged.mask = l.mask;
    if (l.z !== undefined) merged.z = l.z;
  }
  return (
    <AbsoluteFill
      style={{
        opacity: merged.opacity,
        transform: merged.transform,
        filter: merged.filter,
        clipPath: merged.clipPath,
        WebkitMaskImage: merged.mask,
        maskImage: merged.mask,
        zIndex: merged.z,
      }}
    >
      {children}
      {flash && <AbsoluteFill style={{ background: flash.color, opacity: flash.o, pointerEvents: "none" }} />}
    </AbsoluteFill>
  );
};
