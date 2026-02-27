"""Time analysis: categorize events, compute summaries, and generate reports."""

import json
import os
import re
from collections import defaultdict
from datetime import datetime, timedelta, timezone

CATEGORIES_FILE = "categories.json"

# Default categories — users customize via categories.json
DEFAULT_CATEGORIES = {
    "1:1": {
        "description": "One-on-one meetings",
        "patterns": ["1:1", "1-1", "one on one", "1 on 1", "sync with"],
    },
    "Team meetings": {
        "description": "Recurring team syncs, standups, retros",
        "patterns": ["standup", "stand-up", "retro", "sprint", "team sync",
                      "all hands", "all-hands", "weekly", "team meeting"],
    },
    "External": {
        "description": "Meetings with external people, customers, vendors",
        "patterns": ["external", "customer", "vendor", "partner", "client",
                      "sales call", "demo"],
    },
    "Focus time": {
        "description": "Blocked time for deep work",
        "patterns": ["focus", "deep work", "heads down", "no meetings",
                      "maker time", "coding", "writing time"],
    },
    "Interview": {
        "description": "Hiring interviews",
        "patterns": ["interview", "debrief", "hiring"],
    },
    "Social / culture": {
        "description": "Social, team building, coffee chats",
        "patterns": ["coffee", "social", "happy hour", "lunch", "team building",
                      "celebration", "birthday", "offsite"],
    },
    "Other": {
        "description": "Everything that doesn't match another category",
        "patterns": [],
    },
}


def load_categories():
    """Load category definitions, creating the defaults file if missing."""
    if os.path.exists(CATEGORIES_FILE):
        with open(CATEGORIES_FILE) as f:
            return json.load(f)

    # Write defaults so the user can customize
    with open(CATEGORIES_FILE, "w") as f:
        json.dump(DEFAULT_CATEGORIES, f, indent=2)
    return DEFAULT_CATEGORIES


def categorize_event(event, categories):
    """Return the category name for an event based on title pattern matching."""
    title = event["summary"].lower()
    for cat_name, cat_def in categories.items():
        if cat_name == "Other":
            continue
        for pattern in cat_def.get("patterns", []):
            if pattern.lower() in title:
                return cat_name
    return "Other"


def analyze_time(events, categories):
    """Produce a time breakdown by category.

    Returns a dict:
      {
        "by_category": { "1:1": {"hours": 5.5, "count": 8, "events": [...]}, ... },
        "by_day": { "Mon": hours, ... },
        "total_meeting_hours": float,
        "total_events": int,
        "busiest_day": str,
        "avg_daily_meeting_hours": float,
      }
    """
    by_category = defaultdict(lambda: {"hours": 0.0, "count": 0, "events": []})
    by_day_name = defaultdict(float)
    by_date = defaultdict(float)

    # Only analyze timed, non-cancelled events (skip all-day events)
    timed = [e for e in events if not e["is_all_day"] and e["status"] != "cancelled"]

    for event in timed:
        cat = categorize_event(event, categories)
        hours = event["duration_minutes"] / 60
        by_category[cat]["hours"] += hours
        by_category[cat]["count"] += 1
        by_category[cat]["events"].append(event)

        day_name = event["start"].strftime("%a")
        by_day_name[day_name] += hours

        date_str = event["start"].strftime("%Y-%m-%d")
        by_date[date_str] += hours

    total_hours = sum(c["hours"] for c in by_category.values())
    total_events = sum(c["count"] for c in by_category.values())

    busiest_day = max(by_day_name, key=by_day_name.get) if by_day_name else "N/A"
    num_unique_days = len(by_date) or 1
    avg_daily = total_hours / num_unique_days

    return {
        "by_category": dict(by_category),
        "by_day": dict(by_day_name),
        "total_meeting_hours": total_hours,
        "total_events": total_events,
        "busiest_day": busiest_day,
        "avg_daily_meeting_hours": avg_daily,
        "num_days_analyzed": num_unique_days,
    }


def format_time_report(analysis, weeks):
    """Return a human-readable time analysis report string."""
    lines = []
    lines.append("=" * 60)
    lines.append("  TIME ANALYSIS REPORT")
    lines.append(f"  (past {weeks} week{'s' if weeks != 1 else ''} + upcoming {weeks} week{'s' if weeks != 1 else ''})")
    lines.append("=" * 60)
    lines.append("")

    total = analysis["total_meeting_hours"]
    lines.append(f"Total scheduled time:       {total:.1f} hours across {analysis['total_events']} events")
    lines.append(f"Average per working day:    {analysis['avg_daily_meeting_hours']:.1f} hours")
    lines.append(f"Busiest day of the week:    {analysis['busiest_day']}")
    lines.append(f"Days with events:           {analysis['num_days_analyzed']}")
    lines.append("")

    # Category breakdown sorted by hours descending
    lines.append("-" * 60)
    lines.append("  BREAKDOWN BY CATEGORY")
    lines.append("-" * 60)
    cats = sorted(
        analysis["by_category"].items(),
        key=lambda x: x[1]["hours"],
        reverse=True,
    )
    for cat_name, data in cats:
        pct = (data["hours"] / total * 100) if total > 0 else 0
        bar = "#" * int(pct / 2)
        lines.append(
            f"  {cat_name:<22} {data['hours']:6.1f}h  ({data['count']:3} events)  "
            f"{pct:5.1f}%  {bar}"
        )
    lines.append("")

    # Day-of-week breakdown
    lines.append("-" * 60)
    lines.append("  HOURS BY DAY OF WEEK")
    lines.append("-" * 60)
    day_order = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    by_day = analysis["by_day"]
    for d in day_order:
        h = by_day.get(d, 0)
        bar = "#" * int(h)
        lines.append(f"  {d}  {h:5.1f}h  {bar}")
    lines.append("")

    return "\n".join(lines)
