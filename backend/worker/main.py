from __future__ import annotations

import signal
import time

import structlog

from backend.core.config import Config
from backend.core.services import build_services

logger = structlog.get_logger("ingestion_worker")

_running = True


def _stop_handler(signum, _frame):
    global _running
    _running = False
    logger.info("worker_stopping", signal=signum)


def main():
    signal.signal(signal.SIGINT, _stop_handler)
    signal.signal(signal.SIGTERM, _stop_handler)

    poll_interval = float(getattr(Config, "INGESTION_WORKER_POLL_SECONDS", 1.0))
    services = build_services()
    ingestion = services.ingestion

    logger.info("worker_started", poll_interval_seconds=poll_interval)

    while _running:
        job = ingestion.claim_next_job()
        if job is None:
            time.sleep(poll_interval)
            continue

        job_id = job["job_id"]
        logger.info("worker_job_claimed", job_id=job_id, document_id=job.get("document_id"))
        ingestion.process_job(job_id)

    services.close()
    logger.info("worker_stopped")


if __name__ == "__main__":
    main()
