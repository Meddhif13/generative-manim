"""Shared logging helpers for dataset generation tools and apps."""
from __future__ import annotations

import os
from datetime import datetime


def log_event(action: str, details: str) -> None:
    """Append a timestamped event to ``logs/progress.md``.

    Parameters
    ----------
    action:
        Short label describing the event type.
    details:
        Additional context or payload for the event.
    """
    os.makedirs("logs", exist_ok=True)
    with open("logs/progress.md", "a", encoding="utf-8") as f:
        f.write(f"{datetime.utcnow().isoformat()}\t{action}\t{details}\n")
