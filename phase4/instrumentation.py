import json
import logging
import time
from contextlib import contextmanager

logger = logging.getLogger("recommender_metrics")
logger.setLevel(logging.INFO)

# Use a custom handler for structured JSON logs, but we'll just write to a file or stdout
handler = logging.FileHandler("artifacts/metrics.jsonl")
handler.setFormatter(logging.Formatter('%(message)s'))
logger.addHandler(handler)

@contextmanager
def track_latency(operation_name: str, meta: dict = None):
    start = time.perf_counter()
    status = "success"
    error_msg = None
    try:
        yield
    except Exception as e:
        status = "error"
        error_msg = str(e)
        raise
    finally:
        end = time.perf_counter()
        log_entry = {
            "timestamp": time.time(),
            "operation": operation_name,
            "latency_ms": round((end - start) * 1000, 2),
            "status": status,
        }
        if meta:
            log_entry.update(meta)
        if error_msg:
            log_entry["error"] = error_msg
            
        logger.info(json.dumps(log_entry))

def log_event(event_name: str, meta: dict):
    log_entry = {
        "timestamp": time.time(),
        "event": event_name,
    }
    log_entry.update(meta)
    logger.info(json.dumps(log_entry))
