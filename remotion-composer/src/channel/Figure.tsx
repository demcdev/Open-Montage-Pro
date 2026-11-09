import React from "react";
import { COLORS, FONT } from "./tokens";

// A number on screen (the only "text" the No-Text Rule allows). (x, y) is its top-left corner.
export const Figure: React.FC<{ value: string; x: number; y: number; size: number; color?: string; opacity?: number; scale?: number }> = ({
  value,
  x,
  y,
  size,
  color = COLORS.text,
  opacity = 1,
  scale = 1,
}) => (
  <div
    style={{
      position: "absolute",
      left: x,
      top: y,
      fontFamily: FONT,
      fontWeight: 700,
      fontSize: size,
      lineHeight: 1,
      letterSpacing: "-0.02em",
      color,
      opacity,
      transform: `scale(${scale})`,
      transformOrigin: "left center",
      textShadow: `0 0 18px ${color}99, 0 0 42px ${color}55`,
    }}
  >
    {value}
  </div>
);
