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


def test_small_2channel_svg():
    """Generate a minimal 2-channel, 100-sample SVG for manual inspection.

    Output is written to test_small_2ch.svg in the current working directory.
    """
    fs = 100.0
    n = 100
    t = np.arange(n) / fs
    signals = np.zeros((2, n))
    signals[0, :] = 50.0 * np.sin(2 * np.pi * 3 * t)   # 3 Hz sine
    signals[1, :] = 30.0 * np.sin(2 * np.pi * 10 * t)   # 10 Hz sine

    stackplot_svg.save_svg(
        "test_small_2ch.svg",
        signals,
        sample_frequency=fs,
        seconds=n / fs,
        ylabels=["3 Hz (50uV)", "10 Hz (30uV)"],
        width_mm=200,
        height_mm=100,
    )


def test_downsample_reduces_samples():
    """downsample should reduce sample count by the decimation factor."""
    signals = np.random.randn(3, 2560)  # 10s at 256 Hz
    ds, new_fs = stackplot_svg.downsample(signals, 256.0, 64.0)
    assert ds.shape[0] == 3
    assert ds.shape[1] == 2560 // 4  # factor of 4
    assert new_fs == 64.0


def test_downsample_noop_when_already_low():
    """downsample should return data unchanged if fs <= target."""
    signals = np.random.randn(2, 100)
    ds, new_fs = stackplot_svg.downsample(signals, 50.0, 256.0)
    assert ds is signals  # same object, not a copy
    assert new_fs == 50.0


def test_max_samples_per_channel_limits_polyline_points():
    """max_samples_per_channel should produce fewer points in SVG."""
    signals = np.random.randn(2, 5000)  # high sample count
    svg_full = stackplot_svg.stackplot_svg(signals, sample_frequency=1000.0, seconds=5.0)
    svg_ds = stackplot_svg.stackplot_svg(
        signals, sample_frequency=1000.0, seconds=5.0, max_samples_per_channel=500
    )
    # downsampled SVG should be substantially smaller
    assert len(svg_ds) < len(svg_full) * 0.5


def test_bandpass_filter_attenuates_out_of_band():
    """Bandpass 5-30 Hz should attenuate a 1 Hz and a 100 Hz signal."""
    fs = 512.0
    n = int(fs * 4)  # 4 seconds for filter settling
    t = np.arange(n) / fs
    signals = np.zeros((2, n))
    signals[0, :] = np.sin(2 * np.pi * 1.0 * t)    # 1 Hz — below band
    signals[1, :] = np.sin(2 * np.pi * 100.0 * t)   # 100 Hz — above band

    filtered = stackplot_svg.bandpass_filter(signals, fs, low_freq=5.0, high_freq=30.0)

    # middle portion (avoid edge effects) should be heavily attenuated
    mid = slice(n // 4, 3 * n // 4)
    assert np.std(filtered[0, mid]) < 0.1  # 1 Hz mostly removed
    assert np.std(filtered[1, mid]) < 0.1  # 100 Hz mostly removed


def test_bandpass_filter_preserves_in_band():
    """Bandpass 1-70 Hz should preserve a 10 Hz signal."""
    fs = 256.0
    n = int(fs * 4)
    t = np.arange(n) / fs
    signals = np.zeros((1, n))
    signals[0, :] = np.sin(2 * np.pi * 10.0 * t)

    filtered = stackplot_svg.bandpass_filter(signals, fs, low_freq=1.0, high_freq=70.0)

    mid = slice(n // 4, 3 * n // 4)
    # amplitude should be mostly preserved (within 10%)
    assert np.std(filtered[0, mid]) > 0.6


def test_notch_filter_removes_line_noise():
    """Notch at 60 Hz should attenuate 60 Hz while preserving 10 Hz."""
    fs = 512.0
    n = int(fs * 4)
    t = np.arange(n) / fs
    signals = np.zeros((1, n))
    signals[0, :] = np.sin(2 * np.pi * 10.0 * t) + np.sin(2 * np.pi * 60.0 * t)

    filtered = stackplot_svg.notch_filter(signals, fs, notch_freq=60.0)

    mid = slice(n // 4, 3 * n // 4)
    # 60 Hz component should be gone; 10 Hz should remain
    # original std is ~1.0 (two unit sines), filtered should be ~0.7 (one sine)
    assert 0.5 < np.std(filtered[0, mid]) < 0.9


def test_eeg_to_svg_basic():
    """eeg_to_svg should produce valid SVG with default bandpass."""
    fs = 256.0
    n = int(fs * 10)
    signals = np.random.randn(4, n) * 50.0

    svg_str = stackplot_svg.eeg_to_svg(
        signals, fs,
        ylabels=["Ch1", "Ch2", "Ch3", "Ch4"],
        seconds=10.0,
    )
    root = ET.fromstring(svg_str)
    assert root.tag == f"{{{stackplot_svg.SVG_NS}}}svg"
    ns = {"svg": stackplot_svg.SVG_NS}
    assert len(root.findall(".//svg:g[@class='channel']", ns)) == 4


def test_eeg_to_svg_with_montage():
    """eeg_to_svg with a montage should use montage labels."""
    from eegvis.montageview import DoubleBananaMontageView

    rec_labels = [
        "Fp1", "Fp2", "F3", "F4", "C3", "C4", "P3", "P4",
        "O1", "O2", "F7", "F8", "T3", "T4", "T5", "T6",
        "Fz", "Cz", "Pz",
    ]
    montage = DoubleBananaMontageView(rec_labels)
    fs = 256.0
    n = int(fs * 10)
    signals = np.random.randn(len(rec_labels), n) * 50.0

    svg_str = stackplot_svg.eeg_to_svg(signals, fs, montage=montage, seconds=10.0)

    # should contain montage-derived labels
    assert "Fp1-F7" in svg_str
    assert "F7-T3" in svg_str


def test_eeg_to_svg_no_filter():
    """eeg_to_svg with filters disabled should still produce valid SVG."""
    fs = 256.0
    n = int(fs * 5)
    signals = np.random.randn(2, n) * 30.0

    svg_str = stackplot_svg.eeg_to_svg(
        signals, fs, low_freq=None, high_freq=None, seconds=5.0,
    )
    root = ET.fromstring(svg_str)
    assert root.tag == f"{{{stackplot_svg.SVG_NS}}}svg"


def test_eeg_to_svg_with_notch_and_downsample():
    """eeg_to_svg with all pipeline steps enabled."""
    fs = 1000.0
    n = int(fs * 10)
    signals = np.random.randn(3, n) * 50.0

    svg_str = stackplot_svg.eeg_to_svg(
        signals, fs,
        low_freq=1.0, high_freq=70.0,
        notch_freq=60.0,
        target_frequency=256.0,
        max_samples_per_channel=1000,
        seconds=10.0,
    )
    root = ET.fromstring(svg_str)
    ns = {"svg": stackplot_svg.SVG_NS}
    assert len(root.findall(".//svg:g[@class='channel']", ns)) == 3


def test_save_eeg_svg(tmp_path):
    """save_eeg_svg should write a valid SVG file through the full pipeline."""
    filepath = tmp_path / "pipeline_output.svg"
    fs = 256.0
    n = int(fs * 5)
    signals = np.random.randn(3, n) * 50.0

    stackplot_svg.save_eeg_svg(
        str(filepath), signals, fs,
        low_freq=1.0, high_freq=70.0,
        seconds=5.0,
    )
    assert filepath.exists()
    root = ET.fromstring(filepath.read_text())
    assert root.tag == f"{{{stackplot_svg.SVG_NS}}}svg"
