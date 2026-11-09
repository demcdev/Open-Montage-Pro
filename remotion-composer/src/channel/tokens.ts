// The channel's look in one place. Keep it in step with styles/custom/senal-nocturna.yaml
// and channel/channel.yaml.
import { loadSpaceGrotesk } from "../lib/localFonts";

export const COLORS = {
  night: "#070A16",
  nightGlow: "#16203D",
  grid: "#1C2747",
  fill: "#0B1328",
  // The viewer and right answers.
  cyan: "#29D3F5",
  cyanDeep: "#1C8FB0",
  // Warnings and wrong answers.
  magenta: "#FF2E63",
  // Reserved for the payoff.
  gold: "#FFC94D",
  green: "#3DDC97",
  text: "#E8EEFC",
  muted: "#6F80AA",
} as const;

export const FONT = loadSpaceGrotesk(["500", "700"]).fontFamily;

export const WIDTH = 1920;
export const HEIGHT = 1080;
export const FPS = 30;
