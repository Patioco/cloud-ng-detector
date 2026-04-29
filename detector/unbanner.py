import time
import logging
import subprocess
from .notifier import send_slack_alert

log = logging.getLogger("unbanner")


class Unbanner:
    """
    Periodically checks for expired bans and removes them.
    """

    def __init__(self, config):
        self.config = config
        self.unban_interval = config["detector"].get("unban_interval", 60)
        self.ban_duration = config["detector"].get("ban_duration", 300)

        # Track banned IPs and timestamps
        self.banned_ips = {}

    def register_ban(self, ip):
        self.banned_ips[ip] = time.time()

    def unban(self, ip):
        try:
            subprocess.run(["iptables", "-D", "INPUT", "-s", ip, "-j", "DROP"], check=False)
            send_slack_alert(f"♻️ IP unbanned: {ip}")
            log.info(f"Unbanned IP: {ip}")
        except Exception as e:
            log.error(f"Failed to unban {ip}: {e}")

    def run(self):
        """
        Background loop that unbans IPs after ban_duration.
        """
        log.info("Unbanner thread started")

        while True:
            now = time.time()
            expired = [ip for ip, ts in self.banned_ips.items() if now - ts >= self.ban_duration]

            for ip in expired:
                self.unban(ip)
                del self.banned_ips[ip]

            time.sleep(self.unban_interval)
