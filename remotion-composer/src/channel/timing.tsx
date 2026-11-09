// Scenes time themselves against the voice in absolute seconds. Do not wrap them in
// <Sequence>: it restarts the frame count, so every ramp inside would fire at the wrong time.
import React from "react";
import { AbsoluteFill, Easing, interpolate, spring, useCurrentFrame } from "remotion";
import { FPS } from "./tokens";

export const at = (seconds: number) => Math.round(seconds * FPS);

export const ramp = (frame: number, from: number, to: number, a = 0, b = 1) =>
  interpolate(frame, [at(from), at(to)], [a, b], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.inOut(Easing.cubic),
  });

export const pop = (frame: number, seconds: number) =>
  spring({ frame: frame - at(seconds), fps: FPS, config: { damping: 11, stiffness: 150 } });

// Shows its children between two seconds, with a short fade at each edge (in frames).
export const Scene: React.FC<{ from: number; to: number; edge?: number; children: React.ReactNode }> = ({ from, to, edge = 7, children }) => {
  const frame = useCurrentFrame();
  if (frame < at(from) - 1 || frame > at(to) + 1) return null;
  const opacity = interpolate(frame, [at(from) - 1, at(from) + edge, at(to) - edge, at(to) + 1], [0, 1, 1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  return <AbsoluteFill style={{ opacity }}>{children}</AbsoluteFill>;
};
