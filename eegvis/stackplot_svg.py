# -*- coding: utf-8 -*-
"""Pure SVG backend for EEG stack plotting.

Generates standalone SVG files from EEG signal data without requiring
matplotlib. Uses xml.etree.ElementTree for SVG construction.

The coordinate system follows clinical EEG convention where negative
voltages are displayed upward. SVG's native y-down axis makes this
straightforward: raw signal values map directly so that negative
deflections appear as upward movements on screen.
"""

import json

import numpy as np
import xml.etree.ElementTree as ET


SVG_NS = "http://www.w3.org/2000/svg"

# default styling
DEFAULT_TRACE_COLOR = "black"
DEFAULT_TRACE_WIDTH = "0.5"
DEFAULT_FONT_FAMILY = "sans-serif"
DEFAULT_FONT_SIZE = 3.5  # in SVG user units (mm in viewBox coordinates)
DEFAULT_GRID_COLOR = "#cccccc"
DEFAULT_GRID_WIDTH = "0.3"


def downsample(signals, sample_frequency, target_frequency):
    """Downsample signals to approximately target_frequency using scipy.signal.decimate.

    Applies an anti-aliasing filter before decimation. If sample_frequency
    is already at or below target_frequency, returns signals unchanged.

    Args:
        signals: (num_channels, num_samples) numpy array
        sample_frequency: original sampling rate in Hz
        target_frequency: desired output sampling rate in Hz

    Returns:
        (downsampled_signals, new_sample_frequency) tuple
    """
    if sample_frequency <= target_frequency:
        return signals, sample_frequency

    from scipy.signal import decimate

    factor = int(sample_frequency / target_frequency)
    if factor <= 1:
        return signals, sample_frequency

    downsampled = decimate(signals, factor, axis=1)
    new_fs = sample_frequency / factor
    return downsampled, new_fs


def bandpass_filter(signals, sample_frequency, low_freq=1.0, high_freq=70.0):
    """Apply a zero-phase bandpass filter to signals using eegml_signal.

    Uses FIR highpass and lowpass filters (firwin-based) applied sequentially.

    Args:
        signals: (num_channels, num_samples) numpy array
        sample_frequency: sampling rate in Hz
        low_freq: high-pass cutoff frequency in Hz.
            Set to None to skip high-pass (lowpass only).
        high_freq: low-pass cutoff frequency in Hz.
            Set to None to skip low-pass (highpass only).

    Returns:
        filtered signals with same shape as input
    """
    import eegml_signal.filters as esfilters

    result = signals.copy()
    num_samples = signals.shape[1]
    # filtfilt needs 3*numtaps < num_samples for padding
    max_taps = num_samples // 3 - 1

    if low_freq is not None:
        numtaps = min(max(int(2 * sample_frequency), 3), max_taps)
        if numtaps % 2 == 0:
            numtaps += 1  # highpass firwin needs odd numtaps
        hp = esfilters.fir_highpass_firwin_ff(sample_frequency, low_freq, numtaps)
        for ch in range(result.shape[0]):
            result[ch] = hp(result[ch])

    if high_freq is not None:
        numtaps = min(max(int(sample_frequency / 4.0), 3), max_taps)
        lp = esfilters.fir_lowpass_firwin_ff(sample_frequency, high_freq, numtaps)
        for ch in range(result.shape[0]):
            result[ch] = lp(result[ch])

    return result


def notch_filter(signals, sample_frequency, notch_freq=60.0, Q=30.0):
    """Apply a zero-phase notch (band-stop) filter to remove line noise.

    Uses eegml_signal's IIR notch filter.

    Args:
        signals: (num_channels, num_samples) numpy array
        sample_frequency: sampling rate in Hz
        notch_freq: frequency to remove in Hz (default: 60.0 for US mains)
        Q: quality factor controlling notch width (default: 30.0)

    Returns:
        filtered signals with same shape as input
    """
    import eegml_signal.filters as esfilters

    nf = esfilters.notch_filter_iir_ff(notch_freq, sample_frequency, Q)
    result = signals.copy()
    for ch in range(result.shape[0]):
        result[ch] = nf(result[ch])
    return result


def _format_points(t, y):
    """Convert time and amplitude arrays to SVG polyline points string.

    Rounds to 2 decimal places to keep file size reasonable.
    Uses numpy vectorized string formatting for performance.
    """
    coords = np.column_stack((np.round(t, 2), np.round(y, 2)))
    return " ".join(f"{x},{y}" for x, y in coords)


def _format_data_points(t_relative, amplitude):
    """Convert data-coordinate arrays to SVG polyline points string.

    Uses 4 decimal places for time (seconds) and 2 for amplitude.
    For interactive mode where polyline coordinates are in data space.
    """
    coords = np.column_stack((np.round(t_relative, 4), np.round(amplitude, 2)))
    return " ".join(f"{x},{y}" for x, y in coords)


def generate_polyline_data(signals, seconds, yscale=1.0, topdown=True, channel_order=None):
    """Compute SVG polyline points strings for each channel in draw order.

    Produces the same data-coordinate polyline points that stackplot_svg()
    embeds in interactive mode, but as standalone strings suitable for
    streaming updates (e.g. via SSE).

    Args:
        signals: (num_channels, num_samples) numpy array of signal data
        seconds: duration of the signal window in seconds
        yscale: gain multiplier applied to signal amplitudes
        topdown: if True, first channel appears at top (natural order)
        channel_order: explicit draw order as list of channel indices.
            If None, derived from topdown parameter.

    Returns:
        list[str]: one SVG polyline points string per channel in draw order
    """
    num_channels, num_samples = signals.shape
    data = signals.T  # (num_samples, num_channels)

    if channel_order is None:
        channel_order = list(range(num_channels))
        if not topdown:
            channel_order = list(reversed(channel_order))

    t_relative = seconds * np.arange(num_samples, dtype=float) / max(num_samples - 1, 1)

    points_list = []
    for ch_idx in channel_order:
        amplitude = yscale * data[:, ch_idx]
        points_list.append(_format_data_points(t_relative, amplitude))

    return points_list


def _compute_channel_offsets(data, num_channels, sensitivity=None, height=None):
    """Compute vertical offset for each channel.

    Args:
        data: (num_samples, num_channels) array
        num_channels: number of channels
        sensitivity: if set, absolute spacing in data units per channel
        height: total plot height in SVG units (used with sensitivity)

    Returns:
        ticklocs: list of y-offsets for each channel
        dr: spacing between channels
    """
    ch_indices = np.arange(num_channels, dtype=float)
    if sensitivity is not None and height is not None:
        # absolute sensitivity mode: distribute channels evenly across height
        dr = sensitivity * height / num_channels
        ticklocs = ch_indices * dr + dr / 2.0
    else:
        # auto mode: space based on data range
        dr = (data.max() - data.min()) * 0.7
        ticklocs = ch_indices * dr
    return ticklocs, dr


def stackplot_svg(
    signals,
    sample_frequency,
    ylabels=None,
    seconds=None,
    start_time=0.0,
    yscale=1.0,
    sensitivity=None,
    width_mm=300,
    height_mm=200,
    topdown=True,
    linecolor=None,
    linewidth=None,
    grid_interval=1.0,
    show_scalebar=True,
    scalebar_height=None,
    scalebar_units="\u00b5V",
    max_samples_per_channel=None,
    interactive=False,
    embed_js=False,
    channel_groups=None,
):
    """Generate an SVG string of stacked EEG traces.

    Args:
        signals: (num_channels, num_samples) numpy array of signal data
        sample_frequency: sampling rate in Hz
        ylabels: list of channel label strings
        seconds: duration to display (defaults to full signal duration)
        start_time: time offset for x-axis labels in seconds
        yscale: gain multiplier (scalar or per-channel array)
        sensitivity: absolute sensitivity in data_units/mm (e.g. 7 for 7 uV/mm).
            Overrides auto-scaling.
        width_mm: SVG width in mm
        height_mm: SVG height in mm
        topdown: if True, first channel appears at top
        linecolor: trace color (default: black)
        linewidth: trace stroke width
        grid_interval: time interval for vertical grid lines in seconds.
            Set to None to disable grid.
        show_scalebar: whether to draw a vertical scale bar
        scalebar_height: height of scale bar in data units.
            If None, auto-computed as ~10% of channel spacing.
        scalebar_units: units label for scale bar (default: µV)
        max_samples_per_channel: if set, downsample signals so each channel
            has at most this many samples. Reduces SVG file size for
            high sample rate data. Set to None to disable (default).
        interactive: if True, generate SVG with transform-based per-channel
            groups suitable for dynamic rescaling by a web component.
            Labels are separated from traces, polyline coordinates use
            data space (seconds, amplitude), and data-* attributes are
            added for JavaScript consumption.
        embed_js: reserved for future use (embed JS in SVG).
        channel_groups: dict mapping group names to lists of channel indices,
            e.g. {"EEG": [0,1,...,18], "EKG": [19]}. Used in interactive mode
            to add data-channel-group attributes. Default: None (all channels
            in a single "default" group).

    Returns:
        SVG content as a string
    """
    num_channels, num_samples = signals.shape

    if seconds is None:
        seconds = num_samples / sample_frequency

    # optional downsampling to limit SVG size
    if max_samples_per_channel is not None and num_samples > max_samples_per_channel:
        target_fs = max_samples_per_channel / seconds
        signals, sample_frequency = downsample(signals, sample_frequency, target_fs)
        num_channels, num_samples = signals.shape

    if ylabels is None:
        ylabels = [str(i) for i in range(num_channels)]

    if linecolor is None:
        linecolor = DEFAULT_TRACE_COLOR
    if linewidth is None:
        linewidth = DEFAULT_TRACE_WIDTH

    # layout constants (in viewBox units = mm)
    label_margin = 25  # left margin for channel labels
    top_margin = 5
    bottom_margin = 8  # space for time axis labels
    right_margin = 5
    scalebar_margin = 20 if show_scalebar else 0

    plot_width = width_mm - label_margin - right_margin - scalebar_margin
    plot_height = height_mm - top_margin - bottom_margin

    # transpose to (num_samples, num_channels) for processing
    data = signals.T

    # compute vertical offsets in data space
    ticklocs, dr = _compute_channel_offsets(
        yscale * data, num_channels, sensitivity=sensitivity, height=plot_height
    )

    def time_to_x(t):
        """Map time value(s) to SVG x-coordinate(s). Accepts scalars or arrays."""
        return label_margin + (t - start_time) / seconds * plot_width

    # compute mapping from data coordinates to SVG coordinates
    t_data = start_time + seconds * np.arange(num_samples, dtype=float) / max(num_samples - 1, 1)
    t_svg = time_to_x(t_data)

    # y axis: data values are offset by ticklocs, then mapped to SVG y
    # In SVG, y increases downward which gives us "negative is up" for free
    if sensitivity is not None:
        y_data_min = 0.0
        y_data_max = sensitivity * plot_height
    else:
        scaled = yscale * data
        y_data_min = scaled.min()
        y_data_max = (num_channels - 1) * dr + scaled.max()

    y_data_range = y_data_max - y_data_min

    def data_y_to_svg(y_data):
        """Map data y-coordinate(s) to SVG y-coordinate(s).

        Accepts scalars or numpy arrays.
        """
        if y_data_range == 0:
            return top_margin + 0.5 * plot_height
        return top_margin + (y_data - y_data_min) / y_data_range * plot_height

    # channel ordering: topdown=True means first channel at top (natural order)
    # SVG y increases downward, and ticklocs[0] < ticklocs[N-1], so natural
    # order already places draw_idx=0 at the top. Reverse only when NOT topdown.
    channel_order = list(range(num_channels))
    label_order = list(ylabels)
    if not topdown:
        channel_order = list(reversed(channel_order))
        label_order = list(reversed(label_order))

    # interactive mode: compute px_per_sec and y_scale for transforms
    px_per_sec = plot_width / seconds if seconds > 0 else 1.0
    if y_data_range != 0:
        y_scale_factor = plot_height / y_data_range
    else:
        y_scale_factor = 1.0

    # build SVG
    svg_attrs = {
        "xmlns": SVG_NS,
        "viewBox": f"0 0 {width_mm} {height_mm}",
        "width": f"{width_mm}mm",
        "height": f"{height_mm}mm",
    }
    # build channel-index-to-group mapping
    if channel_groups is not None:
        _ch_to_group = {}
        for group_name, indices in channel_groups.items():
            for idx in indices:
                _ch_to_group[idx] = group_name
        group_names = list(channel_groups.keys())
    else:
        _ch_to_group = None
        group_names = None

    if interactive:
        svg_attrs["data-interactive"] = "true"
        svg_attrs["data-seconds"] = str(seconds)
        svg_attrs["data-start-time"] = str(start_time)
        svg_attrs["data-sample-frequency"] = str(sample_frequency)
        svg_attrs["data-num-channels"] = str(num_channels)
        if group_names is not None:
            svg_attrs["data-channel-groups"] = json.dumps(group_names)
        svg_attrs["data-px-per-second"] = f"{px_per_sec:.6f}"
        svg_attrs["data-plot-width"] = f"{plot_width:.2f}"
        svg_attrs["data-label-margin"] = f"{label_margin:.2f}"
    svg = ET.Element("svg", svg_attrs)

    # white background
    ET.SubElement(svg, "rect", {
        "width": "100%",
        "height": "100%",
        "fill": "white",
    })

    # style element for text defaults
    style = ET.SubElement(svg, "style")
    css_text = (
        f"text {{ font-family: {DEFAULT_FONT_FAMILY}; font-size: {DEFAULT_FONT_SIZE}px; }}"
        f" .label {{ text-anchor: end; dominant-baseline: middle; }}"
        f" .time-label {{ text-anchor: middle; dominant-baseline: hanging; }}"
        f" .scalebar-label {{ text-anchor: start; dominant-baseline: middle; }}"
    )
    if interactive:
        css_text += " polyline { vector-effect: non-scaling-stroke; }"
    style.text = css_text

    # clip path for interactive mode
    if interactive:
        defs = ET.SubElement(svg, "defs")
        clip = ET.SubElement(defs, "clipPath", {"id": "plot-area"})
        ET.SubElement(clip, "rect", {
            "x": f"{label_margin:.2f}",
            "y": f"{top_margin:.2f}",
            "width": f"{plot_width:.2f}",
            "height": f"{plot_height:.2f}",
        })

    # vertical grid lines at regular time intervals
    if grid_interval is not None:
        grid_g = ET.SubElement(svg, "g", {"class": "grid"})
        grid_times = np.arange(
            np.ceil(start_time / grid_interval) * grid_interval,
            start_time + seconds + grid_interval * 0.01,  # small epsilon for inclusive end
            grid_interval,
        )
        grid_times = grid_times[grid_times <= start_time + seconds]
        for t in grid_times:
            x = time_to_x(t)
            ET.SubElement(grid_g, "line", {
                "x1": f"{x:.2f}",
                "y1": f"{top_margin:.2f}",
                "x2": f"{x:.2f}",
                "y2": f"{top_margin + plot_height:.2f}",
                "stroke": DEFAULT_GRID_COLOR,
                "stroke-width": DEFAULT_GRID_WIDTH,
            })

    # plot border
    ET.SubElement(svg, "rect", {
        "x": f"{label_margin:.2f}",
        "y": f"{top_margin:.2f}",
        "width": f"{plot_width:.2f}",
        "height": f"{plot_height:.2f}",
        "fill": "none",
        "stroke": "#999999",
        "stroke-width": "0.2",
    })

    if interactive:
        # --- Interactive mode: labels and traces are separate groups ---

        # Channel labels (not inside scaled groups)
        labels_g = ET.SubElement(svg, "g", {"class": "channel-labels"})
        for draw_idx, ch_idx in enumerate(channel_order):
            offset = ticklocs[draw_idx]
            label_y = data_y_to_svg(offset)
            ET.SubElement(labels_g, "text", {
                "x": f"{label_margin - 1.5:.2f}",
                "y": f"{label_y:.2f}",
                "class": "label",
            }).text = label_order[draw_idx]

        # Traces group with clip path
        traces_g = ET.SubElement(svg, "g", {
            "class": "traces",
            "clip-path": "url(#plot-area)",
        })

        # Generate polyline points using shared helper
        points_list = generate_polyline_data(
            signals, seconds, yscale=yscale, channel_order=channel_order,
        )

        for draw_idx, ch_idx in enumerate(channel_order):
            offset = ticklocs[draw_idx]
            baseline_svg = data_y_to_svg(offset)

            ch_group_name = "default"
            if _ch_to_group is not None:
                ch_group_name = _ch_to_group.get(ch_idx, "default")

            ch_g = ET.SubElement(traces_g, "g", {
                "class": "channel",
                "id": f"ch-{draw_idx}",
                "data-channel-index": str(draw_idx),
                "data-channel-group": ch_group_name,
                "data-label": label_order[draw_idx],
                "data-baseline-y": f"{baseline_svg:.2f}",
                "data-x-scale": f"{px_per_sec:.6f}",
                "data-y-scale": f"{y_scale_factor:.6f}",
                "transform": f"translate({label_margin:.2f},{baseline_svg:.2f}) scale({px_per_sec:.6f},{y_scale_factor:.6f})",
            })

            ET.SubElement(ch_g, "polyline", {
                "points": points_list[draw_idx],
                "fill": "none",
                "stroke": linecolor,
                "stroke-width": str(linewidth),
                "vector-effect": "non-scaling-stroke",
            })
    else:
        # --- Static mode: labels inside channel groups (original behavior) ---
        traces_g = ET.SubElement(svg, "g", {"class": "traces"})
        for draw_idx, ch_idx in enumerate(channel_order):
            offset = ticklocs[draw_idx]
            y_trace = yscale * data[:, ch_idx] + offset
            y_svg = data_y_to_svg(y_trace)

            ch_g = ET.SubElement(traces_g, "g", {
                "class": "channel",
                "id": f"ch-{draw_idx}",
            })

            # channel label
            label_y = data_y_to_svg(offset)
            ET.SubElement(ch_g, "text", {
                "x": f"{label_margin - 1.5:.2f}",
                "y": f"{label_y:.2f}",
                "class": "label",
            }).text = label_order[draw_idx]

            # polyline for waveform
            points_str = _format_points(t_svg, y_svg)
            ET.SubElement(ch_g, "polyline", {
                "points": points_str,
                "fill": "none",
                "stroke": linecolor,
                "stroke-width": str(linewidth),
            })

    # time axis labels
    time_g = ET.SubElement(svg, "g", {"class": "timeaxis"})
    time_label_y = top_margin + plot_height + 1.5

    if grid_interval is not None:
        label_times = grid_times
    else:
        label_times = [start_time, start_time + seconds]

    for t in label_times:
        x = time_to_x(t)
        ET.SubElement(time_g, "text", {
            "x": f"{x:.2f}",
            "y": f"{time_label_y:.2f}",
            "class": "time-label",
        }).text = f"{t:.4g}s"

    # vertical scale bar
    if show_scalebar:
        if scalebar_height is None:
            # auto: use ~10% of channel spacing, rounded to 1 significant digit
            scalebar_height = dr * 0.5
            scalebar_height = float(f"{scalebar_height:.1g}")

        sb_x = label_margin + plot_width + 3
        # center the scale bar vertically in the plot
        sb_center_data = (y_data_min + y_data_max) / 2.0
        sb_top_data = sb_center_data - scalebar_height / 2.0
        sb_bot_data = sb_center_data + scalebar_height / 2.0

        sb_top_svg = data_y_to_svg(sb_top_data)
        sb_bot_svg = data_y_to_svg(sb_bot_data)

        sb_g = ET.SubElement(svg, "g", {"class": "scalebar"})
        # vertical line
        ET.SubElement(sb_g, "line", {
            "x1": f"{sb_x:.2f}",
            "y1": f"{sb_top_svg:.2f}",
            "x2": f"{sb_x:.2f}",
            "y2": f"{sb_bot_svg:.2f}",
            "stroke": "black",
            "stroke-width": "0.3",
        })
        # top end cap
        cap_w = 1
        ET.SubElement(sb_g, "line", {
            "x1": f"{sb_x - cap_w:.2f}",
            "y1": f"{sb_top_svg:.2f}",
            "x2": f"{sb_x + cap_w:.2f}",
            "y2": f"{sb_top_svg:.2f}",
            "stroke": "black",
            "stroke-width": "0.3",
        })
        # bottom end cap
        ET.SubElement(sb_g, "line", {
            "x1": f"{sb_x - cap_w:.2f}",
            "y1": f"{sb_bot_svg:.2f}",
            "x2": f"{sb_x + cap_w:.2f}",
            "y2": f"{sb_bot_svg:.2f}",
            "stroke": "black",
            "stroke-width": "0.3",
        })
        # label
        sb_label_y = (sb_top_svg + sb_bot_svg) / 2.0
        ET.SubElement(sb_g, "text", {
            "x": f"{sb_x + cap_w + 1:.2f}",
            "y": f"{sb_label_y:.2f}",
            "class": "scalebar-label",
        }).text = f"{scalebar_height:.4g}{scalebar_units}"

    # serialize
    ET.indent(svg, space="  ")
    return ET.tostring(svg, encoding="unicode", xml_declaration=True)


def save_svg(filepath, signals, sample_frequency, **kwargs):
    """Render stacked EEG traces and write to an SVG file.

    Args:
        filepath: output file path
        signals: (num_channels, num_samples) numpy array
        sample_frequency: sampling rate in Hz
        **kwargs: passed to stackplot_svg()
    """
    svg_str = stackplot_svg(signals, sample_frequency, **kwargs)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(svg_str)


def show_montage_svg(signals, montage, sample_frequency, **kwargs):
    """Apply a montage derivation and render as SVG.

    Args:
        signals: raw signals (num_channels, num_samples) numpy array
        montage: a MontageView instance with .V.data matrix and .montage_labels
        sample_frequency: sampling rate in Hz
        **kwargs: passed to stackplot_svg()

    Returns:
        SVG content as a string
    """
    derived = np.dot(montage.V.data, signals)
    labels = montage.montage_labels
    return stackplot_svg(
        derived,
        sample_frequency,
        ylabels=labels,
        **kwargs,
    )


def save_montage_svg(filepath, signals, montage, sample_frequency, **kwargs):
    """Apply a montage derivation and write SVG to file.

    Args:
        filepath: output file path
        signals: raw signals (num_channels, num_samples) numpy array
        montage: a MontageView instance
        sample_frequency: sampling rate in Hz
        **kwargs: passed to stackplot_svg()
    """
    svg_str = show_montage_svg(signals, montage, sample_frequency, **kwargs)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(svg_str)


def eeg_to_svg(
    signals,
    sample_frequency,
    montage=None,
    low_freq=1.0,
    high_freq=70.0,
    notch_freq=None,
    target_frequency=None,
    max_samples_per_channel=None,
    **kwargs,
):
    """End-to-end pipeline: raw EEG signals to SVG string.

    Pipeline steps:
        1. Downsample (optional, if target_frequency is set)
        2. Apply montage derivation (optional, if montage is provided)
        3. Bandpass filter (optional, if low_freq or high_freq is set)
        4. Notch filter (optional, if notch_freq is set)
        5. Render as SVG via stackplot_svg()

    Args:
        signals: raw signals (num_channels, num_samples) numpy array
        sample_frequency: original sampling rate in Hz
        montage: a MontageView instance (optional). If provided, applies
            montage.V.data matrix multiply and uses montage.montage_labels.
        low_freq: high-pass cutoff in Hz (default: 1.0). Set to None to skip.
        high_freq: low-pass cutoff in Hz (default: 70.0). Set to None to skip.
        notch_freq: notch filter frequency in Hz (default: None).
            Common values: 60.0 Hz (US) or 50.0 (EU).
        target_frequency: if set, downsample to this rate before processing.
        max_samples_per_channel: if set, limit samples per channel in the
            final SVG (applied during rendering, after filtering).
        **kwargs: passed to stackplot_svg() (e.g. width_mm, height_mm,
            sensitivity, yscale, topdown, grid_interval, etc.)

    Returns:
        SVG content as a string
    """
    # 1. downsample
    if target_frequency is not None:
        signals, sample_frequency = downsample(signals, sample_frequency, target_frequency)

    # 2. montage derivation
    ylabels = kwargs.pop("ylabels", None)
    if montage is not None:
        signals = np.dot(montage.V.data, signals)
        if ylabels is None:
            ylabels = montage.montage_labels

    # 3. bandpass filter
    if low_freq is not None or high_freq is not None:
        signals = bandpass_filter(signals, sample_frequency, low_freq, high_freq)

    # 4. notch filter
    if notch_freq is not None:
        signals = notch_filter(signals, sample_frequency, notch_freq)

    # 5. render
    return stackplot_svg(
        signals,
        sample_frequency,
        ylabels=ylabels,
        max_samples_per_channel=max_samples_per_channel,
        **kwargs,
    )


def save_eeg_svg(filepath, signals, sample_frequency, **kwargs):
    """End-to-end pipeline: raw EEG signals to SVG file.

    Args:
        filepath: output file path
        signals: raw signals (num_channels, num_samples) numpy array
        sample_frequency: sampling rate in Hz
        **kwargs: passed to eeg_to_svg()
    """
    svg_str = eeg_to_svg(signals, sample_frequency, **kwargs)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(svg_str)
