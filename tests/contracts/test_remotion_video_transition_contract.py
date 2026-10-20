from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_video_scene_honors_hard_cut_tokens_and_backing_color() -> None:
    """Hard-cut tokens must render as straight cuts, not fades.

    The per-scene fade logic moved out of Explainer.tsx into
    lib/transitions.tsx: Explainer resolves each boundary with
    normalizeTransition() and wraps every scene in TransitionShell.
    """
    explainer = (REPO_ROOT / "remotion-composer/src/Explainer.tsx").read_text(
        encoding="utf-8"
    )
    transitions = (REPO_ROOT / "remotion-composer/src/lib/transitions.tsx").read_text(
        encoding="utf-8"
    )

    # "cut" is a real style, "none" aliases to it, and a missing value is a cut.
    assert "cut: { enter: () => ({}), exit: none }" in transitions
    assert 'none: "cut",' in transitions
    assert 'if (!s) return "cut";' in transitions
    # A cut adds no enter/exit look...
    assert 'inT && inT.style !== "cut"' in transitions
    assert 'outT && outT.style !== "cut"' in transitions
    # ...and the out-transition stays inside the scene's own frames.
    assert "seqFrames - outT.frames" in transitions

    # Explainer resolves each boundary from the cuts and never overlaps on a cut.
    assert "normalizeTransition(" in explainer
    assert "nx.transition_in || c.transition_out || props.defaultTransition" in explainer
    assert 'inT && inT.style !== "cut" ? Math.round(inT.frames / 2) : 0' in explainer
    assert 'outT && outT.style !== "cut" ? Math.round(outT.frames / 2) : 0' in explainer
    assert "<TransitionShell inT={inT} outT={outT} seqFrames={duration}>" in explainer

    # Video scenes keep a backing color behind letterboxed footage.
    assert 'backgroundColor={cut.backgroundColor ?? "#0F172A"}' in explainer


def test_cinematic_fades_are_bounded_by_each_scene_duration() -> None:
    source = (REPO_ROOT / "remotion-composer/src/CinematicRenderer.tsx").read_text(
        encoding="utf-8"
    )

    assert "Math.round(scene.durationSeconds * fps)" in source
    assert "durationInFrames - fadeOutFrames" in source


def _jsx_block(source: str, component: str) -> str:
    """Return the JSX element text for <Component ... /> in the source."""
    start = source.index(f"<{component}")
    end = source.index("/>", start)
    return source[start:end]


def test_chart_scenes_receive_the_theme_text_color() -> None:
    """Charts default textColor to near-black (#1F2937).

    If Explainer does not forward the theme's textColor, every chart title,
    axis label, category label and value renders dark-on-dark and is invisible
    on any dark theme.
    """
    source = (REPO_ROOT / "remotion-composer/src/Explainer.tsx").read_text(
        encoding="utf-8"
    )

    for component in ("BarChart", "LineChart", "PieChart", "KPIGrid"):
        assert "textColor={textColor}" in _jsx_block(source, component), (
            f"{component} must receive the theme textColor, "
            f"or its labels are invisible on dark themes"
        )


def test_comparison_card_surface_follows_the_theme() -> None:
    """ComparisonCard hardcodes cardBackgroundColor to a light grey (#F3F4F6).

    On a dark theme it receives the theme's light textColor, so without a
    themed card surface the labels are light-on-light.
    """
    source = (REPO_ROOT / "remotion-composer/src/Explainer.tsx").read_text(
        encoding="utf-8"
    )
    block = _jsx_block(source, "ComparisonCard")

    assert "textColor={textColor}" in block
    assert "cardBackgroundColor={cut.cardBackgroundColor || theme.surfaceColor}" in block
