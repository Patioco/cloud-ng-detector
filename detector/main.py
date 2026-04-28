import threading
import time
import yaml
from monitor import SlidingWindows, start_log_monitor
from baseline import Baseline
from detector import Detector
from blocker import Blocker
from unbanner import Unbanner
from notifier import Notifier
from dashboard import create_app
import uvicorn

AUDIT_LOG_PATH = "/var/log/hng-detector-audit.log"

def audit_logger(action, ip, rate, baseline, duration):
  ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
  line = f"[{ts}] {action} {ip} | {rate} | {baseline} | {duration}\n"
  with open(AUDIT_LOG_PATH, "a") as f:
    f.write(line)

def main():
  with open("/app/config.yaml") as f:
    config = yaml.safe_load(f)

  windows = SlidingWindows(window_seconds=config["windows"]["per_ip_seconds"])
  baseline = Baseline(window_seconds=config["windows"]["baseline_minutes"] * 60)
  blocker = Blocker(config)
  notifier = Notifier(config["slack"]["webhook_url"])

  detector = Detector(windows, baseline, config, blocker, notifier, audit_logger)
  unbanner = Unbanner(blocker, notifier, audit_logger)

  start_time = time.time()

  # Thread: log monitor
  t_monitor = threading.Thread(target=start_log_monitor, args=(config["log_path"], windows), daemon=True)
  t_monitor.start()

  # Thread: baseline sampler
  def baseline_sampler():
    while True:
      global_rps, global_err_rps, _, _ = windows.get_rates()
      baseline.add_sample(global_rps, global_err_rps)
      time.sleep(1)

  t_baseline = threading.Thread(target=baseline_sampler, daemon=True)
  t_baseline.start()

  # Thread: baseline recalculation
  def baseline_recalc_loop():
    while True:
      baseline.recalc()
      audit_logger("BASELINE_RECALC", "-", "-", "-", "-")
      time.sleep(config["windows"]["baseline_recalc_seconds"])

  t_recalc = threading.Thread(target=baseline_recalc_loop, daemon=True)
  t_recalc.start()

  # Thread: detection loop
  def detection_loop():
    while True:
      detector.check()
      time.sleep(1)

  t_detect = threading.Thread(target=detection_loop, daemon=True)
  t_detect.start()

  # Thread: unban loop
  t_unban = threading.Thread(target=unbanner.loop, daemon=True)
  t_unban.start()

  # Dashboard
  app = create_app(windows, baseline, blocker, start_time)
  uvicorn.run(app, host=config["dashboard"]["host"], port=config["dashboard"]["port"])

if __name__ == "__main__":
  main()
