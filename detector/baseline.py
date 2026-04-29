import time
import logging
from collections import deque

log = logging.getLogger("baseline")


class BaselineEngine:
    """
    Tracks rolling baseline of request rates and error rates.
    Recalculates mean/stddev every N seconds.
    """

    def __init__(self, config):
        self.window_minutes = config["baseline"]["baseline_minutes"]
        self.recalc_seconds = config["baseline"]["baseline_recalc_seconds"]

        self.values = deque()
        self.error_values = deque()

        self.effective_mean = 0
        self.effective_std = 1
        self.effective_err_mean = 0
        self.effective_err_std = 1

        self.last_recalc = time.time()

    def add_sample(self, count: int, error_count: int):
        now = time.time()

        self.values.append((now, count))
        self.error_values.append((now, error_count))

        cutoff = now - (self.window_minutes * 60)

        # Trim old samples
        while self.values and self.values[0][0] < cutoff:
            self.values.popleft()

        while self.error_values and self.error_values[0][0] < cutoff:
            self.error_values.popleft()

        # Recalculate baseline periodically
        if now - self.last_recalc >= self.recalc_seconds:
            self.recalculate()

    def recalculate(self):
        counts = [v for (_, v) in self.values]
        err_counts = [v for (_, v) in self.error_values]

        if counts:
            self.effective_mean = sum(counts) / len(counts)
            self.effective_std = max(1, (sum((x - self.effective_mean) ** 2 for x in counts) / len(counts)) ** 0.5)

        if err_counts:
            self.effective_err_mean = sum(err_counts) / len(err_counts)
            self.effective_err_std = max(1, (sum((x - self.effective_err_mean) ** 2 for x in err_counts) / len(err_counts)) ** 0.5)

        self.last_recalc = time.time()

        # Debug output (correct indentation)
        print(
            f"Baseline recalculated: "
            f"mean={self.effective_mean:.2f} std={self.effective_std:.2f} "
            f"err_mean={self.effective_err_mean:.2f} err_std={self.effective_err_std:.2f}"
        )
