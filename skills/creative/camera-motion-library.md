# Camera, Motion and Effects Library (Remotion)

## When to Use

Any Remotion-rendered video where scenes would otherwise sit still: stat cards over stock images, text cards, still-led explainers. This skill tells you **which move, transition and effect to pick** and how to write them into `edit_decisions`. The full index (every id, alias and AI-video prompt) is [`docs/MOTION_CATALOG.md`](../../docs/MOTION_CATALOG.md); the machine-readable source is `remotion-composer/src/lib/motion-catalog.json`.

> Static slideshows are a defect, not a style. A scene that holds more than ~2 seconds without any camera move, reveal or effect needs a reason.

## What it is (and isn't)

The engine is a **2D camera** on stills and clips: scale, translate, rotate, blur, parallax between background and foreground content, plus a stack of grade/lens/light effects. It approximates real dolly, pan, tilt, crane, arc, handheld and whip moves convincingly on a flat image. It cannot produce true 3D parallax, a real orbit around an object, or a fly-through. For those, either generate real video (use the move's `ai_prompt` — Movement · Speed · Framing · End — with a configured video provider) or fake it with `slider_*`, `wigglegram`, `push_past`, `pass_through`, which sell the illusion at short durations.

## Writing it down

On any cut (the fields live in `edit_decisions.cuts[]` and are forwarded to Remotion):

```json
{
  "id": "cut-1", "source": "assets/images/moon.jpg", "in_seconds": 0, "out_seconds": 6.5,
  "type": "stat_card", "stat": "1,3 s", "subtitle": "LUNA", "backgroundImage": "assets/images/moon.jpg",
  "camera": { "move": "dolly_in", "origin": { "x": 61, "y": 52 }, "intensity": 1.0 },
  "fx": ["halation", "film_grain"],
  "transition_out": "whip_pan_right", "transition_duration": 0.35
}
```

Top level: `fx` (applies to every scene), `autoCamera` (true, or a list of ids — gives background scenes without a camera a rotating default move), `defaultTransition`, `defaultTransitionSeconds`.

`camera` is an id/alias (`"dolly_in"`) or a spec: `move`, `intensity` (0.5 = subtler), `origin` (where the camera points), `from`/`to` overrides (`s` scale, `x`/`y` percent, `r` degrees), `ease`, `parallax` (0 = content fixed, 1 = moves with the image), `shake`, `delay`, `hold`, `reverse`, `freezeAt`.

## Choosing a move

Pick from the **narration beat**, not from the list:

| Narrative beat | Good moves |
|---|---|
| Hook / reveal | `crash_zoom_in`, `whip_pan_*`, `reveal_right`, `earth_zoom_out`, `dolly_in` with a tight `origin` |
| Introduce a subject | `dolly_in`, `zoom_in_slow`, `drone_push_in`, `crane_down` |
| Scale / context | `dolly_out`, `zoom_out_slow`, `crane_up`, `aerial_reveal`, `earth_zoom_out` |
| Comparison / journey | `pan_left/right`, `truck_*`, `slider_*`, `parallax_drift`, `tracking` |
| Tension / urgency | `handheld`, `handheld_intense`, `fpv_drone`, `chase`, `dolly_zoom`, `dutch_angle` |
| Calm / awe | `float`, `steadicam`, `helicopter`, `ken_burns`, `breathe`, `crane_up` |
| Big number / payoff | `punch_in`, `crash_zoom_in`, `infinite_zoom`, `dolly_in` ending on the number |
| Transition into next topic | `pass_through`, `push_past`, `infinite_zoom`, `scale_shift` + matching transition |

### Point at things

- Set `camera.origin` to the object's position (percent of frame) so the zoom closes in on it.
- Add a `focus_ring` or `arrow` overlay at the same `x`,`y` to label it.
- Use a `spotlight` fx (`{ "type": "spotlight", "x": 61, "y": 52, "radius": 30 }`) to dim everything else.
- Chain two cuts of the same image with different `origin`s to move from one object to the next.

## Rules

1. **Variety**: never use the same move on consecutive scenes; alternate direction (left/right, in/out).
2. **One focal object** per frame. Keep the move's end state composed — the last second is when people read.
3. **Legibility first**: text sits in the parallax-damped foreground, but heavy blur (`whip_*`, `crash_*`, `motion_blur`, glitch) should not run while someone must read a number. Hold text moves ≤ intensity 1.
4. **Match speed to pace**: slow narration → `zoom_in_slow`, `float`, `steadicam`; fast cuts → `punch_in`, `whip_*`, `handheld`.
5. **Pair moves with transitions**: a `whip_pan_right` transition after a `pan_right`; `scale_shift`/`match_cut` between visually matching shapes (moon → planet disc); `dip_*` or `dissolve` for time passing; `glitch`/`rgb_split` only for tech/digital subjects.
6. **Effects are seasoning**: one grade (`grade_*`), one texture (`film_grain` ≤ 0.35), optionally `vignette`; add light fx (`halation`, `light_leak`, `lens_flare`) sparingly on hero beats. Letterbox (`letterbox`, ratio 2.39) is a whole-video decision: put it in the top-level `fx`.
7. **Rhythm**: 3–6 s per scene for explainers; a 1–2 s punch-in or whip is fine for emphasis. Align transitions to narration pauses, not mid-word.
8. **Honest visuals**: stock stills used as texture stay labelled as illustrative; camera moves never imply a place or event the image doesn't show.
9. **Performance**: SVG-filter fx (`glitch`, `chromatic_aberration`, `distortion_wave`, `motion_blur`) and duplicated-layer fx (`echo`, `kaleidoscope`, `tilt_shift`, `halation`) cost render time. Use them on a few scenes, not everywhere.

## Recipes

- **Space / science explainer**: top-level `fx: ["film_grain", "vignette"]`; scenes `dolly_in` / `pan_*` / `crane_up` with `origin` on the subject; `halation` on bright bodies; transitions `dissolve` and `scale_shift`; closing `earth_zoom_out` or `infinite_zoom`.
- **Tech / product**: `slider_*` + `parallax_drift`, `grade_cool`, `chromatic_aberration` on titles, transitions `whip_pan_*`/`glitch`, `hud_frame` overlay, `kinetic_text` with `glitch_in`.
- **Documentary**: `ken_burns`, `documentary_drift`, `steadicam`, `grade_vintage` + `film_grain`, `dip_black` between chapters, `lower_third` for names.
- **Hype / social**: `crash_zoom_in`, `punch_in`, `whip_pan_*`, `flash` transitions, `kinetic_text` with `word_pop`, `light_leak`, `split_screen` for comparisons.
- **Comparison**: `split_screen` (`2h`, `3h`, `4`) with a different `camera` per panel and a `label` on each.

## Showcase

`remotion-composer/public/demo-props/` holds ready-made compositions; to preview a single move, render a short composition with that `camera` id (see `docs/MOTION_CATALOG.md` for every id). The test `tests/tools/test_motion_catalog.py` keeps the catalog, the engine and the docs consistent; after editing `motion-catalog.json` run `python scripts/generate_motion_docs.py`.
