import subprocess
import time
from threading import Lock

class Blocker:
  def __init__(self, config):
    self.config = config
    self.bans = {}  # ip -> {"level": int, "until": timestamp}
    self.lock = Lock()

  def _iptables_drop(self, ip: str):
    chain = self.config["ban"]["iptables_chain"]
    subprocess.run(["iptables", "-I", chain, "-s", ip, "-j", "DROP"], check=False)

  def _iptables_unban(self, ip: str):
    chain = self.config["ban"]["iptables_chain"]
    subprocess.run(["iptables", "-D", chain, "-s", ip, "-j", "DROP"], check=False)

  def should_ban(self, ip: str) -> bool:
    with self.lock:
      # allow re-bans after unban, but not spamming
      return True

  def ban(self, ip: str, reason: str, rate: float, baseline: float):
    with self.lock:
      level = self.bans.get(ip, {"level": 0})["level"]
      backoff = self.config["ban"]["backoff_minutes"]
      if level >= len(backoff):
        # permanent
        duration = None
        until = None
      else:
        minutes = backoff[level]
        duration = minutes * 60
        until = time.time() + duration

      self._iptables_drop(ip)
      self.bans[ip] = {"level": level + 1, "until": until}
      return duration

  def get_bans(self):
    with self.lock:
      return dict(self.bans)

  def unban_if_due(self):
    now = time.time()
    to_unban = []
    with self.lock:
      for ip, info in self.bans.items():
        if info["until"] is not None and info["until"] <= now:
          to_unban.append(ip)

      for ip in to_unban:
        self._iptables_unban(ip)
        # keep level, but clear until so next ban is longer
        self.bans[ip]["until"] = None

    return to_unban
