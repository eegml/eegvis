

# Plan: SVG EEG Visualization Backend

## Context

eegvis currently renders EEG traces via matplotlib (static) and bokeh/panel (interactive). We want a pure SVG backend that takes EEG data through the standard pipeline (downsample, montage, filter, plot) and outputs a standalone SVG file. This avoids the matplotlib dependency for static output and produces clean, lightweight vector graphics suitable for reports, web embedding, and archival.

The StratusEEG commercial viewer (see `docs/stratus.md`) confirms SVG is viable for EEG display — they use `<polyline>` per channel, `<line>` for grid/axes, and `<text>` for labels, all inside a `viewBox`-scaled SVG.

## Approach

Create a new module `eegvis/stackplot_svg.py` that mirrors the data flow of `stacklineplot.py` but outputs SVG directly using Python's `xml.etree.ElementTree` (no external dependencies).

### Pipeline Steps (matching the user's 7-step description)

```
raw_signals (N channels, T samples)
  1. [optional] downsample
  2. montage matrix multiply → derived signals (M channels, T samples)
  3. generate montage labels
  4. apply bandpass filter (via eegml_signal.filters)
  5. compute vertical offsets, apply gain, flip polarity
  6. render as SVG polylines with labels, scale bars, time axis
  7. write .svg file
```

Steps 1-4 are handled by existing code (montageview.py, eegml_signal). The new module handles steps 5-7.

### SVG Structure

```xml
<svg xmlns="..." viewBox="0 0 {width} {height}">
  <!-- background -->
  <rect width="100%" height="100%" fill="white"/>

  <!-- time grid lines -->
  <g class="grid">
    <line x1="..." y1="0" x2="..." y2="{height}" stroke="#eee"/>
    ...
  </g>

  <!-- channel traces -->
  <g class="traces">
    <g class="channel" id="ch-0">
      <text x="{label_x}" y="{y_offset}" class="label">Fp1-F7</text>
      <polyline points="x1,y1 x2,y2 ..." stroke="black" fill="none"/>
    </g>
    ...
  </g>

  <!-- scale bar -->
  <g class="scalebar">
    <line .../>
    <text ...>100 µV</text>
  </g>

  <!-- time axis -->
  <g class="timeaxis">
    <text ...>0s</text>
    <text ...>1s</text>
    ...
  </g>
</svg>
```

### Key Design Decisions

1. **No external dependencies** — use `xml.etree.ElementTree` for SVG generation. SVG is just XML.

2. **Coordinate system** — SVG y-axis points down, which naturally matches the clinical "negative is up" convention when we negate the signal. Define a viewBox in mm or abstract units matching the desired output dimensions.

3. **One polyline per channel** — following StratusEEG pattern. Convert each channel's (time, amplitude) data into a space-separated `points` attribute string.

4. **Channel spacing** — reuse the same vertical offset logic from `stacklineplot.py`:
   - Auto mode: `dr = 0.7 * (dmax - dmin)`, offset `i * dr`
   - Sensitivity mode: `perchan_uV = (sensitivity * height_mm) / num_channels`

5. **Downsampling for SVG size** — optional decimation to limit points per channel (e.g., cap at ~2000 points per channel for a 10s window at 256 Hz is already manageable, but 5kHz data needs decimation).

6. **Labels** — channel labels as `<text>` elements positioned at each channel's y-offset, left of the trace area. Time labels along the bottom.

### Public API

```python
def stackplot_svg(
    signals,           # (num_channels, num_samples) numpy array
    sample_frequency,  # Hz
    ylabels=None,      # channel names
    seconds=None,      # duration (derived from signals + fs if not given)
    start_time=0.0,    # time offset for labels
    yscale=1.0,        # gain multiplier (scalar or per-channel array)
    sensitivity=None,  # µV/mm (overrides auto-scaling)
    width_mm=300,      # SVG width in mm
    height_mm=200,     # SVG height in mm
    topdown=True,      # first channel at top
) -> str:
    """Return SVG string of stacked EEG traces."""

def save_svg(
    filepath,
    signals,
    sample_frequency,
    **kwargs,          # same as stackplot_svg
):
    """Write SVG file to disk."""

def show_montage_svg(
    signals,           # raw signals (N channels, T samples)
    montage,           # MontageView instance
    sample_frequency,
    **kwargs,
) -> str:
    """Apply montage derivation, then render as SVG."""
```

### Files to Create/Modify

| File | Action | Description |
|------|--------|-------------|
| `eegvis/stackplot_svg.py` | **Create** | New SVG backend module |
| `tests/test_stackplot_svg.py` | **Create** | Tests for SVG output |
| `eegvis/__init__.py` | No change needed | Import on demand |

### Implementation Order

1. **Core SVG rendering** — `stackplot_svg()` that takes pre-processed signals and outputs SVG string with traces, labels, and time axis
2. **Scale bars** — `add_vertical_scalebar()` helper
3. **Time grid** — vertical grid lines at 1s intervals
4. **`show_montage_svg()`** — convenience wrapper applying montage + rendering
5. **`save_svg()`** — file output wrapper
6. **Tests** — generate SVG from synthetic data, verify structure, visual spot-check

### Verification

- Generate SVG from synthetic sine wave data (multiple channels)
- Open in browser to visually verify layout
- Test with montage derivation (DoubleBananaMontageView)
- Compare channel spacing and scale bar against matplotlib version
- Validate SVG structure with `xml.etree.ElementTree.fromstring()`
