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

from ..stackplot_svg import stackplot_svg, bandpass_filter, notch_filter, downsample
from .session import SessionStore, ViewerSession
from .components import viewer_page, _display_area, _jump_bar, _status_bar

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
