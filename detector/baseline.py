from collections import deque
import time
import statistics
from threading import Lock

class Baseline:
  def __init__(self, window_seconds: int):
    self.window_seconds = window_seconds  # 30 * 60
    self.global_rates = deque(maxlen=window_seconds)
    self.global_error_rates = deque(maxlen=window_seconds)
    self.lock = Lock()
    self.effective_mean = 0.0
    self.effective_std = 0.0
    self.effective_err_mean = 0.0
    self.effective_err_std = 0.0

  def add_sample(self, rps: float, err_rps: float):
    with self.lock:
      self.global_rates.append(rps)
      self.global_error_rates.append(err_rps)

  def recalc(self):
    with self.lock:
      if len(self.global_rates) < 10:
        # not enough data, keep floor values
        return

      self.effective_mean = statistics.fmean(self.global_rates)
      self.effective_std = statistics.pstdev(self.global_rates) or 0.0001

      self.effective_err_mean = statistics.fmean(self.global_error_rates)
      self.effective_err_std = statistics.pstdev(self.global_error_rates) or 0.0001

      # here: write audit log "BASELINE_RECALC"
        print(f"Baseline recalculated: mean={self.effective_mean:.2f} std={self.effective_std:.2f} err_mean={self.effective_err_mean:.2f} err_std={self.effective_err_std:.2f}")    