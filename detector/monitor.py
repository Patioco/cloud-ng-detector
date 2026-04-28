import json
import time
from collections import deque
from dataclasses import dataclass

@dataclass
class RequestEvent:
    timestamp: float
    ip: str
    status: int


def start_log_monitor(log_path: str, windows):
    """
    Continuously tails the Nginx JSON log file and feeds events into SlidingWindows.
    """
    print(f"[monitor] Watching log file: {log_path}")

    # Open file in tail mode
    with open(log_path, "r") as f:
        # Seek to end so we only read new lines
        f.seek(0, 2)

        while True:
            line = f.readline()

            if not line:
                # No new line → wait briefly
                time.sleep(0.1)
                continue

            line = line.strip()
            if not line:
                continue

            try:
                data = json.loads(line)
            except json.JSONDecodeError:
                print(f"[monitor] Skipping malformed JSON: {line}")
                continue

            try:
                event = RequestEvent(
                    timestamp=time.time(),
                    ip=data.get("source_ip", "unknown"),
                    status=int(data.get("status", 0)),
                )
                windows.add_event(event)
            except Exception as e:
                print(f"[monitor] Error processing line: {e}")
