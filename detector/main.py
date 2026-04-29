import logging
import threading

from .monitor import SlidingWindowManager, start_log_monitor
from .baseline import BaselineEngine
from .detector import Detector
from .blocker import Blocker
from .unbanner import Unbanner
from .notifier import send_slack_alert
from .dashboard import start_dashboard
from .config import load_config

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("main")


def main():
    config = load_config()

    # Core components
    window_mgr = SlidingWindowManager(
        window_seconds=config["detector"]["window_seconds"],
        max_entries=config["detector"]["max_entries"]
    )

    baseline = BaselineEngine(config)
    detector = Detector(config, window_mgr, baseline)
    blocker = Blocker(config)
    unbanner = Unbanner(config)

    # Start dashboard (Flask/FastAPI)
    dashboard_thread = threading.Thread(target=start_dashboard, daemon=True)
    dashboard_thread.start()

    # Start unbanner loop
    unbanner_thread = threading.Thread(target=unbanner.run, daemon=True)
    unbanner_thread.start()

    # Start log monitor
    def on_request(ip):
        count = window_mgr.get_count(ip)
        detector.process(ip, count, blocker)

    start_log_monitor(on_request, logfile_path=config["logs"]["access_log"])

    send_slack_alert("🚀 Detector service started successfully")

    log.info("Detector is running...")
    while True:
        pass


if __name__ == "__main__":
    main()
