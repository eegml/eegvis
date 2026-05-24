"""Generate a montage × theme gallery into ``docs/gallery/``.

Renders every bundled :class:`MontageDisplay` profile against every
bundled :class:`Theme` using a single synthetic 23-channel demo dataset
(standard 10-20 plus A1/A2 and Sp1/Sp2 for TCP / true sphenoidal). Writes
one SVG per combination and a static ``index.html`` that lays them out as
a grid for at-a-glance comparison.

Run with:

    uv run python -m docs.gallery.build
    # or
    uv run python docs/gallery/build.py
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np

from eegvis.displays import list_displays, load_display
from eegvis.stackplot_svg import (
    DEFAULT_THEME,
    PUBLICATION_THEME,
    STRATUS_THEME,
    save_montage_display_svg,
)


GALLERY_DIR = Path(__file__).resolve().parent

# ---------------------------------------------------------------------------
# Synthetic recording — large enough to cover every bundled montage.
# Mixed-case electrodes match the schema-side convention (matching the
# normalized neonatal labels post-Fp1 fix).
# ---------------------------------------------------------------------------

REC_LABELS = [
    # standard 10-20
    "Fp1", "Fp2", "F3", "F4", "C3", "C4", "P3", "P4", "O1", "O2",
    "F7", "F8", "T3", "T4", "T5", "T6", "Fz", "Cz", "Pz",
    # ear references for TCP
    "A1", "A2",
    # sphenoidal needles for true_sphenoidal
    "Sp1", "Sp2",
]

# What electrodes does each bundled montage rely on? Used only to gate
# which combinations actually get rendered (we skip a montage if our
# synthetic recording is missing required leads — never happens with the
# 23-channel set above, but the structure keeps this future-proof).
REQUIRED: Dict[str, List[str]] = {
    "double_banana": ["Fp1", "Fp2", "F3", "F4", "C3", "C4", "P3", "P4", "O1", "O2",
                      "F7", "F8", "T3", "T4", "T5", "T6", "Fz", "Cz", "Pz"],
    "double_banana_paired": ["Fp1", "Fp2", "F3", "F4", "C3", "C4", "P3", "P4",
                             "O1", "O2", "F7", "F8", "T3", "T4", "T5", "T6",
                             "Fz", "Cz", "Pz"],
    "double_banana_avg": ["Fp1", "Fp2", "F3", "F4", "C3", "C4", "P3", "P4",
                          "O1", "O2", "F7", "F8", "T3", "T4", "T5", "T6",
                          "Fz", "Cz", "Pz"],
    "circle": ["Fp1", "Fp2", "F7", "T3", "T5", "O1", "O2", "T6", "T4", "F8"],
    "neonatal": ["Fp1", "Fp2", "C3", "C4", "T3", "T4", "O1", "O2", "Cz", "Fz", "Pz"],
    "tcp": ["Fp1", "Fp2", "F3", "F4", "C3", "C4", "P3", "P4", "O1", "O2",
            "F7", "F8", "T3", "T4", "T5", "T6", "Cz", "A1", "A2"],
    "true_sphenoidal": ["Fp1", "Fp2", "F3", "F4", "C3", "C4", "P3", "P4",
                        "O1", "O2", "F7", "F8", "T3", "T4", "T5", "T6",
                        "Fz", "Cz", "Pz", "Sp1", "Sp2"],
}

THEMES = [
    ("default", DEFAULT_THEME),
    ("publication", PUBLICATION_THEME),
    ("stratus", STRATUS_THEME),
]


def synth_recording(
    rec_labels: List[str], fs: float = 256.0, seconds: float = 10.0
) -> np.ndarray:
    """Generate ``(num_channels, num_samples)`` of pseudo-EEG.

    Each channel is a mix of alpha (10 Hz), theta (6 Hz), random noise,
    and a 60 Hz line component, with channel-specific phases — same recipe
    as ``create_demo_study()`` in the viewer.
    """
    rng = np.random.default_rng(42)
    n_samples = int(fs * seconds)
    t = np.arange(n_samples) / fs
    n = len(rec_labels)
    sig = np.zeros((n, n_samples))
    for i in range(n):
        alpha = rng.uniform(10, 40) * np.sin(
            2 * np.pi * (10 + rng.uniform(-1, 1)) * t + rng.uniform(0, 2 * np.pi)
        )
        theta = rng.uniform(5, 15) * np.sin(
            2 * np.pi * (6 + rng.uniform(-0.5, 0.5)) * t + rng.uniform(0, 2 * np.pi)
        )
        sig[i] = alpha + theta + rng.normal(0, 5, n_samples) + 3 * np.sin(
            2 * np.pi * 60 * t
        )
    return sig


def render_one(name: str, theme_name: str, theme, signals, fs) -> Path:
    """Render one ``(montage, theme)`` combination to an SVG file."""
    out = GALLERY_DIR / f"{name}__{theme_name}.svg"
    display = load_display(name)
    save_montage_display_svg(
        out,
        signals,
        fs,
        display,
        rec_labels=REC_LABELS,
        seconds=10.0,
        sensitivity=10.0,
        width_mm=300,
        height_mm=180,
        theme=theme,
        max_samples_per_channel=2000,
    )
    return out


def write_index_html(entries: List[Tuple[str, str, Path]]) -> Path:
    """Compose an HTML page that arranges the SVGs as a grid."""
    montages = sorted({m for m, _, _ in entries})
    themes = [t for t, _ in THEMES]

    # build a lookup: (montage, theme) -> relative path
    lookup: Dict[Tuple[str, str], Path] = {(m, t): p for m, t, p in entries}

    style = """
    :root {
      --grid-gap: 12px;
      --pad: 16px;
      --border: #d0d0d0;
      --label: #444;
    }
    * { box-sizing: border-box; }
    body {
      font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
      margin: 0; padding: var(--pad);
      background: #fafafa; color: #222;
    }
    h1 { font-size: 20px; margin: 0 0 4px; }
    p.lede { color: #666; margin: 0 0 16px; max-width: 60em; }
    .grid {
      display: grid;
      grid-template-columns: 8em repeat(var(--cols), minmax(0, 1fr));
      gap: var(--grid-gap);
      align-items: start;
    }
    .col-header, .row-header {
      font-size: 12px; color: var(--label); text-transform: uppercase;
      letter-spacing: 0.06em; font-weight: 600;
    }
    .col-header { text-align: center; padding: 4px 0; }
    .row-header {
      align-self: center; text-align: right; padding-right: 6px;
      font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
      font-size: 13px; text-transform: none; letter-spacing: 0;
    }
    .cell {
      background: white; border: 1px solid var(--border); border-radius: 4px;
      padding: 4px; overflow: hidden;
    }
    .cell object { width: 100%; height: auto; display: block; }
    .empty { color: #aaa; font-style: italic; padding: 12px; text-align: center; }
    footer {
      margin-top: 24px; color: #888; font-size: 12px;
    }
    """

    rows = [
        '<!doctype html>',
        '<html><head><meta charset="utf-8">',
        "<title>eegvis montage × theme gallery</title>",
        f"<style>{style}</style>",
        "</head><body>",
        "<h1>eegvis montage × theme gallery</h1>",
        '<p class="lede">Every bundled MontageDisplay profile (rows) rendered '
        "with every bundled Theme (columns) against a synthetic 23-channel "
        "demo recording. Generated by <code>docs/gallery/build.py</code>.</p>",
        f'<div class="grid" style="--cols: {len(themes)};">',
        # header row
        '<div></div>',
    ]
    for theme_name in themes:
        rows.append(f'<div class="col-header">{theme_name}</div>')
    for montage in montages:
        rows.append(f'<div class="row-header">{montage}</div>')
        for theme_name in themes:
            path = lookup.get((montage, theme_name))
            if path is None:
                rows.append('<div class="cell empty">—</div>')
            else:
                rel = path.name
                rows.append(
                    f'<div class="cell">'
                    f'<object type="image/svg+xml" data="{rel}"></object>'
                    f"</div>"
                )
    rows.append("</div>")
    rows.append(
        '<footer>Source: <code>docs/gallery/build.py</code> · '
        "Generated from the bundled profiles in "
        "<code>eegvis/displays/</code> and the themes in "
        "<code>eegvis/stackplot_svg.py</code>.</footer>"
    )
    rows.append("</body></html>")

    out = GALLERY_DIR / "index.html"
    out.write_text("\n".join(rows), encoding="utf-8")
    return out


def main() -> None:
    GALLERY_DIR.mkdir(parents=True, exist_ok=True)
    fs = 256.0
    signals = synth_recording(REC_LABELS, fs=fs, seconds=10.0)

    entries: List[Tuple[str, str, Path]] = []
    for montage in list_displays():
        # If the montage needs leads we don't have, skip it for now.
        needed = REQUIRED.get(montage, [])
        missing = [e for e in needed if e not in REC_LABELS]
        if missing:
            print(f"  skip {montage}: missing {missing}")
            continue
        for theme_name, theme in THEMES:
            try:
                path = render_one(montage, theme_name, theme, signals, fs)
                entries.append((montage, theme_name, path))
                print(f"  wrote {path.relative_to(GALLERY_DIR.parent.parent)}")
            except Exception as e:
                print(f"  FAIL {montage} × {theme_name}: {e}")

    index = write_index_html(entries)
    print(f"\nindex: {index.relative_to(GALLERY_DIR.parent.parent)}")
    print(f"total: {len(entries)} SVGs")


if __name__ == "__main__":
    main()
