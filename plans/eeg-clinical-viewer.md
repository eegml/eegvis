# EEG Clinical Viewer — Design Plan

Date: 2026-03-27

## Use Cases (priority order)

1. **Clinical web viewer** — hypermedia/datastar, server-driven
2. **Jupyter notebook** — static SVG + interactive iframe viewer
3. **Publication figures** — clean SVG for Illustrator/Inkscape/Affinity

## Architecture

### Two Web Components

- **Component I (build now):** Thin datastar-driven element. Server renders all SVG. Client handles gain/visibility locally via SVG transforms. No shadow DOM — datastar owns reactivity.
- **Component II (deferred):** Full client-side JS with in-browser signal processing. Fetches raw signal data from server API, stores in client buffer. Requires JS port of rendering pipeline (montage math, filtering, SVG generation). Build after Component I is stable.

### Server

- **Framework:** FastAPI / Starlette
- **HTML/SVG generation:** fasthtml-style Python tag functions (no templates)
- **Data access:** eeghdf (HDF5) or edfarray (Rust-based EDF reader)
- **Communication:** SSE for pushing SVG fragments and annotation data to client

## SVG Structure

Refactor `stackplot_svg.py` to support interactive use:

```xml
<svg viewBox="0 0 {width_mm} {height_mm}">
  <g class="traces">
    <g class="channel" id="ch-0" transform="translate(0, {baseline_y})" data-baseline="{baseline_y}">
      <text class="label">Fp1-F7</text>
      <polyline transform="scale(1, {gain})" points="..." stroke="black" fill="none"/>
    </g>
    <!-- ... more channels ... -->
  </g>
  <g class="annotations">
    <!-- point events: vertical lines -->
    <!-- duration events: semi-transparent rectangles -->
    <!-- text labels -->
  </g>
  <g class="grid"><!-- vertical grid lines --></g>
  <g class="timeaxis"><!-- time labels --></g>
  <g class="scalebar"><!-- amplitude reference --></g>
</svg>
```

Key changes from current implementation:
- Separate `translate` (baseline offset) from `scale` (gain) in channel transforms
- `data-*` attributes for JS discoverability (baseline, channel name, sample rate, time window)
- Separate `<g class="annotations">` layer
- Per-channel gain as array-valued `yscale`

## Interaction Model

### Channel Selection and Gain

- **Select channel:** Click on channel label
- **Per-channel gain:** Up/down arrow keys when a channel is selected
- **Global sensitivity:** Up/down arrow keys when nothing is selected (excludes locked channels)
- **Sensitivity presets:** 1, 2, 3, 5, 7, 10, 15, 20, 30, 50, 70 uV/mm
- **Lock channel:** Right-click context menu on channel label
  - Locked channels ignore global sensitivity changes
  - Locked channels still respond to direct per-channel adjustment when selected

### Time Navigation

- **Page forward/back:** Left/right arrow keys (one full page)
- **Fine step:** j/k and h/l keys (1 second or 10% of page)
- **Jump to time:** Text input field
- **Jump bar:** High-level overview of events across entire recording (up to 24 hrs)
  - Clicking on bar jumps to that time point
  - Scrubber/scrollbar below the jump bar
  - Populated lazily — server computes in background, pushes via SSE when ready
- **Page durations:** 2, 5, 10, 15, 20, 30, 60, 120, 300 seconds

### Montage

- **Switching:** Dropdown/select in toolbar
- **Available montages:** Everything in `montageview.py` (Double Banana, TCP transverse, Laplacian, common average, referential, etc.) plus future additions
- **Per-montage gain state:** Cached server-side per session. Each montage remembers its own channel gains, locks, and visibility. Gains persist when switching between montages.
- **Reset:** User can explicitly reset per-montage gains

### Filters

- **Implementation:** IIR Butterworth (default), FIR available as secondary option
- **Low-frequency filter (high-pass):** 0.1, 0.3, 0.5, 1.0, 1.5, 2.0, 5.0 Hz
- **High-frequency filter (low-pass):** 15, 20, 30, 35, 40, 50, 70, 100 Hz
- **Notch filter:** Off, 50 Hz, 60 Hz
- **Filter changes trigger server re-render** (modifies waveform data, not just display)

### Annotations

- **Create:** Press `a` to enter annotation mode, type label text
  - Click to place point event
  - Click-drag to place duration event
- **Edit:** After placement, move with cursor keys or drag
- **Display:**
  - Point events: vertical lines
  - Duration events: colored semi-transparent rectangles
  - Text labels above/below traces
  - Visible as colored markers in the jump bar
- **Scope:** Global (not channel-specific) to start
- **Storage:** Server-side, persisted to both database and BIDS-compatible TSV sidecar file

## Data Flow (Component I — Hypermedia)

1. **Initial load** — Server sends HTML with datastar-driven `<eeg-viewer>` element + initial SVG + annotation data
2. **Navigation / montage / filter change** — Datastar event → server request → server computes new SVG via `stackplot_svg.py` → SSE push → datastar swaps SVG fragment
3. **Gain / visibility change** — Local SVG transform manipulation via datastar reactive variables, no server round-trip
4. **Annotation creation** — Sent to server → persisted to database + BIDS TSV sidecar → updated SVG pushed back
5. **Jump bar** — Server lazily computes annotation overview in background → SSE push when ready

## Session State

- **Scope:** Per-study, per-session
- **Initial implementation:** In-memory on server
- **Later:** Persist last session to database so it can survive server restart
- **State includes:**
  - Current montage selection
  - Per-montage: channel gains, locks, visibility
  - Current time position
  - Current page duration
  - Filter settings (HP, LP, notch, filter type)

## Annotation Storage

### BIDS-compatible TSV sidecar (`*_events.tsv`)

| onset | duration | trial_type | created_by | created_at | channel |
|-------|----------|------------|------------|------------|---------|
| 3.200 | 0.0 | spike | | | |
| 12.000 | 33.3 | seizure | | | |

### Database

Equivalent schema — same columns, queryable for jump bar and cross-study search.

## Downsampling Strategy

Compare two approaches empirically:
- **Points-per-pixel:** Downsample to match viewport pixel width. Client sends viewport width to server.
- **Min-max decimation:** Keep min and max per bucket to preserve spike envelope.

Evaluate on real clinical EEG with known spikes/sharps to determine which preserves diagnostically relevant features.

## Notebook Integration (Use Case 2)

- `plot_eeg_svg()` — Static inline SVG via `IPython.display.SVG`. No server needed.
- `view_eeg()` — Spins up background FastAPI server, embeds interactive viewer via iframe. Reuses the same hypermedia component from Component I.

## Publication Figures (Use Case 3)

- Clean SVG output with no controls or interactive elements
- Suitable for import into Adobe Illustrator, Affinity Designer, Inkscape
- Uses same `stackplot_svg.py` rendering, stripped to essentials

## Implementation Phases

### Phase 1 — SVG Structure Changes (prerequisite)
- Refactor `stackplot_svg.py`: separate translate (baseline) from scale (gain)
- Add `data-*` attributes for JS discoverability
- Support per-channel gain as array-valued `yscale`
- Add `<g class="annotations">` layer

### Phase 2 — Hypermedia Web Component (Component I)
- Define thin `<eeg-viewer>` custom element with datastar
- Local JS: gain adjustment via SVG transform, channel show/hide
- FastAPI server: endpoints returning SVG fragments for time window + montage + filters
- SSE integration

### Phase 3 — Clinical Viewer Features
- Time navigation (page, fine-step, jump-to, jump bar with scrubber)
- Montage switching with per-montage gain caching
- Sensitivity presets (1, 2, 3, 5, 7, 10, 15, 20, 30, 50, 70 uV/mm)
- IIR Butterworth + FIR filter options with clinical presets
- Annotations (point events, duration events, BIDS TSV + database storage)
- Downsampling comparison (points-per-pixel vs min-max)

### Phase 4 — Publication SVG (Use Case 3)
- Strip controls, simplify output
- Ensure clean vector import into Illustrator/Inkscape/Affinity

### Phase 5 — Notebook Integration (Use Case 2)
- `plot_eeg_svg()` static display
- `view_eeg()` with background server + iframe

### Phase 6 — Client-Side Component (Component II, deferred)
- JS signal processing pipeline
- Client-side SVG rendering
- Client-side montage/filter application
