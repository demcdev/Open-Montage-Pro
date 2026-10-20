import {
  AbsoluteFill,
  Audio,
  Img,
  OffthreadVideo,
  Sequence,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { loadSpaceGrotesk } from "./lib/localFonts";
import { TextCard } from "./components/TextCard";
import { StatCard } from "./components/StatCard";
import { CalloutBox } from "./components/CalloutBox";
import { ComparisonCard } from "./components/ComparisonCard";
import { BarChart } from "./components/charts/BarChart";
import { LineChart } from "./components/charts/LineChart";
import { PieChart } from "./components/charts/PieChart";
import { KPIGrid } from "./components/charts/KPIGrid";
import { ProgressBar } from "./components/ProgressBar";
import { CaptionOverlay, WordCaption } from "./components/CaptionOverlay";
import { SectionTitle } from "./components/SectionTitle";
import { StatReveal } from "./components/StatReveal";
import { HeroTitle } from "./components/HeroTitle";
import { AnimeScene } from "./components/AnimeScene";
import type { CameraMotion } from "./components/AnimeScene";
import { TerminalScene } from "./components/TerminalScene";
import type { TerminalStep } from "./components/TerminalScene";
import { ScreenshotScene } from "./components/ScreenshotScene";
import type { ScreenshotStep } from "./components/ScreenshotScene";
import { ProviderChip } from "./components/ProviderChip";
import { resolveAsset } from "./lib/resolveAsset";
import type { ParticleType } from "./components/ParticleOverlay";
import { resolveTheme, type ThemeConfig, DEFAULT_THEME } from "./Root";
import { Stage, SceneTimingContext, normalizeFx, type FxItem } from "./lib/stage";
import { legacyMotionToSpec, moveIds, type CameraInput } from "./lib/motion";
import { TransitionShell, normalizeTransition, type TransitionSpec } from "./lib/transitions";
import { ScaleWorld, BoneSection } from "./components/ScaleScene";
import type { ScaleWorldProps } from "./components/ScaleScene";
import { KineticText, SplitScreen, Collage, FocusRing, Arrow, LowerThird, HudFrame } from "./components/Cinematic";
import type { TextMode, Panel, SplitLayout, CollageItem } from "./components/Cinematic";

// Load Space Grotesk font for cinematic typography
const { fontFamily } = loadSpaceGrotesk(["400", "700"]);

// ---------------------------------------------------------------------------
// Animated Background — Gradient Mesh + Floating Orbs
// ---------------------------------------------------------------------------

// Parse hex color to RGB components
function hexToRgb(hex: string): { r: number; g: number; b: number } {
  const clean = hex.replace("#", "");
  const bigint = parseInt(clean.length === 3
    ? clean.split("").map(c => c + c).join("")
    : clean, 16);
  return { r: (bigint >> 16) & 255, g: (bigint >> 8) & 255, b: bigint & 255 };
}

// Detect if a color is "light" (for choosing grid/overlay treatment)
function isLightColor(hex: string): boolean {
  const { r, g, b } = hexToRgb(hex);
  return (r * 299 + g * 587 + b * 114) / 1000 > 128;
}

// Scrim painted behind a hero title. It has to wash *away* from the theme's
// text color: a dark scrim under a light theme's dark text drops the pair to
// ~3.4:1, which is the same legibility bug in reverse.
function heroScrim(theme: ThemeConfig): string {
  const { r, g, b } = hexToRgb(
    isLightColor(theme.backgroundColor) ? "#FFFFFF" : "#0F172A"
  );
  return (
    `radial-gradient(ellipse at center, rgba(${r},${g},${b},0.35) 0%, ` +
    `rgba(${r},${g},${b},0.55) 100%)`
  );
}

// Darken/lighten a color by mixing toward black or white
function shiftColor(hex: string, amount: number): string {
  const { r, g, b } = hexToRgb(hex);
  const clamp = (v: number) => Math.max(0, Math.min(255, Math.round(v)));
  if (amount < 0) {
    // Darken
    const f = 1 + amount;
    return `rgb(${clamp(r * f)}, ${clamp(g * f)}, ${clamp(b * f)})`;
  }
  // Lighten
  return `rgb(${clamp(r + (255 - r) * amount)}, ${clamp(g + (255 - g) * amount)}, ${clamp(b + (255 - b) * amount)})`;
}

const AnimatedBackground: React.FC<{ theme: ThemeConfig }> = ({ theme }) => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();

  const bg = theme.backgroundColor;
  const primary = theme.primaryColor;
  const accent = theme.accentColor;
  const surface = theme.surfaceColor;
  const light = isLightColor(bg);

  // Slow-moving gradient angles
  const angle1 = 135 + Math.sin(frame / (fps * 8)) * 30;

  // Build gradient from theme colors instead of hardcoded dark blue
  const { r: bgR, g: bgG, b: bgB } = hexToRgb(bg);
  const { r: priR, g: priG, b: priB } = hexToRgb(primary);
  const { r: accR, g: accG, b: accB } = hexToRgb(accent);

  const gradient = `
    radial-gradient(ellipse at ${30 + Math.sin(frame / (fps * 10)) * 20}% ${40 + Math.cos(frame / (fps * 8)) * 20}%,
      rgba(${priR}, ${priG}, ${priB}, 0.15) 0%, transparent 60%),
    radial-gradient(ellipse at ${70 + Math.cos(frame / (fps * 7)) * 20}% ${60 + Math.sin(frame / (fps * 9)) * 25}%,
      rgba(${accR}, ${accG}, ${accB}, 0.1) 0%, transparent 55%),
    linear-gradient(${angle1}deg, ${bg} 0%, ${shiftColor(bg, light ? -0.05 : 0.05)} 40%, ${surface} 70%, ${bg} 100%)
  `;

  // Floating orbs — derived from theme chart colors with low opacity
  const orbColors = theme.chartColors.slice(0, 5);
  const orbOpacity = light ? 0.06 : 0.08;
  const orbs = [
    { x: 20, y: 30, size: 300, color: orbColors[0] || primary, speedX: 7, speedY: 11 },
    { x: 70, y: 60, size: 250, color: orbColors[1] || accent, speedX: 9, speedY: 8 },
    { x: 40, y: 80, size: 200, color: orbColors[2] || primary, speedX: 13, speedY: 6 },
    { x: 80, y: 20, size: 350, color: orbColors[3] || accent, speedX: 11, speedY: 14 },
    { x: 10, y: 70, size: 180, color: orbColors[4] || primary, speedX: 8, speedY: 10 },
  ];

  // Grid and overlay colors adapt to light vs dark backgrounds
  const gridColor = light ? "rgba(0,0,0,0.03)" : "rgba(255,255,255,0.02)";
  const fadeColor = light
    ? `rgba(${bgR},${bgG},${bgB},0.2)`
    : `rgba(${bgR},${bgG},${bgB},0.4)`;

  return (
    <AbsoluteFill style={{ background: gradient }}>
      {/* Floating glow orbs */}
      {orbs.map((orb, i) => {
        const ox = orb.x + Math.sin(frame / (fps * orb.speedX)) * 15;
        const oy = orb.y + Math.cos(frame / (fps * orb.speedY)) * 12;
        const { r, g, b } = hexToRgb(orb.color);
        return (
          <div
            key={i}
            style={{
              position: "absolute",
              left: `${ox}%`,
              top: `${oy}%`,
              width: orb.size,
              height: orb.size,
              borderRadius: "50%",
              background: `rgba(${r}, ${g}, ${b}, ${orbOpacity})`,
              filter: `blur(${orb.size * 0.4}px)`,
              transform: "translate(-50%, -50%)",
              willChange: "transform",
            }}
          />
        );
      })}

      {/* Subtle grid overlay */}
      <div
        style={{
          position: "absolute",
          inset: 0,
          backgroundImage: `
            linear-gradient(${gridColor} 1px, transparent 1px),
            linear-gradient(90deg, ${gridColor} 1px, transparent 1px)
          `,
          backgroundSize: "60px 60px",
          opacity: 0.5 + Math.sin(frame / (fps * 20)) * 0.2,
        }}
      />

      {/* Top gradient fade for depth */}
      <div
        style={{
          position: "absolute",
          top: 0,
          left: 0,
          right: 0,
          height: "30%",
          background: `linear-gradient(to bottom, ${fadeColor}, transparent)`,
        }}
      />
    </AbsoluteFill>
  );
};

// ---------------------------------------------------------------------------
// Types — aligned with edit_decisions artifact schema
// ---------------------------------------------------------------------------

interface Cut {
  id: string;
  source: string;
  in_seconds: number;
  out_seconds: number;
  layer?: string;
  type?: string;
  // Component-specific props
  text?: string;
  stat?: string;
  subtitle?: string;
  callout_type?: "info" | "warning" | "tip" | "quote";
  title?: string;
  // Video source trim — seek to this point in the source before playback.
  // Defaults to 0 (play from beginning). Use this instead of in_seconds for source trimming.
  source_in_seconds?: number;
  // Comparison props
  leftLabel?: string;
  rightLabel?: string;
  leftValue?: string;
  rightValue?: string;
  // Chart props
  chartData?: any[];
  chartSeries?: any[];
  chartColors?: string[];
  chartAnimation?: string;
  donut?: boolean;
  centerLabel?: string;
  centerValue?: string;
  showGrid?: boolean;
  showValues?: boolean;
  showLegend?: boolean;
  showMarkers?: boolean;
  xLabel?: string;
  yLabel?: string;
  columns?: 2 | 3 | 4;
  // Progress bar props
  progress?: number;
  progressLabel?: string;
  progressColor?: string;
  progressAnimation?: string;
  progressSegments?: any[];
  // Hero title props (when used as scene, not overlay)
  heroSubtitle?: string;
  // Styling overrides
  backgroundColor?: string;
  cardBackgroundColor?: string; // Inner card surface (comparison); defaults to theme.surfaceColor
  backgroundImage?: string; // AI-generated or stock image rendered behind the component
  backgroundVideo?: string; // Video clip rendered behind the component (takes priority over backgroundImage)
  backgroundVideoStart?: number; // Seek position in seconds for background video (default 0)
  backgroundOverlay?: number; // Opacity of dark overlay on backgroundImage/backgroundVideo (0-1, default 0.55)
  /**
   * Camera move on backgroundImage. Scale zooms toward `origin` (percent of the frame,
   * the object the camera "points at"); x/y translate in percent of the frame.
   * Omitted: the default subtle 8% push-in.
   */
  backgroundMotion?: {
    origin?: { x: number; y: number };
    from?: { scale?: number; x?: number; y?: number };
    to?: { scale?: number; x?: number; y?: number };
  };
  /**
   * Camera move (id from lib/motion-catalog.json, e.g. "dolly_in", "whip_pan_left",
   * or a custom spec). Applies to the background and, damped by parallax, to the content.
   */
  camera?: CameraInput;
  /** Effects stack: ["film_grain", {"type":"vignette","strength":0.5}, "grade_teal_orange"] */
  fx?: FxItem[];
  /** Second image for double_exposure */
  imageB?: string;
  // kinetic_text
  textMode?: TextMode;
  highlight?: string[];
  uppercase?: boolean;
  // split_screen / collage
  panels?: Panel[];
  layout?: SplitLayout;
  gap?: number;
  items?: CollageItem[];
  /** scale_comparison: props of ScaleWorld (items, viewFrom, viewTo, bands, marks...) */
  scale?: Omit<ScaleWorldProps, "color" | "accentColor" | "fontFamily">;
  /** bone_section */
  label?: string;
  sublabel?: string;
  color?: string;
  accentColor?: string;
  fontSize?: number;
  // Animation & transitions
  animation?: string;
  transition_in?: string;
  transition_out?: string;
  transition_duration?: number;
  transform?: {
    animation?: string;
    scale?: number;
    position?: string | { x: number; y: number };
  };
  // Anime scene props (type: "anime_scene")
  images?: string[];
  particles?: ParticleType;
  particleColor?: string;
  particleCount?: number;
  particleIntensity?: number;
  vignette?: boolean;
  lightingFrom?: string;
  lightingTo?: string;
  // Terminal scene props (type: "terminal_scene")
  steps?: TerminalStep[];
  terminalTitle?: string;
  prompt?: string;
  // Screenshot scene props (type: "screenshot_scene")
  screenshotSteps?: ScreenshotStep[];
  screenshotSize?: { width: number; height: number };
  cursorStartAt?: [number, number];
}

interface Overlay {
  type: "section_title" | "stat_reveal" | "hero_title" | "provider_chip" | "focus_ring" | "arrow" | "lower_third" | "hud_frame";
  in_seconds: number;
  out_seconds: number;
  text?: string;
  subtitle?: string;
  accentColor?: string;
  position?: string;
  // provider_chip
  providers?: string[];
  cycleSeconds?: number;
  label?: string;
  // focus_ring / arrow
  x?: number;
  y?: number;
  radius?: number;
  shape?: "circle" | "square";
  side?: "right" | "left" | "top" | "bottom";
  angle?: number;
  color?: string;
}

interface AudioLayer {
  src: string;
  volume?: number;
}

interface AudioConfig {
  narration?: AudioLayer;
  music?: AudioLayer & {
    fadeInSeconds?: number;
    fadeOutSeconds?: number;
    /** Start playback from this offset in seconds (skip quiet intros).
     *  Use the audio_energy tool to find the optimal offset. */
    offsetSeconds?: number;
    /** Loop the music if it's shorter than the video duration. */
    loop?: boolean;
  };
}

export interface ExplainerProps {
  [key: string]: unknown;
  cuts: Cut[];
  overlays?: Overlay[];
  captions?: WordCaption[];
  audio?: AudioConfig;
  /** Effects applied to every scene (e.g. film_grain, vignette, letterbox). */
  fx?: FxItem[];
  /** Give background scenes without a camera a rotating default move. */
  autoCamera?: boolean | string[];
  /** Default transition between cuts when a cut does not declare one. */
  defaultTransition?: string;
  defaultTransitionSeconds?: number;
}

// ---------------------------------------------------------------------------
// Image Extensions
// ---------------------------------------------------------------------------

const IMAGE_EXTENSIONS = [".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".tif", ".webp"];
const VIDEO_EXTENSIONS = [".mp4", ".mov", ".webm", ".avi", ".mkv"];

function isImage(source: string): boolean {
  const lower = source.toLowerCase();
  return IMAGE_EXTENSIONS.some((ext) => lower.endsWith(ext));
}

function isVideo(source: string): boolean {
  const lower = source.toLowerCase();
  return VIDEO_EXTENSIONS.some((ext) => lower.endsWith(ext));
}

// ---------------------------------------------------------------------------
// Cinematic vignette overlay
// ---------------------------------------------------------------------------

const Vignette: React.FC = () => (
  <AbsoluteFill
    style={{
      background:
        "radial-gradient(ellipse at center, transparent 50%, rgba(0,0,0,0.6) 100%)",
      pointerEvents: "none",
    }}
  />
);

// ---------------------------------------------------------------------------
// Enhanced Image Scene — spring physics, parallax, variety
// ---------------------------------------------------------------------------

const ImageScene: React.FC<{ cut: Cut; src: string; animation?: string }> = ({ cut, src, animation }) => (
  <Stage
    src={src}
    srcB={cut.imageB}
    camera={cut.camera ?? (cut.backgroundMotion ? legacyMotionToSpec(cut.backgroundMotion) : undefined)}
    legacyAnimation={cut.camera || cut.backgroundMotion ? undefined : animation || "zoom-in"}
    fx={cut.fx}
    backgroundColor="#0F172A"
  />
);

const VideoScene: React.FC<{ cut: Cut; src: string; startFrom?: number }> = ({ cut, src, startFrom = 0 }) => (
  <Stage
    video={{ src, startFrom }}
    camera={cut.camera}
    fx={cut.fx}
    backgroundColor={cut.backgroundColor ?? "#0F172A"}
  />
);

// ---------------------------------------------------------------------------
// Scene renderer — maps cut type / source to the right component
// ---------------------------------------------------------------------------

const SceneRenderer: React.FC<{ cut: Cut; theme: ThemeConfig }> = ({ cut, theme }) => {
  // Wrap component with background video or image if specified
  const maybeWrapWithBg = (element: React.ReactElement) => {
    const hasBg = !!(cut.backgroundVideo || cut.backgroundImage);
    // Backgrounds, a camera move, or fx all go through Stage so content gets
    // parallax + the cinematic overlay stack.
    if (hasBg || cut.camera || (cut.fx && cut.fx.length)) {
      return (
        <Stage
          src={cut.backgroundVideo ? undefined : cut.backgroundImage}
          video={cut.backgroundVideo ? { src: cut.backgroundVideo, startFrom: cut.backgroundVideoStart ?? 0 } : undefined}
          srcB={cut.imageB}
          camera={cut.camera ?? (cut.backgroundMotion ? legacyMotionToSpec(cut.backgroundMotion) : hasBg ? { from: { s: 1 }, to: { s: 1.08 }, ease: "linear" } : undefined)}
          fx={cut.fx}
          overlayOpacity={hasBg ? cut.backgroundOverlay ?? 0.55 : 0}
        >
          {element}
        </Stage>
      );
    }
    return element;
  };

  // Resolve the scene element based on cut type, then wrap with backgroundImage if set
  // Use transparent bg so the animated gradient background shows through
  // When no explicit backgroundColor on the cut, inherit from theme
  const rawBg = (cut.backgroundImage || cut.backgroundVideo) ? "transparent" : (cut.backgroundColor || theme.surfaceColor);
  const bgColor = (rawBg === theme.backgroundColor || rawBg === "#0F172A" || rawBg === "#0f172a") ? "transparent" : rawBg;
  const textColor = cut.color || theme.textColor;
  const accent = cut.accentColor || theme.accentColor;

  // Explicit component types — use theme-derived defaults for colors
  if (cut.type === "text_card" && cut.text) {
    return maybeWrapWithBg(
      <TextCard text={cut.text} fontSize={cut.fontSize} color={textColor} backgroundColor={bgColor} />
    );
  }
  if (cut.type === "stat_card" && cut.stat) {
    return maybeWrapWithBg(
      <StatCard stat={cut.stat} subtitle={cut.subtitle} accentColor={accent} backgroundColor={bgColor} />
    );
  }
  if (cut.type === "callout" && cut.text) {
    return maybeWrapWithBg(
      <CalloutBox
        text={cut.text} type={cut.callout_type} title={cut.title}
        borderColor={accent} backgroundColor={cut.backgroundColor || theme.surfaceColor}
        textColor={textColor} containerBackgroundColor={bgColor}
      />
    );
  }
  if (cut.type === "comparison" && cut.leftLabel && cut.rightLabel && cut.leftValue && cut.rightValue) {
    return maybeWrapWithBg(
      <ComparisonCard
        leftLabel={cut.leftLabel} rightLabel={cut.rightLabel}
        leftValue={cut.leftValue} rightValue={cut.rightValue}
        title={cut.title} backgroundColor={bgColor} textColor={textColor}
        cardBackgroundColor={cut.cardBackgroundColor || theme.surfaceColor}
      />
    );
  }
  if (cut.type === "hero_title" && cut.text) {
    return maybeWrapWithBg(
      <HeroTitle
        title={cut.text}
        subtitle={cut.heroSubtitle || cut.subtitle}
        accentColor={accent}
        textColor={textColor}
        subtitleColor={theme.mutedTextColor}
        scrimBackground={heroScrim(theme)}
      />
    );
  }
  if (cut.type === "terminal_scene" && cut.steps) {
    return maybeWrapWithBg(
      <TerminalScene
        title={cut.terminalTitle || "Terminal"}
        steps={cut.steps as TerminalStep[]}
        prompt={cut.prompt}
        accentColor={accent}
        backgroundColor={bgColor || theme.backgroundColor}
      />
    );
  }
  if (cut.type === "screenshot_scene" && cut.backgroundImage && cut.screenshotSteps) {
    return (
      <ScreenshotScene
        backgroundImage={cut.backgroundImage}
        backgroundSize={cut.screenshotSize}
        steps={cut.screenshotSteps as ScreenshotStep[]}
        accentColor={accent}
        cursorStartAt={cut.cursorStartAt}
      />
    );
  }

  // --- Chart types — use theme.chartColors as default palette ---
  if (cut.type === "bar_chart" && cut.chartData) {
    return maybeWrapWithBg(
      <BarChart
        data={cut.chartData} title={cut.title} colors={cut.chartColors || theme.chartColors}
        animationStyle={(cut.chartAnimation as any) || "grow-up"}
        showGrid={cut.showGrid} showValues={cut.showValues} backgroundColor={bgColor}
        textColor={textColor}
      />
    );
  }
  if (cut.type === "line_chart" && cut.chartSeries) {
    return maybeWrapWithBg(
      <LineChart
        series={cut.chartSeries} title={cut.title} colors={cut.chartColors || theme.chartColors}
        animationStyle={(cut.chartAnimation as any) || "draw"}
        showGrid={cut.showGrid} showMarkers={cut.showMarkers} showLegend={cut.showLegend}
        xLabel={cut.xLabel} yLabel={cut.yLabel} backgroundColor={bgColor}
        textColor={textColor}
      />
    );
  }
  if (cut.type === "pie_chart" && cut.chartData) {
    return maybeWrapWithBg(
      <PieChart
        data={cut.chartData} title={cut.title} colors={cut.chartColors || theme.chartColors}
        animationStyle={(cut.chartAnimation as any) || "expand"}
        donut={cut.donut} centerLabel={cut.centerLabel} centerValue={cut.centerValue}
        showLegend={cut.showLegend} backgroundColor={bgColor}
        textColor={textColor}
      />
    );
  }
  if (cut.type === "kpi_grid" && cut.chartData) {
    return maybeWrapWithBg(
      <KPIGrid
        metrics={cut.chartData} title={cut.title} columns={cut.columns}
        colors={cut.chartColors || theme.chartColors} animationStyle={(cut.chartAnimation as any) || "count-up"}
        backgroundColor={bgColor}
        textColor={textColor}
      />
    );
  }
  if (cut.type === "progress_bar" && cut.progress !== undefined) {
    return maybeWrapWithBg(
      <AbsoluteFill
        style={{
          background: bgColor || theme.surfaceColor,
          display: "flex", alignItems: "center", justifyContent: "center",
          padding: "80px 120px",
        }}
      >
        {cut.title && (
          <div style={{
            position: "absolute", top: 120, fontSize: 48, fontWeight: 700,
            color: textColor, textAlign: "center", width: "100%",
          }}>
            {cut.title}
          </div>
        )}
        <ProgressBar
          progress={cut.progress} label={cut.progressLabel}
          color={cut.progressColor || accent}
          animationStyle={(cut.progressAnimation as any) || "fill"}
          segments={cut.progressSegments} backgroundColor={cut.backgroundColor || theme.surfaceColor}
        />
      </AbsoluteFill>
    );
  }

  // --- Cinematic scene types ---
  if (cut.type === "kinetic_text" && cut.text) {
    return maybeWrapWithBg(
      <KineticText
        text={cut.text} mode={cut.textMode} fontSize={cut.fontSize} color={textColor} accentColor={accent}
        highlight={cut.highlight} uppercase={cut.uppercase} fontFamily={[theme.headingFont, fontFamily, "sans-serif"].filter(Boolean).join(", ")}
      />
    );
  }
  if (cut.type === "split_screen" && cut.panels && cut.panels.length) {
    return <SplitScreen panels={cut.panels} layout={cut.layout} gap={cut.gap} accentColor={accent} background={cut.backgroundColor} />;
  }
  if (cut.type === "collage" && cut.items && cut.items.length) {
    return <Collage items={cut.items} accentColor={accent} background={cut.backgroundColor} />;
  }
  if (cut.type === "scale_comparison" && cut.scale) {
    return (
      <Stage
        camera={cut.camera}
        fx={cut.fx}
        world={<ScaleWorld {...cut.scale} color={textColor} accentColor={accent} fontFamily={[theme.headingFont, fontFamily, "sans-serif"].filter(Boolean).join(", ")} />}
      />
    );
  }
  if (cut.type === "bone_section") {
    return (
      <Stage
        camera={cut.camera}
        fx={cut.fx}
        world={<BoneSection color={textColor} accentColor={accent} label={cut.label} sublabel={cut.sublabel} fontFamily={[theme.headingFont, fontFamily, "sans-serif"].filter(Boolean).join(", ")} />}
      />
    );
  }
  if (cut.type === "double_exposure" && cut.source && cut.imageB) {
    return (
      <Stage
        src={cut.source} srcB={cut.imageB} camera={cut.camera ?? "dolly_in"}
        fx={[{ type: "double_exposure", blend: "screen" }, ...(cut.fx ?? [])]} backgroundColor="#0F172A"
      />
    );
  }

  // --- Anime scene (multi-image crossfade + particles) ---
  if (cut.type === "anime_scene" && cut.images && cut.images.length > 0) {
    return (
      <AnimeScene
        images={cut.images}
        animation={(cut.animation as CameraMotion) || "ken-burns"}
        particles={cut.particles}
        particleColor={cut.particleColor}
        particleCount={cut.particleCount}
        particleIntensity={cut.particleIntensity}
        backgroundColor={cut.backgroundColor}
        vignette={cut.vignette ?? true}
        lightingFrom={cut.lightingFrom}
        lightingTo={cut.lightingTo}
        sceneDurationSeconds={cut.out_seconds - cut.in_seconds}
      />
    );
  }

  // --- Media types (image / video fallback) ---
  const animation = cut.animation || cut.transform?.animation;

  if (cut.source && isImage(cut.source) && !cut.backgroundImage && !cut.backgroundVideo) {
    return <ImageScene cut={cut} src={cut.source} animation={animation} />;
  }

  if (cut.source && isVideo(cut.source)) {
    return <VideoScene cut={cut} src={cut.source} startFrom={cut.source_in_seconds ?? 0} />;
  }

  // Final fallback — try as image if source exists, otherwise show text_card
  if (cut.source && !cut.backgroundImage && !cut.backgroundVideo) {
    return <ImageScene cut={cut} src={cut.source} animation={animation} />;
  }

  // No source, no type — render as text card with cut id as fallback
  return <TextCard text={cut.text || cut.id} color={textColor} backgroundColor={bgColor} />;
};

// ---------------------------------------------------------------------------
// Overlay renderer
// ---------------------------------------------------------------------------

const OverlayRenderer: React.FC<{ overlay: Overlay; theme: ThemeConfig }> = ({
  overlay,
  theme,
}) => {
  if (overlay.type === "section_title") {
    return (
      <SectionTitle
        title={overlay.text ?? ""}
        subtitle={overlay.subtitle}
        accentColor={overlay.accentColor || theme.accentColor}
        textColor={theme.textColor}
        position={(overlay.position as any) || "top-left"}
      />
    );
  }
  if (overlay.type === "stat_reveal") {
    return (
      <StatReveal
        stat={overlay.text ?? ""}
        label={overlay.subtitle}
        accentColor={overlay.accentColor || theme.accentColor}
        textColor={theme.textColor}
        position={(overlay.position as any) || "bottom-right"}
      />
    );
  }
  if (overlay.type === "hero_title") {
    return (
      <HeroTitle
        title={overlay.text ?? ""}
        subtitle={overlay.subtitle}
        accentColor={overlay.accentColor || theme.accentColor}
        textColor={theme.textColor}
        subtitleColor={theme.mutedTextColor}
        scrimBackground={heroScrim(theme)}
      />
    );
  }
  if (overlay.type === "focus_ring") {
    return <FocusRing x={overlay.x} y={overlay.y} radius={overlay.radius} label={overlay.text ?? overlay.label} color={overlay.color ?? overlay.accentColor ?? theme.accentColor} shape={overlay.shape} side={overlay.side} />;
  }
  if (overlay.type === "arrow") {
    return <Arrow x={overlay.x} y={overlay.y} label={overlay.text ?? overlay.label} color={overlay.color ?? overlay.accentColor ?? theme.accentColor} angle={overlay.angle} />;
  }
  if (overlay.type === "lower_third") {
    return <LowerThird text={overlay.text ?? ""} subtitle={overlay.subtitle} color={overlay.color ?? overlay.accentColor ?? theme.accentColor} />;
  }
  if (overlay.type === "hud_frame") {
    return <HudFrame label={overlay.text ?? overlay.label} color={overlay.color ?? overlay.accentColor ?? theme.accentColor} />;
  }
  if (overlay.type === "provider_chip" && overlay.providers) {
    return (
      <ProviderChip
        providers={overlay.providers as string[]}
        cycleSeconds={overlay.cycleSeconds}
        position={(overlay.position as any) || "bottom-right"}
        accentColor={overlay.accentColor}
        label={overlay.label}
      />
    );
  }
  return null;
};

// ---------------------------------------------------------------------------
// Main composition
// ---------------------------------------------------------------------------

export const Explainer: React.FC<ExplainerProps> = (props) => {
  const { cuts, overlays, captions, audio } = props;
  const { fps, durationInFrames } = useVideoConfig();

  // Resolve theme from props — playbook name, theme name, or custom themeConfig
  const theme = resolveTheme(props as Record<string, unknown>);

  return (
    <AbsoluteFill style={{ background: theme.backgroundColor, fontFamily: [theme.headingFont, fontFamily, "sans-serif"].filter(Boolean).join(", ") }}>
      {/* Layer 0: Animated gradient background — driven by theme */}
      <AnimatedBackground theme={theme} />

      {/* Layer 1: Visual scenes (overlapped for transitions) */}
      {cuts.map((cut, i) => {
        const prev = cuts[i - 1];
        const next = cuts[i + 1];
        const trFrames = (c: Cut, nx: Cut | undefined) => {
          const style = normalizeTransition(
            nx ? nx.transition_in || c.transition_out || props.defaultTransition : c.transition_out
          );
          const secs = (nx?.transition_duration ?? c.transition_duration ?? props.defaultTransitionSeconds ?? 0.4);
          return { style, frames: Math.max(2, Math.round(secs * fps)) } as TransitionSpec;
        };
        const inT = prev ? trFrames(prev, cut) : undefined;
        const outT = next ? trFrames(cut, next) : undefined;
        const inHalf = inT && inT.style !== "cut" ? Math.round(inT.frames / 2) : 0;
        const outHalf = outT && outT.style !== "cut" ? Math.round(outT.frames / 2) : 0;
        const baseFrom = Math.round(cut.in_seconds * fps);
        const baseEnd = Math.round(cut.out_seconds * fps);
        const from = Math.max(0, baseFrom - inHalf);
        const duration = baseEnd + outHalf - from;

        // Auto camera: background scenes without a camera get a rotating default move.
        const autoList = Array.isArray(props.autoCamera) ? props.autoCamera : ["dolly_in", "pan_right", "zoom_in_slow", "tilt_up", "pan_left", "ken_burns"];
        const hasBg = !!(cut.backgroundImage || cut.backgroundVideo || (cut.source && !cut.type));
        const withDefaults: Cut = {
          ...cut,
          camera: cut.camera ?? (props.autoCamera && hasBg && !cut.backgroundMotion ? autoList[i % autoList.length] : undefined),
          fx: [...normalizeFx(props.fx), ...normalizeFx(cut.fx)] as FxItem[],
        };
        return (
          <Sequence key={cut.id} from={from} durationInFrames={duration}>
            <SceneTimingContext.Provider value={duration}>
              <TransitionShell inT={inT} outT={outT} seqFrames={duration}>
                <SceneRenderer cut={withDefaults} theme={theme} />
              </TransitionShell>
            </SceneTimingContext.Provider>
          </Sequence>
        );
      })}

      {/* Layer 2: Overlays (section titles, stat reveals, hero titles) */}
      {overlays?.map((overlay, i) => {
        const from = Math.round(overlay.in_seconds * fps);
        const duration = Math.round(
          (overlay.out_seconds - overlay.in_seconds) * fps
        );

        return (
          <Sequence key={`overlay-${i}`} from={from} durationInFrames={duration}>
            <OverlayRenderer overlay={overlay} theme={theme} />
          </Sequence>
        );
      })}

      {/* Layer 3: Captions (word-by-word highlight) */}
      {captions && captions.length > 0 && (
        <CaptionOverlay
          words={captions}
          wordsPerPage={6}
          fontSize={42}
          color={theme.textColor}
          highlightColor={theme.captionHighlightColor}
          backgroundColor={theme.captionBackgroundColor}
        />
      )}

      {/* Layer 4: Audio — narration */}
      {audio?.narration?.src && (
        <Audio src={resolveAsset(audio.narration.src)} volume={audio.narration.volume ?? 1} />
      )}

      {/* Layer 4: Audio — music with offset, fade in/out, and optional loop */}
      {audio?.music?.src && (
        <Audio
          src={resolveAsset(audio.music.src)}
          startFrom={Math.round((audio.music.offsetSeconds ?? 0) * fps)}
          loop={audio.music.loop ?? false}
          loopVolumeCurveBehavior="repeat"
          volume={(f) => {
            const baseVol = audio.music!.volume ?? 0.1;
            const fadeInDur = (audio.music!.fadeInSeconds ?? 2) * fps;
            const fadeOutDur = (audio.music!.fadeOutSeconds ?? 3) * fps;
            const totalFrames = durationInFrames;

            // Fade in
            const fadeIn = interpolate(f, [0, fadeInDur], [0, baseVol], {
              extrapolateLeft: "clamp",
              extrapolateRight: "clamp",
            });
            // Fade out
            const fadeOut = interpolate(
              f,
              [totalFrames - fadeOutDur, totalFrames],
              [baseVol, 0],
              { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
            );
            return Math.min(fadeIn, fadeOut);
          }}
        />
      )}
    </AbsoluteFill>
  );
};
