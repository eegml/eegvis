"""In-memory session state for the EEG viewer.

Each session tracks per-study viewer state: current position, montage,
filters, and per-montage channel gain/lock/visibility settings.
"""

import uuid
from dataclasses import dataclass, field


# Standard clinical sensitivity presets (µV/mm)
SENSITIVITY_PRESETS = [1, 2, 3, 5, 7, 10, 15, 20, 30, 50, 70]

# Standard page duration presets (seconds)
PAGE_DURATION_PRESETS = [2, 5, 10, 15, 20, 30, 60, 120, 300]

DEFAULT_SENSITIVITY = 10  # µV/mm
DEFAULT_PAGE_DURATION = 10  # seconds


@dataclass
class MontageState:
    """Per-montage viewer state: channel gains, locks, visibility."""

    channel_gains: dict[str, float] = field(default_factory=dict)
    channel_locks: dict[str, bool] = field(default_factory=dict)
    channel_visible: dict[str, bool] = field(default_factory=dict)

    def get_gain(self, channel_name: str) -> float:
        return self.channel_gains.get(channel_name, 1.0)

    def set_gain(self, channel_name: str, gain: float):
        self.channel_gains[channel_name] = gain

    def is_locked(self, channel_name: str) -> bool:
        return self.channel_locks.get(channel_name, False)

    def toggle_lock(self, channel_name: str):
        self.channel_locks[channel_name] = not self.is_locked(channel_name)

    def is_visible(self, channel_name: str) -> bool:
        return self.channel_visible.get(channel_name, True)

    def toggle_visible(self, channel_name: str):
        self.channel_visible[channel_name] = not self.is_visible(channel_name)

    def reset(self):
        self.channel_gains.clear()
        self.channel_locks.clear()
        self.channel_visible.clear()


@dataclass
class ViewerSession:
    """Per-study, per-session viewer state."""

    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    study_id: str = ""

    # navigation
    current_time: float = 0.0
    page_duration: float = DEFAULT_PAGE_DURATION

    # montage
    current_montage: str = "raw"
    montage_states: dict[str, MontageState] = field(default_factory=dict)

    # global sensitivity (µV/mm)
    sensitivity: float = DEFAULT_SENSITIVITY

    # filters
    highpass_freq: float | None = 1.0
    lowpass_freq: float | None = 70.0
    notch_freq: float | None = None
    filter_type: str = "iir"  # "iir" (Butterworth) or "fir"

    @property
    def montage_state(self) -> MontageState:
        if self.current_montage not in self.montage_states:
            self.montage_states[self.current_montage] = MontageState()
        return self.montage_states[self.current_montage]

    def page_forward(self, max_time: float):
        self.current_time = min(self.current_time + self.page_duration, max_time - self.page_duration)
        self.current_time = max(0.0, self.current_time)

    def page_backward(self):
        self.current_time = max(0.0, self.current_time - self.page_duration)

    def step_forward(self, step: float, max_time: float):
        self.current_time = min(self.current_time + step, max_time - self.page_duration)
        self.current_time = max(0.0, self.current_time)

    def step_backward(self, step: float):
        self.current_time = max(0.0, self.current_time - step)

    def jump_to(self, time: float, max_time: float):
        self.current_time = max(0.0, min(time, max_time - self.page_duration))

    def adjust_global_sensitivity(self, direction: int):
        """Move sensitivity up or down through presets.

        direction: +1 = increase (less sensitive, bigger number),
                   -1 = decrease (more sensitive, smaller number)
        """
        try:
            idx = SENSITIVITY_PRESETS.index(self.sensitivity)
        except ValueError:
            idx = SENSITIVITY_PRESETS.index(DEFAULT_SENSITIVITY)
        new_idx = max(0, min(len(SENSITIVITY_PRESETS) - 1, idx + direction))
        self.sensitivity = SENSITIVITY_PRESETS[new_idx]


class SessionStore:
    """In-memory store for viewer sessions, keyed by session_id."""

    def __init__(self):
        self._sessions: dict[str, ViewerSession] = {}

    def create(self, study_id: str) -> ViewerSession:
        session = ViewerSession(study_id=study_id)
        self._sessions[session.session_id] = session
        return session

    def get(self, session_id: str) -> ViewerSession | None:
        return self._sessions.get(session_id)

    def delete(self, session_id: str):
        self._sessions.pop(session_id, None)
