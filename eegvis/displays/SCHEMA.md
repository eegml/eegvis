# MontageDisplay JSON schema

This document specifies the file format for the JSON profiles in this
directory and the semantics that load/render code is expected to honor.
It is the canonical reference. Where the spec differs from current
behavior the deltas are flagged with **Δ today** notes.

A profile bundles three things into one file:

1. **A derivation** — the linear combination math that turns recording-electrode
   signals (channels × samples) into derived channels (e.g. `Fp1-F7 = Fp1 - F7`,
   or `Fp1-AVG = Fp1 - mean(...)`).
2. **A display ordering** — groups of derived channels with default colors and
   per-group spacers.
3. **Per-channel overrides** — color, gain, gap, visibility, by label.

The renderer (`stackplot_svg.show_montage_display_svg`) reads the profile,
applies the derivation matrix to the input signals, and lays the result out
according to the groups + overrides.

## Top-level structure

```json
{
  "name": "double_banana",
  "description": "Standard 18-channel double-banana ...",
  "derivation_ref": null,
  "derivation": { ... },
  "groups": [ ... ],
  "channel_overrides": { ... }
}
```

Fields:

| field               | type           | required | meaning                                                                                 |
|---------------------|----------------|----------|-----------------------------------------------------------------------------------------|
| `name`              | string         | yes      | Short identifier. Convention: lower_snake_case, matches the filename stem.              |
| `description`       | string         | optional | Free-form clinical / authoring notes.                                                   |
| `derivation_ref`    | string \| null | one-of   | Name of a built-in `MontageView` factory (e.g. `"double_banana"`, `"true_sphenoidal"`). |
| `derivation`        | object \| null | one-of   | Self-contained derivation block (see below).                                            |
| `groups`            | array          | yes      | Ordered list of `ChannelGroup` objects.                                                 |
| `channel_overrides` | object         | optional | Map of `<channel_label>` → `ChannelStyle`.                                              |

Exactly one of `derivation_ref` and `derivation` must be set. `derivation_ref`
defers the math to a Python class registered with
`register_builtin_derivation`; `derivation` carries the math inline so the
file is portable.

### Order convention

Channels listed earlier in `groups` (and earlier within a group's `channels`
array) are drawn **higher on the page**. `gap_after_mm` on a group or
channel inserts space *below* it.

## Derivation block

The `derivation` object has a `type` discriminator with two values:

### `type: "symbolic"` (preferred for new profiles)

Defines the derivation as a list of named channels, each a symbolic linear
combination of recording electrodes and optional named *virtual* electrodes.
The matrix is built at apply time once `rec_labels` are known, so the same
JSON works across recordings with different electrode sets (as long as the
named electrodes are present).

```json
"derivation": {
  "type": "symbolic",
  "reversed_polarity": true,
  "virtual_channels": {
    "AVG": {
      "type": "mean",
      "electrodes": ["Fp1", "F7", "T3", "T5", "Fp2", "F8", "T4", "T6",
                     "F3", "C3", "P3", "O1", "F4", "C4", "P4", "O2",
                     "Fz", "Cz", "Pz"]
    }
  },
  "channels": [
    {"label": "Fp1-F7", "diffpair": ["Fp1", "F7"]},
    {"label": "Fp1-AVG", "diffpair": ["Fp1", "AVG"]},
    {"label": "weighted",
     "sum_coefficients": {"Fp1": 0.5, "F7": -0.5, "T3": 0.5, "T5": -0.5}}
  ]
}
```

Fields:

| field | type | required | meaning |
|---|---|---|---|
| `type` | string | yes | Must be `"symbolic"`. |
| `reversed_polarity` | bool | optional (default `true`) | If `true`, the final matrix is multiplied by −1 so positive deflections render downward (clinical "negative up" convention). |
| `virtual_channels` | object | optional | Map of `<virtual_name>` → `VirtualElectrode`. |
| `channels` | array | yes | Ordered list of `SymbolicChannel`. Each row in the order it appears becomes one derived channel; the order of `groups[].channels` references these labels but does not have to match this order. |

#### VirtualElectrode

A named linear combination of physical electrodes. Used wherever an
electrode name is referenced (in `diffpair` or `sum_coefficients`). Virtual
names take precedence over physical electrodes with the same name — pick
names that don't collide with your recording channels.

Two flavors:

**`type: "mean"`** — equal-weight average of the listed electrodes.

```json
{"type": "mean", "electrodes": ["A1", "A2"]}
```

Resolves to coefficient `1/N` on each listed electrode, where `N` is the
length of `electrodes`. Useful for common-average reference, linked-ears
average (`mean(A1, A2)`), etc.

**`type: "weighted"`** — explicit weights.

```json
{"type": "weighted", "weights": {"A1": 0.5, "A2": 0.5}}
```

Resolves to the literal coefficient map (no normalization).

#### SymbolicChannel

One derived channel. Exactly one of `diffpair` and `sum_coefficients` must be
set.

| field | type | meaning |
|---|---|---|
| `label` | string | Channel label. Used by `groups[].channels` and `channel_overrides`. |
| `diffpair` | `[string, string]` | Bipolar shorthand: `[a, b]` → coefficient +1 on `a`, −1 on `b`. Either name may reference a virtual channel. |
| `sum_coefficients` | object | General linear combination: map of electrode (or virtual) name → coefficient. Names not listed get coefficient 0. |

**Reference resolution**: when a name appears in `diffpair` or
`sum_coefficients`, it is looked up first in `virtual_channels`, then in
`rec_labels`. Unresolved names raise an error at build time so authors
catch typos early.

**Polarity reversal**: `reversed_polarity: true` flips the sign of the
entire matrix after virtuals have been resolved. It does *not* apply to
individual rows. To make a specific channel polarity-positive while the
rest are reversed, invert the entries inside that row's
`sum_coefficients`.

### `type: "matrix"` (legacy / interop)

Carries the resolved matrix explicitly. Locked to a specific `rec_labels`
ordering so it is not portable across recordings with different electrode
layouts. Useful for fully self-contained exports.

```json
"derivation": {
  "type": "matrix",
  "reversed_polarity": true,
  "montage_labels": ["Fp1-F7", "F7-T3", ...],
  "rec_labels": ["Fp1", "Fp2", "F3", ...],
  "matrix": [[1, 0, 0, ...], [0, 0, ...], ...]
}
```

`matrix.shape` must be `(len(montage_labels), len(rec_labels))`.

> **Δ today**: the current `MontageDerivation` dataclass omits the `type`
> field. The new spec adds it as a discriminator for forward-compatibility
> with the symbolic form. A loader that sees a `derivation` block without
> a `type` field treats it as `"matrix"`.

## Groups (`groups[]`)

```json
{
  "name": "left_temporal",
  "channels": ["Fp1-F7", "F7-T3", "T3-T5", "T5-O1"],
  "color": "#1f4e79",
  "gap_after_mm": 5.0
}
```

| field | type | required | meaning |
|---|---|---|---|
| `name` | string | yes | Identifier, not displayed. |
| `channels` | array of strings | yes | Channel labels in render order (top to bottom within the group). Each must match a `derivation.channels[].label` (or `derivation_ref`'s output). Hidden channels (via `channel_overrides`) are skipped silently. |
| `color` | string \| null | optional | CSS color applied to the group's traces unless an override wins. `null` falls back to the renderer's theme color. |
| `gap_after_mm` | number | optional (default 0) | Extra vertical mm of space inserted below the group's last visible channel. |

Channels not listed in any group are ignored — they will be derived but not
rendered. This allows a derivation to define more channels than any given
display surfaces.

## Channel overrides (`channel_overrides{}`)

Per-channel adjustments keyed by label. Any field at its default falls back
to the channel's group setting (color) or the renderer default.

```json
"channel_overrides": {
  "F7-Sp1": {"label": "F7-Sp1", "color": "#3a7ab8"},
  "Sp1-T3": {"label": "Sp1-T3", "color": "#3a7ab8", "gain": 1.5}
}
```

| field | type | meaning |
|---|---|---|
| `label` | string | Must equal the dict key. (Carried because `ChannelStyle` is also used standalone.) |
| `color` | string \| null | Trace color override. |
| `gap_after_mm` | number \| null | Extra space below this channel. Wins over the group's `gap_after_mm`. |
| `visible` | bool (default `true`) | If `false`, the channel is dropped from layout and the matrix row for it is skipped during rendering. |
| `gain` | number (default 1.0) | Dimensionless y-scale multiplier; combined multiplicatively with the renderer's global `yscale` / `sensitivity`. |
| `sensitivity` | number \| null | Absolute sensitivity in μV/mm. Overrides the renderer's global sensitivity for this channel. If both `gain` and `sensitivity` are set, `sensitivity` wins and `gain` is applied on top of it. Must be > 0. |
| `lf` | number \| null | Per-channel low-frequency cutoff (high-pass filter), Hz. `0` or `null` disables. |
| `hf` | number \| null | Per-channel high-frequency cutoff (low-pass filter), Hz. `0` or `null` disables. |
| `cal` | number \| null | Per-channel calibration amplitude in μV (used for per-channel scale bar / calibration pulse). Must be > 0. |
| `width` | number \| null | Per-channel trace stroke width in mm. Must be > 0. |

> **Δ today**: `sensitivity`, `lf`, `hf`, `cal`, `width` are *captured* in
> the JSON profile and surfaced in the editor UI, but the SVG renderer
> currently uses only its global toolbar values. Per-channel wire-through
> in `stackplot_svg` is tracked separately.

## End-to-end examples

### 1. Simple bipolar chain (circle)

```json
{
  "name": "circle",
  "derivation": {
    "type": "symbolic",
    "channels": [
      {"label": "Fp1-F7",  "diffpair": ["Fp1", "F7"]},
      {"label": "F7-T3",   "diffpair": ["F7",  "T3"]},
      {"label": "T3-T5",   "diffpair": ["T3",  "T5"]},
      {"label": "T5-O1",   "diffpair": ["T5",  "O1"]},
      {"label": "O1-O2",   "diffpair": ["O1",  "O2"]},
      {"label": "O2-T6",   "diffpair": ["O2",  "T6"]},
      {"label": "T6-T4",   "diffpair": ["T6",  "T4"]},
      {"label": "T4-F8",   "diffpair": ["T4",  "F8"]},
      {"label": "F8-Fp2",  "diffpair": ["F8",  "Fp2"]},
      {"label": "Fp2-Fp1", "diffpair": ["Fp2", "Fp1"]}
    ]
  },
  "groups": [ ... ]
}
```

### 2. Common-average reference (double_banana_avg)

```json
{
  "name": "double_banana_avg",
  "derivation": {
    "type": "symbolic",
    "virtual_channels": {
      "AVG": {
        "type": "mean",
        "electrodes": ["Fp1","F7","T3","T5","Fp2","F8","T4","T6",
                       "F3","C3","P3","O1","F4","C4","P4","O2",
                       "Fz","Cz","Pz"]
      }
    },
    "channels": [
      {"label": "Fp1-AVG", "diffpair": ["Fp1", "AVG"]},
      {"label": "F7-AVG",  "diffpair": ["F7",  "AVG"]},
      ...
    ]
  },
  "groups": [ ... ]
}
```

Resolution for `Fp1-AVG` given `rec_labels = [Fp1, F7, T3, ...]` (19 of them):

```
AVG row = (1/19) * (Fp1 + F7 + T3 + ... + Pz)
Fp1-AVG = Fp1 - AVG
        = (1 - 1/19) * Fp1 + (-1/19) * F7 + (-1/19) * T3 + ...
        = (18/19) * Fp1 - (1/19) * (sum of others)
```

> **Δ today**: this differs from `CommonAvgRefMontageView` by a constant
> factor of N/(N−1) = 19/18 ≈ 1.056 (the existing class implements a
> leave-one-out form). Visually indistinguishable; rendered amplitudes
> differ by ~5%.

### 3. Linked-ears reference (illustrative; no bundled profile yet)

```json
{
  "name": "linked_ears",
  "derivation": {
    "type": "symbolic",
    "virtual_channels": {
      "LE": {"type": "mean", "electrodes": ["A1", "A2"]}
    },
    "channels": [
      {"label": "Fp1-LE", "diffpair": ["Fp1", "LE"]},
      {"label": "Fp2-LE", "diffpair": ["Fp2", "LE"]}
    ]
  }
}
```

### 4. Custom weighted derivation (illustrative)

A bipolar Laplacian for C3, weighted manually:

```json
{
  "label": "C3-laplacian",
  "sum_coefficients": {
    "C3": 1.0,
    "F3": -0.25, "P3": -0.25, "T3": -0.25, "Cz": -0.25
  }
}
```

## Implementation notes (proposal)

> **Δ today**: this section describes intended changes that have not
> landed yet. Open in this dir: `montage_display.py` currently exposes
> `MontageDerivation` (matrix only). The symbolic form adds two new
> dataclasses and one router.

Proposed Python types:

```python
@dataclass
class VirtualElectrode:
    type: str                                    # "mean" | "weighted"
    electrodes: list[str] = field(default=list)  # for type=mean
    weights: dict[str, float] = field(default=dict)  # for type=weighted

    def resolve(self, rec_labels: list[str]) -> np.ndarray: ...

@dataclass
class SymbolicChannel:
    label: str
    diffpair: list[str] | None = None
    sum_coefficients: dict[str, float] | None = None

    def resolve(self, rec_labels, virtuals) -> np.ndarray: ...

@dataclass
class SymbolicDerivation:
    channels: list[SymbolicChannel]
    virtual_channels: dict[str, VirtualElectrode] = field(default=dict)
    reversed_polarity: bool = True

    def to_montage_view(self, rec_labels): ...
```

`MontageDisplay.derivation` becomes `MontageDerivation | SymbolicDerivation`.
JSON load dispatches on `derivation.type` (defaulting to `"matrix"` for
back-compat).

## Authoring conventions

- One profile per file. Filename stem matches `name` (e.g. `circle.json`).
- 2-space JSON indentation, trailing commas omitted.
- Channel labels use the same casing as the rec_labels they reference
  (`Fp1-F7`, not `FP1-F7`).
- Virtual electrode names are uppercase by convention to keep them visually
  distinct from electrode names (`AVG`, `LE`, `EAR`).
- Place spacers (`gap_after_mm`) only at boundaries clinicians actually
  care about (chain transitions, left/right hemisphere transitions, etc.) —
  not between every group.
- Prefer `derivation` (self-contained) over `derivation_ref` for new
  profiles. `derivation_ref` remains supported for legacy / quick reuse of
  the built-in `MontageView` classes.

## The `trace` exception

`derivation_ref: "trace"` is the canonical exception to the "prefer
symbolic" rule. The trace montage is the identity derivation: the matrix
is `I`, and the output channels are exactly `rec_labels` — so both the
dimension *and* the labels are determined by the recording at apply time,
not by anything authored ahead of time. A symbolic profile cannot express
this: `channels` is an authored list, but a trace profile's channel list
is the recording's channel list.

`trace` therefore stays Python-only. Reference it from a profile as:

```json
{
  "name": "trace",
  "derivation_ref": "trace",
  "groups": []
}
```

If `groups` is empty (or omitted), the renderer is expected to fall back
to a default "one group containing every derived channel" layout. See
`TraceMontageView` in `eegvis/montageview.py`.
