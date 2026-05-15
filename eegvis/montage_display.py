# -*- coding: utf-8 -*-
"""Montage display profiles: derivation + presentation (groups, gaps, colors).

A ``MontageDisplay`` bundles three things that have historically lived in
separate places:

1. **Which derivation to apply** — a built-in by name
   (``derivation_ref="double_banana"``), a self-contained matrix block
   (:class:`MontageDerivation`), or a portable symbolic linear-combination
   block (:class:`SymbolicDerivation`) — see ``displays/SCHEMA.md``.
2. **How to group and order the derived channels** — a list of
   :class:`ChannelGroup` with names, default colors, and a ``gap_after_mm``
   that produces an extra visual break after the group.
3. **Per-channel overrides** — :class:`ChannelStyle` entries keyed by label
   for color, extra gap, visibility, and gain.

Display profiles round-trip through JSON via :meth:`MontageDisplay.save` and
:meth:`MontageDisplay.load`.
"""

from __future__ import annotations

import dataclasses
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, List, Optional, Union

import numpy as np


@dataclass
class ChannelStyle:
    """Per-channel display override.

    Any field left at its default falls back to the channel's group setting
    (or to the renderer's global default — e.g. the viewer-toolbar
    sensitivity).

    Clinical-style per-channel attributes:

    - ``sensitivity``: absolute sensitivity in μV/mm. Overrides the
      renderer's global sensitivity for this channel.
    - ``lf``: low-frequency cutoff (high-pass filter), Hz.
    - ``hf``: high-frequency cutoff (low-pass filter), Hz.
    - ``cal``: calibration amplitude, μV (used for the per-channel scale
      bar / calibration pulse).
    - ``width``: trace stroke width in mm.
    - ``gain``: dimensionless multiplier on top of the global / sensitivity
      scaling. Distinct from ``sensitivity``: ``gain`` is relative,
      ``sensitivity`` is absolute. If both are set, ``sensitivity`` wins
      and ``gain`` is composed on top of it.

    These are *captured* in the JSON profile and surfaced in the editor;
    the SVG renderer does not yet honor them per-channel (it uses the
    global toolbar values). Wiring them through ``stackplot_svg`` is a
    separate change tracked in ``TODO.md``.
    """

    label: str
    color: Optional[str] = None
    gap_after_mm: Optional[float] = None
    visible: bool = True
    gain: float = 1.0
    sensitivity: Optional[float] = None
    lf: Optional[float] = None
    hf: Optional[float] = None
    cal: Optional[float] = None
    width: Optional[float] = None


@dataclass
class ChannelGroup:
    """A contiguous, named group of channels with shared default styling."""

    name: str
    channels: List[str] = field(default_factory=list)
    color: Optional[str] = None
    gap_after_mm: float = 0.0


@dataclass
class MontageDerivation:
    """Self-contained linear derivation: M output channels from N inputs.

    ``matrix`` is shape (len(montage_labels), len(rec_labels)). The matrix is
    stored as-is — if a polarity flip was applied when building the original
    MontageView, that flip should already be baked into ``matrix``. The
    ``reversed_polarity`` flag is preserved as metadata only.
    """

    montage_labels: List[str]
    rec_labels: List[str]
    matrix: List[List[float]]
    reversed_polarity: bool = True

    def to_montage_view(self):
        from .montageview import MontageView

        mv = MontageView(
            list(self.montage_labels),
            list(self.rec_labels),
            reversed_polarity=self.reversed_polarity,
        )
        arr = np.asarray(self.matrix, dtype=float)
        expected = (len(self.montage_labels), len(self.rec_labels))
        if arr.shape != expected:
            raise ValueError(
                f"matrix shape {arr.shape} does not match "
                f"(len(montage_labels), len(rec_labels))={expected}"
            )
        mv.V.data[:] = arr
        mv.name = "from_file"
        return mv

    @classmethod
    def from_montage_view(cls, mv) -> "MontageDerivation":
        return cls(
            montage_labels=list(mv.montage_labels),
            rec_labels=list(mv.rec_labels),
            matrix=np.asarray(mv.V.data).tolist(),
            reversed_polarity=getattr(mv, "reversed_polarity", True),
        )


@dataclass
class VirtualElectrode:
    """A named linear combination of physical electrodes.

    Used wherever an electrode name is referenced inside a
    :class:`SymbolicChannel` (in ``diffpair`` or ``sum_coefficients``).
    Virtual names take precedence over physical electrodes of the same
    name when resolved against ``rec_labels``.
    """

    type: str = "mean"
    electrodes: List[str] = field(default_factory=list)
    weights: Dict[str, float] = field(default_factory=dict)

    def resolve(self, rec_labels: List[str]) -> np.ndarray:
        """Return a length-``len(rec_labels)`` coefficient vector."""
        n = len(rec_labels)
        out = np.zeros(n, dtype=float)
        idx = {lbl: i for i, lbl in enumerate(rec_labels)}
        if self.type == "mean":
            if not self.electrodes:
                raise ValueError(
                    "VirtualElectrode type 'mean' requires a non-empty 'electrodes' list"
                )
            w = 1.0 / len(self.electrodes)
            for e in self.electrodes:
                if e not in idx:
                    raise KeyError(
                        f"electrode {e!r} required by virtual 'mean' channel "
                        f"is not present in rec_labels {rec_labels}"
                    )
                out[idx[e]] += w
        elif self.type == "weighted":
            for e, w in self.weights.items():
                if e not in idx:
                    raise KeyError(
                        f"electrode {e!r} required by virtual 'weighted' channel "
                        f"is not present in rec_labels {rec_labels}"
                    )
                out[idx[e]] += float(w)
        else:
            raise ValueError(
                f"unknown VirtualElectrode type {self.type!r}; "
                f"expected 'mean' or 'weighted'"
            )
        return out


@dataclass
class SymbolicChannel:
    """One derived channel defined as a symbolic linear combination.

    Exactly one of ``diffpair`` and ``sum_coefficients`` must be set.

    - ``diffpair=[a, b]`` is the bipolar shorthand: +1 on ``a``, −1 on ``b``.
      Either name may reference a physical electrode (in ``rec_labels``) or
      a :class:`VirtualElectrode`.
    - ``sum_coefficients={name: weight, ...}`` is the general form: an
      explicit weighted sum over named electrodes / virtuals.
    """

    label: str
    diffpair: Optional[List[str]] = None
    sum_coefficients: Optional[Dict[str, float]] = None

    def resolve(
        self,
        rec_labels: List[str],
        virtual_channels: Dict[str, VirtualElectrode],
    ) -> np.ndarray:
        """Return the coefficient vector this channel applies to rec_labels."""
        n = len(rec_labels)
        out = np.zeros(n, dtype=float)
        idx = {lbl: i for i, lbl in enumerate(rec_labels)}

        def add(name: str, weight: float) -> None:
            if name in virtual_channels:
                out[:] += weight * virtual_channels[name].resolve(rec_labels)
            elif name in idx:
                out[idx[name]] += weight
            else:
                raise KeyError(
                    f"channel {self.label!r}: name {name!r} is neither a "
                    f"virtual channel {list(virtual_channels)} nor a rec_label "
                    f"{rec_labels}"
                )

        diffpair_set = self.diffpair is not None
        coeff_set = self.sum_coefficients is not None
        if diffpair_set == coeff_set:
            raise ValueError(
                f"channel {self.label!r}: must set exactly one of 'diffpair' "
                f"or 'sum_coefficients', got diffpair={self.diffpair!r}, "
                f"sum_coefficients={self.sum_coefficients!r}"
            )
        if diffpair_set:
            if len(self.diffpair) != 2:
                raise ValueError(
                    f"channel {self.label!r}: diffpair must be [a, b], "
                    f"got {self.diffpair!r}"
                )
            add(self.diffpair[0], 1.0)
            add(self.diffpair[1], -1.0)
        else:
            for name, w in self.sum_coefficients.items():
                add(name, float(w))
        return out


@dataclass
class SymbolicDerivation:
    """Portable derivation expressed as symbolic per-channel coefficients.

    The matrix is built at apply time from ``rec_labels`` so the same
    profile works across recordings with different electrode sets, as long
    as the named electrodes are present.
    """

    channels: List[SymbolicChannel] = field(default_factory=list)
    virtual_channels: Dict[str, VirtualElectrode] = field(default_factory=dict)
    reversed_polarity: bool = True

    @property
    def montage_labels(self) -> List[str]:
        return [c.label for c in self.channels]

    def to_montage_view(self, rec_labels: List[str]):
        """Resolve virtuals and build a :class:`MontageView`."""
        from .montageview import MontageView

        labels = list(self.montage_labels)
        rec_labels = list(rec_labels)
        m, n = len(labels), len(rec_labels)
        matrix = np.zeros((m, n), dtype=float)
        for i, channel in enumerate(self.channels):
            matrix[i] = channel.resolve(rec_labels, self.virtual_channels)
        if self.reversed_polarity:
            matrix = -matrix
        mv = MontageView(labels, rec_labels, reversed_polarity=self.reversed_polarity)
        mv.V.data[:] = matrix
        mv.name = "from_symbolic"
        return mv

    def to_dict(self) -> dict:
        d: dict = {
            "type": "symbolic",
            "reversed_polarity": self.reversed_polarity,
        }
        if self.virtual_channels:
            d["virtual_channels"] = {
                name: _virtual_to_dict(v) for name, v in self.virtual_channels.items()
            }
        d["channels"] = [_symbolic_channel_to_dict(c) for c in self.channels]
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "SymbolicDerivation":
        virtuals = {
            name: _dataclass_from_dict(VirtualElectrode, v)
            for name, v in d.get("virtual_channels", {}).items()
        }
        channels = [
            _dataclass_from_dict(SymbolicChannel, c) for c in d.get("channels", [])
        ]
        return cls(
            channels=channels,
            virtual_channels=virtuals,
            reversed_polarity=d.get("reversed_polarity", True),
        )


def _virtual_to_dict(v: VirtualElectrode) -> dict:
    """Serialize a VirtualElectrode, omitting the unused field."""
    if v.type == "mean":
        return {"type": "mean", "electrodes": list(v.electrodes)}
    if v.type == "weighted":
        return {"type": "weighted", "weights": dict(v.weights)}
    return dataclasses.asdict(v)


def _symbolic_channel_to_dict(c: SymbolicChannel) -> dict:
    """Serialize a SymbolicChannel, including only the populated form."""
    out: dict = {"label": c.label}
    if c.diffpair is not None:
        out["diffpair"] = list(c.diffpair)
    if c.sum_coefficients is not None:
        out["sum_coefficients"] = dict(c.sum_coefficients)
    return out


# Registry of built-in MontageView subclasses, keyed by short name.
_BUILTIN_DERIVATIONS: Dict[str, Callable] = {}


def register_builtin_derivation(name: str, factory: Callable) -> None:
    """Register a ``MontageView`` factory under ``name``.

    The factory is called as ``factory(rec_labels)`` and must return a
    ``MontageView`` (or compatible) instance with ``.V``, ``.montage_labels``,
    and ``.rec_labels``.
    """
    _BUILTIN_DERIVATIONS[name] = factory


def _register_defaults() -> None:
    if _BUILTIN_DERIVATIONS:
        return
    from .montageview import (
        CircumferentialMontageView,
        CommonAvgRefMontageView,
        DoubleBananaMontageView,
        LaplacianMontageView,
        NeonatalMontageView,
        TCPMontageView,
        TraceMontageView,
        TrueSphenoidalMontageView,
    )

    register_builtin_derivation("double_banana", DoubleBananaMontageView)
    register_builtin_derivation("tcp", TCPMontageView)
    register_builtin_derivation("laplacian", LaplacianMontageView)
    register_builtin_derivation("circle", CircumferentialMontageView)
    register_builtin_derivation("neonatal", NeonatalMontageView)
    register_builtin_derivation("common_avg", CommonAvgRefMontageView)
    register_builtin_derivation("true_sphenoidal", TrueSphenoidalMontageView)
    # 'trace' is special: identity matrix over rec_labels, channels are
    # whatever the recording provides. Cannot be expressed as a static
    # symbolic profile — it lives only as a derivation_ref. See SCHEMA.md.
    register_builtin_derivation("trace", TraceMontageView)


def list_builtin_derivations() -> List[str]:
    _register_defaults()
    return sorted(_BUILTIN_DERIVATIONS.keys())


@dataclass
class MontageDisplay:
    """A montage derivation plus display profile (groups, spacing, colors).

    Exactly one of ``derivation_ref`` and ``derivation`` should be set:
    ``derivation_ref`` references a built-in by name (compact) and requires
    ``rec_labels`` at build time; ``derivation`` carries a self-contained
    matrix (portable across installations).

    **Channel order convention**: channels listed earlier in ``groups`` (and
    earlier within a group's ``channels`` list) are drawn higher on the
    page. A ``gap_after_mm`` on a group or channel inserts visual space
    *below* that group/channel, i.e. between it and whatever follows in the
    file. Renderers are responsible for translating this top-down order to
    whatever internal coordinate convention they use.
    """

    name: str = ""
    description: str = ""
    derivation_ref: Optional[str] = None
    derivation: Optional[Union[MontageDerivation, SymbolicDerivation]] = None
    groups: List[ChannelGroup] = field(default_factory=list)
    channel_overrides: Dict[str, ChannelStyle] = field(default_factory=dict)

    def _iter_visible(self):
        """Yield (group, channel_label, is_last_visible_in_group)."""
        for g in self.groups:
            visible = [
                c
                for c in g.channels
                if self.channel_overrides.get(c, ChannelStyle(c)).visible
            ]
            for i, c in enumerate(visible):
                yield g, c, (i == len(visible) - 1)

    def resolve_ordered_labels(self) -> List[str]:
        """Flatten visible channels across groups into display order."""
        return [c for _, c, _ in self._iter_visible()]

    def resolve_gaps_mm(self) -> List[float]:
        """Per-channel ``gap_after_mm`` in display order.

        Channel overrides win over the group's ``gap_after_mm``; the group's
        gap is only applied to the last visible channel of that group.
        """
        out: List[float] = []
        for g, c, is_last in self._iter_visible():
            override = self.channel_overrides.get(c)
            if override is not None and override.gap_after_mm is not None:
                out.append(float(override.gap_after_mm))
            elif is_last:
                out.append(float(g.gap_after_mm))
            else:
                out.append(0.0)
        return out

    def resolve_colors(self) -> List[Optional[str]]:
        """Per-channel color in display order (None = use renderer default)."""
        out: List[Optional[str]] = []
        for g, c, _ in self._iter_visible():
            override = self.channel_overrides.get(c)
            if override is not None and override.color is not None:
                out.append(override.color)
            else:
                out.append(g.color)
        return out

    def resolve_gains(self) -> List[float]:
        """Per-channel gain multiplier in display order."""
        out: List[float] = []
        for _, c, _ in self._iter_visible():
            override = self.channel_overrides.get(c)
            out.append(float(override.gain) if override is not None else 1.0)
        return out

    def build_montage_view(self, rec_labels: Optional[List[str]] = None):
        """Build a ``MontageView`` from the profile's derivation.

        - ``derivation`` (symbolic): resolves virtuals against
          ``rec_labels`` to build the matrix.
        - ``derivation`` (matrix): self-contained, ``rec_labels`` is unused.
        - ``derivation_ref``: looks up a built-in ``MontageView`` factory;
          requires ``rec_labels``.
        """
        if self.derivation is not None:
            if isinstance(self.derivation, SymbolicDerivation):
                if rec_labels is None:
                    raise ValueError(
                        "rec_labels is required when MontageDisplay uses a "
                        "symbolic derivation"
                    )
                return self.derivation.to_montage_view(rec_labels)
            return self.derivation.to_montage_view()
        if self.derivation_ref is not None:
            if rec_labels is None:
                raise ValueError(
                    "rec_labels is required when MontageDisplay uses derivation_ref"
                )
            _register_defaults()
            factory = _BUILTIN_DERIVATIONS.get(self.derivation_ref)
            if factory is None:
                raise KeyError(
                    f"unknown derivation_ref {self.derivation_ref!r}; "
                    f"known: {list_builtin_derivations()}"
                )
            return factory(list(rec_labels))
        raise ValueError("MontageDisplay has neither derivation nor derivation_ref")

    def to_dict(self) -> dict:
        d: dict = {
            "name": self.name,
            "description": self.description,
            "groups": [dataclasses.asdict(g) for g in self.groups],
            "channel_overrides": {
                k: dataclasses.asdict(v) for k, v in self.channel_overrides.items()
            },
        }
        if self.derivation_ref is not None:
            d["derivation_ref"] = self.derivation_ref
        if self.derivation is not None:
            if isinstance(self.derivation, SymbolicDerivation):
                d["derivation"] = self.derivation.to_dict()
            else:
                deriv_dict = dataclasses.asdict(self.derivation)
                deriv_dict["type"] = "matrix"
                d["derivation"] = deriv_dict
        return d

    @classmethod
    def from_dict(cls, d: dict, validate: bool = True) -> "MontageDisplay":
        """Build a :class:`MontageDisplay` from a dict.

        If ``validate`` is True (default) the dict is checked against
        :func:`validate_montage_display_dict` first so typos and structural
        errors raise with a clear pointer to the bad field. Pass
        ``validate=False`` to tolerate unknown keys (forward-compat or
        partial dicts in tests).
        """
        if validate:
            validate_montage_display_dict(d)
        groups = [_dataclass_from_dict(ChannelGroup, g) for g in d.get("groups", [])]
        overrides = {
            k: _dataclass_from_dict(ChannelStyle, v)
            for k, v in d.get("channel_overrides", {}).items()
        }
        deriv = None
        deriv_dict = d.get("derivation")
        if deriv_dict is not None:
            dtype = deriv_dict.get("type", "matrix")
            if dtype == "symbolic":
                deriv = SymbolicDerivation.from_dict(deriv_dict)
            elif dtype == "matrix":
                deriv = _dataclass_from_dict(MontageDerivation, deriv_dict)
            else:
                raise ValueError(
                    f"unknown derivation type {dtype!r}; expected "
                    f"'symbolic' or 'matrix'"
                )
        return cls(
            name=d.get("name", ""),
            description=d.get("description", ""),
            derivation_ref=d.get("derivation_ref"),
            derivation=deriv,
            groups=groups,
            channel_overrides=overrides,
        )

    def save(self, path) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load(cls, path, validate: bool = True) -> "MontageDisplay":
        with open(path, "r", encoding="utf-8") as f:
            return cls.from_dict(json.load(f), validate=validate)


def _dataclass_from_dict(klass, data: dict):
    """Construct a dataclass instance from a dict, ignoring unknown keys.

    Tolerates older or partial JSON without raising on extra fields.
    """
    valid = {f.name for f in dataclasses.fields(klass)}
    return klass(**{k: v for k, v in data.items() if k in valid})


# ----- JSON Schema validation -----------------------------------------------

_SCHEMA_PATH = (
    Path(__file__).resolve().parent / "displays" / "montage_display.schema.json"
)
_SCHEMA_CACHE: Optional[dict] = None
_VALIDATOR_CACHE = None


def _load_schema() -> dict:
    global _SCHEMA_CACHE
    if _SCHEMA_CACHE is None:
        with open(_SCHEMA_PATH, "r", encoding="utf-8") as f:
            _SCHEMA_CACHE = json.load(f)
    return _SCHEMA_CACHE


def _get_validator():
    global _VALIDATOR_CACHE
    if _VALIDATOR_CACHE is None:
        import jsonschema

        schema = _load_schema()
        cls = jsonschema.validators.validator_for(schema)
        cls.check_schema(schema)
        _VALIDATOR_CACHE = cls(schema)
    return _VALIDATOR_CACHE


def _format_jsonpath(path) -> str:
    """Render a jsonschema absolute_path as a readable dotted/indexed path.

    Empty path renders as ``"<root>"``.
    """
    parts: List[str] = []
    for p in path:
        if isinstance(p, int):
            parts.append(f"[{p}]")
        elif parts:
            parts.append(f".{p}")
        else:
            parts.append(str(p))
    return "".join(parts) or "<root>"


def _all_leaves(error):
    """Flatten an error tree to its terminal sub-errors (no further context)."""
    if not error.context:
        return [error]
    out = []
    for sub in error.context:
        out.extend(_all_leaves(sub))
    return out


# Validator keywords that aren't useful at the leaf level — these are
# composite gates that re-wrap children. Skip them when picking the best
# leaf so the message points at a concrete constraint.
_COMPOSITE_KEYWORDS = {"oneOf", "anyOf", "allOf"}


def _leaf_score(error):
    """Rank a leaf for actionability.

    Higher is better. Prioritizes deeper paths, then prefers concrete
    validator keywords (``additionalProperties``, ``required``, ``const``,
    ``enum``, ``type``, ``not``) over composite gates.
    """
    depth = len(list(error.absolute_path))
    keyword = error.validator or ""
    composite_penalty = -1 if keyword in _COMPOSITE_KEYWORDS else 0
    return (depth, composite_penalty)


def _customize_message(error) -> str:
    """Rewrite a few common jsonschema messages into clinician-friendly form."""
    keyword = error.validator or ""
    if keyword == "not":
        # "not" failures on sibling-required clauses — i.e. mutually
        # exclusive fields. Identify the field by inspecting the schema.
        schema = error.schema or {}
        not_clause = schema.get("not", {}) if isinstance(schema, dict) else {}
        required = (
            not_clause.get("required", []) if isinstance(not_clause, dict) else []
        )
        if required:
            forbidden = ", ".join(required)
            return f"{forbidden} must not be set here"
    if keyword == "required":
        missing = list(getattr(error, "validator_value", []) or [])
        if missing:
            return f"missing required field(s): {', '.join(missing)}"
    return error.message


def validate_montage_display_dict(d: dict) -> None:
    """Validate ``d`` against the bundled JSON Schema.

    On failure, raises :class:`jsonschema.ValidationError` whose message
    is prefixed with the dotted/indexed path to the offending field
    (e.g. ``"at derivation.channels[0]: 'pair' was unexpected"``). For
    ``oneOf`` / ``anyOf`` failures the message points to the deepest
    concrete sub-error rather than the parent "not valid under any of
    the given schemas".
    """
    validator = _get_validator()
    errors = list(validator.iter_errors(d))
    if not errors:
        return
    leaves: list = []
    for e in errors:
        leaves.extend(_all_leaves(e))
    if not leaves:
        # Edge case: shouldn't happen since iter_errors returned something.
        leaves = errors
    leaves.sort(key=_leaf_score, reverse=True)
    best = leaves[0]
    best.message = (
        f"at {_format_jsonpath(best.absolute_path)}: {_customize_message(best)}"
    )
    raise best


# A clinically reasonable default for the standard 18-channel double banana,
# with left-hemisphere chains in blue and right-hemisphere chains in red, plus
# small visual breaks between the four temporal/parasagittal chains and the
# midline pair.
DEFAULT_LEFT_COLOR = "#1f4e79"
DEFAULT_RIGHT_COLOR = "#a8323e"
DEFAULT_MIDLINE_COLOR = "#000000"


def default_double_banana_display() -> MontageDisplay:
    return MontageDisplay(
        name="double_banana_default",
        description=(
            "Standard 18-channel double banana, chains color-coded by "
            "hemisphere with extra spacing between chains."
        ),
        derivation_ref="double_banana",
        groups=[
            ChannelGroup(
                "left_temporal",
                ["Fp1-F7", "F7-T3", "T3-T5", "T5-O1"],
                color=DEFAULT_LEFT_COLOR,
                gap_after_mm=3.0,
            ),
            ChannelGroup(
                "right_temporal",
                ["Fp2-F8", "F8-T4", "T4-T6", "T6-O2"],
                color=DEFAULT_RIGHT_COLOR,
                gap_after_mm=3.0,
            ),
            ChannelGroup(
                "left_parasagittal",
                ["Fp1-F3", "F3-C3", "C3-P3", "P3-O1"],
                color=DEFAULT_LEFT_COLOR,
                gap_after_mm=3.0,
            ),
            ChannelGroup(
                "right_parasagittal",
                ["Fp2-F4", "F4-C4", "C4-P4", "P4-O2"],
                color=DEFAULT_RIGHT_COLOR,
                gap_after_mm=3.0,
            ),
            ChannelGroup(
                "midline",
                ["Fz-Cz", "Cz-Pz"],
                color=DEFAULT_MIDLINE_COLOR,
            ),
        ],
    )
