/**
 * Camera motion engine.
 *
 * Moves are DATA (motion-catalog.json): a from/to state vector plus optional
 * modifiers (shake, orbit, float, pulse, wiggle). This module resolves a move
 * name (or a custom spec) into per-frame CSS transforms for the background
 * layer and a parallax-damped transform for the foreground content.
 *
 * State vector: s = scale, x/y = translate in % of the frame, r = rotation in
 * degrees, b = blur in px. All moves are 2D approximations of real camera
 * moves; true 3D moves need AI video generation (see each move's `ai_prompt`).
 */
import catalog from "./motion-catalog.json";

export interface Vec {
  s?: number;
  x?: number;
  y?: number;
  r?: number;
  b?: number;
}

export interface CameraSpec {
  /** Move id or alias from motion-catalog.json (e.g. "dolly_in", "whip_pan_left"). */
  move?: string;
  /** Multiplies the move's distance from identity (1 = as designed, 0.5 = subtler). */
  intensity?: number;
  /** Fraction of the scene to wait before moving (0-0.9). */
  delay?: number;
  /** Fraction of the scene to hold at the end (0-0.9). */
  hold?: number;
  /** Plays the move backwards. */
  reverse?: boolean;
  /** Easing name (see catalog.ease). Overrides the move's default. */
  ease?: string;
  /** Zoom origin as a percent of the frame — the object the camera "points at". */
  origin?: { x: number; y: number };
  from?: Vec;
  to?: Vec;
  /** Foreground (text/cards) damping: 0 = fixed, 1 = moves with the background. */
  parallax?: number;
  /** Extra shake on top of the move. */
  shake?: { ax?: number; ay?: number; ar?: number; f?: number };
  /** Seed for deterministic shake / drift. */
  seed?: number;
  /** Freeze the move at this fraction of the scene (0-1). */
  freezeAt?: number;
}

export interface MoveDef {
  id: string;
  category: string;
  summary: string;
  aliases: string[];
  from: Vec;
  to: Vec;
  ease: string;
  origin?: { x: number; y: number };
  autoBlur?: number;
  parallax?: number;
  fg?: { from: Vec; to: Vec };
  fx?: string[];
  mods?: {
    shake?: { ax: number; ay: number; ar: number; f: number };
    orbit?: { R: number; turns: number; rot: number };
    float?: { y: number; cycles: number };
    pulse?: { s: number; cycles: number };
    wiggle?: { x: number; period: number };
  };
  ai_prompt: string;
}

const MOVES: Record<string, MoveDef> = {};
for (const m of (catalog as unknown as { camera: MoveDef[] }).camera) {
  MOVES[m.id] = m;
  for (const a of m.aliases ?? []) MOVES[a] = m;
}
// Legacy animation names used by older compositions.
const LEGACY: Record<string, string> = {
  "zoom-in": "zoom_in_slow",
  "zoom-out": "zoom_out_slow",
  "pan-left": "pan_left",
  "pan-right": "pan_right",
  "ken-burns": "ken_burns",
  "ken-burns-slow-zoom": "ken_burns",
  "drift-up": "pedestal_up",
  "drift-down": "pedestal_down",
  "parallax": "parallax_drift",
  "static": "static",
  "none": "static",
};

export function moveIds(): string[] {
  return Array.from(new Set(Object.values(MOVES).map((m) => m.id)));
}
export function getMove(id: string): MoveDef | undefined {
  return MOVES[id] ?? MOVES[LEGACY[id]];
}

// ---------------------------------------------------------------------------
// Easing
// ---------------------------------------------------------------------------
const clamp01 = (t: number) => Math.min(1, Math.max(0, t));
const bell = (t: number) => Math.sin(Math.PI * clamp01(t));

export const EASINGS: Record<string, (t: number) => number> = {
  linear: (t) => t,
  in_quad: (t) => t * t,
  out_quad: (t) => 1 - (1 - t) * (1 - t),
  in_out_quad: (t) => (t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2),
  in_cubic: (t) => t * t * t,
  out_cubic: (t) => 1 - Math.pow(1 - t, 3),
  in_out_cubic: (t) => (t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2),
  in_expo: (t) => (t === 0 ? 0 : Math.pow(2, 10 * t - 10)),
  out_expo: (t) => (t === 1 ? 1 : 1 - Math.pow(2, -10 * t)),
  in_out_expo: (t) =>
    t === 0 ? 0 : t === 1 ? 1 : t < 0.5 ? Math.pow(2, 20 * t - 10) / 2 : (2 - Math.pow(2, -20 * t + 10)) / 2,
  in_out_sine: (t) => -(Math.cos(Math.PI * t) - 1) / 2,
  smooth: (t) => t * t * (3 - 2 * t),
  // hold, snap through the middle, settle: the "whip" of a whip pan / crash zoom
  whip: (t) => {
    const u = clamp01((t - 0.3) / 0.4);
    return u * u * u * (u * (u * 6 - 15) + 10);
  },
  snap_end: (t) => {
    const u = clamp01((t - 0.75) / 0.25);
    return u * u * (3 - 2 * u);
  },
  step_mid: (t) => {
    const u = clamp01((t - 0.48) / 0.06);
    return u * u * (3 - 2 * u);
  },
  back_out: (t) => {
    const c1 = 1.70158;
    const c3 = c1 + 1;
    return 1 + c3 * Math.pow(t - 1, 3) + c1 * Math.pow(t - 1, 2);
  },
  bounce_out: (t) => {
    const n1 = 7.5625;
    const d1 = 2.75;
    if (t < 1 / d1) return n1 * t * t;
    if (t < 2 / d1) return n1 * (t -= 1.5 / d1) * t + 0.75;
    if (t < 2.5 / d1) return n1 * (t -= 2.25 / d1) * t + 0.9375;
    return n1 * (t -= 2.625 / d1) * t + 0.984375;
  },
  ramp_slow_fast: (t) => Math.pow(t, 2.6),
  ramp_fast_slow: (t) => 1 - Math.pow(1 - t, 2.6),
  stutter: (t) => Math.floor(t * 8) / 8,
};
export const ease = (name: string | undefined, t: number): number =>
  (EASINGS[name ?? "smooth"] ?? EASINGS.smooth)(clamp01(t));

// ---------------------------------------------------------------------------
// Deterministic noise (sum of sines) — no Math.random so renders are repeatable
// ---------------------------------------------------------------------------
const noise = (f: number, seed: number) =>
  (Math.sin(f * 1.31 + seed) + Math.sin(f * 2.17 + seed * 1.7) * 0.6 + Math.sin(f * 3.71 + seed * 2.3) * 0.3) / 1.9;

// ---------------------------------------------------------------------------
// Resolve + evaluate
// ---------------------------------------------------------------------------
export interface ResolvedCamera {
  def: MoveDef | undefined;
  spec: CameraSpec;
}

export type CameraInput = string | CameraSpec | undefined | null;

export function resolveCamera(input: CameraInput, legacyAnimation?: string): ResolvedCamera | undefined {
  let spec: CameraSpec | undefined;
  if (typeof input === "string") spec = { move: input };
  else if (input && typeof input === "object") spec = input;
  else if (legacyAnimation) spec = { move: legacyAnimation };
  if (!spec) return undefined;
  const def = spec.move ? getMove(spec.move) : undefined;
  if (spec.move && !def && !spec.from && !spec.to) {
    // eslint-disable-next-line no-console
    console.warn(`[motion] unknown camera move "${spec.move}" — using static`);
  }
  return { def, spec };
}

export interface CameraState {
  /** transform for the background layer */
  bg: string;
  /** transform for the foreground content (parallax) */
  fg: string;
  blur: number;
  origin: string;
  /** raw values for effects that need them */
  raw: { s: number; x: number; y: number; r: number; p: number };
}

export const IDENTITY: CameraState = {
  bg: "none",
  fg: "none",
  blur: 0,
  origin: "50% 50%",
  raw: { s: 1, x: 0, y: 0, r: 0, p: 0 },
};

const val = (v: Vec | undefined, k: keyof Vec, d: number) => (v && v[k] !== undefined ? (v[k] as number) : d);

function stateAt(cam: ResolvedCamera, t: number, frame: number, fps: number) {
  const { def, spec } = cam;
  const dflt = def ?? ({ from: {}, to: {}, ease: "smooth" } as MoveDef);
  const from: Vec = { ...dflt.from, ...(spec.from ?? {}) };
  const to: Vec = { ...dflt.to, ...(spec.to ?? {}) };

  const delay = spec.delay ?? 0;
  const hold = spec.hold ?? 0;
  let u = clamp01((t - delay) / Math.max(0.05, 1 - delay - hold));
  if (spec.freezeAt !== undefined) u = Math.min(u, clamp01(spec.freezeAt));
  if (spec.reverse) u = 1 - u;
  const p = ease(spec.ease ?? dflt.ease, u);

  const k = spec.intensity ?? 1;
  const lerp = (a: number, b: number) => a + (b - a) * p;
  const ident = (key: keyof Vec) => (key === "s" ? 1 : 0);
  const mix = (key: keyof Vec) => {
    const v = lerp(val(from, key, ident(key)), val(to, key, ident(key)));
    return ident(key) + (v - ident(key)) * k;
  };
  let s = mix("s");
  let x = mix("x");
  let y = mix("y");
  let r = mix("r");
  let b = mix("b");

  const mods = dflt.mods ?? {};
  const seed = spec.seed ?? 3;
  const sh = { ...(mods.shake ?? {}), ...(spec.shake ?? {}) } as { ax?: number; ay?: number; ar?: number; f?: number };
  if (mods.shake || spec.shake) {
    const f = frame * (sh.f ?? 1);
    x += (sh.ax ?? 0) * k * noise(f, seed);
    y += (sh.ay ?? 0) * k * noise(f + 40, seed + 1);
    r += (sh.ar ?? 0) * k * noise(f + 80, seed + 2);
  }
  if (mods.orbit) {
    const a = 2 * Math.PI * mods.orbit.turns * p;
    x += mods.orbit.R * k * Math.sin(a);
    y += mods.orbit.R * k * 0.35 * (1 - Math.cos(a));
    r += mods.orbit.rot * k * Math.sin(a);
  }
  if (mods.float) y += mods.float.y * k * Math.sin(2 * Math.PI * mods.float.cycles * t);
  if (mods.pulse) s += mods.pulse.s * k * Math.sin(2 * Math.PI * mods.pulse.cycles * t);
  if (mods.wiggle) x += mods.wiggle.x * k * (Math.floor(frame / mods.wiggle.period) % 2 === 0 ? 1 : -1);

  return { s, x, y, r, b, p, def: dflt, from, to, u };
}

export function evalCamera(cam: ResolvedCamera | undefined, frame: number, durationInFrames: number, fps: number): CameraState {
  if (!cam) return IDENTITY;
  const t = clamp01(frame / Math.max(1, durationInFrames - 1));
  const cur = stateAt(cam, t, frame, fps);
  let { s, x, y, r, b } = cur;

  // Overscan: never expose the image edge when translating / rotating.
  // Small rotations need extra scale to cover the corners; large rotations
  // (camera_roll, spiral) carry their own scale in the move definition.
  const shift = (2 * Math.max(Math.abs(x), Math.abs(y))) / 100;
  s = Math.max(s, 1 + shift + (Math.abs(r) <= 24 ? 0.034 * Math.abs(r) : 0));

  // Automatic motion blur from the speed of the move
  const auto = cur.def.autoBlur ?? 0;
  if (auto > 0) {
    const prev = stateAt(cam, clamp01((frame - 1) / Math.max(1, durationInFrames - 1)), frame - 1, fps);
    const speed = Math.hypot(x - prev.x, y - prev.y) + Math.abs(s - prev.s) * 60 + Math.abs(r - prev.r) * 3;
    b = Math.max(b, Math.min(auto, speed * 1.6));
  }

  // Foreground (parallax): damped copy of the background transform
  const dflt = cur.def;
  const par = cam.spec.parallax ?? dflt.parallax ?? 0.12;
  let fs = 1 + (s - 1) * Math.min(1, par * 2.4);
  let fx = x * par;
  let fy = y * par;
  if (dflt.fg) {
    const ff = { ...dflt.fg.from };
    const ft = { ...dflt.fg.to };
    fs = val(ff, "s", 1) + (val(ft, "s", 1) - val(ff, "s", 1)) * cur.p;
    fx = 0;
    fy = 0;
  }

  const o = cam.spec.origin ?? dflt.origin ?? { x: 50, y: 50 };
  return {
    bg: `translate(${x.toFixed(3)}%, ${y.toFixed(3)}%) rotate(${r.toFixed(3)}deg) scale(${s.toFixed(4)})`,
    fg: `translate(${fx.toFixed(3)}%, ${fy.toFixed(3)}%) scale(${fs.toFixed(4)})`,
    blur: Math.max(0, b),
    origin: `${o.x}% ${o.y}%`,
    raw: { s, x, y, r, p: cur.p },
  };
}

/** Back-compat bridge for the old `backgroundMotion` prop. */
export function legacyMotionToSpec(m: {
  origin?: { x: number; y: number };
  from?: { scale?: number; x?: number; y?: number };
  to?: { scale?: number; x?: number; y?: number };
}): CameraSpec {
  const conv = (v?: { scale?: number; x?: number; y?: number }): Vec | undefined =>
    v ? { s: v.scale, x: v.x, y: v.y } : undefined;
  return { origin: m.origin, from: conv(m.from) ?? { s: 1 }, to: conv(m.to) ?? { s: 1.08 }, ease: "smooth" };
}
