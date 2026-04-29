import requests
import logging
from .config import load_config

log = logging.getLogger("notifier")

config = load_config()
slack_cfg = config.get("alerts", {}).get("slack", {})


def send_slack_alert(message: str):
    """Send a Slack alert if enabled and webhook is configured."""
    if not slack_cfg.get("enabled", False):
        return

    webhook = slack_cfg.get("webhook_url")
    if not webhook:
        log.warning("Slack alert enabled but no webhook URL configured.")
        return

    payload = {"text": message}

    try:
        resp = requests.post(webhook, json=payload, timeout=5)
        if resp.status_code >= 300:
            log.error(f"Slack webhook returned {resp.status_code}: {resp.text}")
    except Exception as e:
        log.error(f"Failed to send Slack alert: {e}")