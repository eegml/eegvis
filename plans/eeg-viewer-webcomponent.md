# Plan: Interactive SVG EEG Web Component (Phase 1)

## Context

eegvis has a panel/bokeh EEG browser with interactive features (scrolling, montage switching, gain control, filtering). We want to build a web component system that replicates these features using modern web standards.

**Phase 1** (this plan): Refactor the SVG backend to use per-channel SVG transform groups, then wrap it in a Lit web component with dynamic horizontal scale control via TC39 Signals.

**Tech stack**: Lit + `@lit-labs/signals` (TC39 Signals polyfill). No Datastar dependency — we adopt the Datastar *pattern* (SSE → reactive state → re-render) but implement it ourselves inside the shadow DOM. SSE channel streaming is deferred to Phase 2.

---

## Part A: Refactor `stackplot_svg.py` for Transform-Based Rendering

### A1. Add `interactive` parameter to `stackplot_svg()`

Add `interactive=False` and `embed_js=False` parameters. When `interactive=False`, output is identical to today. When `True`, the SVG structure changes to use transforms.

**File:** `eegvis/stackplot_svg.py` — modify `stackplot_svg()` signature (line 154)

### A2. Add `<defs>` with `<clipPath>` (interactive mode)

When `interactive=True`, insert a `<defs>` block with a clip path for the plot area:

```xml
<defs>
  <clipPath id="plot-area">
    <rect x="{label_margin}" y="{top_margin}" width="{plot_width}" height="{plot_height}"/>
  </clipPath>
</defs>
```

### A3. Separate labels from channel trace groups (interactive mode)

Currently each `<g class="channel">` contains both label `<text>` and `<polyline>` (lines 337-357). In interactive mode, split into:

- `<g class="channel-labels">` — contains all label `<text>` elements, unscaled
- `<g class="traces" clip-path="url(#plot-area)">` — contains channel `<g>` with only `<polyline>`, each with a `transform`

Labels must not be inside scaled groups or they'd stretch with horizontal scaling.

### A4. Transform-based coordinate system for traces (interactive mode)

Instead of pre-computing SVG coordinates for polyline points, store them in **data coordinates** (time in seconds relative to start, amplitude in data units relative to channel baseline = 0).

Each channel group gets a transform:
```xml
<g class="channel" id="ch-0"
   data-channel-index="0" data-label="Fp1-F7"
   data-baseline-y="{baseline_svg}" data-x-scale="{px_per_sec}" data-y-scale="{data_to_svg}"
   transform="translate({label_margin},{baseline_svg}) scale({px_per_sec},{data_to_svg})">
  <polyline points="{t0,a0 t1,a1 ...}"
            vector-effect="non-scaling-stroke" fill="none" stroke="black" stroke-width="0.5"/>
</g>
```

Where:
- `px_per_sec = plot_width / seconds` (mm per second)
- `data_to_svg = plot_height / y_data_range` (mm per data unit)
- Polyline x-values: `(t - start_time)` in seconds
- Polyline y-values: `yscale * signal[ch, sample]` (amplitude relative to baseline 0)
- `baseline_svg = data_y_to_svg(ticklocs[draw_idx])` — SVG y of channel's zero line

Add a `_format_data_points(t_relative, amplitude)` helper with 4 decimal places for time, 2 for amplitude.

### A5. Add `data-*` metadata on SVG root (interactive mode)

```python
svg.set("data-interactive", "true")
svg.set("data-seconds", str(seconds))
svg.set("data-start-time", str(start_time))
svg.set("data-sample-frequency", str(sample_frequency))
svg.set("data-num-channels", str(num_channels))
svg.set("data-px-per-second", f"{px_per_sec:.6f}")
svg.set("data-plot-width", f"{plot_width:.2f}")
svg.set("data-label-margin", f"{label_margin:.2f}")
```

### A6. CSS additions for interactive mode

Add to the `<style>` element when interactive:
```css
polyline { vector-effect: non-scaling-stroke; }
```

### A7. Pass `interactive`/`embed_js` through pipeline functions

Update `save_svg()`, `show_montage_svg()`, `save_montage_svg()`, `eeg_to_svg()`, `save_eeg_svg()` to accept and forward `interactive` and `embed_js` kwargs.

---

## Part B: Lit Web Component — `<eeg-viewer>`

### B1. Create `eegvis/static/eeg-viewer.js`

A Lit web component using `@lit-labs/signals` that:
- Accepts an SVG string (from Python's `stackplot_svg(..., interactive=True)`) via a `svg-content` attribute or property
- Injects the SVG into its shadow DOM
- Exposes a `secondsPerPage` signal controlling horizontal scale
- Provides +/- buttons or a slider for horizontal scale adjustment
- When `secondsPerPage` changes, updates the `transform` attribute on each `<g class="channel">` and regenerates grid lines / time axis labels

```js
import { LitElement, html, css } from 'lit';
import { SignalWatcher, signal } from '@lit-labs/signals';

class EegViewer extends SignalWatcher(LitElement) {
  // Reactive signal for horizontal scale
  #secondsPerPage = signal(10);

  // Property: raw SVG string from Python
  static properties = {
    svgContent: { type: String, attribute: 'svg-content' },
  };

  render() {
    return html`
      <div class="controls">
        <button @click=${() => this.zoomIn()}>Zoom In</button>
        <button @click=${() => this.zoomOut()}>Zoom Out</button>
        <span>${this.#secondsPerPage.get()}s/page</span>
      </div>
      <div class="svg-container" .innerHTML=${this.svgContent}></div>
    `;
  }

  updated() {
    this.#applyHorizontalScale(this.#secondsPerPage.get());
  }

  #applyHorizontalScale(newSeconds) {
    const svg = this.shadowRoot.querySelector('svg[data-interactive]');
    if (!svg) return;
    const plotWidth = parseFloat(svg.dataset.plotWidth);
    const labelMargin = parseFloat(svg.dataset.labelMargin);
    const newPxPerSec = plotWidth / newSeconds;

    svg.querySelectorAll('g.channel').forEach(ch => {
      const baselineY = parseFloat(ch.dataset.baselineY);
      const yScale = parseFloat(ch.dataset.yScale);
      ch.setAttribute('transform',
        `translate(${labelMargin},${baselineY}) scale(${newPxPerSec},${yScale})`);
    });
    // Also update grid and time axis...
  }
}
customElements.define('eeg-viewer', EegViewer);
```

### B2. Create `eegvis/static/package.json`

Minimal npm package for the JS dependencies:
```json
{
  "name": "eegvis-components",
  "private": true,
  "dependencies": {
    "lit": "^3.0.0",
    "@lit-labs/signals": "^0.2.0"
  }
}
```

### B3. Python helper to serve the component

Add `eegvis/serve_component.py` — a minimal function that wraps an interactive SVG in an HTML page with the `<eeg-viewer>` web component:

```python
def render_eeg_html(signals, sample_frequency, montage=None, **kwargs):
    """Generate a standalone HTML page with the <eeg-viewer> web component."""
    svg_str = eeg_to_svg(signals, sample_frequency, montage=montage,
                         interactive=True, **kwargs)
    # Return HTML that imports the component and passes svg_str
    ...
```

This enables quick local previewing (open in browser) without a server.

---

## Part C: Tests

### C1. Existing tests pass unchanged

All 23 existing tests in `tests/test_stackplot_svg.py` must pass because `interactive` defaults to `False`.

### C2. New tests for interactive mode

Add to `tests/test_stackplot_svg.py`:

- `test_interactive_has_clip_path` — verify `<clipPath id="plot-area">` exists
- `test_interactive_traces_clipped` — `.traces` group has `clip-path="url(#plot-area)"`
- `test_interactive_channels_have_transform` — each `.channel` group has `translate(...) scale(...)`
- `test_interactive_labels_separate` — `<g class="channel-labels">` exists with correct count
- `test_interactive_data_attributes` — SVG root has `data-seconds`, `data-interactive`, etc.
- `test_interactive_polyline_data_coords` — first x-value is near 0 (seconds), not 25 (mm)
- `test_interactive_vector_effect` — CSS contains `non-scaling-stroke`
- `test_interactive_visual_equivalence` — same viewBox, same channel/polyline count as static mode

---

## Files Modified/Created

| File | Action |
|------|--------|
| `eegvis/stackplot_svg.py` | Modify — add interactive mode to `stackplot_svg()`, new helpers |
| `tests/test_stackplot_svg.py` | Modify — add ~8 new interactive-mode tests |
| `eegvis/static/eeg-viewer.js` | Create — Lit web component |
| `eegvis/static/package.json` | Create — JS dependencies |
| `eegvis/serve_component.py` | Create — Python HTML wrapper helper |

## Verification

1. `uv run python -m pytest tests/test_stackplot_svg.py -v` — all existing + new tests pass
2. Generate an interactive SVG: `stackplot_svg(signals, fs, interactive=True)` — open in browser, verify it looks correct
3. Generate HTML with `render_eeg_html()` — open in browser, verify zoom in/out buttons change horizontal scale
4. Verify static mode unchanged: `stackplot_svg(signals, fs)` output is byte-identical to before
