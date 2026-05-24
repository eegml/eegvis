"""Download a sample EDF file from PhysioNet for testing.

Source: EEG Motor Movement/Imagery Dataset (eegmmidb)
https://physionet.org/content/eegmmidb/1.0.0/

Downloads subject S001, run 01 (eyes-open baseline recording).
64 channels, 160 Hz, ~61 seconds.
"""

import os
import urllib.request

URL = "https://physionet.org/files/eegmmidb/1.0.0/S001/S001R01.edf"
DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
OUTPUT_PATH = os.path.join(DATA_DIR, "S001R01.edf")


def main():
    os.makedirs(DATA_DIR, exist_ok=True)

    if os.path.exists(OUTPUT_PATH):
        print(f"Already exists: {OUTPUT_PATH}")
        return

    print(f"Downloading {URL}")
    urllib.request.urlretrieve(URL, OUTPUT_PATH)
    size_kb = os.path.getsize(OUTPUT_PATH) / 1024
    print(f"Saved to {OUTPUT_PATH} ({size_kb:.0f} KB)")


if __name__ == "__main__":
    main()
