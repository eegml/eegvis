# Plan: SSE-based Real-time EEG Polyline Streaming with Datastar

## Context

The user wants to prototype real-time EEG visualization by streaming polyline updates from a Python server to the browser via Server-Sent Events. Rather than building SSE into a web component, Datastar handles the SSE connection and DOM patching. The server generates SVG polyline fragments and sends them as `datastar-patch-elements` events that replace polyline elements inside the existing interactive SVG.

## Changes

### 1. Add `generate_polyline_data()` to `eegvis/stackplot_svg.py`

Factor out the polyline points computation from the interactive block (lines ~421-454) into a standalone function:

```python
def generate_polyline_data(signals, seconds, yscale=1.0, topdown=True, channel_order=None):
```

- Takes already-processed signals `(num_channels, num_samples)`
- Returns `list[str]` — one points string per channel in draw order
- Reuses existing `_format_data_points()` helper (line 131)
- Refactor the interactive loop in `stackplot_svg()` to call this function instead of computing inline

### 2. Create `scripts/datastar_sse_demo.py` — Litestar SSE server

**Run:** `uv run --with litestar --with uvicorn python scripts/datastar_sse_demo.py`

- `GET /` — serves HTML page with:
  - Datastar loaded from CDN (`https://cdn.jsdelivr.net/gh/starfederation/datastar@v1/bundles/datastar.js`)
  - Initial full SVG rendered via `eeg_to_svg(..., interactive=True)` in the light DOM (not shadow DOM — Datastar needs selector access)
  - `data-init="@get('/feed')"` to auto-connect to SSE on page load
- `GET /feed` — SSE endpoint using Litestar's `Stream` response that:
  - Pre-generates ~120s of simulated EEG (21 channels: 20 EEG + 1 EKG)
  - Every ~0.5s, advances a 10s sliding window and emits `datastar-patch-elements` events
  - One event per channel: `selector #ch-{i} polyline`, `mode outer`, `namespace svg`
  - Also updates a time display span

### 3. Add tests for `generate_polyline_data` in `tests/test_stackplot_svg.py`

- Verify it returns correct number of point strings
- Verify output matches polylines from interactive SVG (consistency check)
- Verify `channel_order` parameter works

## Files

| File | Action |
|------|--------|
| `eegvis/stackplot_svg.py` | Add `generate_polyline_data()`, refactor interactive loop to use it |
| `scripts/datastar_sse_demo.py` | New — litestar SSE demo server |
| `tests/test_stackplot_svg.py` | Add 2-3 tests for `generate_polyline_data` |

## Verification

1. `uv run python -m pytest tests/ -v` — all existing tests pass, new tests pass
2. `uv run --with litestar --with uvicorn python scripts/datastar_sse_demo.py` — open http://localhost:8000, verify polylines update in real-time as the time window scrolls
