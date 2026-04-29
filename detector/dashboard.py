import psutil
import threading
import logging
from fastapi import FastAPI
import uvicorn

log = logging.getLogger("dashboard")

app = FastAPI()


@app.get("/")
def root():
    return {"status": "ok", "message": "Detector dashboard running"}


@app.get("/metrics")
def metrics():
    cpu = psutil.cpu_percent()
    mem = psutil.virtual_memory().percent
    return {
        "cpu_percent": cpu,
        "memory_percent": mem
    }


def start_dashboard():
    """
    Runs the FastAPI dashboard in a background thread.
    """
    log.info("Starting dashboard on port 8090")

    def run():
        uvicorn.run(app, host="0.0.0.0", port=8090, log_level="info")

    thread = threading.Thread(target=run, daemon=True)
    thread.start()
    return thread
