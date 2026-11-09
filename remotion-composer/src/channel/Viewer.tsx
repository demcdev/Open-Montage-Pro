import React from "react";
import { COLORS } from "./tokens";

// You. The No-Text Rule keeps "tú" off the screen, so the viewer is this figure: the only
// cyan body with a magenta eye. Draw it inside <Stage>; (x, y) is where its feet touch the ground.
export const Viewer: React.FC<{
  x: number;
  y: number;
  scale?: number;
  // 1 faces right, -1 faces left.
  facing?: 1 | -1;
  // 0..1: outlines draw on first, the fill follows.
  drawn?: number;
  // 0..1: the eye closes.
  blink?: number;
  // Arm angle in degrees; 0 rests along the body, 70 points ahead.
  point?: number;
}> = ({ x, y, scale = 1, facing = 1, drawn = 1, blink = 0, point = 0 }) => {
  const outline = { stroke: COLORS.cyan, strokeWidth: 8, fill: COLORS.fill, pathLength: 1, strokeDasharray: 1, strokeDashoffset: 1 - drawn };
  return (
    <g transform={`translate(${x} ${y}) scale(${scale * facing} ${scale})`} filter="url(#glow)" strokeLinecap="round" strokeLinejoin="round">
      <rect x={-96} y={-264} width={192} height={264} rx={80} {...outline} />
      <circle cy={-354} r={80} {...outline} />
      <g transform={`translate(112 -226) rotate(${-point})`}>
        <path d="M0 0 L0 120" stroke={COLORS.cyan} strokeWidth={22} opacity={drawn} />
      </g>
      <ellipse cx={30} cy={-362} rx={13} ry={13 * (1 - blink) + 1} fill={COLORS.magenta} opacity={drawn} />
    </g>
  );
};
