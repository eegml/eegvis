import webbrowser
from pathlib import Path
import numpy as np
from eegvis.serve_component import save_eeg_html

# Simulate 20-channel clinical EEG + 1 EKG channel, 256 Hz, 10 seconds
num_eeg = 20
fs = 256
seconds = 10
n = fs * seconds

rng = np.random.default_rng(42)
signals = np.zeros((num_eeg + 1, n))

# EEG channels: ~50 uV random with varying frequency content
for i in range(num_eeg):
    signals[i] = rng.standard_normal(n) * 50.0

# EKG channel: larger amplitude with a slower rhythm
t = np.arange(n) / fs
signals[num_eeg] = 200.0 * np.sin(2 * np.pi * 1.2 * t) + rng.standard_normal(n) * 20.0

labels = [f"EEG-{i+1}" for i in range(num_eeg)] + ["EKG"]
channel_groups = {"EEG": list(range(num_eeg)), "EKG": [num_eeg]}

outpath = Path("demo_svg.html").resolve()
save_eeg_html(
    outpath, signals, fs,
    ylabels=labels,
    low_freq=None, high_freq=None,
    channel_groups=channel_groups,
)
webbrowser.open(outpath.as_uri())
