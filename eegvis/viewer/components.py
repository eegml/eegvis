# %%
"""ztml HTML components for the EEG viewer."""

# from datastar_py import attribute_generator as dsattr # import ServerSentEventGenerator as SSE
# # %%
# # little experiment
# #_id = "fakeid"
# str(dsattr.on('click', f"@get('/api/navigate?session_id={_id}&action=page_back')"))
# # %%
# r = dsattr.on('click', f"@get('/api/navigate?session_id={_id}')").debounce(300)
# # %%
# r.throttle(100)
# # %%
# str(r)
# # %%
# dict(r)
# %%
from ztml import (
    Body,
    Button,
    Div,
    Fragment,
    H1,
    Head,
    Html,
    Label,
    Meta,
    Option,
    P,
    Raw,
    RawCss,
    Script,
    Select,
    Span,
    Style,
    Title,
    Input,
)

# %%
# Div('testdiv').data("on:click","expression").__html__()
# %%
from .session import (
    SENSITIVITY_PRESETS,
    PAGE_DURATION_PRESETS,
    ViewerSession,
)

DATASTAR_CDN = "https://cdn.jsdelivr.net/gh/starfederation/datastar@v1.0.0-RC.8/bundles/datastar.js"


def page_shell(*children):
    """Full HTML document shell with datastar loaded."""
    return Fragment(
        Raw("<!DOCTYPE html>"),
        Html(
            Head(
                Meta().charset("utf-8"),
                Meta().name("viewport").content("width=device-width, initial-scale=1"),
                Title("EEG Viewer"),
                Script().src(DATASTAR_CDN).type("module"),
                _viewer_styles(),
            ),
            Body(*children),
        ),
    )


def _viewer_styles():
    """Inline CSS for the viewer layout."""
    return Style(
        RawCss("""
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { font-family: system-ui, -apple-system, sans-serif; background: #f5f5f5; }
        .viewer-root { max-width: 1400px; margin: 0 auto; padding: 8px; }
        .toolbar {
            display: flex; gap: 8px; align-items: center; flex-wrap: wrap;
            padding: 8px; background: white; border: 1px solid #ddd;
            border-radius: 4px; margin-bottom: 8px;
        }
        .toolbar label { font-size: 13px; color: #555; }
        .toolbar select, .toolbar input, .toolbar button {
            font-size: 13px; padding: 4px 8px; border: 1px solid #ccc;
            border-radius: 3px; background: white;
        }
        .toolbar button { cursor: pointer; }
        .toolbar button:hover { background: #eee; }
        .toolbar .separator { width: 1px; height: 24px; background: #ddd; }
        .display-area {
            background: white; border: 1px solid #ddd; border-radius: 4px;
            padding: 4px; overflow: hidden;
        }
        .display-area svg { width: 100%; height: auto; }
        .status-bar {
            display: flex; justify-content: space-between; align-items: center;
            padding: 4px 8px; font-size: 12px; color: #777;
            background: white; border: 1px solid #ddd;
            border-radius: 4px; margin-top: 8px;
        }
        .jump-bar {
            height: 24px; background: #eee; border: 1px solid #ddd;
            border-radius: 3px; margin-top: 8px; position: relative;
            cursor: pointer;
        }
        .jump-bar .position-marker {
            position: absolute; top: 0; height: 100%;
            background: rgba(66, 133, 244, 0.3); border-left: 2px solid #4285f4;
        }
    """)
    )


def viewer_page(
    session: ViewerSession,
    montage_names: list[str],
    svg_content: str,
    total_duration: float,
):
    """Build the full viewer page."""
    signals = {
        "sensitivity": session.sensitivity,
        "pageDuration": session.page_duration,
        "currentTime": session.current_time,
        "montage": f"'{session.current_montage}'",
        "selectedChannel": "null",
        "_totalDuration": total_duration,
    }
    signals_str = ", ".join(f"{k}: {v}" for k, v in signals.items())

    return page_shell(
        Div(
            _toolbar(session, montage_names),
            _display_area(svg_content),
            _jump_bar(session, total_duration),
            _status_bar(session),
        )
        .cls("viewer-root")
        .attr("data-signals", f"{{{signals_str}}}")
        .attr("tabindex", "0")
        .data("on:keydown", _keydown_handler(session.session_id)),
        # .attr("data-on:keydown", _keydown_handler(session.session_id)),
    )


def _toolbar(session: ViewerSession, montage_names: list[str]):
    """Toolbar with montage, sensitivity, page duration, navigation, and filter controls."""
    return Div(
        # montage selector
        Label("Montage:"),
        _montage_select(session, montage_names),
        _separator(),
        # sensitivity
        Label("Sensitivity:"),
        _sensitivity_select(session),
        _separator(),
        # page duration
        Label("Page:"),
        _page_duration_select(session),
        _separator(),
        # navigation
        Button("\u25c0\u25c0")
        .title("Previous page (Left arrow)")
        .attr(
            "data-on:click",
            f"@get('/api/navigate?session_id={session.session_id}&action=page_back')",
        ),
        Button("\u25c0")
        .title("Step back (h/j)")
        .attr(
            "data-on:click",
            f"@get('/api/navigate?session_id={session.session_id}&action=step_back')",
        ),
        Button("\u25b6")
        .title("Step forward (k/l)")
        .attr(
            "data-on:click",
            f"@get('/api/navigate?session_id={session.session_id}&action=step_forward')",
        ),
        Button("\u25b6\u25b6")
        .title("Next page (Right arrow)")
        .attr(
            "data-on:click",
            f"@get('/api/navigate?session_id={session.session_id}&action=page_forward')",
        ),
        _separator(),
        # jump to time
        Label("Go to:"),
        Input()
        .type("number")
        .attr("data-bind", "currentTime")
        .attr("min", "0")
        .attr("step", "1")
        .attr(
            "data-on:change",
            f"@get('/api/navigate?session_id={session.session_id}&action=jump&time=' + $currentTime)",
        )
        .style("width: 70px"),
        Label("s"),
        _separator(),
        # filters
        Label("HP:"),
        _filter_select(
            "highpass",
            session.session_id,
            [None, 0.1, 0.3, 0.5, 1.0, 1.5, 2.0, 5.0],
            session.highpass_freq,
        ),
        Label("LP:"),
        _filter_select(
            "lowpass",
            session.session_id,
            [None, 15, 20, 30, 35, 40, 50, 70, 100],
            session.lowpass_freq,
        ),
        Label("Notch:"),
        _filter_select(
            "notch",
            session.session_id,
            [None, 50, 60],
            session.notch_freq,
        ),
    ).cls("toolbar")


def _montage_select(session: ViewerSession, montage_names: list[str]):
    """Montage dropdown."""
    options = []
    for name in montage_names:
        opt = Option(name).value(name)
        if name == session.current_montage:
            opt = opt.selected(True)
        options.append(opt)
    return (
        Select(*options)
        .attr("data-bind", "montage")
        .attr(
            "data-on:change",
            f"@get('/api/set_montage?session_id={session.session_id}&montage=' + $montage)",
        )
    )


def _sensitivity_select(session: ViewerSession):
    """Sensitivity preset dropdown."""
    options = []
    for s in SENSITIVITY_PRESETS:
        opt = Option(f"{s} \u00b5V/mm").value(str(s))
        if s == session.sensitivity:
            opt = opt.selected(True)
        options.append(opt)
    return (
        Select(*options)
        .attr("data-bind", "sensitivity")
        .attr(
            "data-on:change",
            f"@get('/api/set_sensitivity?session_id={session.session_id}&sensitivity=' + $sensitivity)",
        )
    )


def _page_duration_select(session: ViewerSession):
    """Page duration dropdown."""
    options = []
    for d in PAGE_DURATION_PRESETS:
        label = f"{d}s" if d < 60 else f"{d // 60}m"
        opt = Option(label).value(str(d))
        if d == session.page_duration:
            opt = opt.selected(True)
        options.append(opt)
    return (
        Select(*options)
        .attr("data-bind", "pageDuration")
        .attr(
            "data-on:change",
            f"@get('/api/set_page_duration?session_id={session.session_id}&duration=' + $pageDuration)",
        )
    )


def _filter_select(
    filter_type: str, session_id: str, values: list, current: float | None
):
    """Filter preset dropdown."""
    options = []
    for v in values:
        label = "Off" if v is None else f"{v} Hz"
        val_str = "none" if v is None else str(v)
        opt = Option(label).value(val_str)
        if v == current or (v is None and current is None):
            opt = opt.selected(True)
        options.append(opt)
    return Select(*options).attr(
        "data-on:change",
        f"@get('/api/set_filter?session_id={session_id}&type={filter_type}&value=' + evt.target.value)",
    )


def _separator():
    return Div().cls("separator")


def _display_area(svg_content: str):
    """Main SVG display area."""
    return (
        Div(
            Raw(svg_content),
        )
        .cls("display-area")
        .id("eeg-display")
    )


def _jump_bar(session: ViewerSession, total_duration: float):
    """Jump bar showing position in recording."""
    if total_duration > 0:
        left_pct = session.current_time / total_duration * 100
        width_pct = session.page_duration / total_duration * 100
    else:
        left_pct = 0
        width_pct = 100
    return (
        Div(
            Div()
            .cls("position-marker")
            .style(f"left: {left_pct:.1f}%; width: {width_pct:.1f}%"),
        )
        .cls("jump-bar")
        .id("jump-bar")
        .attr(
            "data-on:click",
            f"@get('/api/navigate?session_id={session.session_id}&action=jump&time=' + "
            f"Math.round(evt.offsetX / evt.target.offsetWidth * {total_duration}))",
        )
    )


def _status_bar(session: ViewerSession):
    """Status bar showing current state."""
    time_str = f"{session.current_time:.1f}s - {session.current_time + session.page_duration:.1f}s"
    return (
        Div(
            Span(f"Time: {time_str}"),
            Span(f"Montage: {session.current_montage}"),
            Span(f"Sensitivity: {session.sensitivity} \u00b5V/mm"),
            Span(
                f"Filters: HP {session.highpass_freq or 'Off'} / LP {session.lowpass_freq or 'Off'} / Notch {session.notch_freq or 'Off'}"
            ),
        )
        .cls("status-bar")
        .id("status-bar")
    )


def _keydown_handler(session_id: str):
    """Datastar expression for keyboard navigation.

    Sends the key to the server which maps it to an action.
    Only sends for keys we care about to avoid unnecessary requests.
    """
    keys = "ArrowRight,ArrowLeft,ArrowUp,ArrowDown,h,j,k,l"
    return (
        f"'{keys}'.split(',').includes(evt.key) && "
        f"@get('/api/keydown?session_id={session_id}&key=' + evt.key)"
    )
