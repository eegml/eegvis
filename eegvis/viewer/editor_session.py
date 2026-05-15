"""Editor session state + flat-row representation of a MontageDisplay.

The montage-editor UI presents the profile as a flat list of rows, the
same way classic clinical "Pattern Editor" dialogs (NK/Stellate/Persyst)
do. Each row is either a *channel* (G1-G2 bipolar pair) or a *separator*
(visual gap between groups). This module converts between that flat form
and the structured :class:`MontageDisplay` we serialize to JSON.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from ..montage_display import (
    ChannelGroup,
    ChannelStyle,
    MontageDisplay,
    SymbolicChannel,
    SymbolicDerivation,
)

# How much vertical mm a separator row contributes between groups when we
# fold flat rows back into MontageDisplay groups.
DEFAULT_SEPARATOR_MM = 5.0

# Default colors offered in the editor color picker (clinical convention:
# blue=left, red=right, black=midline).
DEFAULT_COLOR_PALETTE = [
    "#000000",  # black / midline
    "#1f4e79",  # blue / left
    "#a8323e",  # red / right
    "#3a7ab8",  # light blue / left accent
    "#d9686f",  # light red / right accent
    "#4a8c2e",  # green
    "#7b3aa2",  # purple
]


@dataclass
class EditorRow:
    """One row in the flat editor view.

    Channel row: ``kind == "channel"``, ``g1``/``g2`` are electrode labels.
    Separator row: ``kind == "separator"``, electrode fields are unused.

    The clinical-style per-channel attributes (``sensitivity``, ``lf``,
    ``hf``, ``cal``, ``width``) mirror :class:`ChannelStyle` fields and
    round-trip through ``channel_overrides`` on save/load.
    """

    kind: str = "channel"  # "channel" | "separator"
    g1: str = ""
    g2: str = ""
    color: Optional[str] = None
    visible: bool = True
    sensitivity: Optional[float] = None
    lf: Optional[float] = None
    hf: Optional[float] = None
    cal: Optional[float] = None
    width: Optional[float] = None


@dataclass
class EditorSession:
    """Working state of one editor instance, keyed by ``session_id``."""

    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = "untitled"
    description: str = ""
    rows: List[EditorRow] = field(default_factory=list)
    selected_row: int = 0
    save_scope: str = "user"  # "user" | "system"

    # ----- conversion to/from MontageDisplay -----

    def to_display(self) -> MontageDisplay:
        """Fold the flat rows back into a :class:`MontageDisplay`.

        Contiguous non-separator rows become one :class:`ChannelGroup`;
        the group's ``gap_after_mm`` is set when a separator row follows.
        Per-row color overrides are emitted as ``ChannelStyle`` entries.
        Symbolic ``diffpair`` is used for every channel.
        """
        channels: List[SymbolicChannel] = []
        groups: List[ChannelGroup] = []
        overrides: Dict[str, ChannelStyle] = {}

        current: List[str] = []
        group_idx = 1

        def flush(gap_mm: float) -> None:
            nonlocal group_idx
            if not current:
                return
            groups.append(
                ChannelGroup(
                    name=f"group{group_idx}",
                    channels=list(current),
                    gap_after_mm=gap_mm,
                )
            )
            current.clear()
            group_idx += 1

        for row in self.rows:
            if row.kind == "separator":
                flush(DEFAULT_SEPARATOR_MM)
                continue
            label = _channel_label(row.g1, row.g2)
            if label is None:
                continue  # skip half-blank channel rows
            channels.append(SymbolicChannel(label=label, diffpair=[row.g1, row.g2]))
            current.append(label)
            style: Optional[ChannelStyle] = None
            if row.color:
                style = overrides.setdefault(label, ChannelStyle(label=label))
                style.color = row.color
            if not row.visible:
                style = overrides.setdefault(label, ChannelStyle(label=label))
                style.visible = False
            for attr in ("sensitivity", "lf", "hf", "cal", "width"):
                v = getattr(row, attr)
                if v is not None:
                    style = overrides.setdefault(label, ChannelStyle(label=label))
                    setattr(style, attr, v)
        flush(0.0)

        return MontageDisplay(
            name=self.name,
            description=self.description,
            derivation=SymbolicDerivation(channels=channels),
            groups=groups,
            channel_overrides=overrides,
        )

    @classmethod
    def from_display(cls, display: MontageDisplay) -> "EditorSession":
        """Unfold a :class:`MontageDisplay` into editor rows.

        Symbolic ``diffpair`` channels become channel rows. Channels using
        ``sum_coefficients`` are dropped from the flat view but kept on
        the session's underlying display so they're not lost when we save
        (this is a v1 limitation — the editor doesn't yet expose weighted
        sums in the UI).
        """
        rows: List[EditorRow] = []
        diffpairs: Dict[str, List[str]] = {}
        if display.derivation is not None and isinstance(
            display.derivation, SymbolicDerivation
        ):
            for ch in display.derivation.channels:
                if ch.diffpair is not None:
                    diffpairs[ch.label] = list(ch.diffpair)

        for gi, group in enumerate(display.groups):
            for label in group.channels:
                pair = diffpairs.get(label)
                if pair is None or len(pair) != 2:
                    # Channel uses sum_coefficients (or comes from a non-
                    # symbolic derivation). Show as a "computed" placeholder.
                    rows.append(
                        EditorRow(
                            kind="channel",
                            g1=label,
                            g2="(computed)",
                            color=display.channel_overrides.get(
                                label, ChannelStyle(label=label)
                            ).color
                            or group.color,
                            visible=display.channel_overrides.get(
                                label, ChannelStyle(label=label)
                            ).visible,
                        )
                    )
                else:
                    override = display.channel_overrides.get(label)
                    rows.append(
                        EditorRow(
                            kind="channel",
                            g1=pair[0],
                            g2=pair[1],
                            color=(override.color if override else None) or group.color,
                            visible=(override.visible if override else True),
                            sensitivity=override.sensitivity if override else None,
                            lf=override.lf if override else None,
                            hf=override.hf if override else None,
                            cal=override.cal if override else None,
                            width=override.width if override else None,
                        )
                    )
            # Group's trailing gap becomes a separator row between groups.
            if (
                group.gap_after_mm
                and group.gap_after_mm > 0
                and gi != len(display.groups) - 1
            ):
                rows.append(EditorRow(kind="separator"))

        return cls(name=display.name, description=display.description, rows=rows)

    # ----- mutations -----

    def insert_channel(self, at: Optional[int] = None) -> int:
        """Insert a blank channel row at ``at`` (or after the selected row)."""
        idx = self._insert_index(at)
        self.rows.insert(idx, EditorRow(kind="channel"))
        self.selected_row = idx
        return idx

    def insert_separator(self, at: Optional[int] = None) -> int:
        idx = self._insert_index(at)
        self.rows.insert(idx, EditorRow(kind="separator"))
        self.selected_row = idx
        return idx

    def delete_row(self, at: Optional[int] = None) -> None:
        if not self.rows:
            return
        idx = self._clamp(at if at is not None else self.selected_row)
        del self.rows[idx]
        if self.selected_row >= len(self.rows):
            self.selected_row = max(0, len(self.rows) - 1)

    def set_cell(self, row: int, field: str, value: str) -> None:
        if not 0 <= row < len(self.rows):
            return
        r = self.rows[row]
        if field == "g1":
            r.g1 = value
        elif field == "g2":
            r.g2 = value
        elif field == "color":
            r.color = value or None
        elif field == "visible":
            r.visible = value not in ("false", "0", "")
        elif field in ("sensitivity", "lf", "hf", "cal", "width"):
            setattr(r, field, _parse_optional_float(value))
        else:
            raise ValueError(f"unknown field {field!r}")

    # ----- helpers -----

    def _insert_index(self, at: Optional[int]) -> int:
        if at is None:
            return min(self.selected_row + 1, len(self.rows))
        return self._clamp(at)

    def _clamp(self, idx: int) -> int:
        return max(0, min(idx, len(self.rows) - 1)) if self.rows else 0


def _channel_label(g1: str, g2: str) -> Optional[str]:
    g1 = (g1 or "").strip()
    g2 = (g2 or "").strip()
    if not g1 or not g2:
        return None
    return f"{g1}-{g2}"


def _parse_optional_float(value: str) -> Optional[float]:
    """Parse a string from the editor into ``float | None``. Empty -> None."""
    if value is None:
        return None
    s = str(value).strip()
    if not s:
        return None
    try:
        return float(s)
    except ValueError:
        return None
