// Icons for the No-Text Rule. Right and wrong never rely on color alone: the ✓ and ✗ shapes
// carry the meaning too. Draw them inside <Stage>, centered on (x, y).
import React from "react";
import { COLORS } from "./tokens";

type Placed = { x: number; y: number; size?: number; opacity?: number };

const Card: React.FC<{ color: string; children: React.ReactNode }> = ({ color, children }) => (
  <>
    <rect x={-130} y={-150} width={260} height={300} rx={28} fill={COLORS.fill} stroke={color} strokeWidth={6} />
    {children}
  </>
);

export const Check: React.FC<Placed & { card?: boolean }> = ({ x, y, size = 1, opacity = 1, card = true }) => {
  const mark = <path d="M-60 4 L-14 52 L70 -50" fill="none" stroke={COLORS.cyan} strokeWidth={16} strokeLinecap="round" strokeLinejoin="round" />;
  return (
    <g transform={`translate(${x} ${y}) scale(${size})`} opacity={opacity} filter="url(#glow)">
      {card ? <Card color={COLORS.cyan}>{mark}</Card> : mark}
    </g>
  );
};

export const Cross: React.FC<Placed & { card?: boolean }> = ({ x, y, size = 1, opacity = 1, card = true }) => {
  const mark = <path d="M-58 -58 L58 58 M58 -58 L-58 58" stroke={COLORS.magenta} strokeWidth={16} strokeLinecap="round" />;
  return (
    <g transform={`translate(${x} ${y}) scale(${size})`} opacity={opacity} filter="url(#glow)">
      {card ? <Card color={COLORS.magenta}>{mark}</Card> : mark}
    </g>
  );
};

// A dotted arrow from (x, y) to (toX, toY); drawn 0..1 grows it from the tail.
export const Arrow: React.FC<{ x: number; y: number; toX: number; toY: number; drawn?: number; color?: string }> = ({ x, y, toX, toY, drawn = 1, color = COLORS.text }) => {
  const endX = x + (toX - x) * drawn;
  const endY = y + (toY - y) * drawn;
  const angle = (Math.atan2(toY - y, toX - x) * 180) / Math.PI;
  return (
    <g filter="url(#glow)" stroke={color} strokeWidth={8} strokeLinecap="round" fill="none" opacity={drawn > 0 ? 1 : 0}>
      <path d={`M${x} ${y} L${endX} ${endY}`} strokeDasharray="2 26" />
      <path d="M-30 -30 L0 0 L-30 30" strokeLinejoin="round" transform={`translate(${endX} ${endY}) rotate(${angle})`} />
    </g>
  );
};

// ⇄: a trade or a swap between two things.
export const Swap: React.FC<Placed> = ({ x, y, size = 1, opacity = 1 }) => (
  <g transform={`translate(${x} ${y}) scale(${size})`} opacity={opacity} filter="url(#glow)" stroke={COLORS.gold} strokeWidth={12} strokeLinecap="round" strokeLinejoin="round" fill="none">
    <path d="M-80 -30 H80 M50 -60 L80 -30 L50 0" />
    <path d="M80 30 H-80 M-50 0 L-80 30 L-50 60" />
  </g>
);
