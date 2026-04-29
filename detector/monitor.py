import time
import threading
import logging
from collections import defaultdict, deque

log = logging.getLogger("monitor")


class SlidingWindowManager:
    """
    Tracks request counts per IP using a sliding time window.
    Used by the detector to identify anomalies.
    """

    def __init__(self, window_seconds=10, max_entries=5000):
        self.window_seconds = window_seconds
        self.max_entries = max_entries
        self.windows = defaultdict(deque)

    def add_event(self, ip: str):
        now = time.time()
        window = self.windows[ip]

        window.append(now)

        # Trim old entries
        while window and now - window[0] > self.window_seconds:
            window.popleft()

        # Prevent unbounded memory growth
        if len(window) > self.max_entries:
            window.popleft()

    def get_count(self, ip: str) -> int:
        now = time.time()
        window = self.windows[ip]

        # Remove expired timestamps
        while window and now - window[0] > self.window_seconds:
            window.popleft()

        return len(window)


def start_log_monitor(callback, logfile_path="/var/log/nginx/access.log"):
    """
    Tails the log file and calls `callback(ip)` for each request.
    Runs in its own thread.
    """
    def follow():
        log.info(f"Monitoring log file: {logfile_path}")

        with open(logfile_path, "r") as f:
            # Do NOT seek to end — start reading from current content
            while True:
                line = f.readline()
                if not line:
                    time.sleep(0.01)
                    continue

                ip = line.split(" ")[0]
                callback(ip)

    thread = threading.Thread(target=follow, daemon=True)
    thread.start()
    return thread