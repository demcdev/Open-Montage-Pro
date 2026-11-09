import React from "react";
import { AbsoluteFill } from "remotion";
import { COLORS, HEIGHT, WIDTH } from "./tokens";

// Night background: a radial glow over a faint grid. Every shot of the channel sits on it.
export const Backdrop: React.FC<{ grid?: boolean }> = ({ grid = true }) => (
  <AbsoluteFill style={{ background: `radial-gradient(ellipse 75% 70% at 50% 40%, ${COLORS.nightGlow}, ${COLORS.night})` }}>
    {grid ? (
      <AbsoluteFill
        style={{
          opacity: 0.7,
          backgroundImage: `linear-gradient(${COLORS.grid} 1px, transparent 1px), linear-gradient(90deg, ${COLORS.grid} 1px, transparent 1px)`,
          backgroundSize: "96px 96px",
        }}
      />
    ) : null}
  </AbsoluteFill>
);

// Full-frame SVG layer with the glow filter the kit's drawings use (filter="url(#glow)").
export const Stage: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <svg width={WIDTH} height={HEIGHT} style={{ position: "absolute", inset: 0 }}>
    <defs>
      <filter id="glow" x="-50%" y="-50%" width="200%" height="200%">
        <feGaussianBlur stdDeviation="9" result="blur" />
        <feMerge>
          <feMergeNode in="blur" />
          <feMergeNode in="SourceGraphic" />
        </feMerge>
      </filter>
    </defs>
    {children}
  </svg>
);
