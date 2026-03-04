"""
Minimal Python SSE server for testing Datastar + Shadow DOM examples.

Usage:
    python server.py

Then open http://localhost:8000/01_light_dom.html   (no server needed, but convenient)
          http://localhost:8000/02_shadow_dom.html   (no server needed, but convenient)
          http://localhost:8000/03_sse_shadow_dom.html (needs this server for SSE)

The server provides:
    GET /api/stream-eeg   - SSE stream of simulated EEG data (Datastar protocol)
    GET /api/update-once  - Single SSE response with one data point
    GET /*                - Static file serving for HTML files
"""

import http.server
import json
import math
import time
import random
from pathlib import Path

PORT = 8000
STATIC_DIR = Path(__file__).parent


class DatastarHandler(http.server.SimpleHTTPRequestHandler):
    """HTTP handler that serves static files and Datastar-compatible SSE endpoints."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(STATIC_DIR), **kwargs)

    def do_GET(self):
        if self.path.startswith("/api/"):
            self._handle_api()
        else:
            super().do_GET()

    def _handle_api(self):
        if self.path == "/api/stream-eeg":
            self._stream_eeg()
        elif self.path == "/api/update-once":
            self._update_once()
        else:
            self.send_error(404, "Unknown API endpoint")

    def _stream_eeg(self):
        """Stream simulated EEG data as Datastar SSE events."""
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()

        channels = ["Fp1", "Fp2", "F3", "F4", "C3", "C4", "P3", "P4", "O1", "O2"]
        t = 0.0

        try:
            for i in range(50):  # Send 50 updates then stop
                channel = channels[i % len(channels)]
                # Simulate EEG-like signal: mix of alpha (10Hz) and noise
                amplitude = round(
                    50 * math.sin(2 * math.pi * 10 * t)
                    + 20 * math.sin(2 * math.pi * 3 * t)
                    + random.gauss(0, 10),
                    1,
                )
                timestamp = time.strftime("%H:%M:%S")

                # Datastar SSE protocol: merge-signals event
                self.wfile.write(b"event: datastar-merge-signals\n")
                signals = {
                    "eegChannel": channel,
                    "amplitude": amplitude,
                    "timestamp": timestamp,
                }
                self.wfile.write(f"data: signals {json.dumps(signals)}\n".encode())
                self.wfile.write(b"\n")
                self.wfile.flush()

                t += 0.01
                time.sleep(0.2)

        except (BrokenPipeError, ConnectionResetError):
            pass  # Client disconnected

    def _update_once(self):
        """Send a single Datastar SSE signal update."""
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()

        amplitude = round(random.gauss(0, 50), 1)
        timestamp = time.strftime("%H:%M:%S")
        channels = ["Fp1", "Fp2", "F3", "F4", "C3", "C4"]
        channel = random.choice(channels)

        self.wfile.write(b"event: datastar-merge-signals\n")
        signals = {
            "eegChannel": channel,
            "amplitude": amplitude,
            "timestamp": timestamp,
        }
        self.wfile.write(f"data: signals {json.dumps(signals)}\n".encode())
        self.wfile.write(b"\n")
        self.wfile.flush()


if __name__ == "__main__":
    with http.server.HTTPServer(("", PORT), DatastarHandler) as httpd:
        print(f"Datastar SSE test server running at http://localhost:{PORT}")
        print(f"Open http://localhost:{PORT}/01_light_dom.html")
        print(f"     http://localhost:{PORT}/02_shadow_dom.html")
        print(f"     http://localhost:{PORT}/03_sse_shadow_dom.html")
        print("Press Ctrl+C to stop.")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down.")
