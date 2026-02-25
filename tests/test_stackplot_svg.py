import numpy as np
import xml.etree.ElementTree as ET
import eegvis.stackplot_svg as stackplot_svg


def make_sine_signals(num_channels=5, num_samples=800, fs=256.0):
    """Generate multi-channel sine wave test data at different frequencies."""
    t = np.arange(num_samples) / fs
    signals = np.zeros((num_channels, num_samples))
    for i in range(num_channels):
        freq = 2 + i * 3  # 2, 5, 8, 11, 14 Hz
        signals[i, :] = 50.0 * np.sin(2 * np.pi * freq * t)
    return signals


def make_calibration_signal(num_samples, levels=None):
    if levels is None:
        levels = [0, 10, -10, 10, -10]
    interval = num_samples // len(levels)
    data = np.zeros(num_samples)
    for ii, level in enumerate(levels):
        data[ii * interval : (ii + 1) * interval] = level
    return data


def test_stackplot_svg_returns_valid_svg():
    """Verify returned string is parseable SVG with expected structure."""
    signals = np.random.randn(5, 800)
    svg_str = stackplot_svg.stackplot_svg(signals, sample_frequency=256.0, seconds=3.0)

    # must be parseable XML
    root = ET.fromstring(svg_str)
    assert root.tag == f"{{{stackplot_svg.SVG_NS}}}svg"

    # should have channel groups
    ns = {"svg": stackplot_svg.SVG_NS}
    channels = root.findall(".//svg:g[@class='channel']", ns)
    assert len(channels) == 5


def test_stackplot_svg_channel_labels():
    """Channel labels should appear as text elements."""
    labels = ["Fp1-F7", "F7-T3", "T3-T5", "T5-O1"]
    signals = np.random.randn(4, 500)
    svg_str = stackplot_svg.stackplot_svg(
        signals, sample_frequency=256.0, ylabels=labels
    )

    for label in labels:
        assert label in svg_str


def test_stackplot_svg_with_sensitivity():
    """Sensitivity mode should produce valid SVG."""
    signals = np.random.randn(5, 800)
    svg_str = stackplot_svg.stackplot_svg(
        signals, sample_frequency=256.0, seconds=3.0, sensitivity=7.0
    )
    root = ET.fromstring(svg_str)
    assert root.tag == f"{{{stackplot_svg.SVG_NS}}}svg"


def test_stackplot_svg_no_grid():
    """Disabling grid should produce SVG without grid group."""
    signals = np.random.randn(3, 300)
    svg_str = stackplot_svg.stackplot_svg(
        signals, sample_frequency=256.0, grid_interval=None
    )
    root = ET.fromstring(svg_str)
    ns = {"svg": stackplot_svg.SVG_NS}
    grid = root.findall(".//svg:g[@class='grid']", ns)
    assert len(grid) == 0


def test_stackplot_svg_no_scalebar():
    """Disabling scalebar should produce SVG without scalebar group."""
    signals = np.random.randn(3, 300)
    svg_str = stackplot_svg.stackplot_svg(
        signals, sample_frequency=256.0, show_scalebar=False
    )
    root = ET.fromstring(svg_str)
    ns = {"svg": stackplot_svg.SVG_NS}
    scalebar = root.findall(".//svg:g[@class='scalebar']", ns)
    assert len(scalebar) == 0


def test_stackplot_svg_scalebar_present():
    """Default should include scalebar with unit text."""
    signals = np.random.randn(5, 800)
    svg_str = stackplot_svg.stackplot_svg(
        signals, sample_frequency=256.0, seconds=3.0
    )
    assert "\u00b5V" in svg_str  # µV


def test_stackplot_svg_time_labels():
    """Time axis labels should reflect start_time and duration."""
    signals = np.random.randn(3, 512)
    svg_str = stackplot_svg.stackplot_svg(
        signals, sample_frequency=256.0, seconds=2.0, start_time=5.0
    )
    # should contain time labels like "5s", "6s", "7s"
    assert "5s" in svg_str
    assert "6s" in svg_str
    assert "7s" in svg_str


def test_save_svg(tmp_path):
    """save_svg should write a file that is valid SVG."""
    filepath = tmp_path / "test_output.svg"
    signals = make_sine_signals()
    stackplot_svg.save_svg(str(filepath), signals, sample_frequency=256.0, seconds=3.0)

    assert filepath.exists()
    content = filepath.read_text()
    root = ET.fromstring(content)
    assert root.tag == f"{{{stackplot_svg.SVG_NS}}}svg"


def test_save_svg_with_calibration(tmp_path):
    """Visual test: save SVG with calibration signal on last channel."""
    filepath = tmp_path / "test_calibration.svg"
    num_samples = 800
    signals = np.random.randn(5, num_samples) * 30.0
    signals[-1, :] = make_calibration_signal(num_samples, levels=[0, 100, -100, 100, -100])

    labels = ["Ch1", "Ch2", "Ch3", "Ch4", "Cal 100\u00b5V"]
    stackplot_svg.save_svg(
        str(filepath),
        signals,
        sample_frequency=256.0,
        seconds=num_samples / 256.0,
        ylabels=labels,
    )
    assert filepath.exists()


def test_stackplot_svg_polyline_count():
    """Each channel should have exactly one polyline."""
    num_ch = 8
    signals = np.random.randn(num_ch, 400)
    svg_str = stackplot_svg.stackplot_svg(signals, sample_frequency=256.0)

    root = ET.fromstring(svg_str)
    ns = {"svg": stackplot_svg.SVG_NS}
    polylines = root.findall(".//svg:polyline", ns)
    assert len(polylines) == num_ch


def test_stackplot_svg_topdown_false():
    """With topdown=False, channel order should differ."""
    labels = ["A", "B", "C"]
    signals = np.random.randn(3, 200)

    svg_td = stackplot_svg.stackplot_svg(
        signals, sample_frequency=256.0, ylabels=labels, topdown=True
    )
    svg_bu = stackplot_svg.stackplot_svg(
        signals, sample_frequency=256.0, ylabels=labels, topdown=False
    )

    # both should be valid
    ET.fromstring(svg_td)
    ET.fromstring(svg_bu)

    # the label ordering in the SVG text should differ
    # In topdown, "A" label appears first (at top); in bottom-up, "C" appears first
    idx_a_td = svg_td.index(">A<")
    idx_c_td = svg_td.index(">C<")
    idx_a_bu = svg_bu.index(">A<")
    idx_c_bu = svg_bu.index(">C<")
    # topdown=True reverses order so C is drawn first (at top), A last (at bottom)
    # topdown=False keeps natural order so A is drawn first
    assert idx_c_td < idx_a_td
    assert idx_a_bu < idx_c_bu
