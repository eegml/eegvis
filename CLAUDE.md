# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

eegvis is a Python library for visualizing EEG (electroencephalogram) data with
multiple backends: matplotlib (static), **pure SVG** (clinical-style stacked
traces, no matplotlib dependency), bokeh (interactive), and panel (dashboards).
It targets clinical EEG workflows with montage-based channel derivations.

A growing focus of the project is **SVG output** for clinical-style review:
both standalone files for reports/printing and a hypermedia browser-based
viewer built on FastAPI + datastar + ztml.

## Build & Development

```bash
# Install in development mode (uses flit backend)
pip install -e .

# With optional EDF file support
pip install -e ".[eeghdf]"
pip install -e ".[pyedflib]"    # pyedflib must be <=0.1.22 (sample_frequency bug in later versions)
```

Core dependencies now include `fastapi`, `datastar-py>=0.8.0`, and `ztml>=0.2.4`
to support the hypermedia viewer (see `eegvis/viewer/`).

## Testing

```bash
# Run tests with pytest
pytest tests/
pytest tests/test_stackplot_svg.py        # SVG backend tests
pytest tests/test_montage_display.py      # MontageDisplay / bundled profiles

# Run via tox (multiple Python/matplotlib versions)
tox
tox -e py310
tox -e py37-mpl3.2    # tests against matplotlib 3.2 (Colab compatibility)
```

A local pre-commit hook in `.git/hooks/pre-commit` runs `uvx ruff format` on
staged `.py` files and re-stages them. Bypass with `--no-verify`.

## Architecture

### Visualization Backends (parallel implementations)

- **`stacklineplot.py`** — Matplotlib backend using LineCollection with AffineDeltaTransform (backported from mpl 3.3 for 3.2 compatibility). Static/publication output.
- **`stackplot_svg.py`** — Pure SVG backend (no matplotlib). Generates standalone SVG strings/files using `xml.etree.ElementTree`. Native y-down axis gives "negative up" clinical convention for free.
- **`stackplot_bokeh.py`** — Bokeh backend with ipywidgets integration and `push_notebook()` for interactive Jupyter use.
- **`eegpanel.py`** / **`eegbokeh.py`** — Experimental Panel and pure-Bokeh browser implementations.

### SVG Backend (`stackplot_svg.py`)

The SVG backend is structured as a pipeline of pure functions:

- **`stackplot_svg(signals, sample_frequency, ...)`** — Core renderer. Returns
  an SVG string. Layout is in millimeter units via `viewBox`. Each channel is a
  `<g class="channel">` containing a `<text class="label">` and a `<polyline>`
  whose `points` are time-in-SVG-units paired with raw data values; per-channel
  `scale(1, y_scale_factor)` transforms map data units to SVG y. Strokes use
  `vector-effect="non-scaling-stroke"` so line weight stays constant under
  zoom. Includes vertical time grid, scale bar (µV by default), border,
  channel labels, and an empty `<g class="annotations">` layer for downstream
  viewer overlays. Extra knobs:
  - `theme=` picks a `SvgTheme` (background, grid, trace, label colors and
    weights). Bundled themes: `DEFAULT_THEME`, `PUBLICATION_THEME`,
    `STRATUS_THEME` (color-cycles traces in `color_group_size`-channel bands).
  - `channel_gaps_mm=` is a per-channel sequence of extra vertical mm to
    insert *after* each channel — used for inter-group spacers.
  - `channel_colors=` is a per-channel sequence of explicit color overrides
    that wins over the theme's group-cycled color.
  - `preserve_aspect_ratio=` is written verbatim to the SVG root attribute
    (default: omit). Set to `"none"` to let the SVG stretch independently
    in x and y to fill its container — used by the viewer to spread
    waveforms edge-to-edge.
- **`save_svg(filepath, ...)`** — Writes the SVG string to disk.
- **`show_montage_svg` / `save_montage_svg`** — Convenience wrappers that
  apply a `MontageView.V.data` matrix multiply before rendering and use
  `montage.montage_labels` as channel labels.
- **`show_montage_display_svg(signals, sample_frequency, display, rec_labels=, ...)` /
  `save_montage_display_svg`** — Render using a `MontageDisplay` profile
  (see below). Honors the display's group order, per-group/per-channel
  colors, gaps, gains, and visibility. Flips channel order before calling
  `stackplot_svg` so that profiles can keep the clinical "first listed =
  top of page" convention while the underlying renderer numbers channels
  bottom-up.
- **`eeg_to_svg(signals, sample_frequency, montage=, low_freq=, high_freq=, notch_freq=, target_frequency=, max_samples_per_channel=, ...)`**
  — End-to-end pipeline: downsample → montage derivation → bandpass → notch → render.
- **`save_eeg_svg(filepath, ...)`** — File-output sibling of `eeg_to_svg`.

Supporting helpers in the same module:

- **`downsample(signals, fs, target_fs)`** — `scipy.signal.decimate`-based, returns `(signals, new_fs)`.
- **`bandpass_filter` / `notch_filter`** — Thin wrappers over `eegml_signal.filters` (FIR firwin highpass/lowpass; IIR notch).
- **`_compute_channel_offsets`** — Computes per-channel vertical offsets in data space. Two modes: absolute (sensitivity in data_units/mm × plot height) and auto (`(max - min) * 0.7`).

SVG output carries data on the root and on each channel group (`data-sample-frequency`,
`data-start-time`, `data-seconds`, `data-num-channels`, plus per-channel
`data-baseline`, `data-channel-name`, `data-channel-index`, `data-yscale`).
These attributes are intended to be consumed by the viewer's client-side code
and by annotation tooling.

`max_samples_per_channel` is the main lever for keeping SVG file size sane on
high-sample-rate recordings — it triggers a one-shot decimation tuned so each
polyline has at most that many points.

### Montage Display Profiles (`montage_display.py` + `displays/`)

A `MontageDisplay` bundles three things that historically lived in separate
places: the derivation (matrix or built-in name), the channel grouping/order,
and per-channel style overrides. It is the canonical way to author a
clinical layout that wants per-hemisphere coloring or visual spacers between
chains.

- **`MontageDisplay`** carries `derivation_ref` (a name like `"double_banana"`
  resolved against `_BUILTIN_DERIVATIONS`) or a self-contained
  `MontageDerivation(matrix, montage_labels, rec_labels)`, a list of
  `ChannelGroup` (name, channels, default color, `gap_after_mm`), and a dict
  of per-channel `ChannelStyle` overrides (color, gain, gap, visibility).
- **Order convention**: channels listed earlier in the file are drawn
  *higher* on the page. `gap_after_mm` inserts space *below* that group or
  channel.
- **`save() / load()`** serialize a profile to / from JSON.
- **`eegvis/displays/`** ships JSON profiles next to the package. Use
  `from eegvis.displays import list_displays, load_display`. Currently
  bundled:
  - `double_banana.json` — clinical "left chains | midline | right chains"
    layout, blue/black/red coloring, with two large spacers at the left↔right
    transitions around the midline.
  - `double_banana_paired.json` — LT/RT, LL/RR stacked layout with spacers
    between every left/right hand-off.

### Hypermedia Clinical Viewer (`eegvis/viewer/`)

A FastAPI app that renders SVG pages of EEG and streams updates via datastar
Server-Sent Events. The server holds session state and re-renders SVG on each
navigation/filter change — clients are mostly passive consumers of HTML/SVG
patches.

- **`viewer/app.py`** — FastAPI routes. `GET /` serves the initial page;
  `/api/navigate`, `/api/keydown`, `/api/set_montage`, `/api/set_sensitivity`,
  `/api/set_page_duration`, `/api/set_filter` return `DatastarResponse` SSE
  streams that patch `#eeg-display`, `#jump-bar`, and `#status-bar`. Studies
  are registered via `load_study(study_id, signals, sample_frequency, channel_labels, montage_names)`.
  `_render_page_svg` slices the current time window, applies session filters,
  per-channel gains from `MontageState`, and calls `stackplot_svg`.
- **`viewer/session.py`** — `ViewerSession`, `MontageState`, and `SessionStore`
  dataclasses. Tracks current time, page duration, montage, per-channel gain/lock/visibility,
  filter cutoffs, and global sensitivity (µV/mm). Provides
  `SENSITIVITY_PRESETS` and `PAGE_DURATION_PRESETS` lists matching common
  clinical defaults.
- **`viewer/components.py`** — ztml HTML components for the page shell, toolbar
  (montage / sensitivity / page-duration / nav / filter selects), display
  area, jump bar, and status bar. Uses datastar `data-on:*` and `data-bind`
  attributes; loads the datastar runtime from the jsDelivr CDN. Layout is a
  fixed-height (`100vh`) flex column: toolbar / jump-bar / status-bar take
  their natural size; `.display-area` flex-grows to fill the rest and the
  SVG inside is rendered with `preserveAspectRatio="none"` so the waveforms
  span edge-to-edge horizontally.

Run the demo with synthetic data:

```bash
uv run python -m eegvis.viewer.app           # one-shot demo on :8000
uv run uvicorn eegvis.viewer.app:app --reload
```

`create_demo_study()` synthesizes a 19-channel × 2-minute mix of alpha, theta,
noise, and 60 Hz line noise so the viewer is exercisable without real data.

### Montage System

- **`montageview.py`** — Defines clinical EEG montages (Double Banana, TCP, Laplacian, etc.) as linear transformation matrices using xarray DataArrays over OrderedDicts of channels.
- **`montage_derivations_edf_simplified.py`** — Montage matrices for EDF-specific channel naming conventions ("EEG FP1", "EEG F3" style).

### Data Abstraction

- **`nb_eegview.py`** contains `MinimalEEGRecord` — the standard data container wrapping `signals` (channels × samples numpy array) + `sample_frequency`, with optional electrode labels, montages, and datetime metadata.

### Signal Processing

- Filtering uses external `eegml_signal.filters` package (notch, low-pass, high-pass).
- Known issue: firwin filters can produce ringing artifacts.

### Support Modules

- **`mpl_helpers.py`** — Matplotlib coordinate transforms and canvas utilities.
- **`utils/laplacian.py`** — Laplacian montage implementation with XML configuration.

## Key Conventions

- Signal data is stored as numpy arrays shaped (channels × samples).
- Montage derivations are expressed as xarray matrix operations over ordered channel dictionaries.
- Clinical "negative up" display: in the SVG backend this falls out of SVG's
  native y-down axis — raw data values map directly without sign flip.
- SVG layout coordinates are in millimeters via `viewBox`. Standalone exports
  rely on the default `preserveAspectRatio="xMidYMid meet"` (letterbox to
  preserve aspect for print); the viewer overrides this to `"none"` to fill
  the available container in both dimensions.
- Channel ordering: `stackplot_svg` numbers channels bottom-up (index 0 at
  the bottom), but `MontageDisplay` and its `show_montage_display_svg`
  wrapper expose the inverse convention (first listed = top of page).
  Author profiles in clinical top-down order.
- Python 3.7+ required (f-strings). Some files retain `__future__` imports for historical compatibility.
- matplotlib >=3.2 is supported via backported `AffineDeltaTransform`.
