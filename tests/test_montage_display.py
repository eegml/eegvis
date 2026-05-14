"""Tests for MontageDisplay (derivation + spacing + colors) and the related
gap/color extensions in stackplot_svg."""

import json
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

import numpy as np
import pytest

import eegvis.stackplot_svg as stackplot_svg
from eegvis.montage_display import (
    ChannelGroup,
    ChannelStyle,
    MontageDerivation,
    MontageDisplay,
    SymbolicChannel,
    SymbolicDerivation,
    VirtualElectrode,
    default_double_banana_display,
    list_builtin_derivations,
)
from eegvis.stackplot_svg import (
    _compute_channel_offsets,
    save_montage_display_svg,
    show_montage_display_svg,
)


SVG_NS = stackplot_svg.SVG_NS
NS = {"svg": SVG_NS}


# ---------- _compute_channel_offsets with gap_after_mm ----------


def test_gap_offsets_sensitivity_mode_shifts_later_channels():
    """In sensitivity mode, a gap after channel 0 should push channel 1+ further down."""
    data = np.zeros((100, 4))
    ticklocs_no_gap, _ = _compute_channel_offsets(
        data, num_channels=4, sensitivity=7.0, height=200
    )
    gaps = [5.0, 0.0, 0.0, 0.0]
    ticklocs_with_gap, _ = _compute_channel_offsets(
        data, num_channels=4, sensitivity=7.0, height=200, gap_after_mm=gaps
    )
    # Channel 0 stays near top; channels 1..3 should be shifted by 5mm*7 = 35 data units
    # (modulo the smaller dr from squeezing into the remaining height).
    assert ticklocs_with_gap[1] > ticklocs_no_gap[1]
    assert ticklocs_with_gap[2] > ticklocs_no_gap[2]
    # The gap separation between ch0 and ch1 should be larger than the
    # nominal channel spacing.
    spacing_01 = ticklocs_with_gap[1] - ticklocs_with_gap[0]
    spacing_12 = ticklocs_with_gap[2] - ticklocs_with_gap[1]
    assert spacing_01 > spacing_12


def test_gap_offsets_auto_mode():
    """Auto mode should also widen the gap between channels."""
    data = np.random.RandomState(0).randn(50, 3) * 10.0
    ticklocs_no_gap, dr_no = _compute_channel_offsets(
        data, num_channels=3, sensitivity=None, height=100
    )
    ticklocs_with_gap, dr_yes = _compute_channel_offsets(
        data, num_channels=3, sensitivity=None, height=100, gap_after_mm=[3.0, 0.0, 0.0]
    )
    # dr is data-driven and unaffected by gaps in auto mode
    assert dr_no == dr_yes
    # ch1 and ch2 should be further down with the gap applied
    assert ticklocs_with_gap[1] > ticklocs_no_gap[1]


def test_gap_after_mm_wrong_length_raises():
    data = np.zeros((10, 3))
    with pytest.raises(ValueError):
        _compute_channel_offsets(
            data, num_channels=3, sensitivity=7.0, height=100, gap_after_mm=[1.0, 2.0]
        )


# ---------- stackplot_svg with channel_gaps_mm and channel_colors ----------


def test_stackplot_svg_with_channel_gaps_renders():
    signals = np.random.RandomState(1).randn(4, 400)
    svg_str = stackplot_svg.stackplot_svg(
        signals,
        sample_frequency=200.0,
        seconds=2.0,
        sensitivity=7.0,
        channel_gaps_mm=[0.0, 5.0, 0.0, 0.0],
    )
    root = ET.fromstring(svg_str)
    channels = root.findall(".//svg:g[@class='channel']", NS)
    assert len(channels) == 4


def _channel_y(group_elem):
    """Return the baseline y offset from a channel <g>'s transform."""
    return float(group_elem.attrib["data-baseline"])


def test_channel_gaps_increase_visual_separation():
    """A gap after channel 0 should put a larger pixel gap between rendered ch 0 and ch 1."""
    signals = np.zeros((4, 200))
    common = dict(sample_frequency=200.0, seconds=1.0, sensitivity=7.0, topdown=False)
    svg_no = stackplot_svg.stackplot_svg(signals, **common)
    svg_yes = stackplot_svg.stackplot_svg(
        signals, channel_gaps_mm=[10.0, 0.0, 0.0, 0.0], **common
    )
    chs_no = ET.fromstring(svg_no).findall(".//svg:g[@class='channel']", NS)
    chs_yes = ET.fromstring(svg_yes).findall(".//svg:g[@class='channel']", NS)
    # topdown=False means ch_idx 0 is drawn first (top), so consecutive
    # elements correspond to consecutive channels.
    sep_no = _channel_y(chs_no[1]) - _channel_y(chs_no[0])
    sep_yes = _channel_y(chs_yes[1]) - _channel_y(chs_yes[0])
    assert sep_yes > sep_no


def test_channel_colors_override_theme():
    signals = np.random.RandomState(2).randn(3, 200)
    colors = ["#ff0000", None, "#00ff00"]
    svg_str = stackplot_svg.stackplot_svg(
        signals,
        sample_frequency=200.0,
        seconds=1.0,
        channel_colors=colors,
        topdown=False,
    )
    root = ET.fromstring(svg_str)
    polys = root.findall(".//svg:polyline[@class='trace']", NS)
    assert len(polys) == 3
    # channel ordering: with topdown=False, draw order matches channel index
    strokes = [p.attrib["stroke"] for p in polys]
    assert strokes[0] == "#ff0000"
    assert strokes[2] == "#00ff00"
    # The middle one (None override) takes the theme default ("black")
    assert strokes[1] == "black"


def test_channel_colors_wrong_length_raises():
    signals = np.random.randn(3, 100)
    with pytest.raises(ValueError):
        stackplot_svg.stackplot_svg(
            signals, sample_frequency=200.0, channel_colors=["red", "blue"]
        )


# ---------- MontageDisplay resolution helpers ----------


def test_resolve_ordered_labels_and_gaps_and_colors():
    d = MontageDisplay(
        name="t",
        groups=[
            ChannelGroup("a", ["A1", "A2"], color="red", gap_after_mm=4.0),
            ChannelGroup("b", ["B1", "B2"], color="blue"),
        ],
        channel_overrides={"A2": ChannelStyle(label="A2", color="orange")},
    )
    assert d.resolve_ordered_labels() == ["A1", "A2", "B1", "B2"]
    # A2 is last of group 'a' → gets group's gap_after_mm = 4.0
    assert d.resolve_gaps_mm() == [0.0, 4.0, 0.0, 0.0]
    assert d.resolve_colors() == ["red", "orange", "blue", "blue"]
    assert d.resolve_gains() == [1.0, 1.0, 1.0, 1.0]


def test_resolve_hidden_channel_is_dropped():
    d = MontageDisplay(
        groups=[
            ChannelGroup("a", ["A1", "A2", "A3"], color="red", gap_after_mm=2.0),
        ],
        channel_overrides={"A2": ChannelStyle(label="A2", visible=False)},
    )
    assert d.resolve_ordered_labels() == ["A1", "A3"]
    # A3 is now the last visible in the group, so it gets the group gap
    assert d.resolve_gaps_mm() == [0.0, 2.0]


def test_channel_override_gap_wins_over_group_gap():
    d = MontageDisplay(
        groups=[
            ChannelGroup("a", ["A1", "A2"], color="red", gap_after_mm=5.0),
        ],
        channel_overrides={"A2": ChannelStyle(label="A2", gap_after_mm=1.5)},
    )
    # A2 is last of group; override gap 1.5 wins over group gap 5.0
    assert d.resolve_gaps_mm() == [0.0, 1.5]


# ---------- JSON round-trip ----------


def test_montage_display_json_roundtrip_with_ref():
    d = default_double_banana_display()
    with tempfile.TemporaryDirectory() as td:
        path = Path(td) / "display.json"
        d.save(path)
        loaded = MontageDisplay.load(path)
    assert loaded.name == d.name
    assert loaded.derivation_ref == "double_banana"
    assert [g.name for g in loaded.groups] == [g.name for g in d.groups]
    assert loaded.groups[0].gap_after_mm == 3.0
    assert loaded.resolve_ordered_labels() == d.resolve_ordered_labels()


def test_montage_display_json_roundtrip_with_embedded_matrix():
    deriv = MontageDerivation(
        montage_labels=["a-b", "b-c"],
        rec_labels=["a", "b", "c"],
        matrix=[[1.0, -1.0, 0.0], [0.0, 1.0, -1.0]],
        reversed_polarity=False,
    )
    d = MontageDisplay(
        name="custom",
        derivation=deriv,
        groups=[ChannelGroup("only", ["a-b", "b-c"], color="green")],
    )
    with tempfile.TemporaryDirectory() as td:
        path = Path(td) / "d.json"
        d.save(path)
        with open(path) as f:
            raw = json.load(f)
        assert raw["derivation"]["matrix"] == [[1.0, -1.0, 0.0], [0.0, 1.0, -1.0]]
        loaded = MontageDisplay.load(path)
    assert loaded.derivation is not None
    assert loaded.derivation.matrix == [[1.0, -1.0, 0.0], [0.0, 1.0, -1.0]]
    assert loaded.derivation.reversed_polarity is False


def test_json_tolerates_unknown_keys_with_validate_off():
    """Loading with validate=False ignores extra keys (forward-compat)."""
    raw = {
        "name": "x",
        "groups": [
            {
                "name": "g",
                "channels": ["A"],
                "color": "red",
                "gap_after_mm": 0.0,
                "extra_field_from_future_version": 42,
            },
        ],
    }
    with tempfile.TemporaryDirectory() as td:
        path = Path(td) / "d.json"
        with open(path, "w") as f:
            json.dump(raw, f)
        loaded = MontageDisplay.load(path, validate=False)
    assert loaded.groups[0].name == "g"


def test_strict_validation_catches_unknown_keys():
    """With default validate=True, unknown keys raise."""
    import jsonschema

    raw = {
        "name": "x",
        "groups": [
            {
                "name": "g",
                "channels": ["A"],
                "extra_field_from_future_version": 42,
            },
        ],
    }
    with pytest.raises(jsonschema.ValidationError):
        MontageDisplay.from_dict(raw)


# ---------- build_montage_view ----------


def test_build_montage_view_from_ref_requires_rec_labels():
    d = MontageDisplay(derivation_ref="double_banana")
    with pytest.raises(ValueError):
        d.build_montage_view()


def test_build_montage_view_from_ref():
    rec = [
        "Fp1",
        "Fp2",
        "F7",
        "F8",
        "F3",
        "F4",
        "Fz",
        "T3",
        "T4",
        "C3",
        "C4",
        "Cz",
        "T5",
        "T6",
        "P3",
        "P4",
        "Pz",
        "O1",
        "O2",
    ]
    d = default_double_banana_display()
    mv = d.build_montage_view(rec_labels=rec)
    assert mv.shape == (18, 19)
    assert "Fp1-F7" in list(mv.montage_labels)


def test_build_montage_view_from_embedded_matrix():
    deriv = MontageDerivation(
        montage_labels=["a-b"],
        rec_labels=["a", "b"],
        matrix=[[1.0, -1.0]],
    )
    d = MontageDisplay(derivation=deriv)
    mv = d.build_montage_view()
    assert mv.V.data.tolist() == [[1.0, -1.0]]


def test_build_montage_view_no_derivation_raises():
    d = MontageDisplay()
    with pytest.raises(ValueError):
        d.build_montage_view()


def test_derivation_ref_trace_is_identity_over_rec_labels():
    """'trace' is the pass-through derivation: V is the identity over
    rec_labels, montage_labels == rec_labels. Reversed-polarity flips sign."""
    rec = ["Fp1", "Fp2", "F3", "C3"]
    d = MontageDisplay(
        name="t",
        derivation_ref="trace",
        groups=[ChannelGroup("g", rec)],
    )
    mv = d.build_montage_view(rec_labels=rec)
    expected = -np.eye(len(rec))  # default reversed_polarity=True
    assert np.allclose(mv.V.data, expected)
    assert list(mv.montage_labels) == rec


def test_derivation_ref_trace_lists_in_builtins():
    """Regression: 'trace' must be in the registry so derivation_ref works."""
    assert "trace" in list_builtin_derivations()


def test_list_builtin_derivations_contains_known():
    names = list_builtin_derivations()
    assert "double_banana" in names
    assert "tcp" in names
    assert "laplacian" in names


# ---------- show_montage_display_svg end-to-end ----------


def _synth_rec(num_samples=400, fs=200.0):
    rec_labels = [
        "Fp1",
        "Fp2",
        "F7",
        "F8",
        "F3",
        "F4",
        "Fz",
        "T3",
        "T4",
        "C3",
        "C4",
        "Cz",
        "T5",
        "T6",
        "P3",
        "P4",
        "Pz",
        "O1",
        "O2",
    ]
    rng = np.random.RandomState(7)
    signals = rng.randn(len(rec_labels), num_samples) * 20.0
    return signals, fs, rec_labels


def test_show_montage_display_svg_renders_grouped_double_banana():
    signals, fs, rec = _synth_rec()
    d = default_double_banana_display()
    svg_str = show_montage_display_svg(signals, fs, d, rec_labels=rec, sensitivity=7.0)
    root = ET.fromstring(svg_str)
    channels = root.findall(".//svg:g[@class='channel']", NS)
    assert len(channels) == 18

    labels = [ch.attrib["data-channel-name"] for ch in channels]
    # Display order present (channels are in display order in the SVG, though
    # topdown may have reversed visual order; data-channel-name still matches).
    assert "Fp1-F7" in labels
    assert "Cz-Pz" in labels


def test_show_montage_display_svg_applies_group_colors():
    signals, fs, rec = _synth_rec()
    d = default_double_banana_display()
    svg_str = show_montage_display_svg(signals, fs, d, rec_labels=rec, sensitivity=7.0)
    root = ET.fromstring(svg_str)
    polys = root.findall(".//svg:polyline[@class='trace']", NS)
    strokes = {p.attrib["stroke"] for p in polys}
    assert "#1f4e79" in strokes  # left chains
    assert "#a8323e" in strokes  # right chains
    assert "#000000" in strokes  # midline


def test_save_montage_display_svg_writes_file():
    signals, fs, rec = _synth_rec()
    d = default_double_banana_display()
    with tempfile.TemporaryDirectory() as td:
        out = Path(td) / "out.svg"
        save_montage_display_svg(out, signals, fs, d, rec_labels=rec, sensitivity=7.0)
        assert out.exists() and out.stat().st_size > 0
        text = out.read_text(encoding="utf-8")
        assert "<svg" in text


def test_show_montage_display_svg_with_embedded_matrix():
    """An embedded MontageDerivation should not require rec_labels."""
    rng = np.random.RandomState(3)
    signals = rng.randn(3, 300) * 10.0
    deriv = MontageDerivation(
        montage_labels=["a-b", "b-c"],
        rec_labels=["a", "b", "c"],
        matrix=[[1.0, -1.0, 0.0], [0.0, 1.0, -1.0]],
    )
    d = MontageDisplay(
        name="t",
        derivation=deriv,
        groups=[ChannelGroup("g", ["a-b", "b-c"], color="purple")],
    )
    svg_str = show_montage_display_svg(signals, 200.0, d, sensitivity=7.0)
    root = ET.fromstring(svg_str)
    polys = root.findall(".//svg:polyline[@class='trace']", NS)
    assert len(polys) == 2
    assert all(p.attrib["stroke"] == "purple" for p in polys)


def test_show_montage_display_svg_hidden_channel_dropped():
    signals, fs, rec = _synth_rec()
    d = default_double_banana_display()
    d.channel_overrides["Cz-Pz"] = ChannelStyle(label="Cz-Pz", visible=False)
    svg_str = show_montage_display_svg(signals, fs, d, rec_labels=rec, sensitivity=7.0)
    root = ET.fromstring(svg_str)
    channels = root.findall(".//svg:g[@class='channel']", NS)
    labels = [ch.attrib["data-channel-name"] for ch in channels]
    assert "Cz-Pz" not in labels
    assert len(channels) == 17


# ---------- SymbolicDerivation ----------


def test_symbolic_diffpair_builds_bipolar_matrix():
    deriv = SymbolicDerivation(
        channels=[
            SymbolicChannel(label="A-B", diffpair=["A", "B"]),
            SymbolicChannel(label="B-C", diffpair=["B", "C"]),
        ],
        reversed_polarity=False,
    )
    mv = deriv.to_montage_view(["A", "B", "C"])
    expected = np.array([[1, -1, 0], [0, 1, -1]], dtype=float)
    assert np.allclose(mv.V.data, expected)


def test_symbolic_reversed_polarity_negates_matrix():
    deriv = SymbolicDerivation(
        channels=[SymbolicChannel(label="A-B", diffpair=["A", "B"])],
        reversed_polarity=True,
    )
    mv = deriv.to_montage_view(["A", "B"])
    assert np.allclose(mv.V.data, [[-1, 1]])


def test_symbolic_sum_coefficients_general_form():
    deriv = SymbolicDerivation(
        channels=[
            SymbolicChannel(
                label="laplacian",
                sum_coefficients={
                    "C": 1.0,
                    "N": -0.25,
                    "S": -0.25,
                    "E": -0.25,
                    "W": -0.25,
                },
            )
        ],
        reversed_polarity=False,
    )
    mv = deriv.to_montage_view(["N", "E", "C", "W", "S"])
    assert np.allclose(mv.V.data, [[-0.25, -0.25, 1.0, -0.25, -0.25]])


def test_symbolic_virtual_mean_resolves_to_common_average():
    deriv = SymbolicDerivation(
        channels=[
            SymbolicChannel(label="A-AVG", diffpair=["A", "AVG"]),
            SymbolicChannel(label="B-AVG", diffpair=["B", "AVG"]),
        ],
        virtual_channels={
            "AVG": VirtualElectrode(type="mean", electrodes=["A", "B", "C"])
        },
        reversed_polarity=False,
    )
    mv = deriv.to_montage_view(["A", "B", "C"])
    # A-AVG = A - (1/3)(A+B+C) = (2/3)A - (1/3)B - (1/3)C
    # B-AVG = B - (1/3)(A+B+C) = -(1/3)A + (2/3)B - (1/3)C
    expected = np.array([[2 / 3, -1 / 3, -1 / 3], [-1 / 3, 2 / 3, -1 / 3]], dtype=float)
    assert np.allclose(mv.V.data, expected)


def test_symbolic_virtual_weighted_uses_explicit_weights():
    deriv = SymbolicDerivation(
        channels=[SymbolicChannel(label="X-LE", diffpair=["X", "LE"])],
        virtual_channels={
            "LE": VirtualElectrode(type="weighted", weights={"A1": 0.5, "A2": 0.5})
        },
        reversed_polarity=False,
    )
    mv = deriv.to_montage_view(["X", "A1", "A2"])
    assert np.allclose(mv.V.data, [[1.0, -0.5, -0.5]])


def test_symbolic_diffpair_missing_electrode_raises():
    deriv = SymbolicDerivation(
        channels=[SymbolicChannel(label="X-Y", diffpair=["X", "Y"])],
    )
    with pytest.raises(KeyError, match="neither a virtual channel"):
        deriv.to_montage_view(["X", "Z"])


def test_symbolic_channel_must_pick_one_form():
    bad_both = SymbolicChannel(
        label="x", diffpair=["A", "B"], sum_coefficients={"A": 1}
    )
    with pytest.raises(ValueError, match="exactly one"):
        bad_both.resolve(["A", "B"], {})

    bad_neither = SymbolicChannel(label="x")
    with pytest.raises(ValueError, match="exactly one"):
        bad_neither.resolve(["A", "B"], {})


def test_symbolic_matches_derivation_ref_for_double_banana():
    """SymbolicDerivation with diffpair pairs should produce the same matrix
    as the built-in DoubleBananaMontageView."""
    rec = [
        "Fp1",
        "Fp2",
        "F3",
        "F4",
        "C3",
        "C4",
        "P3",
        "P4",
        "O1",
        "O2",
        "F7",
        "F8",
        "T3",
        "T4",
        "T5",
        "T6",
        "Fz",
        "Cz",
        "Pz",
    ]
    db_labels = [
        "Fp1-F7",
        "F7-T3",
        "T3-T5",
        "T5-O1",
        "Fp2-F8",
        "F8-T4",
        "T4-T6",
        "T6-O2",
        "Fp1-F3",
        "F3-C3",
        "C3-P3",
        "P3-O1",
        "Fp2-F4",
        "F4-C4",
        "C4-P4",
        "P4-O2",
        "Fz-Cz",
        "Cz-Pz",
    ]
    d_ref = MontageDisplay(
        name="ref",
        derivation_ref="double_banana",
        groups=[ChannelGroup("g", db_labels)],
    )
    d_sym = MontageDisplay(
        name="sym",
        derivation=SymbolicDerivation(
            channels=[
                SymbolicChannel(label=lbl, diffpair=lbl.split("-")) for lbl in db_labels
            ],
            reversed_polarity=True,
        ),
        groups=[ChannelGroup("g", db_labels)],
    )
    mv_ref = d_ref.build_montage_view(rec_labels=rec)
    mv_sym = d_sym.build_montage_view(rec_labels=rec)
    assert np.allclose(mv_ref.V.data, mv_sym.V.data)


def test_symbolic_derivation_json_roundtrip():
    d = MontageDisplay(
        name="sym_rt",
        derivation=SymbolicDerivation(
            channels=[
                SymbolicChannel(label="A-B", diffpair=["A", "B"]),
                SymbolicChannel(label="custom", sum_coefficients={"A": 0.5, "B": -0.5}),
            ],
            virtual_channels={
                "AVG": VirtualElectrode(type="mean", electrodes=["A", "B", "C"])
            },
            reversed_polarity=False,
        ),
        groups=[ChannelGroup("g", ["A-B", "custom"])],
    )
    js = d.to_dict()
    assert js["derivation"]["type"] == "symbolic"
    d2 = MontageDisplay.from_dict(js)
    assert isinstance(d2.derivation, SymbolicDerivation)
    assert d2.derivation.channels[0].diffpair == ["A", "B"]
    assert d2.derivation.channels[1].sum_coefficients == {"A": 0.5, "B": -0.5}
    assert d2.derivation.virtual_channels["AVG"].electrodes == ["A", "B", "C"]


def test_legacy_matrix_derivation_without_type_field_still_loads():
    """A pre-spec derivation block without the 'type' field is treated as
    matrix form for back-compat."""
    js = {
        "name": "old",
        "description": "",
        "derivation": {
            "montage_labels": ["A-B"],
            "rec_labels": ["A", "B"],
            "matrix": [[1, -1]],
            "reversed_polarity": False,
        },
        "groups": [{"name": "g", "channels": ["A-B"]}],
    }
    d = MontageDisplay.from_dict(js)
    assert isinstance(d.derivation, MontageDerivation)
    mv = d.build_montage_view()
    assert np.allclose(mv.V.data, [[1, -1]])


def test_bundled_displays_all_load_as_symbolic():
    """All shipped JSON profiles should now use SymbolicDerivation."""
    from eegvis.displays import list_displays, load_display

    for name in list_displays():
        d = load_display(name)
        assert isinstance(d.derivation, SymbolicDerivation), (
            f"bundled profile {name!r} should use SymbolicDerivation, "
            f"got {type(d.derivation).__name__}"
        )


# ---------- JSON Schema validation ----------


def test_validation_catches_pair_typo_for_diffpair():
    """Common typo: writing 'pair' instead of 'diffpair'."""
    import jsonschema
    from eegvis.montage_display import validate_montage_display_dict

    raw = {
        "name": "x",
        "derivation": {
            "type": "symbolic",
            "channels": [{"label": "A-B", "pair": ["A", "B"]}],
        },
        "groups": [{"name": "g", "channels": ["A-B"]}],
    }
    with pytest.raises(jsonschema.ValidationError):
        validate_montage_display_dict(raw)


def test_validation_requires_exactly_one_channel_form():
    import jsonschema
    from eegvis.montage_display import validate_montage_display_dict

    both = {
        "name": "x",
        "derivation": {
            "type": "symbolic",
            "channels": [
                {
                    "label": "A-B",
                    "diffpair": ["A", "B"],
                    "sum_coefficients": {"A": 1, "B": -1},
                }
            ],
        },
        "groups": [{"name": "g", "channels": ["A-B"]}],
    }
    with pytest.raises(jsonschema.ValidationError):
        validate_montage_display_dict(both)

    neither = {
        "name": "x",
        "derivation": {
            "type": "symbolic",
            "channels": [{"label": "A-B"}],
        },
        "groups": [{"name": "g", "channels": ["A-B"]}],
    }
    with pytest.raises(jsonschema.ValidationError):
        validate_montage_display_dict(neither)


def test_validation_rejects_unknown_virtual_type():
    import jsonschema
    from eegvis.montage_display import validate_montage_display_dict

    raw = {
        "name": "x",
        "derivation": {
            "type": "symbolic",
            "virtual_channels": {"AVG": {"type": "median", "electrodes": ["A", "B"]}},
            "channels": [{"label": "A-AVG", "diffpair": ["A", "AVG"]}],
        },
        "groups": [{"name": "g", "channels": ["A-AVG"]}],
    }
    with pytest.raises(jsonschema.ValidationError):
        validate_montage_display_dict(raw)


def test_validation_requires_either_derivation_or_ref():
    import jsonschema
    from eegvis.montage_display import validate_montage_display_dict

    with pytest.raises(jsonschema.ValidationError):
        validate_montage_display_dict({"name": "x", "groups": []})


def test_validation_passes_for_all_bundled_profiles():
    """All shipped JSON files must satisfy the schema."""
    from eegvis.displays import list_displays, load_display

    for name in list_displays():
        # load() with default validate=True would raise; passing == success
        load_display(name)


# ---------- Error messages should point at the offending field ----------


def _err_message(raw):
    """Run validation and return the resulting message (or '' if none)."""
    import jsonschema
    from eegvis.montage_display import validate_montage_display_dict

    try:
        validate_montage_display_dict(raw)
        return ""
    except jsonschema.ValidationError as e:
        return e.message


def test_error_message_for_pair_typo_points_at_channel():
    msg = _err_message(
        {
            "name": "x",
            "derivation": {
                "type": "symbolic",
                "channels": [{"label": "A-B", "pair": ["A", "B"]}],
            },
            "groups": [{"name": "g", "channels": ["A-B"]}],
        }
    )
    assert "derivation.channels[0]" in msg
    assert "pair" in msg


def test_error_message_for_both_channel_forms_set():
    msg = _err_message(
        {
            "name": "x",
            "derivation": {
                "type": "symbolic",
                "channels": [
                    {
                        "label": "A-B",
                        "diffpair": ["A", "B"],
                        "sum_coefficients": {"A": 1, "B": -1},
                    }
                ],
            },
            "groups": [{"name": "g", "channels": ["A-B"]}],
        }
    )
    assert "derivation.channels[0]" in msg
    assert "must not be set" in msg


def test_error_message_for_neither_channel_form():
    msg = _err_message(
        {
            "name": "x",
            "derivation": {
                "type": "symbolic",
                "channels": [{"label": "A-B"}],
            },
            "groups": [{"name": "g", "channels": ["A-B"]}],
        }
    )
    assert "derivation.channels[0]" in msg
    assert "missing required field" in msg


def test_error_message_for_negative_gap():
    msg = _err_message(
        {
            "name": "x",
            "derivation": {
                "type": "symbolic",
                "channels": [{"label": "A-B", "diffpair": ["A", "B"]}],
            },
            "groups": [{"name": "g", "channels": ["A-B"], "gap_after_mm": -1.0}],
        }
    )
    assert "groups[0].gap_after_mm" in msg
    assert "minimum" in msg


# ---------- Per-channel clinical attributes (Sens/LF/HF/CAL/Width) ----------


def test_channel_style_accepts_new_attributes():
    style = ChannelStyle(
        label="Fp1-F7",
        sensitivity=7.0,
        lf=1.0,
        hf=70.0,
        cal=50.0,
        width=0.4,
    )
    assert style.sensitivity == 7.0
    assert style.lf == 1.0
    assert style.hf == 70.0
    assert style.cal == 50.0
    assert style.width == 0.4


def test_schema_accepts_per_channel_attributes():
    from eegvis.montage_display import validate_montage_display_dict

    raw = {
        "name": "x",
        "derivation": {
            "type": "symbolic",
            "channels": [{"label": "A-B", "diffpair": ["A", "B"]}],
        },
        "groups": [{"name": "g", "channels": ["A-B"]}],
        "channel_overrides": {
            "A-B": {
                "label": "A-B",
                "sensitivity": 7.0,
                "lf": 1.0,
                "hf": 70.0,
                "cal": 50.0,
                "width": 0.4,
            },
        },
    }
    validate_montage_display_dict(raw)  # no raise


def test_schema_rejects_zero_or_negative_sensitivity():
    import jsonschema
    from eegvis.montage_display import validate_montage_display_dict

    raw = {
        "name": "x",
        "derivation": {
            "type": "symbolic",
            "channels": [{"label": "A-B", "diffpair": ["A", "B"]}],
        },
        "groups": [{"name": "g", "channels": ["A-B"]}],
        "channel_overrides": {
            "A-B": {"label": "A-B", "sensitivity": 0},
        },
    }
    with pytest.raises(jsonschema.ValidationError):
        validate_montage_display_dict(raw)


def test_schema_allows_null_to_clear_per_channel_attr():
    from eegvis.montage_display import validate_montage_display_dict

    raw = {
        "name": "x",
        "derivation": {
            "type": "symbolic",
            "channels": [{"label": "A-B", "diffpair": ["A", "B"]}],
        },
        "groups": [{"name": "g", "channels": ["A-B"]}],
        "channel_overrides": {
            "A-B": {"label": "A-B", "sensitivity": None, "lf": None},
        },
    }
    validate_montage_display_dict(raw)  # null is allowed


def test_json_roundtrip_preserves_per_channel_attributes():
    """JSON save/load preserves the new fields."""
    d = MontageDisplay(
        name="rt",
        derivation=SymbolicDerivation(
            channels=[SymbolicChannel(label="A-B", diffpair=["A", "B"])]
        ),
        groups=[ChannelGroup("g", ["A-B"])],
        channel_overrides={
            "A-B": ChannelStyle(
                label="A-B", sensitivity=7.0, lf=1.0, hf=70.0, cal=50.0, width=0.4
            )
        },
    )
    with tempfile.TemporaryDirectory() as td:
        path = Path(td) / "rt.json"
        d.save(path)
        loaded = MontageDisplay.load(path)
    style = loaded.channel_overrides["A-B"]
    assert style.sensitivity == 7.0
    assert style.lf == 1.0
    assert style.hf == 70.0
    assert style.cal == 50.0
    assert style.width == 0.4


def test_editor_session_roundtrips_per_channel_attributes():
    """EditorRow attrs survive to_display() -> from_display()."""
    from eegvis.viewer.editor_session import EditorRow, EditorSession

    sess = EditorSession(
        name="rt",
        rows=[
            EditorRow(
                kind="channel",
                g1="A",
                g2="B",
                color="#1f4e79",
                sensitivity=7.0,
                lf=1.0,
                hf=70.0,
                cal=50.0,
                width=0.4,
            )
        ],
    )
    display = sess.to_display()
    style = display.channel_overrides["A-B"]
    assert style.sensitivity == 7.0
    assert style.width == 0.4

    restored = EditorSession.from_display(display)
    assert len(restored.rows) == 1
    row = restored.rows[0]
    assert row.sensitivity == 7.0
    assert row.lf == 1.0
    assert row.hf == 70.0
    assert row.cal == 50.0
    assert row.width == 0.4


def test_editor_set_cell_parses_numeric_fields():
    from eegvis.viewer.editor_session import EditorRow, EditorSession

    sess = EditorSession(rows=[EditorRow(kind="channel", g1="A", g2="B")])
    sess.set_cell(0, "sensitivity", "7.5")
    sess.set_cell(0, "lf", "1.0")
    sess.set_cell(0, "width", "")  # empty clears
    assert sess.rows[0].sensitivity == 7.5
    assert sess.rows[0].lf == 1.0
    assert sess.rows[0].width is None


# ---------- Renderer wire-through for per-channel attrs ----------


def _synth_for_overrides():
    """Tiny 3-channel synthetic for the override-rendering tests."""
    fs = 200.0
    rec = ["A", "B", "C"]
    t = np.arange(int(fs * 2)) / fs
    rng = np.random.default_rng(0)
    signals = np.zeros((3, len(t)))
    for i in range(3):
        signals[i] = rng.normal(0, 5, len(t)) + 10 * np.sin(2 * np.pi * 10 * t)
    return signals, fs, rec


def _build_display_with_overrides(overrides):
    return MontageDisplay(
        name="t",
        derivation=SymbolicDerivation(
            channels=[
                SymbolicChannel(label="A-B", diffpair=["A", "B"]),
                SymbolicChannel(label="B-C", diffpair=["B", "C"]),
            ],
        ),
        groups=[ChannelGroup("g", ["A-B", "B-C"])],
        channel_overrides=overrides,
    )


def test_per_channel_width_lands_on_polyline_stroke_width():
    signals, fs, rec = _synth_for_overrides()
    d = _build_display_with_overrides({"A-B": ChannelStyle(label="A-B", width=0.9)})
    svg_str = show_montage_display_svg(signals, fs, d, rec_labels=rec, sensitivity=7.0)
    root = ET.fromstring(svg_str)
    # Match by data-channel-name (independent of bottom-up render order)
    polys = {}
    for ch in root.findall(".//svg:g[@class='channel']", NS):
        name = ch.attrib["data-channel-name"]
        poly = ch.find("./svg:polyline", NS)
        polys[name] = float(poly.attrib["stroke-width"])
    assert polys["A-B"] == 0.9
    # B-C falls back to theme default
    assert polys["B-C"] != 0.9


def test_per_channel_cal_renders_annotation():
    signals, fs, rec = _synth_for_overrides()
    d = _build_display_with_overrides({"A-B": ChannelStyle(label="A-B", cal=50.0)})
    svg_str = show_montage_display_svg(signals, fs, d, rec_labels=rec, sensitivity=7.0)
    root = ET.fromstring(svg_str)
    cal_texts = []
    for ch in root.findall(".//svg:g[@class='channel']", NS):
        for txt in ch.findall("./svg:text[@class='channel-cal']", NS):
            cal_texts.append((ch.attrib["data-channel-name"], txt.text))
    assert ("A-B", "50µV") in cal_texts
    # B-C has no override → no annotation
    assert not any(name == "B-C" for name, _ in cal_texts)


def test_per_channel_sensitivity_scales_yscale():
    """Channel with smaller per-channel sensitivity should render with a
    larger y_scale_factor (more sensitive = bigger amplitude)."""
    signals, fs, rec = _synth_for_overrides()
    # Channel A-B at half the global sensitivity should be 2x larger.
    d = _build_display_with_overrides(
        {"A-B": ChannelStyle(label="A-B", sensitivity=3.5)}  # global is 7.0
    )
    svg_str = show_montage_display_svg(signals, fs, d, rec_labels=rec, sensitivity=7.0)
    root = ET.fromstring(svg_str)
    yscales = {}
    for ch in root.findall(".//svg:g[@class='channel']", NS):
        name = ch.attrib["data-channel-name"]
        poly = ch.find("./svg:polyline", NS)
        yscales[name] = float(poly.attrib["data-yscale"])
    # A-B should be roughly 2x B-C
    assert yscales["A-B"] / yscales["B-C"] == pytest.approx(2.0, rel=1e-3)


def test_per_channel_lf_hf_changes_trace_points():
    """When LF/HF are set per-channel, the corresponding polyline points
    should differ from the unfiltered case for that channel only."""
    signals, fs, rec = _synth_for_overrides()
    d_plain = _build_display_with_overrides({})
    d_filt = _build_display_with_overrides(
        {"A-B": ChannelStyle(label="A-B", lf=2.0, hf=20.0)}
    )
    plain = ET.fromstring(
        show_montage_display_svg(signals, fs, d_plain, rec_labels=rec, sensitivity=7.0)
    )
    filt = ET.fromstring(
        show_montage_display_svg(signals, fs, d_filt, rec_labels=rec, sensitivity=7.0)
    )

    def points(root, name):
        for ch in root.findall(".//svg:g[@class='channel']", NS):
            if ch.attrib["data-channel-name"] == name:
                return ch.find("./svg:polyline", NS).attrib["points"]
        return None

    assert points(plain, "A-B") != points(filt, "A-B"), (
        "A-B trace should change after per-channel filtering"
    )
    # B-C had no override — its trace should be identical.
    assert points(plain, "B-C") == points(filt, "B-C")


def test_channel_widths_length_validation():
    """stackplot_svg should raise if channel_widths length != num_channels."""
    signals = np.zeros((3, 100))
    with pytest.raises(ValueError, match="channel_widths must have length 3"):
        stackplot_svg.stackplot_svg(
            signals, sample_frequency=100.0, channel_widths=[0.5, 0.5]
        )


def test_channel_cal_length_validation():
    signals = np.zeros((3, 100))
    with pytest.raises(ValueError, match="channel_cal must have length 3"):
        stackplot_svg.stackplot_svg(
            signals, sample_frequency=100.0, channel_cal=[50, 50]
        )


def test_apply_per_channel_bandpass_only_filters_specified_rows():
    from eegvis.stackplot_svg import apply_per_channel_bandpass

    fs = 200.0
    t = np.arange(int(fs * 2)) / fs
    signals = np.stack(
        [
            np.sin(2 * np.pi * 10 * t),
            np.sin(2 * np.pi * 10 * t),
            np.sin(2 * np.pi * 10 * t),
        ]
    )
    out = apply_per_channel_bandpass(
        signals, fs, channel_lf=[None, 0.5, None], channel_hf=[None, 30.0, None]
    )
    # Row 0 and 2 should be byte-identical, row 1 should differ.
    assert np.array_equal(out[0], signals[0])
    assert np.array_equal(out[2], signals[2])
    assert not np.array_equal(out[1], signals[1])
