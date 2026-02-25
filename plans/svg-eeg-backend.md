# Plan: SVG EEG Visualization Backend

## Context

eegvis currently renders EEG traces via matplotlib (static) and bokeh/panel (interactive). We want a pure SVG backend that takes EEG data through the standard pipeline (downsample, montage, filter, plot) and outputs a standalone SVG file. This avoids the matplotlib dependency for static output and produces clean, lightweight vector graphics suitable for reports, web embedding, and archival.

The StratusEEG commercial viewer (see `docs/stratus.md`) confirms SVG is viable for EEG display — they use `<polyline>` per channel, `<line>` for grid/axes, and `<text>` for labels, all inside a `viewBox`-scaled SVG.

## Status

### Completed

- **Core SVG rendering** (`stackplot_svg()`) — generates SVG string with polyline-per-channel traces, channel labels, time axis labels, vertical grid lines, plot border, and scale bar. Uses `xml.etree.ElementTree`, no matplotlib dependency.
- **Scale bar** — vertical scale bar with end caps and label, auto-sized or explicit height.
- **Time grid** — vertical grid lines at configurable intervals.
- **Montage wrappers** — `show_montage_svg()` and `save_montage_svg()` apply montage derivation then render.
- **File output** — `save_svg()` writes to disk.
- **Downsampling** — `downsample()` function using `scipy.signal.decimate` with anti-aliasing. Also available as `max_samples_per_channel` parameter on `stackplot_svg()` for automatic decimation.
- **Bandpass filtering** — `bandpass_filter()` using `eegml_signal.filters` FIR highpass + lowpass. Auto-limits numtaps to signal length.
- **Notch filtering** — `notch_filter()` using `eegml_signal.filters.notch_filter_iir_ff`.
- **End-to-end pipeline** — `eeg_to_svg()` and `save_eeg_svg()` chain all steps: downsample → montage → bandpass → notch → render SVG.
- **Tests** — 23 tests covering: SVG structure, channel labels, sensitivity mode, grid/scalebar toggle, time labels, file output, topdown ordering, downsampling, bandpass attenuation/preservation, notch filtering, pipeline with montage, pipeline with all options.
- **Layout tuning** — font size reduced to 3.5mm, margins scaled for mm-based viewBox coordinates. Still needs further refinement (see TODO).

### TODO

- **Layout polish** — scale bar positioning and sizing still needs work; label spacing could be improved; overall proportions need tuning with real EEG data.
- **Per-channel gain** — support array-valued `yscale` for individual channel sensitivity control.
- **Annotations/events** — support for marking events or time regions on the SVG (colored rect overlays).
- **Color per channel** — allow different trace colors (e.g. to distinguish
  left/right hemisphere).
- spacers between channels to define groups of channels
- **Horizontal time scale bar** — in addition to the vertical amplitude scale bar.
- **Testing with real EEG files** — verify with eeghdf/edfio or pyedflib data, not just synthetic signals.

## Architecture

### Files

| File                          | Status  | Description                |
|-------------------------------|---------|----------------------------|
| `eegvis/stackplot_svg.py`     | Created | SVG backend module         |
| `tests/test_stackplot_svg.py` | Created | 23 tests                   |

### Public API

```python
# Low-level: render pre-processed signals
stackplot_svg(signals, sample_frequency, ...) -> str
save_svg(filepath, signals, sample_frequency, **kwargs)

# Montage convenience wrappers
show_montage_svg(signals, montage, sample_frequency, **kwargs) -> str
save_montage_svg(filepath, signals, montage, sample_frequency, **kwargs)

# Processing utilities (can be used standalone)
downsample(signals, sample_frequency, target_frequency) -> (signals, new_fs)
bandpass_filter(signals, sample_frequency, low_freq=1.0, high_freq=70.0)
notch_filter(signals, sample_frequency, notch_freq=60.0, Q=30.0)

# End-to-end pipeline: raw data → SVG
eeg_to_svg(signals, sample_frequency,
    montage=None, low_freq=1.0, high_freq=70.0,
    notch_freq=None, target_frequency=None,
    max_samples_per_channel=None, **kwargs) -> str
save_eeg_svg(filepath, signals, sample_frequency, **kwargs)
```

### Pipeline Steps

```
raw_signals (N channels, T samples)
  1. downsample (optional, via scipy.signal.decimate)
  2. montage matrix multiply → derived signals (M channels, T samples)
  3. generate montage labels (from montage.montage_labels)
  4. bandpass filter (via eegml_signal.filters FIR highpass + lowpass)
  5. notch filter (optional, via eegml_signal.filters IIR notch)
  6. render as SVG polylines with labels, scale bars, time axis
  7. write .svg file
```

### SVG Structure
This is the initial stab at the SVG structure. May want to factor this more to
descriminate better between data traces and annotations in the future.

```xml
<svg xmlns="..." viewBox="0 0 {width_mm} {height_mm}" width="{width_mm}mm" height="{height_mm}mm">
  <rect width="100%" height="100%" fill="white"/>
  <style>text { font-family: sans-serif; font-size: 3.5px; } ...</style>
  <g class="grid">          <!-- vertical grid lines at time intervals -->
  <rect .../>               <!-- plot border -->
  <g class="traces">        <!-- one <g class="channel"> per channel -->
    <g class="channel" id="ch-0">
      <text class="label">Fp1-F7</text>
      <polyline points="..." stroke="black" fill="none"/>
    </g>
  </g>
  <g class="timeaxis">      <!-- time labels along bottom -->
  <g class="scalebar">      <!-- vertical scale bar with end caps + label -->
</svg>
```

### Key Design Decisions

1. **No matplotlib dependency** — pure `xml.etree.ElementTree` SVG generation.
2. **Coordinate system** — viewBox in mm. SVG y-down naturally gives "negative is up" clinical convention.
3. **One polyline per channel** — following StratusEEG pattern.
4. **Channel spacing** — auto mode (0.7 × data range) or sensitivity mode (µV/mm).
5. **Filtering via eegml_signal** — uses existing FIR/IIR filter functions, with numtaps auto-limited to avoid filtfilt padding errors on short signals.
6. **Downsampling via scipy** — `scipy.signal.decimate` with anti-aliasing filter.
