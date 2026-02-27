"""Weekly review: how did last week go vs goals, and what's coming this week."""

import json
import os
from collections import defaultdict
from datetime import datetime, timedelta, timezone

from analyze import analyze_time, categorize_event, load_categories
from pending_invites import find_pending_invites
from snapshots_store import build_pending_summary, save_snapshot

GOALS_FILE = "goals.json"

DEFAULT_GOALS = {
    "total_meeting_hours_per_week": 20,
    "category_targets": {
        "1:1": 5,
        "Team meetings": 4,
        "Focus time": 8,
        "External": 2,
        "Interview": 1,
    },
}


def load_goals():
    """Load time allocation goals, creating defaults if missing."""
    if os.path.exists(GOALS_FILE):
        with open(GOALS_FILE) as f:
            return json.load(f)

    with open(GOALS_FILE, "w") as f:
        json.dump(DEFAULT_GOALS, f, indent=2)
    return DEFAULT_GOALS


def _week_boundaries():
    """Return (last_week_start, last_week_end, this_week_start, this_week_end).

    Weeks are Mon-Sun. last_week is the most recently completed week.
    this_week runs from the most recent Monday through next Sunday.
    """
    now = datetime.now(timezone.utc)
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)

    # Monday of this week
    this_monday = today - timedelta(days=today.weekday())
    last_monday = this_monday - timedelta(days=7)
    next_monday = this_monday + timedelta(days=7)

    return last_monday, this_monday, this_monday, next_monday


def _filter_week(events, week_start, week_end):
    """Return events that fall within [week_start, week_end)."""
    result = []
    for e in events:
        s = e["start"]
        if not s.tzinfo:
            # All-day events: compare dates
            if s.date() >= week_start.date() and s.date() < week_end.date():
                result.append(e)
        else:
            if s >= week_start and s < week_end:
                result.append(e)
    return result


def format_weekly_review(events):
    """Generate the full weekly review report.

    Also auto-saves a snapshot of last week for future diffing.
    """
    categories = load_categories()
    goals = load_goals()

    last_start, last_end, this_start, this_end = _week_boundaries()

    last_week_events = _filter_week(events, last_start, last_end)
    this_week_events = _filter_week(events, this_start, this_end)

    last_analysis = analyze_time(last_week_events, categories)
    this_analysis = analyze_time(this_week_events, categories)

    # Auto-save last week's snapshot
    last_pending = build_pending_summary(last_week_events)
    label = f"week-of-{last_start.strftime('%Y-%m-%d')}"
    snap_path = save_snapshot(last_analysis, last_pending, label=label)

    lines = []
    lines.append("=" * 64)
    lines.append("  WEEKLY REVIEW")
    lines.append(f"  Last week: {last_start.strftime('%b %d')} – {(last_end - timedelta(days=1)).strftime('%b %d')}")
    lines.append(f"  This week: {this_start.strftime('%b %d')} – {(this_end - timedelta(days=1)).strftime('%b %d')}")
    lines.append("=" * 64)
    lines.append("")
    lines.append(f"  (Snapshot saved: {snap_path})")
    lines.append("")

    # --- Last week vs goals ---
    lines.append("-" * 64)
    lines.append("  LAST WEEK vs GOALS")
    lines.append("-" * 64)

    target_total = goals.get("total_meeting_hours_per_week", 0)
    actual_total = last_analysis["total_meeting_hours"]
    delta_total = actual_total - target_total

    lines.append(
        f"  Total meetings:  {actual_total:.1f}h actual  /  "
        f"{target_total:.1f}h target  ({_signed(delta_total)}h)"
    )
    if delta_total > 2:
        lines.append("  *** Over target — consider declining lower-priority meetings ***")
    elif delta_total < -2:
        lines.append("  *** Under target — you had more free time than planned ***")
    lines.append("")

    cat_targets = goals.get("category_targets", {})
    all_cats = sorted(
        set(list(last_analysis["by_category"].keys()) + list(cat_targets.keys()))
    )

    lines.append(
        f"  {'Category':<20} {'Actual':>7} {'Target':>7} {'Delta':>7} {'Status'}"
    )
    lines.append(f"  {'─' * 20} {'─' * 7} {'─' * 7} {'─' * 7} {'─' * 12}")

    for cat in all_cats:
        actual = last_analysis["by_category"].get(cat, {}).get("hours", 0)
        target = cat_targets.get(cat, 0)
        delta = actual - target
        status = _goal_status(delta, target)
        lines.append(
            f"  {cat:<20} {actual:6.1f}h {target:6.1f}h {_signed(delta):>6}h {status}"
        )
    lines.append("")

    # --- Pending invite hygiene ---
    last_pending_list = find_pending_invites(last_week_events)
    this_pending_list = find_pending_invites(this_week_events)

    lines.append("-" * 64)
    lines.append("  INVITE HYGIENE")
    lines.append("-" * 64)
    lines.append(f"  Last week: {len(last_pending_list)} event(s) you never accepted/declined")
    lines.append(f"  This week: {len(this_pending_list)} event(s) still need a response")
    if this_pending_list:
        lines.append("")
        lines.append("  Events needing response this week:")
        for e in this_pending_list:
            time_str = e["start"].strftime("%a %I:%M %p") if not e["is_all_day"] else e["start"].strftime("%a (all day)")
            status = "!!" if e["my_response"] == "needsAction" else "??"
            lines.append(f"    [{status}] {time_str}  {e['summary']}")
    lines.append("")

    # --- This week preview ---
    lines.append("-" * 64)
    lines.append("  THIS WEEK PREVIEW")
    lines.append("-" * 64)

    this_total = this_analysis["total_meeting_hours"]
    this_events = this_analysis["total_events"]
    lines.append(f"  {this_events} events  |  {this_total:.1f}h of meetings scheduled")

    if target_total > 0:
        proj_delta = this_total - target_total
        lines.append(
            f"  vs target: {_signed(proj_delta)}h "
            f"({'over' if proj_delta > 0 else 'under'} your {target_total:.0f}h goal)"
        )
    lines.append("")

    # Per-day load for the coming week
    day_order = ["Mon", "Tue", "Wed", "Thu", "Fri"]
    lines.append(f"  {'Day':<6} {'Hours':>6}  {'Load'}")
    lines.append(f"  {'─' * 5} {'─' * 6}  {'─' * 20}")
    for d in day_order:
        h = this_analysis["by_day"].get(d, 0)
        bar = "#" * int(h * 2)
        warning = " <-- heavy!" if h > 6 else ""
        lines.append(f"  {d:<6} {h:5.1f}h  {bar}{warning}")
    lines.append("")

    # --- Suggestions ---
    lines.append("-" * 64)
    lines.append("  ADJUSTMENTS TO CONSIDER")
    lines.append("-" * 64)

    suggestions = _generate_suggestions(last_analysis, this_analysis, goals, this_pending_list)
    for s in suggestions:
        lines.append(f"  -> {s}")
    lines.append("")

    return "\n".join(lines)


def _goal_status(delta, target):
    """Return a human label for how actual compares to target."""
    if target == 0:
        if delta > 0.5:
            return "(no target)"
        return ""
    ratio = delta / target if target else 0
    if ratio > 0.5:
        return "*** OVER ***"
    elif ratio > 0.2:
        return "slightly over"
    elif ratio < -0.5:
        return "well under"
    elif ratio < -0.2:
        return "slightly under"
    return "on track"


def _signed(val):
    return f"+{val:.1f}" if val >= 0 else f"{val:.1f}"


def _generate_suggestions(last_analysis, this_analysis, goals, pending):
    """Generate actionable suggestions based on the data."""
    suggestions = []
    cat_targets = goals.get("category_targets", {})

    # Check for over-indexed categories
    for cat, data in last_analysis["by_category"].items():
        target = cat_targets.get(cat, 0)
        if target > 0 and data["hours"] > target * 1.5:
            suggestions.append(
                f"{cat} was {data['hours']:.1f}h last week vs {target:.1f}h target. "
                f"Can you decline or shorten some?"
            )

    # Check focus time
    focus_actual = last_analysis["by_category"].get("Focus time", {}).get("hours", 0)
    focus_target = cat_targets.get("Focus time", 0)
    if focus_target > 0 and focus_actual < focus_target * 0.5:
        suggestions.append(
            f"Focus time was only {focus_actual:.1f}h vs {focus_target:.1f}h target. "
            f"Block more focus time on your calendar."
        )

    # Pending invites
    if len(pending) > 3:
        suggestions.append(
            f"You have {len(pending)} unresponded invites this week. "
            f"Go through them now — accept or decline each one."
        )

    # Heavy days
    for d, h in this_analysis["by_day"].items():
        if h > 6:
            suggestions.append(
                f"{d} has {h:.1f}h of meetings. Consider moving or declining something."
            )

    if not suggestions:
        suggestions.append("Looking good! No major adjustments needed.")

    return suggestions
