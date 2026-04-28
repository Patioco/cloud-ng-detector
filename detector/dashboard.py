from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import time
import psutil


def create_app(windows, baseline, blocker, start_time):
    app = FastAPI()

    @app.get("/metrics")
    def metrics():
        global_rps, global_err_rps, per_ip_rps, per_ip_err_rps = windows.get_rates()
        bans = blocker.get_bans()
        uptime = time.time() - start_time
        cpu = psutil.cpu_percent()
        mem = psutil.virtual_memory().percent

        top_ips = sorted(per_ip_rps.items(), key=lambda x: x[1], reverse=True)[:10]

        return {
            "global_rps": global_rps,
            "global_err_rps": global_err_rps,
            "baseline_mean": baseline.effective_mean,
            "baseline_std": baseline.effective_std,
            "baseline_err_mean": baseline.effective_err_mean,
            "baseline_err_std": baseline.effective_err_std,
            "bans": bans,
            "top_ips": top_ips,
            "uptime": uptime,
            "cpu": cpu,
            "mem": mem,
        }

    @app.get("/", response_class=HTMLResponse)
    def dashboard():
        return """
        <html>
        <head>
            <title>HNG Detector Dashboard</title>
            <meta http-equiv="refresh" content="3">
            <style>
                body { font-family: Arial; padding: 20px; background: #f5f5f5; }
                h1 { color: #333; }
                pre { background: #fff; padding: 15px; border-radius: 8px; }
            </style>
        </head>
        <body>
            <h1>HNG Detector — Live Metrics</h1>
            <p>Auto-refreshing every 3 seconds</p>
            <pre id="metrics">Loading...</pre>

            <script>
                async function loadMetrics() {
                    const res = await fetch('/metrics');
                    const data = await res.json();
                    document.getElementById('metrics').textContent =
                        JSON.stringify(data, null, 2);
                }
                loadMetrics();
                setInterval(loadMetrics, 3000);
            </script>
        </body>
        </html>
        """

    return app
