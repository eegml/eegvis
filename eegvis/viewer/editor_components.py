"""ztml components for the MontageDisplay editor page.

The editor presents a flat table of channels and separators (one row each)
modeled on classic clinical "Pattern Editor" dialogs. Inline inputs are
bound to the server's :class:`EditorSession` via datastar; each edit
triggers an SSE patch that re-renders the table and the preview SVG.
"""

from __future__ import annotations

from typing import List

from ztml import (
    Body,
    Button,
    Div,
    Fragment,
    H2,
    Head,
    Html,
    Input,
    Label,
    Meta,
    Option,
    Raw,
    RawCss,
    Script,
    Select,
    Span,
    Style,
    Title,
)

from .editor_session import (
    DEFAULT_COLOR_PALETTE,
    EditorRow,
    EditorSession,
)

DATASTAR_CDN = "https://cdn.jsdelivr.net/gh/starfederation/datastar@v1.0.0-RC.8/bundles/datastar.js"


def editor_page(
    session: EditorSession,
    profile_options: dict,
    preview_svg: str,
):
    """Top-level editor HTML document."""
    return Fragment(
        Raw("<!DOCTYPE html>"),
        Html(
            Head(
                Meta().charset("utf-8"),
                Meta().name("viewport").content("width=device-width, initial-scale=1"),
                Title(f"Montage Editor — {session.name}"),
                Script().src(DATASTAR_CDN).type("module"),
                _editor_styles(),
            ),
            Body(
                Div(
                    Div(
                        _editor_header(session, profile_options),
                        _editor_table(session),
                    ).cls("editor-main"),
                    _editor_sidebar(session, profile_options),
                ).cls("editor-root"),
                Div(
                    H2("Preview"),
                    _editor_preview(preview_svg),
                ).cls("editor-preview"),
            ),
        ),
    )


def _editor_styles():
    return Style(
        RawCss("""
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { font-family: system-ui, -apple-system, sans-serif; background: #f3f3f3; color: #222; }
        .editor-root {
            display: grid;
            grid-template-columns: minmax(0, 1fr) 240px;
            gap: 12px;
            padding: 12px;
            max-width: 1400px;
            margin: 0 auto;
        }
        .editor-main { background: white; border: 1px solid #ccc; border-radius: 4px; padding: 12px; }
        .editor-header {
            display: grid;
            grid-template-columns: 120px 1fr 120px 1fr;
            align-items: center;
            gap: 8px;
            margin-bottom: 12px;
        }
        .editor-header label { font-size: 12px; color: #555; }
        .editor-header select, .editor-header input[type=text] {
            padding: 4px 6px; border: 1px solid #ccc; border-radius: 3px;
            font-size: 13px; width: 100%;
        }
        .editor-table {
            width: 100%; border-collapse: collapse;
            font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
            font-size: 12px;
        }
        .editor-table th {
            background: #ececec; padding: 4px 6px;
            border: 1px solid #bbb; text-align: center; font-weight: 600;
        }
        .editor-table td { border: 1px solid #ddd; padding: 0; }
        .editor-table tr.selected td { background: #e0ecff; }
        .editor-table tr.separator td { background: #2664c5; color: white; }
        .editor-table tr.separator td.ch-cell { background: #fafafa; color: #2664c5; }
        .editor-table .ch-cell {
            text-align: center; padding: 4px 8px; font-weight: 600; cursor: pointer;
        }
        .editor-table input[type=text],
        .editor-table input[type=color] {
            width: 100%; border: none; padding: 4px 6px;
            font: inherit; background: transparent;
        }
        .editor-table input[type=text]:focus { background: #fff8c5; outline: 1px solid #4285f4; }
        .editor-table input.num-cell { width: 100%; text-align: right; max-width: 60px; }
        .editor-table .disp-cell { text-align: center; cursor: pointer; user-select: none; }
        .editor-table .color-cell { width: 60px; padding: 2px; }
        .editor-table input[type=color] { height: 22px; padding: 0; cursor: pointer; }

        .editor-sidebar {
            background: white; border: 1px solid #ccc; border-radius: 4px;
            padding: 12px; align-self: start; display: grid; gap: 12px;
            position: sticky; top: 12px;
        }
        .editor-sidebar .group { display: grid; gap: 6px; padding: 8px; border: 1px solid #ddd; border-radius: 3px; }
        .editor-sidebar .group-title { font-size: 11px; text-transform: uppercase; color: #777; letter-spacing: 0.04em; }
        .editor-sidebar button {
            padding: 6px 10px; border: 1px solid #bbb; background: #f7f7f7;
            border-radius: 3px; cursor: pointer; font-size: 13px;
        }
        .editor-sidebar button:hover { background: #ececec; }
        .editor-sidebar button.primary { background: #2664c5; color: white; border-color: #1d4fa0; }
        .editor-sidebar button.primary:hover { background: #1d4fa0; }
        .editor-sidebar .row-button { display: grid; grid-template-columns: 1fr 1fr; gap: 4px; }

        .editor-preview {
            max-width: 1400px; margin: 0 auto 16px; padding: 0 12px;
        }
        .editor-preview h2 { font-size: 13px; color: #555; margin: 4px 0; }
        .editor-preview-svg {
            background: white; border: 1px solid #ccc; border-radius: 4px;
            padding: 8px; overflow: hidden;
        }
        .editor-preview-svg svg { width: 100%; height: auto; }
        """)
    )


def _editor_header(session: EditorSession, profile_options: dict):
    return (
        Div(
            Label("Pattern"),
            _pattern_select(session, profile_options),
            Label("Name"),
            Input()
            .type("text")
            .value(session.name)
            .id("editor-name")
            .attr(
                "data-on:change",
                f"@post('/editor/api/rename?session_id={session.session_id}&name=' + encodeURIComponent(evt.target.value))",
            ),
        )
        .id("editor-header")
        .cls("editor-header")
    )


def _pattern_select(session: EditorSession, profile_options: dict):
    options = []
    system = profile_options.get("system", [])
    user = profile_options.get("user", [])
    options.append(Option("— new —").value(""))
    if user:
        options.append(Option("— user —").attr("disabled", "disabled"))
        for n in user:
            options.append(Option(n).value(f"user:{n}"))
    if system:
        options.append(Option("— system —").attr("disabled", "disabled"))
        for n in system:
            options.append(Option(n).value(f"system:{n}"))
    sel = Select(*options)
    sel = sel.attr(
        "data-on:change",
        f"@post('/editor/api/load?session_id={session.session_id}&scoped=' + encodeURIComponent(evt.target.value))",
    )
    return sel


def _editor_table(session: EditorSession):
    rows_html: List = []
    rows_html.append(
        Raw(
            """
        <thead>
          <tr>
            <th>CH#</th><th>G1</th><th>G2</th>
            <th title="Sensitivity µV/mm">Sens</th>
            <th title="Low-frequency / high-pass cutoff Hz">LF</th>
            <th title="High-frequency / low-pass cutoff Hz">HF</th>
            <th title="Calibration µV">CAL</th>
            <th title="Trace stroke width mm">Width</th>
            <th>Disp</th>
            <th>Color</th>
            <th></th>
          </tr>
        </thead>
        """
        )
    )
    rows_html.append(_render_tbody(session))
    return Raw(f'<table class="editor-table">{_concat(rows_html)}</table>')


def _render_tbody(session: EditorSession) -> Raw:
    """Just the <tbody> — what the SSE patch targets when state changes."""
    parts = ['<tbody id="editor-tbody">']
    for i, row in enumerate(session.rows):
        parts.append(_render_row(session.session_id, i, row, i == session.selected_row))
    parts.append("</tbody>")
    return Raw("".join(parts))


def _render_row(session_id: str, idx: int, row: EditorRow, selected: bool) -> str:
    """Render one row of the editor table as raw HTML (faster than ztml chain)."""
    klass = []
    if selected:
        klass.append("selected")
    if row.kind == "separator":
        klass.append("separator")
    klass_attr = f' class="{" ".join(klass)}"' if klass else ""

    set_cell_url = f"/editor/api/set_cell?session_id={session_id}&row={idx}"
    select_url = f"/editor/api/select?session_id={session_id}&row={idx}"

    ch_cell = (
        f'<td class="ch-cell" data-on:click="@post(\'{select_url}\')">CH{idx + 1}</td>'
    )

    if row.kind == "separator":
        body = (
            '<td colspan="8" style="text-align:center;font-weight:600">— separator —</td>'
            '<td class="color-cell"></td>'
        )
        return f"<tr{klass_attr}>{ch_cell}{body}</tr>"

    def _text(field: str, value: str) -> str:
        return (
            f'<input type="text" value="{_escape(value)}" '
            f"data-on:change=\"@post('{set_cell_url}&field={field}&value=' + encodeURIComponent(evt.target.value))\">"
        )

    def _num(field: str, value) -> str:
        """Numeric input. Empty string means 'inherit / no override'."""
        display = "" if value is None else _format_num(value)
        return (
            f'<input type="text" inputmode="decimal" class="num-cell" '
            f'value="{_escape(display)}" '
            f"data-on:change=\"@post('{set_cell_url}&field={field}&value=' + encodeURIComponent(evt.target.value))\">"
        )

    color_val = row.color or "#000000"
    color_cell = (
        f'<td class="color-cell"><input type="color" value="{_escape(color_val)}" '
        f"data-on:change=\"@post('{set_cell_url}&field=color&value=' + encodeURIComponent(evt.target.value))\"></td>"
    )

    disp_label = "On" if row.visible else "Off"
    next_val = "false" if row.visible else "true"
    disp_cell = (
        f'<td class="disp-cell" '
        f"data-on:click=\"@post('{set_cell_url}&field=visible&value={next_val}')\">"
        f"{disp_label}</td>"
    )

    return (
        f"<tr{klass_attr}>"
        f"{ch_cell}"
        f"<td>{_text('g1', row.g1)}</td>"
        f"<td>{_text('g2', row.g2)}</td>"
        f"<td>{_num('sensitivity', row.sensitivity)}</td>"
        f"<td>{_num('lf', row.lf)}</td>"
        f"<td>{_num('hf', row.hf)}</td>"
        f"<td>{_num('cal', row.cal)}</td>"
        f"<td>{_num('width', row.width)}</td>"
        f"{disp_cell}"
        f"{color_cell}"
        f"<td></td>"
        f"</tr>"
    )


def _format_num(value) -> str:
    """Render a float for the editor: integers as ints, floats trimmed."""
    if isinstance(value, int) or (isinstance(value, float) and value.is_integer()):
        return str(int(value))
    return f"{float(value):g}"


def _editor_sidebar(session: EditorSession, profile_options: dict):
    sid = session.session_id
    return Div(
        Div(
            Span("Channel").cls("group-title"),
            Div(
                Button("Insert").attr(
                    "data-on:click",
                    f"@post('/editor/api/insert_channel?session_id={sid}')",
                ),
                Button("Delete").attr(
                    "data-on:click", f"@post('/editor/api/delete_row?session_id={sid}')"
                ),
            ).cls("row-button"),
        ).cls("group"),
        Div(
            Span("Separator").cls("group-title"),
            Div(
                Button("Insert").attr(
                    "data-on:click",
                    f"@post('/editor/api/insert_separator?session_id={sid}')",
                ),
                Button("Delete").attr(
                    "data-on:click", f"@post('/editor/api/delete_row?session_id={sid}')"
                ),
            ).cls("row-button"),
        ).cls("group"),
        Div(
            Span("File").cls("group-title"),
            Button("Save to user dir")
            .cls("primary")
            .attr("data-on:click", f"@post('/editor/api/save?session_id={sid}')"),
        ).cls("group"),
    ).cls("editor-sidebar")


def _editor_preview(svg: str):
    return Div(Raw(svg)).cls("editor-preview-svg").id("editor-preview")


# ----- helpers -----


def _concat(items) -> str:
    return "".join(render_fragment(i) for i in items)


def render_fragment(item) -> str:
    """Stringify either a ztml element, a Raw, or a plain str."""
    if isinstance(item, str):
        return item
    if hasattr(item, "__html__"):
        return item.__html__()
    return str(item)


def _escape(s: str) -> str:
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def render_tbody_patch(session: EditorSession) -> str:
    """Return the inner HTML of the editor tbody for SSE patches."""
    return render_fragment(_render_tbody(session))
