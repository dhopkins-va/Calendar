"""Save and load calendar analysis snapshots for later comparison."""

import json
import os
from datetime import datetime, timezone
from pathlib import Path

SNAPSHOTS_DIR = "snapshots"


def save_snapshot(analysis, pending_summary, label=None):
    """Save an analysis result to disk. Returns the snapshot path."""
    Path(SNAPSHOTS_DIR).mkdir(exist_ok=True)

    now = datetime.now(timezone.utc)
    timestamp = now.strftime("%Y%m%d_%H%M%S")
    slug = f"_{label}" if label else ""
    filename = f"{timestamp}{slug}.json"
    path = os.path.join(SNAPSHOTS_DIR, filename)

    # Strip non-serializable event objects from the category data
    serializable_cats = {}
    for cat_name, cat_data in analysis["by_category"].items():
        serializable_cats[cat_name] = {
            "hours": cat_data["hours"],
            "count": cat_data["count"],
        }

    snapshot = {
        "saved_at": now.isoformat(),
        "label": label or "",
        "analysis": {
            "by_category": serializable_cats,
            "by_day": analysis["by_day"],
            "total_meeting_hours": analysis["total_meeting_hours"],
            "total_events": analysis["total_events"],
            "busiest_day": analysis["busiest_day"],
            "avg_daily_meeting_hours": analysis["avg_daily_meeting_hours"],
            "num_days_analyzed": analysis["num_days_analyzed"],
        },
        "pending": pending_summary,
    }

    with open(path, "w") as f:
        json.dump(snapshot, f, indent=2)

    return path


def load_snapshot(path):
    """Load a snapshot from a file path."""
    with open(path) as f:
        return json.load(f)


def list_snapshots():
    """Return a list of (path, saved_at, label) for all snapshots, newest first."""
    if not os.path.isdir(SNAPSHOTS_DIR):
        return []

    results = []
    for name in sorted(os.listdir(SNAPSHOTS_DIR), reverse=True):
        if not name.endswith(".json"):
            continue
        path = os.path.join(SNAPSHOTS_DIR, name)
        try:
            snap = load_snapshot(path)
            results.append((path, snap.get("saved_at", ""), snap.get("label", "")))
        except (json.JSONDecodeError, KeyError):
            continue
    return results


def build_pending_summary(events):
    """Build a serializable summary of pending invite counts."""
    from pending_invites import (
        find_pending_invites,
        find_past_unresponded,
        find_upcoming_unresponded,
    )

    all_pending = find_pending_invites(events)
    past = find_past_unresponded(events)
    upcoming = find_upcoming_unresponded(events)

    return {
        "total_pending": len(all_pending),
        "past_unresponded": len(past),
        "upcoming_unresponded": len(upcoming),
    }
