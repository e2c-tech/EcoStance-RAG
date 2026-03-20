"""
Starts the Celery worker alongside a lightweight HTTP health server.
"""
import os
import threading
import logging
from http.server import HTTPServer, BaseHTTPRequestHandler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("WorkerStart")

HEALTH_PORT = int(os.getenv("WORKER_HEALTH_PORT", "9008"))


class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/health":
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"OK")
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass  # Suppress default HTTP logs


def run_health_server():
    server = HTTPServer(("0.0.0.0", HEALTH_PORT), HealthHandler)
    logger.info(f"✓ Worker health server started on port {HEALTH_PORT}")
    server.serve_forever()


if __name__ == "__main__":
    # Start health server in background thread
    thread = threading.Thread(target=run_health_server, daemon=True)
    thread.start()

    # Start Celery worker (blocking)
    from app.worker.tasks import celery_app
    logger.info("🚀 Starting Celery worker...")
    celery_app.worker_main([
        "worker",
        "--loglevel=info",
        "--concurrency=4",
        "--max-tasks-per-child=1000",
    ])
