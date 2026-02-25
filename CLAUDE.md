# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

eegvis is a Python library for visualizing EEG (electroencephalogram) data with
multiple backends: matplotlib (static), SVG, bokeh (interactive), and panel (dashboards). It targets clinical EEG workflows with montage-based channel derivations.

## Build & Development

```bash
# Install in development mode (uses flit backend)
pip install -e .

# With optional EDF file support
pip install -e ".[eeghdf]"
pip install -e ".[pyedflib]"    # pyedflib must be <=0.1.22 (sample_frequency bug in later versions)
```

## Testing

```bash
# Run tests with pytest
pytest tests/

# Run via tox (multiple Python/matplotlib versions)
tox
tox -e py310
tox -e py37-mpl3.2    # tests against matplotlib 3.2 (Colab compatibility)
```

## Architecture

### Visualization Backends (three parallel implementations)

- **`stacklineplot.py`** — Matplotlib backend using LineCollection with AffineDeltaTransform (backported from mpl 3.3 for 3.2 compatibility). Static/publication output.
- **`stackplot_bokeh.py`** — Bokeh backend with ipywidgets integration and `push_notebook()` for interactive Jupyter use.
- **`eegpanel.py`** / **`eegbokeh.py`** — Experimental Panel and pure-Bokeh browser implementations.

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
- Python 3.7+ required (f-strings). Some files retain `__future__` imports for historical compatibility.
- matplotlib >=3.2 is supported via backported `AffineDeltaTransform`.
