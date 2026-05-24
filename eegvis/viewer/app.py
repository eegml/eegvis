"""FastAPI application for the EEG clinical viewer.

Run with:
    uv run uvicorn eegvis.viewer.app:app --reload
    uv run python -m eegvis.viewer.app  # for demo with synthetic data
"""

import numpy as np
from fastapi import FastAPI, Query, Request
from fastapi.responses import HTMLResponse
from datastar_py import ServerSentEventGenerator as SSE
from datastar_py.fastapi import DatastarResponse
from ztml import render

from ..displays import (
    list_displays_by_scope,
    load_display,
    save_user_display,
)
from ..stackplot_svg import (
    bandpass_filter,
    downsample,
    notch_filter,
    show_montage_display_svg,
    stackplot_svg,
)
from .components import _display_area, _jump_bar, _status_bar, viewer_page
from .editor_components import editor_page, render_tbody_patch
from .editor_session import EditorSession
from .session import SessionStore, ViewerSession

app = FastAPI(title="EEG Viewer")

# global state
sessions = SessionStore()
_studies: dict[str, "_StudyData"] = {}


class _StudyData:
    """Loaded EEG study data held in memory."""

    def __init__(
        self,
        signals: np.ndarray,
        sample_frequency: float,
        channel_labels: list[str],
        montage_names: list[str] | None = None,
    ):
        self.signals = signals
        self.sample_frequency = sample_frequency
        self.channel_labels = channel_labels
        self.montage_names = montage_names or ["raw"]
        self.total_duration = signals.shape[1] / sample_frequency


def load_study(
    study_id: str,
    signals: np.ndarray,
    sample_frequency: float,
    channel_labels: list[str],
    montage_names: list[str] | None = None,
):
    """Load a study into the server for viewing."""
    _studies[study_id] = _StudyData(
        signals, sample_frequency, channel_labels, montage_names
    )


def _render_page_svg(study: "_StudyData", session: ViewerSession) -> str:
    """Render the current page of EEG as SVG."""
    fs = study.sample_frequency
    start_sample = int(session.current_time * fs)
    end_sample = int((session.current_time + session.page_duration) * fs)
    end_sample = min(end_sample, study.signals.shape[1])

    page_signals = study.signals[:, start_sample:end_sample].copy()

    # apply filters
    if session.highpass_freq is not None or session.lowpass_freq is not None:
        page_signals = bandpass_filter(
            page_signals,
            fs,
            low_freq=session.highpass_freq,
            high_freq=session.lowpass_freq,
        )
    if session.notch_freq is not None:
        page_signals = notch_filter(page_signals, fs, notch_freq=session.notch_freq)

    # per-channel gain from montage state
    ms = session.montage_state
    yscale = [ms.get_gain(label) for label in study.channel_labels]

    return stackplot_svg(
        page_signals,
        fs,
        ylabels=study.channel_labels,
        seconds=session.page_duration,
        start_time=session.current_time,
        yscale=yscale,
        sensitivity=session.sensitivity,
        show_scalebar=True,
        max_samples_per_channel=2000,
        preserve_aspect_ratio="none",
    )


def _make_update_events(study: "_StudyData", session: ViewerSession) -> list:
    """Generate datastar SSE events to update the viewer."""
    svg_content = _render_page_svg(study, session)
    return [
        SSE.patch_elements(
            render(_display_area(svg_content)), selector="#eeg-display", mode="outer"
        ),
        SSE.patch_elements(
            render(_jump_bar(session, study.total_duration)),
            selector="#jump-bar",
            mode="outer",
        ),
        SSE.patch_elements(
            render(_status_bar(session)), selector="#status-bar", mode="outer"
        ),
        SSE.patch_signals(
            {
                "currentTime": session.current_time,
                "sensitivity": session.sensitivity,
                "pageDuration": session.page_duration,
            }
        ),
    ]


@app.get("/", response_class=HTMLResponse)
async def index(study_id: str = "demo"):
    """Serve the main viewer page."""
    study = _studies.get(study_id)
    if study is None:
        return HTMLResponse("<h1>Study not found</h1>", status_code=404)

    session = sessions.create(study_id)
    svg_content = _render_page_svg(study, session)
    html = render(
        viewer_page(session, study.montage_names, svg_content, study.total_duration)
    )
    return HTMLResponse(html)


@app.get("/api/navigate")
async def navigate(
    session_id: str = Query(...),
    action: str = Query(...),
    time: float | None = Query(None),
):
    """Handle navigation actions, return SSE updates."""
    session = sessions.get(session_id)
    if session is None:
        return DatastarResponse()
    study = _studies.get(session.study_id)
    if study is None:
        return DatastarResponse()

    max_time = study.total_duration
    step = max(1.0, session.page_duration * 0.1)

    match action:
        case "page_forward":
            session.page_forward(max_time)
        case "page_back":
            session.page_backward()
        case "step_forward":
            session.step_forward(step, max_time)
        case "step_back":
            session.step_backward(step)
        case "jump":
            if time is not None:
                session.jump_to(time, max_time)
        case "sensitivity_up":
            session.adjust_global_sensitivity(-1)
        case "sensitivity_down":
            session.adjust_global_sensitivity(1)

    return DatastarResponse(_make_update_events(study, session))


KEY_TO_ACTION = {
    "ArrowRight": "page_forward",
    "ArrowLeft": "page_back",
    "l": "step_forward",
    "k": "step_forward",
    "h": "step_back",
    "j": "step_back",
    "ArrowUp": "sensitivity_up",
    "ArrowDown": "sensitivity_down",
}


@app.get("/api/keydown")
async def keydown(session_id: str = Query(...), key: str = Query(...)):
    """Handle keyboard events by mapping key to navigation action."""
    action = KEY_TO_ACTION.get(key)
    if action is None:
        return DatastarResponse()

    session = sessions.get(session_id)
    if session is None:
        return DatastarResponse()
    study = _studies.get(session.study_id)
    if study is None:
        return DatastarResponse()

    max_time = study.total_duration
    step = max(1.0, session.page_duration * 0.1)

    match action:
        case "page_forward":
            session.page_forward(max_time)
        case "page_back":
            session.page_backward()
        case "step_forward":
            session.step_forward(step, max_time)
        case "step_back":
            session.step_backward(step)
        case "sensitivity_up":
            session.adjust_global_sensitivity(-1)
        case "sensitivity_down":
            session.adjust_global_sensitivity(1)

    return DatastarResponse(_make_update_events(study, session))


@app.get("/api/set_montage")
async def set_montage(session_id: str = Query(...), montage: str = Query(...)):
    """Switch montage."""
    session = sessions.get(session_id)
    if session is None:
        return DatastarResponse()
    session.current_montage = montage
    study = _studies.get(session.study_id)
    if study is None:
        return DatastarResponse()
    return DatastarResponse(_make_update_events(study, session))


@app.get("/api/set_sensitivity")
async def set_sensitivity(
    session_id: str = Query(...), sensitivity: float = Query(...)
):
    """Set global sensitivity."""
    session = sessions.get(session_id)
    if session is None:
        return DatastarResponse()
    session.sensitivity = sensitivity
    study = _studies.get(session.study_id)
    if study is None:
        return DatastarResponse()
    return DatastarResponse(_make_update_events(study, session))


@app.get("/api/set_page_duration")
async def set_page_duration(session_id: str = Query(...), duration: float = Query(...)):
    """Set page duration."""
    session = sessions.get(session_id)
    if session is None:
        return DatastarResponse()
    session.page_duration = duration
    study = _studies.get(session.study_id)
    if study is None:
        return DatastarResponse()
    return DatastarResponse(_make_update_events(study, session))


@app.get("/api/set_filter")
async def set_filter(
    session_id: str = Query(...),
    type: str = Query(...),
    value: str = Query(...),
):
    """Set filter parameters."""
    session = sessions.get(session_id)
    if session is None:
        return DatastarResponse()

    freq = None if value == "none" else float(value)
    match type:
        case "highpass":
            session.highpass_freq = freq
        case "lowpass":
            session.lowpass_freq = freq
        case "notch":
            session.notch_freq = freq

    study = _studies.get(session.study_id)
    if study is None:
        return DatastarResponse()
    return DatastarResponse(_make_update_events(study, session))


# --------------------------------------------------------------------------
# MontageDisplay editor
# --------------------------------------------------------------------------

_editor_sessions: dict[str, EditorSession] = {}


def _get_or_create_editor_session(session_id: str | None) -> EditorSession:
    if session_id and session_id in _editor_sessions:
        return _editor_sessions[session_id]
    s = EditorSession()
    _editor_sessions[s.session_id] = s
    return s


def _editor_preview_svg(session: EditorSession, study_id: str = "demo") -> str:
    """Render a preview of the in-progress montage against the loaded study."""
    study = _studies.get(study_id)
    if study is None:
        return "<svg></svg>"
    display = session.to_display()
    if not display.groups or not any(g.channels for g in display.groups):
        return (
            '<svg viewBox="0 0 300 60" xmlns="http://www.w3.org/2000/svg">'
            '<text x="10" y="35" font-size="10" fill="#888">'
            "Add at least one channel to see preview"
            "</text></svg>"
        )
    fs = study.sample_frequency
    n_secs = 10.0
    page = study.signals[:, : int(n_secs * fs)]
    try:
        return show_montage_display_svg(
            page,
            fs,
            display,
            rec_labels=study.channel_labels,
            seconds=n_secs,
            sensitivity=10.0,
            width_mm=300,
            height_mm=180,
            preserve_aspect_ratio="none",
            max_samples_per_channel=2000,
        )
    except (KeyError, ValueError) as e:
        return (
            f'<svg viewBox="0 0 400 60" xmlns="http://www.w3.org/2000/svg">'
            f'<text x="10" y="35" font-size="10" fill="#c33">'
            f"preview error: {str(e)[:120]}"
            f"</text></svg>"
        )


def _editor_patch_events(session: EditorSession):
    """SSE events to refresh the tbody and the preview."""
    return [
        SSE.patch_elements(
            render_tbody_patch(session), selector="#editor-tbody", mode="outer"
        ),
        SSE.patch_elements(
            f'<div id="editor-preview" class="editor-preview-svg">{_editor_preview_svg(session)}</div>',
            selector="#editor-preview",
            mode="outer",
        ),
    ]


@app.get("/editor", response_class=HTMLResponse)
async def editor_index(session_id: str | None = Query(None)):
    session = _get_or_create_editor_session(session_id)
    profile_options = list_displays_by_scope()
    html = render(editor_page(session, profile_options, _editor_preview_svg(session)))
    return HTMLResponse(html)


@app.post("/editor/api/load")
async def editor_load(
    session_id: str = Query(...),
    scoped: str = Query(""),
):
    """Load a bundled or user profile into the editor session.

    ``scoped`` has the form ``"system:<name>"`` or ``"user:<name>"``; empty
    starts a blank profile.
    """
    session = _get_or_create_editor_session(session_id)
    if scoped:
        scope, _, name = scoped.partition(":")
        try:
            display = load_display(name, scope=scope or None)
            new_session = EditorSession.from_display(display)
            new_session.session_id = session.session_id
            _editor_sessions[session.session_id] = new_session
            session = new_session
        except KeyError:
            pass
    else:
        # blank
        new_session = EditorSession(session_id=session.session_id)
        _editor_sessions[session.session_id] = new_session
        session = new_session
    events = _editor_patch_events(session)
    events.append(
        SSE.patch_elements(
            f'<input type="text" id="editor-name" value="{session.name}" '
            f"data-on:change=\"@post('/editor/api/rename?session_id={session.session_id}&amp;name=' + encodeURIComponent(evt.target.value))\">",
            selector="#editor-name",
            mode="outer",
        )
    )
    return DatastarResponse(events)


@app.post("/editor/api/rename")
async def editor_rename(session_id: str = Query(...), name: str = Query(...)):
    session = _get_or_create_editor_session(session_id)
    session.name = name
    return DatastarResponse()


@app.post("/editor/api/insert_channel")
async def editor_insert_channel(session_id: str = Query(...)):
    session = _get_or_create_editor_session(session_id)
    session.insert_channel()
    return DatastarResponse(_editor_patch_events(session))


@app.post("/editor/api/insert_separator")
async def editor_insert_separator(session_id: str = Query(...)):
    session = _get_or_create_editor_session(session_id)
    session.insert_separator()
    return DatastarResponse(_editor_patch_events(session))


@app.post("/editor/api/delete_row")
async def editor_delete_row(session_id: str = Query(...)):
    session = _get_or_create_editor_session(session_id)
    session.delete_row()
    return DatastarResponse(_editor_patch_events(session))


@app.post("/editor/api/select")
async def editor_select(session_id: str = Query(...), row: int = Query(...)):
    session = _get_or_create_editor_session(session_id)
    session.selected_row = max(0, min(row, len(session.rows) - 1))
    return DatastarResponse(_editor_patch_events(session))


@app.post("/editor/api/set_cell")
async def editor_set_cell(
    session_id: str = Query(...),
    row: int = Query(...),
    field: str = Query(...),
    value: str = Query(""),
):
    session = _get_or_create_editor_session(session_id)
    session.set_cell(row, field, value)
    return DatastarResponse(_editor_patch_events(session))


@app.post("/editor/api/save")
async def editor_save(session_id: str = Query(...)):
    session = _get_or_create_editor_session(session_id)
    display = session.to_display()
    try:
        path = save_user_display(display)
    except ValueError as e:
        return DatastarResponse(
            [
                SSE.patch_elements(
                    f'<div id="editor-preview" class="editor-preview-svg">'
                    f'<p style="color:#c33">save failed: {e}</p></div>',
                    selector="#editor-preview",
                    mode="outer",
                ),
            ]
        )
    return DatastarResponse(
        [
            SSE.patch_elements(
                f'<div id="editor-preview" class="editor-preview-svg">'
                f"<p>saved to <code>{path}</code></p>"
                f"{_editor_preview_svg(session)}</div>",
                selector="#editor-preview",
                mode="outer",
            ),
        ]
    )


def create_demo_study():
    """Create a synthetic EEG study for demo/testing."""
    fs = 256.0
    duration = 120.0  # 2 minutes
    num_channels = 19
    num_samples = int(fs * duration)

    channel_labels = [
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

    rng = np.random.default_rng(42)
    t = np.arange(num_samples) / fs

    signals = np.zeros((num_channels, num_samples))
    for i in range(num_channels):
        # background: mix of alpha (10Hz) and theta (6Hz) with noise
        alpha = rng.uniform(10, 40) * np.sin(
            2 * np.pi * (10 + rng.uniform(-1, 1)) * t + rng.uniform(0, 2 * np.pi)
        )
        theta = rng.uniform(5, 15) * np.sin(
            2 * np.pi * (6 + rng.uniform(-0.5, 0.5)) * t + rng.uniform(0, 2 * np.pi)
        )
        noise = rng.normal(0, 5, num_samples)
        # 60Hz line noise
        line_noise = 3 * np.sin(2 * np.pi * 60 * t)
        signals[i, :] = alpha + theta + noise + line_noise

    load_study("demo", signals, fs, channel_labels)


if __name__ == "__main__":
    import uvicorn

    create_demo_study()
    print("Starting EEG viewer at http://localhost:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)
