// Measures what a viewer would see at one instant and reports layout problems:
// text outside the canvas, text cut by its container, text on top of other text,
// text hidden behind a graphic, and graphics that leave the canvas.
//
// It runs inside the page of the composition, so it measures real boxes after
// fonts, transforms and animation. tools/analysis/layout_audit.py decides what
// each finding means across samples.
(() => {
  const LOG_PREFIX = "__OM_LAYOUT__";
  const EDGE_TOLERANCE = 2;
  const MIN_OPACITY = 0.15;
  const MIN_OVERLAP_RATIO = 0.08;
  const BACKGROUND_AREA_RATIO = 0.6;
  const GRAPHIC_CUT_RATIO = 0.02;
  const COVERED_RATIO = 0.2;
  const SAME_LAYER_RATIO = 0.7;
  const SKIPPED_TAGS = new Set(["SCRIPT", "STYLE", "NOSCRIPT", "TITLE", "DEFS", "METADATA"]);
  const GRAPHICS = "img,svg,canvas,video";

  const area = (box) => Math.max(0, box.right - box.left) * Math.max(0, box.bottom - box.top);
  const rounded = (box) => [box.left, box.top, box.right, box.bottom].map(Math.round);

  const intersect = (a, b) => ({
    left: Math.max(a.left, b.left),
    top: Math.max(a.top, b.top),
    right: Math.min(a.right, b.right),
    bottom: Math.min(a.bottom, b.bottom),
  });

  const overlapArea = (a, b) => {
    const box = intersect(a, b);
    return box.right > box.left && box.bottom > box.top ? area(box) : 0;
  };

  const canvasBox = () => {
    const root = document.querySelector("[data-composition-id]");
    if (root) {
      const box = root.getBoundingClientRect();
      if (box.width > 0 && box.height > 0) return box;
    }
    return { left: 0, top: 0, right: window.innerWidth, bottom: window.innerHeight };
  };

  // Walks the ancestors once, so a parent's opacity or clip counts for the child.
  const visibility = (element, canvas) => {
    let opacity = 1;
    let clip = null;
    let allowOverflow = false;
    let allowOverlap = false;
    for (let node = element; node && node.nodeType === 1; node = node.parentElement) {
      const style = getComputedStyle(node);
      if (style.display === "none" || style.visibility === "hidden" || node.hasAttribute("data-layout-ignore")) {
        return null;
      }
      opacity *= Number(style.opacity);
      if (node.hasAttribute("data-layout-allow-overflow")) allowOverflow = true;
      if (node.hasAttribute("data-layout-allow-overlap")) allowOverlap = true;
      if (node !== element && style.overflow !== "visible") {
        const box = node.getBoundingClientRect();
        // A canvas-sized wrapper only frames the video; off-canvas is reported apart.
        const inside = box.left > canvas.left || box.top > canvas.top || box.right < canvas.right || box.bottom < canvas.bottom;
        if (inside) clip = clip ? intersect(clip, box) : box;
      }
    }
    return opacity < MIN_OPACITY ? null : { opacity, clip, allowOverflow, allowOverlap };
  };

  const collectTexts = (canvas) => {
    const byElement = new Map();
    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
    for (let node = walker.nextNode(); node; node = walker.nextNode()) {
      const text = node.textContent.trim();
      const element = node.parentElement;
      if (!text || !element || SKIPPED_TAGS.has(element.tagName.toUpperCase())) continue;
      const range = document.createRange();
      range.selectNodeContents(node);
      const lines = [...range.getClientRects()].filter((box) => box.width > 1 && box.height > 1);
      if (!lines.length) continue;
      const item = byElement.get(element) || { element, text: "", lines: [] };
      item.text = `${item.text} ${text}`.trim();
      item.lines.push(...lines);
      byElement.set(element, item);
    }
    const items = [];
    for (const item of byElement.values()) {
      const seen = visibility(item.element, canvas);
      if (!seen) continue;
      const box = item.lines.reduce((all, line) => ({
        left: Math.min(all.left, line.left),
        top: Math.min(all.top, line.top),
        right: Math.max(all.right, line.right),
        bottom: Math.max(all.bottom, line.bottom),
      }));
      const shown = seen.clip ? intersect(box, seen.clip) : box;
      if (shown.right <= shown.left || shown.bottom <= shown.top) continue;
      items.push({ ...item, ...seen, box, shown });
    }
    return items;
  };

  const collectGraphics = (canvas) => {
    const canvasArea = area(canvas);
    const items = [];
    for (const element of document.querySelectorAll(GRAPHICS)) {
      if (element.parentElement && element.parentElement.closest("svg")) continue;
      const box = element.getBoundingClientRect();
      if (box.width < 2 || box.height < 2) continue;
      if (area(box) >= canvasArea * BACKGROUND_AREA_RATIO) continue;
      const seen = visibility(element, canvas);
      if (seen) items.push({ element, box, ...seen });
    }
    return items;
  };

  const label = (text) => (text.length > 60 ? `${text.slice(0, 57)}...` : text);
  const graphicName = (element) => element.getAttribute("src")?.split("/").pop() || element.tagName.toLowerCase();

  const isLayerOf = (a, b) => {
    if (a.text !== b.text) return false;
    const shared = overlapArea(a.box, b.box);
    return shared >= SAME_LAYER_RATIO * Math.max(area(a.box), area(b.box));
  };

  const linesOverlap = (a, b) => {
    let shared = 0;
    for (const lineA of a.lines) for (const lineB of b.lines) shared += overlapArea(lineA, lineB);
    return shared;
  };

  const measure = () => {
    const canvas = canvasBox();
    const texts = collectTexts(canvas);
    const graphics = collectGraphics(canvas);
    const findings = [];

    for (const item of texts) {
      if (item.allowOverflow) continue;
      const outside =
        item.box.left < canvas.left - EDGE_TOLERANCE ||
        item.box.top < canvas.top - EDGE_TOLERANCE ||
        item.box.right > canvas.right + EDGE_TOLERANCE ||
        item.box.bottom > canvas.bottom + EDGE_TOLERANCE;
      if (outside) {
        findings.push({ rule: "text_off_canvas", text: label(item.text), box: rounded(item.box) });
      } else if (item.clip && area(item.shown) < area(item.box) - EDGE_TOLERANCE * Math.max(item.box.right - item.box.left, 1)) {
        findings.push({ rule: "text_cut_off", text: label(item.text), box: rounded(item.box) });
      }
    }

    for (let i = 0; i < texts.length; i += 1) {
      for (let j = i + 1; j < texts.length; j += 1) {
        const a = texts[i];
        const b = texts[j];
        if (a.allowOverlap || b.allowOverlap) continue;
        if (a.element.contains(b.element) || b.element.contains(a.element) || isLayerOf(a, b)) continue;
        const smaller = Math.min(area(a.box), area(b.box));
        if (linesOverlap(a, b) >= smaller * MIN_OVERLAP_RATIO) {
          findings.push({ rule: "text_overlap", text: label(a.text), other: label(b.text), box: rounded(intersect(a.box, b.box)) });
        }
      }
    }

    for (const item of texts) {
      if (item.allowOverlap) continue;
      for (const graphic of graphics) {
        if (graphic.allowOverlap || graphic.element.contains(item.element)) continue;
        const shared = intersect(item.shown, graphic.box);
        if (overlapArea(item.shown, graphic.box) < area(item.shown) * COVERED_RATIO) continue;
        const top = document.elementFromPoint((shared.left + shared.right) / 2, (shared.top + shared.bottom) / 2);
        if (top && (top === graphic.element || graphic.element.contains(top))) {
          findings.push({ rule: "text_covered", text: label(item.text), other: graphicName(graphic.element), box: rounded(shared) });
        }
      }
    }

    for (const graphic of graphics) {
      if (graphic.allowOverflow) continue;
      const width = graphic.box.right - graphic.box.left;
      const height = graphic.box.bottom - graphic.box.top;
      const cutX = Math.max(canvas.left - graphic.box.left, 0) + Math.max(graphic.box.right - canvas.right, 0);
      const cutY = Math.max(canvas.top - graphic.box.top, 0) + Math.max(graphic.box.bottom - canvas.bottom, 0);
      if (cutX > width * GRAPHIC_CUT_RATIO || cutY > height * GRAPHIC_CUT_RATIO) {
        findings.push({ rule: "graphic_off_canvas", text: graphicName(graphic.element), box: rounded(graphic.box) });
      }
    }

    return { texts: texts.length, graphics: graphics.length, findings };
  };

  window.__omLayoutMeasure = measure;

  // Remotion turns remotion_renderReady on once a frame is painted and right before
  // its screenshot, which is the one moment a measurement matches that frame.
  if (!("remotion_renderReady" in window)) return;
  let ready = window.remotion_renderReady;
  let frame = null;
  let measured = null;
  let setFrame = null;
  Object.defineProperty(window, "remotion_setFrame", {
    configurable: true,
    get: () => setFrame,
    set: (original) => {
      setFrame = (next, ...rest) => {
        frame = next;
        return original(next, ...rest);
      };
    },
  });
  Object.defineProperty(window, "remotion_renderReady", {
    configurable: true,
    get: () => ready,
    set: (value) => {
      ready = value;
      if (value !== true || frame === null || frame === measured) return;
      measured = frame;
      console.log(`${LOG_PREFIX}${JSON.stringify({ frame, ...measure() })}`);
    },
  });
})();
