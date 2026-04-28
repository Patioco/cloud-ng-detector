# HNG Stage 3 — Anomaly Detection Engine

A real-time HTTP traffic anomaly detection and DDoS mitigation daemon built alongside a Nextcloud deployment. Monitors Nginx access logs, learns normal traffic patterns, and automatically blocks suspicious IPs using `iptables` — with exponential backoff, Slack alerting, and a live metrics dashboard.

| Submission Field   | Value                                                  |
|--------------------|--------------------------------------------------------|
| **Server IP**      | `<YOUR_SERVER_IP>`                                     |
| **Dashboard URL**  | `http://<YOUR_SERVER_IP>:9000`                         |
| **GitHub Repo**    | `https://github.com/<your-username>/hng-stage3-devsecops` |
| **Blog Post**      | `https://<your-published-blog-url>`                    |

---

## Table of Contents

- [Project Overview](#project-overview)
- [Language Choice](#language-choice)
- [Architecture](#architecture)
- [Sliding Window](#sliding-window)
- [Baseline Logic](#baseline-logic)
- [Detection Logic](#detection-logic)
- [Blocking & Unban Flow](#blocking--unban-flow)
- [Dashboard](#dashboard)
- [Setup Instructions](#setup-instructions)
- [Repository Structure](#repository-structure)
- [Screenshots](#screenshots)
- [Blog Post](#blog-post)
- [License](#license)

---

## Project Overview

This project deploys a **Nextcloud** instance behind **Nginx** and runs a custom **anomaly detection daemon** that:

1. **Tails** Nginx JSON access logs in real time via a shared Docker volume.
2. **Learns** normal traffic baselines using a 30-minute rolling window.
3. **Detects** anomalies via z-score analysis and multiplier thresholds.
4. **Blocks** offending IPs at the kernel level with `iptables DROP` rules.
5. **Alerts** your team instantly through a Slack webhook integration.
6. **Displays** live metrics on a built-in HTTP dashboard.

All thresholds and configuration live in `detector/config.yaml` — nothing is hardcoded.

---

## Language Choice

**Python 3.11** was chosen because:

- `collections.deque` provides O(1) `popleft` — ideal for the sliding window requirement.
- `threading` + `queue` allow the log monitor, baseline recalculator, notifier, and dashboard to run concurrently without async runtime complexity.
- `subprocess.run` gives clean, auditable `iptables` integration.
- The entire detector fits in a single Docker image under 200 MB.

---

## Architecture

```
Nginx (JSON access logs)
        │
        ▼
(shared Docker volume: hng-nginx-logs, read-only to detector)
        │
        ▼
   LogMonitor
   ┌────┴────────────────────────────────────┐
   │                                         │
   ▼                                         ▼
BaselineTracker                      AnomalyDetector
 · rolling 30-min window deque        · per-IP sliding windows
 · recalc every 60s                   · z-score + multiplier checks
 · per-hour slot baselines            · error-rate tightening
   │                                         │
   └──────────────┬──────────────────────────┘
                  │
                  ▼
         IPBlocker (iptables)
          · exponential backoff
          · auto-unban scheduler
                  │
         ┌───────┴───────┐
         ▼               ▼
   SlackNotifier     Dashboard
   · webhook alerts  · live metrics on :9000
```

| Component          | Role                                                                 |
|--------------------|----------------------------------------------------------------------|
| **Nginx**          | Public reverse proxy; produces JSON-formatted access logs            |
| **Nextcloud**      | Required `kefaslungu/hng-nextcloud` Docker image                     |
| **Detector**       | Python daemon — monitoring, baselines, blocking, Slack, dashboard    |
| **MariaDB**        | Persistent database backend for Nextcloud                            |
| **Docker Compose** | Runtime orchestration for the full stack                             |

---

## Sliding Window

The detector maintains two **60-second deque-backed windows**:

| Window             | Scope     | Purpose                              |
|--------------------|-----------|--------------------------------------|
| **Global deque**   | All IPs   | Aggregate request rate               |
| **Per-IP deque**   | Single IP | Individual IP request rate            |

**How it works:**

1. Every parsed Nginx log line appends its timestamp to the relevant deque(s).
2. Before calculating a rate, timestamps older than `now − 60s` are evicted.
3. The request rate is computed as:

```
rate = len(deque) / 60.0  # requests per second
```

Error traffic (4xx/5xx responses) uses the same deque structure but only stores error timestamps.

---

## Baseline Logic

Baselines are calculated from **per-second request counts over the last 30 minutes**. Every 60 seconds, the `BaselineTracker` recalculates:

| Metric                   | Description                                      |
|--------------------------|--------------------------------------------------|
| `mean`                   | Average requests per second over the window      |
| `stddev`                 | Standard deviation of request rates              |
| `error_mean`             | Average 4xx/5xx error rate                       |
| `error_stddev`           | Standard deviation of error rates                |

**Key behaviours:**

- **Per-hour slots** — once the current hour accumulates enough samples, its baseline becomes the *effective* baseline, adapting to time-of-day traffic patterns.
- **Floor values** — configured in `detector/config.yaml`, these prevent division-by-zero and cold-start blind spots (e.g., `stddev` floor of `1.0`).
- **Activation guard** — the baseline only activates after a minimum number of data points are collected, avoiding false positives on startup.

---

## Detection Logic

For each request, the detector compares the current 60-second rate against the effective baseline:

```
z_score = (current_rate - baseline_mean) / baseline_stddev
```

### Anomaly triggers — either condition firing is sufficient:

| Condition            | Rule                          | Rationale                                    |
|----------------------|-------------------------------|----------------------------------------------|
| **Z-Score breach**   | `z_score > 3.0`              | Rate is 3+ standard deviations above normal  |
| **5× Multiplier**    | `current_rate > 5 × mean`    | Catches anomalies even with high variance     |

### Error-rate tightening:

If an IP's 4xx/5xx rate reaches **3× its baseline error rate**, that IP automatically receives **tighter detection thresholds** — reducing the z-score trigger and multiplier so suspicious behaviour is caught faster.

### Cooldown:

A **30-second per-IP cooldown** prevents alert floods for the same IP.

---

## Blocking & Unban Flow

### How `iptables` blocks an IP

When a per-IP anomaly fires, the daemon executes:

```bash
iptables -I INPUT 1 -s <OFFENDING_IP> -j DROP
```

- `-I INPUT 1` inserts the rule at the **top** of the INPUT chain — it takes effect immediately and cannot be bypassed by rules lower in the chain.
- Packets from the banned IP are **silently discarded at the kernel level** before Nginx ever sees them.

### Auto-unban

When the ban duration expires, the daemon removes the rule:

```bash
iptables -D INPUT -s <OFFENDING_IP> -j DROP
```

### Exponential backoff schedule

| Offence | Ban Duration   | Notes                                    |
|---------|----------------|------------------------------------------|
| 1st     | 10 minutes     | Light warning                            |
| 2nd     | 30 minutes     | Escalation                               |
| 3rd     | 2 hours        | Extended block                           |
| 4th+    | **Permanent**  | Never auto-released; manual intervention |

> The detector requires `CAP_NET_ADMIN` (provided via `cap_add: [NET_ADMIN]` in Docker Compose).

### Whitelist

Trusted IPs (your own, monitoring probes, etc.) are defined in `detector/config.yaml` and are **never blocked**, regardless of traffic volume.

---

## Dashboard

A lightweight, built-in HTTP dashboard is served on **port 9000** and provides real-time visibility into the detector's state:

| Panel                    | Description                                              |
|--------------------------|----------------------------------------------------------|
| **Current Request Rate** | Live requests/sec across all IPs                         |
| **Baseline Stats**       | Active mean, stddev, error mean, error stddev            |
| **Blocked IPs**          | Currently banned IPs with offence count and unban time   |
| **Recent Alerts**        | Last N anomaly detections with timestamps and z-scores   |
| **System Health**        | Uptime, log lines processed, baseline recalculation age  |

Access at: `http://<YOUR_SERVER_IP>:9000`

---

## Setup Instructions

### Prerequisites

| Requirement     | Minimum                        |
|-----------------|--------------------------------|
| **OS**          | Ubuntu 22.04+                  |
| **CPU**         | 2 vCPU                         |
| **RAM**         | 2 GB                           |
| **Ports open**  | 80 (HTTP), 9000 (Dashboard)    |

### 1. Install Docker

```bash
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER && newgrp docker
```

### 2. Clone the repository

```bash
git clone https://github.com/<your-username>/hng-stage3-devsecops.git
cd hng-stage3-devsecops
```

### 3. Configure the detector

```bash
cp detector/config.example.yaml detector/config.yaml
```

Edit `detector/config.yaml`:

- **`slack_webhook_url`** — paste your Slack incoming webhook URL.
- **`whitelist`** — add your own IP(s) so you never get blocked.
- **`thresholds`** — tune z-score, multiplier, and floor values if needed (defaults are production-ready).

### 4. Start the stack

```bash
docker compose up -d --build
```

### 5. Verify

| Check                     | Command / URL                              |
|---------------------------|--------------------------------------------|
| Nextcloud is reachable    | `curl http://<YOUR_SERVER_IP>`             |
| Dashboard is live         | `http://<YOUR_SERVER_IP>:9000`             |
| Detector logs             | `docker logs -f detector`                  |
| All containers running    | `docker compose ps`                        |

---

## Repository Structure

```
hng-stage3-devsecops/
├── detector/
│   ├── main.py              # Entry point — wires all components together
│   ├── monitor.py           # Tails Nginx JSON logs, parses lines
│   ├── baseline.py          # Rolling 30-min baseline tracker
│   ├── detector.py          # Anomaly detection (z-score + multiplier)
│   ├── blocker.py           # iptables blocking, unban scheduler, backoff
│   ├── notifier.py          # Slack webhook integration
│   ├── dashboard.py         # HTTP dashboard server (:9000)
│   ├── config.yaml          # All thresholds, whitelist, Slack URL
│   ├── config.example.yaml  # Template config (committed to repo)
│   ├── requirements.txt     # Python dependencies
│   └── Dockerfile           # Detector container build
├── nginx/
│   ├── nginx.conf           # Reverse proxy config with JSON log format
│   └── Dockerfile           # Nginx container build (if customised)
├── docker-compose.yml       # Full stack orchestration
├── screenshots/             # Dashboard and alert screenshots
├── .gitignore
├── LICENSE
└── README.md                # ← You are here
```

---

## Screenshots

> Add screenshots to the `screenshots/` directory and update the paths below.

| Screenshot                    | Description                                  |
|-------------------------------|----------------------------------------------|
| `screenshots/dashboard.png`   | Live dashboard showing metrics and baselines |
| `screenshots/slack-alert.png` | Slack notification on anomaly detection       |
| `screenshots/block-log.png`   | Detector logs showing IP block event          |
| `screenshots/nextcloud.png`   | Nextcloud instance running behind Nginx       |
| `screenshots/unban-log.png`   | Auto-unban log after backoff timer expires    |

---

## Blog Post

> **Link:** `https://<your-published-blog-url>`
>
> The blog post covers the design decisions, architecture walkthrough, detection algorithm explanation, and lessons learned during this project. Publish it before final submission.

---

## License

This project is licensed under the [MIT License](LICENSE).

---

<p align="center">
  Built for the <a href="https://hng.tech">HNG Internship</a> — Stage 3 DevSecOps Track
</p>
