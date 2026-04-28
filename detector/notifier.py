import requests
import datetime as dt

class Notifier:
    def __init__(self, method, path=None):
        self.method = method
        self.path = path

    def _write(self, text):
        if self.method == "file" and self.path:
            with open(self.path, "a") as f:
                f.write(text + "\n")

    def ip_ban(self, ip, rate, baseline, z, duration):
        msg = f"BAN {ip} | rate={rate:.2f} | baseline={baseline:.2f} | z={z:.2f} | duration={duration}"
        self._write(msg)

    def ip_unban(self, ip):
        self._write(f"UNBAN {ip}")

    def global_alert(self, rate, baseline, z):
        self._write(f"GLOBAL ALERT | rate={rate:.2f} | baseline={baseline:.2f} | z={z:.2f}")
