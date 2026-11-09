import React from "react";
import { AbsoluteFill, useCurrentFrame } from "remotion";
import { Backdrop, Stage } from "./Backdrop";
import { Figure } from "./Figure";
import { Viewer } from "./Viewer";
import { COLORS } from "./tokens";
import { at, pop, ramp } from "./timing";

// The channel's close: the viewer faces the possible next topics, each a silhouette with a
// "?", and an arrow points down to the comments. `from` is the second the card starts.
// Pass up to three silhouettes as SVG drawings centered on (0, 0), about 400 px wide.
export const EndCard: React.FC<{ from: number; topics: React.ReactNode[]; fadeOut?: number }> = ({ from, topics, fadeOut }) => {
  const frame = useCurrentFrame();
  const slots = [680, 1180, 1680].slice(0, topics.length);
  const arrowAt = from + 0.4 + topics.length * 0.2;
  const bounce = frame >= at(arrowAt) ? Math.abs(Math.sin((frame - at(arrowAt)) / 7)) * 30 : 0;
  return (
    <AbsoluteFill>
      <Backdrop />
      <Stage>
        <Viewer x={260} y={900} scale={0.9} drawn={ramp(frame, from, from + 0.5)} point={70 * ramp(frame, from + 0.3, from + 0.6)} />
        {topics.map((topic, index) => (
          <g key={index} transform={`translate(${slots[index]} 470) scale(${pop(frame, from + 0.2 + index * 0.2)})`} fill={COLORS.fill} stroke={COLORS.cyanDeep} strokeWidth={6} filter="url(#glow)">
            {topic}
          </g>
        ))}
        <g opacity={ramp(frame, arrowAt, arrowAt + 0.3)} transform={`translate(${slots.reduce((sum, x) => sum + x, 0) / slots.length} ${860 + bounce})`} filter="url(#glow)">
          <path d="M-22 -100 H22 V0 H70 L0 86 L-70 0 H-22 Z" fill={COLORS.gold} />
        </g>
      </Stage>
      {slots.map((x, index) => (
        <Figure key={x} value="?" x={x - 35} y={180} size={120} color={COLORS.gold} scale={pop(frame, from + 0.2 + index * 0.2)} />
      ))}
      {fadeOut !== undefined ? <AbsoluteFill style={{ background: COLORS.night, opacity: ramp(frame, fadeOut, fadeOut + 0.6) }} data-layout-ignore /> : null}
    </AbsoluteFill>
  );
};
