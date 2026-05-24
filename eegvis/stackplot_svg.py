# -*- coding: utf-8 -*-
"""Pure SVG backend for EEG stack plotting.

Generates standalone SVG files from EEG signal data without requiring
matplotlib. Uses xml.etree.ElementTree for SVG construction.

The coordinate system follows clinical EEG convention where negative
voltages are displayed upward. SVG's native y-down axis makes this
straightforward: raw signal values map directly so that negative
deflections appear as upward movements on screen.
"""

from dataclasses import dataclass, field
from typing import List, Optional

import numpy as np
import xml.etree.ElementTree as ET


SVG_NS = "http://www.w3.org/2000/svg"


@dataclass
class Theme:
    """Styling configuration for SVG EEG output.

    All size values are in SVG user units (mm when viewBox matches width_mm/height_mm).
    """

    # Fonts
    font_family: str = "sans-serif"
    font_size: float = 3.5
    label_font_family: str = "sans-serif"
    label_font_size: float = 3.5
    label_color: str = "black"
    time_label_font_size: float = 3.5
    time_label_color: str = "black"
    scalebar_font_family: str = "sans-serif"
    scalebar_font_size: float = 3.5
    scalebar_color: str = "black"
    scalebar_bold: bool = False

    # Traces
    trace_colors: list = field(default_factory=lambda: ["black"])
    trace_width: float = 0.5

    # Grid
    major_grid_color: str = "#cccccc"
    major_grid_width: float = 0.3
    minor_grid_color: str = "#bfbfbf"
    minor_grid_width: float = 0.3
    minor_grid_dash: str = "4"

    # Scale bar
    scalebar_line_color: str = "black"
    scalebar_line_width: float = 0.3
    scalebar_bg_color: str = "none"
    scalebar_bg_opacity: float = 0.5

    # Misc
    border_color: str = "#999999"
    border_width: float = 0.2
    background_color: str = "white"


DEFAULT_THEME = Theme()

STRATUS_THEME = Theme(
    font_family="Segoe UI, sans-serif",
    font_size=3.5,
    label_font_family="Segoe UI, sans-serif",
    label_font_size=4.0,
    label_color="#838487",
    time_label_font_size=3.8,
    time_label_color="#000000",
    scalebar_font_family="Segoe UI, sans-serif",
    scalebar_font_size=3.8,
    scalebar_color="#000000",
    scalebar_bold=True,
    trace_colors=["#00007f", "#000000", "#7f0000"],
    trace_width=0.5,
    major_grid_color="#808080",
    major_grid_width=0.5,
    minor_grid_color="#bfbfbf",
    minor_grid_width=0.3,
    minor_grid_dash="4",
    scalebar_line_color="#000000",
    scalebar_line_width=0.5,
    scalebar_bg_color="#dfdfdf",
    scalebar_bg_opacity=0.5,
    border_color="#808080",
    border_width=0.3,
    background_color="white",
)

PUBLICATION_THEME = Theme(
    font_family="DejaVu Sans, Arial, sans-serif",
    font_size=3.0,
    label_font_family="DejaVu Sans, Arial, sans-serif",
    label_font_size=3.0,
    label_color="#333333",
    time_label_font_size=3.0,
    time_label_color="#222222",
    scalebar_font_family="DejaVu Sans, Arial, sans-serif",
    scalebar_font_size=3.0,
    scalebar_color="#222222",
    scalebar_bold=False,
    trace_colors=["#222222"],
    trace_width=0.4,
    major_grid_color="#dddddd",
    major_grid_width=0.2,
    minor_grid_color="#eeeeee",
    minor_grid_width=0.15,
    minor_grid_dash="2",
    scalebar_line_color="#333333",
    scalebar_line_width=0.25,
    scalebar_bg_color="none",
    scalebar_bg_opacity=0.0,
    border_color="#bbbbbb",
    border_width=0.15,
    background_color="white",
)


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
    max_taps = num_samples // 3 - 1

    if low_freq is not None:
        numtaps = min(max(int(2 * sample_frequency), 3), max_taps)
        if numtaps % 2 == 0:
            numtaps += 1
        hp = esfilters.fir_highpass_firwin_ff(sample_frequency, low_freq, numtaps)
        for ch in range(result.shape[0]):
            result[ch] = hp(result[ch])

    if high_freq is not None:
        numtaps = min(max(int(sample_frequency / 4.0), 3), max_taps)
        lp = esfilters.fir_lowpass_firwin_ff(sample_frequency, high_freq, numtaps)
        for ch in range(result.shape[0]):
            result[ch] = lp(result[ch])

    return result


def apply_per_channel_bandpass(
    signals, sample_frequency, channel_lf=None, channel_hf=None
):
    """Apply bandpass filtering with per-channel cutoffs.

    ``channel_lf`` and ``channel_hf`` are sequences of length
    ``num_channels``. An entry of ``None``, ``0``, or a negative value
    skips that direction for that channel. Channels with both set are
    bandpassed; channels with neither are passed through untouched.

    Internally just calls :func:`bandpass_filter` on each row that needs
    filtering — slow for very many channels with disparate cutoffs, but
    fine for clinical 20-channel work.
    """
    if channel_lf is None and channel_hf is None:
        return signals
    num_channels = signals.shape[0]
    out = signals.copy()
    for ch in range(num_channels):
        lf = channel_lf[ch] if channel_lf is not None else None
        hf = channel_hf[ch] if channel_hf is not None else None
        # Normalize "no filter" semantics: 0 or negative or None = skip.
        if lf is not None and lf <= 0:
            lf = None
        if hf is not None and hf <= 0:
            hf = None
        if lf is None and hf is None:
            continue
        row = signals[ch : ch + 1]
        filtered = bandpass_filter(row, sample_frequency, low_freq=lf, high_freq=hf)
        out[ch] = filtered[0]
    return out


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


def _compute_channel_offsets(
    data, num_channels, sensitivity=None, height=None, gap_after_mm=None
):
    """Compute vertical offset for each channel.

    Args:
        data: (num_samples, num_channels) array
        num_channels: number of channels
        sensitivity: if set, absolute spacing in data units per channel
        height: total plot height in SVG units (used with sensitivity, and to
            convert gap_after_mm to data units in auto mode)
        gap_after_mm: optional per-channel array of extra gap (in mm of plot
            space) after each channel. Length num_channels; the last entry is
            ignored. In sensitivity mode the gaps consume the budget exactly;
            in auto mode the conversion to data units uses the no-gap channel
            spacing and is approximate.

    Returns:
        ticklocs: array of y-offsets for each channel in data units
        dr: nominal spacing between channels in data units
    """
    if gap_after_mm is None:
        cum_gap_mm = np.zeros(num_channels, dtype=float)
    else:
        gaps = np.asarray(gap_after_mm, dtype=float)
        if gaps.shape != (num_channels,):
            raise ValueError(
                f"gap_after_mm must have length {num_channels}, got {gaps.shape}"
            )
        # cumulative gap before channel i = sum of gaps[0..i-1]
        cum_gap_mm = np.concatenate(([0.0], np.cumsum(gaps[:-1])))

    ch_indices = np.arange(num_channels, dtype=float)
    if sensitivity is not None and height is not None:
        total_gap_mm = float(cum_gap_mm[-1]) if num_channels > 0 else 0.0
        usable_height = max(height - total_gap_mm, 1e-6)
        dr = sensitivity * usable_height / num_channels
        ticklocs = ch_indices * dr + cum_gap_mm * sensitivity + dr / 2.0
    else:
        dr = (data.max() - data.min()) * 0.7
        if height is not None and height > 0 and num_channels > 0:
            # Approximate conversion: in a no-gap layout, num_channels * dr
            # data units span plot_height mm.
            data_per_mm = (num_channels * dr) / height
        else:
            data_per_mm = 0.0
        ticklocs = ch_indices * dr + cum_gap_mm * data_per_mm
    return ticklocs, dr


def _build_style_element(svg, theme):
    """Create the <style> element with theme-driven CSS rules."""
    style = ET.SubElement(svg, "style")
    font_weight_sb = "bold" if theme.scalebar_bold else "normal"
    style.text = (
        f".trace {{ fill: none; stroke-width: {theme.trace_width}; vector-effect: non-scaling-stroke; }}"
        f" .label {{ font-family: {theme.label_font_family}; font-size: {theme.label_font_size}px; "
        f"fill: {theme.label_color}; text-anchor: end; dominant-baseline: middle; }}"
        f" .time-label {{ font-size: {theme.time_label_font_size}px; "
        f"fill: {theme.time_label_color}; text-anchor: middle; dominant-baseline: hanging; }}"
        f" .scalebar-label {{ font-family: {theme.scalebar_font_family}; "
        f"font-size: {theme.scalebar_font_size}px; font-weight: {font_weight_sb}; "
        f"fill: {theme.scalebar_color}; text-anchor: start; dominant-baseline: middle; }}"
        f" .major-grid {{ stroke: {theme.major_grid_color}; stroke-width: {theme.major_grid_width}; }}"
        f" .minor-grid {{ stroke: {theme.minor_grid_color}; stroke-width: {theme.minor_grid_width}; "
        f"stroke-dasharray: {theme.minor_grid_dash}; }}"
    )


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
    minor_grid=False,
    minor_grid_interval=None,
    show_scalebar=True,
    scalebar_height=None,
    scalebar_units="µV",
    max_samples_per_channel=None,
    theme=None,
    color_group_size=4,
    channel_gaps_mm=None,
    channel_colors=None,
    channel_widths=None,
    channel_cal=None,
    preserve_aspect_ratio=None,
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
        linecolor: trace color (overrides theme)
        linewidth: trace stroke width (overrides theme)
        grid_interval: time interval for vertical grid lines in seconds.
            Set to None to disable grid.
        minor_grid: if True, draw minor (dashed) grid lines between major grid.
        minor_grid_interval: override minor grid interval in seconds.
            Defaults to grid_interval / 4.
        show_scalebar: whether to draw a vertical scale bar
        scalebar_height: height of scale bar in data units.
            If None, auto-computed as ~10% of channel spacing.
        scalebar_units: units label for scale bar (default: µV)
        max_samples_per_channel: if set, downsample signals so each channel
            has at most this many samples. Reduces SVG file size for
            high sample rate data. Set to None to disable (default).
        theme: a Theme instance controlling all styling.
            Defaults to DEFAULT_THEME.
        color_group_size: number of channels per color group when theme has
            multiple trace colors. Default 4 (Stratus-style bands).
        channel_gaps_mm: optional per-channel sequence of extra gap (in mm of
            plot space) to insert after each channel. Length must equal
            num_channels; the gap after the last channel is ignored. Used to
            create visual separation between groups of channels (e.g. between
            left and right hemisphere chains). In sensitivity mode the gaps
            consume the available plot_height; in auto mode the conversion is
            approximate.
        channel_colors: optional per-channel sequence of trace color overrides
            (length must equal num_channels). An entry of None falls back to
            the theme's group-cycled color. Channels are matched by their
            original index in the signals array, not by display order.
        channel_widths: optional per-channel sequence of trace stroke widths
            in mm (length must equal num_channels). An entry of None falls
            back to the theme's ``trace_width`` (or ``linewidth`` if set).
        channel_cal: optional per-channel sequence of calibration amplitudes
            in µV (length must equal num_channels). When set, a small
            "<amp>µV" annotation is rendered at the right edge of each
            channel's trace. An entry of None disables the annotation for
            that channel.
        preserve_aspect_ratio: optional value for the SVG root's
            ``preserveAspectRatio`` attribute. Leave as None (default) to
            omit the attribute and rely on the SVG default of
            "xMidYMid meet" (letterbox to preserve aspect). Set to "none"
            for the SVG to stretch independently in x and y to fill its
            container — useful for full-page strip-chart viewers.

    Returns:
        SVG content as a string
    """
    if theme is None:
        theme = DEFAULT_THEME

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

    # Resolve trace color and width: explicit params override theme
    if linecolor is not None:
        trace_color_list = [linecolor]
    else:
        trace_color_list = theme.trace_colors
    trace_width = linewidth if linewidth is not None else theme.trace_width

    # normalize yscale to per-channel array
    if np.isscalar(yscale):
        yscale_array = np.full(num_channels, float(yscale))
        yscale_ref = float(yscale)
    else:
        yscale_array = np.asarray(yscale, dtype=float)
        yscale_ref = float(np.mean(yscale_array))

    # layout constants (in viewBox units = mm)
    label_margin = 25
    top_margin = 5
    bottom_margin = 8
    right_margin = 5
    scalebar_margin = 20 if show_scalebar else 0

    plot_width = width_mm - label_margin - right_margin - scalebar_margin
    plot_height = height_mm - top_margin - bottom_margin

    # transpose to (num_samples, num_channels) for processing
    data = signals.T

    if channel_gaps_mm is not None:
        gaps_arr = np.asarray(channel_gaps_mm, dtype=float)
        if gaps_arr.shape != (num_channels,):
            raise ValueError(
                f"channel_gaps_mm must have length {num_channels}, got {gaps_arr.shape}"
            )
    else:
        gaps_arr = None

    if channel_colors is not None:
        if len(channel_colors) != num_channels:
            raise ValueError(
                f"channel_colors must have length {num_channels}, "
                f"got {len(channel_colors)}"
            )

    if channel_widths is not None:
        if len(channel_widths) != num_channels:
            raise ValueError(
                f"channel_widths must have length {num_channels}, "
                f"got {len(channel_widths)}"
            )

    if channel_cal is not None:
        if len(channel_cal) != num_channels:
            raise ValueError(
                f"channel_cal must have length {num_channels}, got {len(channel_cal)}"
            )

    # compute vertical offsets in data space
    ticklocs, dr = _compute_channel_offsets(
        yscale_ref * data,
        num_channels,
        sensitivity=sensitivity,
        height=plot_height,
        gap_after_mm=gaps_arr,
    )

    def time_to_x(t):
        """Map time value(s) to SVG x-coordinate(s). Accepts scalars or arrays."""
        return label_margin + (t - start_time) / seconds * plot_width

    # compute mapping from data coordinates to SVG coordinates
    t_data = start_time + seconds * np.arange(num_samples, dtype=float) / max(
        num_samples - 1, 1
    )
    t_svg = time_to_x(t_data)

    # y axis: data values are offset by ticklocs, then mapped to SVG y
    if sensitivity is not None:
        y_data_min = 0.0
        y_data_max = sensitivity * plot_height
    else:
        scaled = yscale_ref * data
        y_data_min = scaled.min()
        last_offset = ticklocs[-1] if num_channels > 0 else 0.0
        y_data_max = last_offset + scaled.max()

    y_data_range = y_data_max - y_data_min

    def data_y_to_svg(y_data):
        """Map data y-coordinate(s) to SVG y-coordinate(s)."""
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
    svg_attrs = {
        "xmlns": SVG_NS,
        "viewBox": f"0 0 {width_mm} {height_mm}",
        "width": f"{width_mm}mm",
        "height": f"{height_mm}mm",
        "data-sample-frequency": str(sample_frequency),
        "data-start-time": str(start_time),
        "data-seconds": str(seconds),
        "data-num-channels": str(num_channels),
    }
    if preserve_aspect_ratio is not None:
        svg_attrs["preserveAspectRatio"] = preserve_aspect_ratio
    svg = ET.Element("svg", svg_attrs)

    # background
    ET.SubElement(
        svg,
        "rect",
        {
            "width": "100%",
            "height": "100%",
            "fill": theme.background_color,
        },
    )

    _build_style_element(svg, theme)

    # Grid lines
    if grid_interval is not None:
        grid_g = ET.SubElement(svg, "g", {"class": "grid"})
        grid_times = np.arange(
            np.ceil(start_time / grid_interval) * grid_interval,
            start_time + seconds + grid_interval * 0.01,
            grid_interval,
        )
        grid_times = grid_times[grid_times <= start_time + seconds]

        # Minor grid lines
        if minor_grid:
            mi = (
                minor_grid_interval
                if minor_grid_interval is not None
                else grid_interval / 4.0
            )
            minor_times = np.arange(
                np.ceil(start_time / mi) * mi,
                start_time + seconds + mi * 0.01,
                mi,
            )
            minor_times = minor_times[minor_times <= start_time + seconds]
            # Remove times that coincide with major grid
            minor_times = minor_times[
                np.abs(np.subtract.outer(minor_times, grid_times).min(axis=1))
                > mi * 0.01
            ]
            for t in minor_times:
                x = time_to_x(t)
                ET.SubElement(
                    grid_g,
                    "line",
                    {
                        "x1": f"{x:.2f}",
                        "y1": f"{top_margin:.2f}",
                        "x2": f"{x:.2f}",
                        "y2": f"{top_margin + plot_height:.2f}",
                        "class": "minor-grid",
                    },
                )

        # Major grid lines
        for t in grid_times:
            x = time_to_x(t)
            ET.SubElement(
                grid_g,
                "line",
                {
                    "x1": f"{x:.2f}",
                    "y1": f"{top_margin:.2f}",
                    "x2": f"{x:.2f}",
                    "y2": f"{top_margin + plot_height:.2f}",
                    "class": "major-grid",
                },
            )

    # plot border
    ET.SubElement(
        svg,
        "rect",
        {
            "x": f"{label_margin:.2f}",
            "y": f"{top_margin:.2f}",
            "width": f"{plot_width:.2f}",
            "height": f"{plot_height:.2f}",
            "fill": "none",
            "stroke": theme.border_color,
            "stroke-width": str(theme.border_width),
        },
    )

    # channel traces and labels
    traces_g = ET.SubElement(svg, "g", {"class": "traces"})
    num_colors = len(trace_color_list)
    for draw_idx, ch_idx in enumerate(channel_order):
        offset = ticklocs[draw_idx]
        baseline_y = data_y_to_svg(offset)
        ch_yscale = yscale_array[ch_idx]

        if y_data_range != 0:
            y_scale_factor = ch_yscale * plot_height / y_data_range
        else:
            y_scale_factor = 1.0

        # Determine trace color for this channel: explicit per-channel
        # override (matched by original channel index) wins over theme cycling.
        ch_color = None
        if channel_colors is not None:
            ch_color = channel_colors[ch_idx]
        if ch_color is None:
            color_idx = (draw_idx // color_group_size) % num_colors
            ch_color = trace_color_list[color_idx]

        ch_g = ET.SubElement(
            traces_g,
            "g",
            {
                "class": "channel",
                "id": f"ch-{draw_idx}",
                "transform": f"translate(0,{baseline_y:.2f})",
                "data-baseline": f"{baseline_y:.2f}",
                "data-channel-name": label_order[draw_idx],
                "data-channel-index": str(ch_idx),
            },
        )

        # channel label
        ET.SubElement(
            ch_g,
            "text",
            {
                "x": f"{label_margin - 1.5:.2f}",
                "y": "0",
                "class": "label",
            },
        ).text = label_order[draw_idx]

        # per-channel stroke width override (matched by original ch_idx)
        ch_width = trace_width
        if channel_widths is not None and channel_widths[ch_idx] is not None:
            ch_width = float(channel_widths[ch_idx])

        # polyline
        y_raw = data[:, ch_idx]
        points_str = _format_points(t_svg, y_raw)
        ET.SubElement(
            ch_g,
            "polyline",
            {
                "points": points_str,
                "class": "trace",
                "stroke": ch_color,
                "stroke-width": str(ch_width),
                "transform": f"scale(1,{y_scale_factor:.6f})",
                "data-yscale": f"{y_scale_factor:.6f}",
            },
        )

        # per-channel calibration annotation (small text at right edge)
        if channel_cal is not None and channel_cal[ch_idx] is not None:
            cal_val = float(channel_cal[ch_idx])
            ET.SubElement(
                ch_g,
                "text",
                {
                    "x": f"{label_margin + plot_width + 1:.2f}",
                    "y": "0",
                    "class": "channel-cal",
                    "font-size": "2.2",
                    "fill": "#666",
                },
            ).text = f"{cal_val:g}µV"

    # annotations layer
    ET.SubElement(svg, "g", {"class": "annotations"})

    # time axis labels
    time_g = ET.SubElement(svg, "g", {"class": "timeaxis"})
    time_label_y = top_margin + plot_height + 1.5

    if grid_interval is not None:
        label_times = grid_times
    else:
        label_times = [start_time, start_time + seconds]

    for t in label_times:
        x = time_to_x(t)
        ET.SubElement(
            time_g,
            "text",
            {
                "x": f"{x:.2f}",
                "y": f"{time_label_y:.2f}",
                "class": "time-label",
            },
        ).text = f"{t:.4g}s"

    # vertical scale bar
    if show_scalebar:
        if scalebar_height is None:
            scalebar_height = dr * 0.5
            scalebar_height = float(f"{scalebar_height:.1g}")

        sb_x = label_margin + plot_width + 3
        sb_center_data = (y_data_min + y_data_max) / 2.0
        sb_top_data = sb_center_data - scalebar_height / 2.0
        sb_bot_data = sb_center_data + scalebar_height / 2.0

        sb_top_svg = data_y_to_svg(sb_top_data)
        sb_bot_svg = data_y_to_svg(sb_bot_data)

        sb_g = ET.SubElement(svg, "g", {"class": "scalebar"})

        # Background rect (Stratus style)
        if theme.scalebar_bg_color != "none":
            cap_w = 1
            ET.SubElement(
                sb_g,
                "rect",
                {
                    "x": f"{sb_x - cap_w - 1:.2f}",
                    "y": f"{sb_top_svg:.2f}",
                    "width": f"{2 * cap_w + 3:.2f}",
                    "height": f"{sb_bot_svg - sb_top_svg:.2f}",
                    "fill": theme.scalebar_bg_color,
                    "fill-opacity": str(theme.scalebar_bg_opacity),
                },
            )

        # vertical line
        ET.SubElement(
            sb_g,
            "line",
            {
                "x1": f"{sb_x:.2f}",
                "y1": f"{sb_top_svg:.2f}",
                "x2": f"{sb_x:.2f}",
                "y2": f"{sb_bot_svg:.2f}",
                "stroke": theme.scalebar_line_color,
                "stroke-width": str(theme.scalebar_line_width),
            },
        )
        # end caps
        cap_w = 1
        for y_pos in (sb_top_svg, sb_bot_svg):
            ET.SubElement(
                sb_g,
                "line",
                {
                    "x1": f"{sb_x - cap_w:.2f}",
                    "y1": f"{y_pos:.2f}",
                    "x2": f"{sb_x + cap_w:.2f}",
                    "y2": f"{y_pos:.2f}",
                    "stroke": theme.scalebar_line_color,
                    "stroke-width": str(theme.scalebar_line_width),
                },
            )
        # label
        sb_label_y = (sb_top_svg + sb_bot_svg) / 2.0
        ET.SubElement(
            sb_g,
            "text",
            {
                "x": f"{sb_x + cap_w + 1:.2f}",
                "y": f"{sb_label_y:.2f}",
                "class": "scalebar-label",
            },
        ).text = f"{scalebar_height:.4g}{scalebar_units}"

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


def show_montage_display_svg(
    signals, sample_frequency, display, rec_labels=None, **kwargs
):
    """Render an SVG using a :class:`MontageDisplay` profile.

    The display profile carries the derivation (either by name or as an
    embedded matrix), the channel grouping/order, per-group gaps, and
    per-channel color/gain overrides. Hidden channels are dropped before
    rendering.

    Channels listed earlier in the display profile are drawn higher on the
    page (clinical convention). This function flips the order before handing
    it to :func:`stackplot_svg`, which numbers channels bottom-up.

    Args:
        signals: raw signals (num_channels, num_samples) numpy array
        sample_frequency: sampling rate in Hz
        display: a ``MontageDisplay`` instance
        rec_labels: list of recording channel labels in row order, required
            when ``display`` uses ``derivation_ref`` (a built-in lookup).
        **kwargs: passed to ``stackplot_svg`` (e.g. width_mm, sensitivity).
            ``ylabels``, ``yscale``, ``channel_gaps_mm``, and
            ``channel_colors`` are derived from ``display`` and should not
            be passed in.

    Returns:
        SVG content as a string
    """
    mv = display.build_montage_view(rec_labels=rec_labels)
    derived = np.dot(mv.V.data, signals)
    montage_labels = list(mv.montage_labels)

    ordered = display.resolve_ordered_labels()
    gaps_mm = display.resolve_gaps_mm()
    colors = display.resolve_colors()
    gains = display.resolve_gains()
    # Per-channel clinical attributes — None means "inherit global".
    per_chan_sens: List[Optional[float]] = []
    per_chan_lf: List[Optional[float]] = []
    per_chan_hf: List[Optional[float]] = []
    per_chan_cal: List[Optional[float]] = []
    per_chan_width: List[Optional[float]] = []
    for lbl in ordered:
        override = display.channel_overrides.get(lbl)
        per_chan_sens.append(override.sensitivity if override else None)
        per_chan_lf.append(override.lf if override else None)
        per_chan_hf.append(override.hf if override else None)
        per_chan_cal.append(override.cal if override else None)
        per_chan_width.append(override.width if override else None)

    label_to_row = {lbl: i for i, lbl in enumerate(montage_labels)}
    try:
        indices = [label_to_row[lbl] for lbl in ordered]
    except KeyError as e:
        raise KeyError(
            f"channel {e.args[0]!r} from MontageDisplay is not present in "
            f"montage_labels {montage_labels}"
        ) from None
    derived_ordered = derived[indices]

    # Apply per-channel bandpass before stacking (only if any channel has
    # LF or HF set).
    if any(v is not None for v in per_chan_lf) or any(
        v is not None for v in per_chan_hf
    ):
        derived_ordered = apply_per_channel_bandpass(
            derived_ordered,
            sample_frequency,
            channel_lf=per_chan_lf,
            channel_hf=per_chan_hf,
        )

    # MontageDisplay lists channels top-down (file order matches visual
    # order); stackplot_svg numbers channels bottom-up. Reverse so the
    # first-listed channel ends up at the top of the page. The gap below
    # display channel i (between i and i+1) must move to the boundary
    # between channels n-2-i and n-1-i in render order — i.e. take the
    # inter-channel gaps (gaps_mm[:-1]), reverse them, and append a unused
    # trailing zero.
    n = len(ordered)
    derived_ordered = derived_ordered[::-1]
    ordered_render = list(reversed(ordered))
    colors_render = list(reversed(colors))
    gains_render = list(reversed(gains))
    widths_render = list(reversed(per_chan_width))
    cal_render = list(reversed(per_chan_cal))
    sens_render = list(reversed(per_chan_sens))
    if n > 0:
        gaps_render = list(reversed(gaps_mm[:-1])) + [0.0]
    else:
        gaps_render = []

    base_yscale = kwargs.pop("yscale", 1.0)
    if np.isscalar(base_yscale):
        yscale_arr = np.asarray(gains_render, dtype=float) * float(base_yscale)
    else:
        yscale_arr = np.asarray(base_yscale, dtype=float) * np.asarray(
            gains_render, dtype=float
        )

    # Fold per-channel sensitivity into yscale: smaller channel sens means
    # larger trace, so yscale[i] *= global_sens / channel_sens[i].
    global_sens = kwargs.get("sensitivity")
    if global_sens is not None:
        for i, ch_sens in enumerate(sens_render):
            if ch_sens is not None and ch_sens > 0:
                yscale_arr[i] *= float(global_sens) / float(ch_sens)

    for reserved in (
        "ylabels",
        "channel_gaps_mm",
        "channel_colors",
        "channel_widths",
        "channel_cal",
    ):
        kwargs.pop(reserved, None)

    return stackplot_svg(
        derived_ordered,
        sample_frequency,
        ylabels=ordered_render,
        yscale=yscale_arr,
        channel_gaps_mm=gaps_render,
        channel_colors=colors_render,
        channel_widths=widths_render,
        channel_cal=cal_render,
        **kwargs,
    )


def save_montage_display_svg(
    filepath, signals, sample_frequency, display, rec_labels=None, **kwargs
):
    """Render a ``MontageDisplay`` and write the SVG to file."""
    svg_str = show_montage_display_svg(
        signals, sample_frequency, display, rec_labels=rec_labels, **kwargs
    )
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(svg_str)


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
            Common values: 60.0 (US) or 50.0 (EU).
        target_frequency: if set, downsample to this rate before processing.
        max_samples_per_channel: if set, limit samples per channel in the
            final SVG (applied during rendering, after filtering).
        **kwargs: passed to stackplot_svg() (e.g. width_mm, height_mm,
            sensitivity, yscale, topdown, grid_interval, theme, etc.)

    Returns:
        SVG content as a string
    """
    # 1. downsample
    if target_frequency is not None:
        signals, sample_frequency = downsample(
            signals, sample_frequency, target_frequency
        )

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
