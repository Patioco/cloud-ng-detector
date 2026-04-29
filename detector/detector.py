import logging
from .notifier import send_slack_alert

log = logging.getLogger("detector")


class Detector:
    """
    Applies anomaly detection using sliding windows + rolling baseline.
    """

    def __init__(self, config, window_mgr, baseline):
        self.config = config
        self.window_mgr = window_mgr
        self.baseline = baseline

        self.zscore_threshold = config["detector"]["zscore_threshold"]
        self.multiplier_threshold = config["detector"]["multiplier_threshold"]
        self.error_multiplier = config["detector"]["error_multiplier"]

    def process(self, ip: str, count: int, blocker):
        """
        Called for each request. Updates baseline and checks for anomalies.
        """

        # Update baseline with request count (errors=0 for now)
        self.baseline.add_sample(count, 0)

        mean = self.baseline.effective_mean
        std = self.baseline.effective_std

        # Z-score detection
        if std > 0:
            z = (count - mean) / std
        else:
            z = 0

        # Multiplier detection
        multiplier = count / max(1, mean)

        if z >= self.zscore_threshold or multiplier >= self.multiplier_threshold:
            msg = (
                f"🚨 Anomaly detected for IP {ip} — "
                f"count={count}, mean={mean:.2f}, std={std:.2f}, "
                f"z={z:.2f}, multiplier={multiplier:.2f}"
            )

            log.warning(msg)
            send_slack_alert(msg)

            blocker.block(ip)
