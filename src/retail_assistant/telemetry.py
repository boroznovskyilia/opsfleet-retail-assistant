"""Metadata-only correlated JSON diagnostics, separate from owned evidence."""

import json
import logging
import time
from logging.handlers import RotatingFileHandler

LOG = logging.getLogger("opsfleet")


def configure(runtime):
    runtime.mkdir(parents=True, exist_ok=True, mode=0o700)
    for handler in LOG.handlers[:]:
        LOG.removeHandler(handler)
        handler.close()
    path = runtime / "events.jsonl"
    handler = RotatingFileHandler(path, maxBytes=2 * 1024 * 1024, backupCount=2)
    path.chmod(0o600)
    LOG.addHandler(handler)
    LOG.setLevel(logging.INFO)
    LOG.propagate = False


def event(name, **fields):
    LOG.info(
        json.dumps({"time": time.time(), "event": name, **fields}, allow_nan=False)
    )
