import time

class Unbanner:
  def __init__(self, blocker, notifier, audit_logger):
    self.blocker = blocker
    self.notifier = notifier
    self.audit_logger = audit_logger

  def loop(self):
    while True:
      to_unban = self.blocker.unban_if_due()
      for ip in to_unban:
        self.notifier.ip_unban(ip)
        self.audit_logger("UNBAN", ip, "-", "-", "-")
      time.sleep(10)
