"""Serve interactive EEG viewer as a standalone HTML page.

Wraps an interactive SVG (from stackplot_svg(..., interactive=True)) in an HTML
page with the <eeg-viewer> Lit web component. The HTML page loads Lit and the
component from CDN/esm.sh so no local npm install is required for previewing.
"""

import html as html_mod
from pathlib import Path

import jinja2

from eegvis.stackplot_svg import eeg_to_svg

_TEMPLATE_DIR = Path(__file__).parent / "templates"
_jinja_env = jinja2.Environment(
    loader=jinja2.FileSystemLoader(_TEMPLATE_DIR),
    autoescape=False,
    auto_reload=False,
)


def render_eeg_html(signals, sample_frequency, montage=None, **kwargs):
    """Generate a standalone HTML page with the <eeg-viewer> web component.

    Args:
        signals: raw signals (num_channels, num_samples) numpy array
        sample_frequency: sampling rate in Hz
        montage: optional MontageView instance
        **kwargs: passed to eeg_to_svg()

    Returns:
        HTML content as a string
    """
    import json

    svg_str = eeg_to_svg(
        signals, sample_frequency, montage=montage,
        interactive=True, **kwargs,
    )
    svg_json = json.dumps(svg_str)
    template = _jinja_env.get_template("eeg_viewer.html")
    return template.render(svg_json=svg_json)


def save_eeg_html(filepath, signals, sample_frequency, **kwargs):
    """Generate and save a standalone HTML EEG viewer page.

    Args:
        filepath: output file path
        signals: raw signals (num_channels, num_samples) numpy array
        sample_frequency: sampling rate in Hz
        **kwargs: passed to render_eeg_html()
    """
    html_str = render_eeg_html(signals, sample_frequency, **kwargs)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(html_str)
