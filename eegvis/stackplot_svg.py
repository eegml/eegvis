# -*- coding: utf-8 -*-
"""Pure SVG backend for EEG stack plotting.

Generates standalone SVG files from EEG signal data without requiring
matplotlib. Uses xml.etree.ElementTree for SVG construction.

The coordinate system follows clinical EEG convention where negative
voltages are displayed upward. SVG's native y-down axis makes this
straightforward: raw signal values map directly so that negative
deflections appear as upward movements on screen.
"""

import numpy as np
import xml.etree.ElementTree as ET


SVG_NS = "http://www.w3.org/2000/svg"

# default styling
DEFAULT_TRACE_COLOR = "black"
DEFAULT_TRACE_WIDTH = "0.5"
DEFAULT_FONT_FAMILY = "sans-serif"
DEFAULT_FONT_SIZE = 10  # in SVG user units (roughly px)
DEFAULT_GRID_COLOR = "#cccccc"
DEFAULT_GRID_WIDTH = "0.3"


def _format_points(t, y):
    """Convert time and amplitude arrays to SVG polyline points string.

    Rounds to 2 decimal places to keep file size reasonable.
    Uses numpy vectorized string formatting for performance.
    """
    coords = np.column_stack((np.round(t, 2), np.round(y, 2)))
    return " ".join(f"{x},{y}" for x, y in coords)


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

    Returns:
        SVG content as a string
    """
    num_channels, num_samples = signals.shape

    if seconds is None:
        seconds = num_samples / sample_frequency

    if ylabels is None:
        ylabels = [str(i) for i in range(num_channels)]

    if linecolor is None:
        linecolor = DEFAULT_TRACE_COLOR
    if linewidth is None:
        linewidth = DEFAULT_TRACE_WIDTH

    # layout constants
    label_margin = 60  # left margin for channel labels
    top_margin = 15
    bottom_margin = 25  # space for time axis labels
    right_margin = 20
    scalebar_margin = 50 if show_scalebar else 0

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

    # channel ordering
    channel_order = list(range(num_channels))
    label_order = list(ylabels)
    if topdown:
        channel_order = list(reversed(channel_order))
        label_order = list(reversed(label_order))

    # build SVG
    svg = ET.Element("svg", {
        "xmlns": SVG_NS,
        "viewBox": f"0 0 {width_mm} {height_mm}",
        "width": f"{width_mm}mm",
        "height": f"{height_mm}mm",
    })

    # white background
    ET.SubElement(svg, "rect", {
        "width": "100%",
        "height": "100%",
        "fill": "white",
    })

    # style element for text defaults
    style = ET.SubElement(svg, "style")
    style.text = (
        f"text {{ font-family: {DEFAULT_FONT_FAMILY}; font-size: {DEFAULT_FONT_SIZE}px; }}"
        f" .label {{ text-anchor: end; dominant-baseline: middle; }}"
        f" .time-label {{ text-anchor: middle; dominant-baseline: hanging; }}"
        f" .scalebar-label {{ text-anchor: start; dominant-baseline: middle; }}"
    )

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
        "stroke-width": "0.5",
    })

    # channel traces and labels
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
            "x": f"{label_margin - 4:.2f}",
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
    time_label_y = top_margin + plot_height + 5

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

        sb_x = label_margin + plot_width + 15
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
            "stroke-width": "1",
        })
        # top end cap
        cap_w = 3
        ET.SubElement(sb_g, "line", {
            "x1": f"{sb_x - cap_w:.2f}",
            "y1": f"{sb_top_svg:.2f}",
            "x2": f"{sb_x + cap_w:.2f}",
            "y2": f"{sb_top_svg:.2f}",
            "stroke": "black",
            "stroke-width": "1",
        })
        # bottom end cap
        ET.SubElement(sb_g, "line", {
            "x1": f"{sb_x - cap_w:.2f}",
            "y1": f"{sb_bot_svg:.2f}",
            "x2": f"{sb_x + cap_w:.2f}",
            "y2": f"{sb_bot_svg:.2f}",
            "stroke": "black",
            "stroke-width": "1",
        })
        # label
        sb_label_y = (sb_top_svg + sb_bot_svg) / 2.0
        ET.SubElement(sb_g, "text", {
            "x": f"{sb_x + cap_w + 3:.2f}",
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
