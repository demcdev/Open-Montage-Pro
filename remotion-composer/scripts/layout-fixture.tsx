// A frame with every layout mistake the audit must find, next to the look-alikes it
// must leave alone. tests/qa/test_layout_audit.py renders it through layout-audit.mjs.
import React from "react";
import { AbsoluteFill, Composition, registerRoot } from "remotion";

const text = (left: number, top: number, extra: React.CSSProperties = {}): React.CSSProperties => ({
  position: "absolute",
  left,
  top,
  color: "white",
  fontFamily: "sans-serif",
  fontSize: 48,
  whiteSpace: "nowrap",
  ...extra,
});

const Marker: React.FC<{ left: number; top: number }> = ({ left, top }) => (
  <svg width={300} height={120} style={{ position: "absolute", left, top }}>
    <rect width={300} height={120} fill="tomato" />
  </svg>
);

const Broken: React.FC = () => (
  <AbsoluteFill style={{ backgroundColor: "#123" }}>
    <div style={text(1700, 40)}>fuera del lienzo</div>

    <div style={text(100, 160)}>primer titulo</div>
    <div style={text(160, 170)}>segundo titulo</div>

    <div style={{ position: "absolute", left: 100, top: 300, width: 160, height: 70, overflow: "hidden" }}>
      <div style={text(0, 0)}>texto recortado por su caja</div>
    </div>

    <div style={text(100, 460)}>tapado por grafico</div>
    <Marker left={120} top={430} />

    <svg width={300} height={120} style={{ position: "absolute", left: -150, top: 620 }}>
      <rect width={300} height={120} fill="gold" />
    </svg>

    {/* Below: nothing here may be reported. */}
    <div style={{ position: "absolute", left: 900, top: 160 }}>
      <div style={text(0, 0, { color: "black", transform: "translate(2px, 2px)" })}>con sombra</div>
      <div style={text(0, 0)}>con sombra</div>
    </div>

    <div style={text(900, 300)}>texto visible</div>
    <div style={text(900, 300, { opacity: 0 })}>texto oculto</div>

    <div data-layout-allow-overlap style={text(900, 420)}>encimado adrede uno</div>
    <div data-layout-allow-overlap style={text(940, 430)}>encimado adrede dos</div>

    <div data-layout-allow-overflow style={text(1800, 560)}>sale adrede del lienzo</div>

    <div data-layout-ignore style={text(1800, 700)}>ignorado por completo</div>

    <div style={{ position: "absolute", left: 900, top: 700, width: 400, height: 200, background: "#345" }}>
      <div style={text(20, 20)}>sobre tarjeta</div>
    </div>
  </AbsoluteFill>
);

const Root: React.FC = () => (
  <Composition id="LayoutFixture" component={Broken} durationInFrames={90} fps={30} width={1920} height={1080} />
);

registerRoot(Root);

