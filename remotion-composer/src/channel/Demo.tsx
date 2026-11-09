import React from "react";
import { AbsoluteFill, useCurrentFrame } from "remotion";
import { Backdrop, Stage } from "./Backdrop";
import { EndCard } from "./EndCard";
import { Figure } from "./Figure";
import { Arrow, Check, Cross, Swap } from "./Icons";
import { Viewer } from "./Viewer";
import { COLORS } from "./tokens";
import { Scene, at, pop, ramp } from "./timing";

// Every piece of the kit on screen once, to check the look after a change.
export const CHANNEL_KIT_DEMO_FRAMES = at(7);

const Comparison: React.FC = () => {
  const frame = useCurrentFrame();
  return (
    <>
      <Backdrop />
      <Stage>
        <Viewer x={330} y={900} drawn={ramp(frame, 0, 0.8)} point={70 * ramp(frame, 1, 1.4)} blink={frame > at(2.2) && frame < at(2.4) ? 1 : 0} />
        <Arrow x={520} y={600} toX={940} toY={600} drawn={ramp(frame, 1.2, 1.8)} />
        <Check x={1180} y={620} size={pop(frame, 1.8)} />
        <Cross x={1540} y={620} size={pop(frame, 2.1)} />
      </Stage>
      <Figure value="×12" x={1050} y={190} size={200} scale={pop(frame, 1.5)} />
    </>
  );
};

const Trade: React.FC = () => {
  const frame = useCurrentFrame();
  return (
    <>
      <Backdrop />
      <Stage>
        <Viewer x={520} y={860} drawn={1} />
        <Viewer x={1400} y={860} facing={-1} drawn={1} />
        <Swap x={960} y={520} size={1.4 * pop(frame, 3.3)} />
      </Stage>
      <Figure value="16" x={1290} y={160} size={150} color={COLORS.gold} opacity={ramp(frame, 3.6, 3.9)} />
      <Figure value="3" x={480} y={160} size={150} opacity={ramp(frame, 3.6, 3.9)} />
    </>
  );
};

const Fish = <path d="M-200 10 Q-70 -60 60 -34 L92 -104 L116 -28 Q176 -16 206 -62 L190 10 L212 66 Q160 34 112 32 Q0 66 -200 10 Z" />;
const Planet = (
  <>
    <circle r={130} />
    <ellipse rx={220} ry={46} fill="none" />
  </>
);

export const ChannelKitDemo: React.FC = () => (
  <AbsoluteFill style={{ backgroundColor: COLORS.night }}>
    <Scene from={0} to={3}>
      <Comparison />
    </Scene>
    <Scene from={3} to={4.8}>
      <Trade />
    </Scene>
    <Scene from={4.8} to={7}>
      <EndCard from={4.8} topics={[Fish, Planet]} fadeOut={6.3} />
    </Scene>
  </AbsoluteFill>
);
