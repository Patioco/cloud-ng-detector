import time
from math import fabs

class Detector:
  def __init__(self, windows: SlidingWindows, baseline: Baseline, config, blocker, notifier, audit_logger):
    self.windows = windows
    self.baseline = baseline
    self.config = config
    self.blocker = blocker
    self.notifier = notifier
    self.audit_logger = audit_logger

  def check(self):
    global_rps, global_err_rps, per_ip_rps, per_ip_err_rps = self.windows.get_rates()

    mean = self.baseline.effective_mean or 0.1
    std = self.baseline.effective_std or 0.1

    # Global anomaly
    z = (global_rps - mean) / std
    if z > self.config["thresholds"]["zscore"] or global_rps > self.config["thresholds"]["multiplier"] * mean:
      self.notifier.global_alert(global_rps, mean, z)
      self.audit_logger("GLOBAL_ANOMALY", "-", global_rps, mean, "-")

    # Per-IP anomalies
    for ip, rps in per_ip_rps.items():
      ip_err_rps = per_ip_err_rps.get(ip, 0.0)

      # error surge tightening
      err_mean = self.baseline.effective_err_mean or 0.1
      if ip_err_rps > self.config["thresholds"]["error_multiplier"] * err_mean:
        # tighten thresholds for this IP (e.g. lower zscore or multiplier)
        z_thresh = self.config["thresholds"]["zscore"] * 0.7
        mult = self.config["thresholds"]["multiplier"] * 0.7
      else:
        z_thresh = self.config["thresholds"]["zscore"]
        mult = self.config["thresholds"]["multiplier"]

      z_ip = (rps - mean) / std
      if z_ip > z_thresh or rps > mult * mean:
        if self.blocker.should_ban(ip):
          duration = self.blocker.ban(ip, reason="rate_anomaly", rate=rps, baseline=mean)
          self.notifier.ip_ban(ip, rps, mean, z_ip, duration)
          self.audit_logger("BAN", ip, rps, mean, duration)
        else:
          self.notifier.ip_alert(ip, rps, mean, z_ip)
          self.audit_logger("IP_ANOMALY", ip, rps, mean, "-")