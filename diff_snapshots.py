"""Compare two calendar snapshots and produce a diff report."""


def diff_analyses(old_snap, new_snap):
    """Compare two snapshot dicts and return a structured diff.

    Returns a dict with:
      - category_changes: list of {name, old_hours, new_hours, delta_hours, old_pct, new_pct, delta_pct}
      - day_changes: list of {day, old_hours, new_hours, delta_hours}
      - summary_changes: dict of top-level metric deltas
      - pending_changes: dict of pending invite count deltas
    """
    old_a = old_snap["analysis"]
    new_a = new_snap["analysis"]

    # --- Category diff ---
    all_cats = sorted(
        set(old_a["by_category"].keys()) | set(new_a["by_category"].keys())
    )
    old_total = old_a["total_meeting_hours"] or 1
    new_total = new_a["total_meeting_hours"] or 1

    category_changes = []
    for cat in all_cats:
        old_h = old_a["by_category"].get(cat, {}).get("hours", 0)
        new_h = new_a["by_category"].get(cat, {}).get("hours", 0)
        old_pct = old_h / old_total * 100
        new_pct = new_h / new_total * 100
        category_changes.append({
            "name": cat,
            "old_hours": old_h,
            "new_hours": new_h,
            "delta_hours": new_h - old_h,
            "old_pct": old_pct,
            "new_pct": new_pct,
            "delta_pct": new_pct - old_pct,
        })
    category_changes.sort(key=lambda c: abs(c["delta_hours"]), reverse=True)

    # --- Day-of-week diff ---
    day_order = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    day_changes = []
    for d in day_order:
        old_h = old_a["by_day"].get(d, 0)
        new_h = new_a["by_day"].get(d, 0)
        day_changes.append({
            "day": d,
            "old_hours": old_h,
            "new_hours": new_h,
            "delta_hours": new_h - old_h,
        })

    # --- Top-level summary diff ---
    summary_changes = {
        "total_hours": {
            "old": old_a["total_meeting_hours"],
            "new": new_a["total_meeting_hours"],
            "delta": new_a["total_meeting_hours"] - old_a["total_meeting_hours"],
        },
        "total_events": {
            "old": old_a["total_events"],
            "new": new_a["total_events"],
            "delta": new_a["total_events"] - old_a["total_events"],
        },
        "avg_daily": {
            "old": old_a["avg_daily_meeting_hours"],
            "new": new_a["avg_daily_meeting_hours"],
            "delta": new_a["avg_daily_meeting_hours"] - old_a["avg_daily_meeting_hours"],
        },
    }

    # --- Pending invites diff ---
    old_p = old_snap.get("pending", {})
    new_p = new_snap.get("pending", {})
    pending_changes = {}
    for key in ("total_pending", "past_unresponded", "upcoming_unresponded"):
        old_v = old_p.get(key, 0)
        new_v = new_p.get(key, 0)
        pending_changes[key] = {"old": old_v, "new": new_v, "delta": new_v - old_v}

    return {
        "category_changes": category_changes,
        "day_changes": day_changes,
        "summary_changes": summary_changes,
        "pending_changes": pending_changes,
    }


def format_diff_report(diff, old_snap, new_snap):
    """Return a human-readable diff report string."""
    lines = []
    lines.append("=" * 64)
    lines.append("  CALENDAR DIFF — WHAT CHANGED?")
    lines.append("=" * 64)

    old_label = old_snap.get("label") or old_snap.get("saved_at", "?")
    new_label = new_snap.get("label") or new_snap.get("saved_at", "?")
    lines.append(f"  Before: {old_label}")
    lines.append(f"  After:  {new_label}")
    lines.append("")

    # --- Summary ---
    sc = diff["summary_changes"]
    lines.append("-" * 64)
    lines.append("  OVERALL")
    lines.append("-" * 64)
    lines.append(
        f"  Total hours:  {sc['total_hours']['old']:.1f}h -> "
        f"{sc['total_hours']['new']:.1f}h  "
        f"({_signed(sc['total_hours']['delta'])}h)"
    )
    lines.append(
        f"  Total events: {sc['total_events']['old']} -> "
        f"{sc['total_events']['new']}  "
        f"({_signed_int(sc['total_events']['delta'])})"
    )
    lines.append(
        f"  Avg daily:    {sc['avg_daily']['old']:.1f}h -> "
        f"{sc['avg_daily']['new']:.1f}h  "
        f"({_signed(sc['avg_daily']['delta'])}h)"
    )
    lines.append("")

    # --- Category breakdown ---
    lines.append("-" * 64)
    lines.append("  CATEGORY CHANGES (sorted by biggest shift)")
    lines.append("-" * 64)
    lines.append(
        f"  {'Category':<20} {'Before':>7} {'After':>7} {'Delta':>8} {'%Chg':>8}"
    )
    lines.append(f"  {'─' * 20} {'─' * 7} {'─' * 7} {'─' * 8} {'─' * 8}")

    for c in diff["category_changes"]:
        indicator = _direction_indicator(c["delta_hours"])
        lines.append(
            f"  {c['name']:<20} {c['old_hours']:6.1f}h {c['new_hours']:6.1f}h "
            f"{_signed(c['delta_hours']):>7}h {_signed(c['delta_pct']):>6}pp {indicator}"
        )
    lines.append("")

    # --- Day-of-week changes ---
    has_day_changes = any(abs(d["delta_hours"]) >= 0.1 for d in diff["day_changes"])
    if has_day_changes:
        lines.append("-" * 64)
        lines.append("  DAY-OF-WEEK CHANGES")
        lines.append("-" * 64)
        for d in diff["day_changes"]:
            if abs(d["delta_hours"]) < 0.1:
                continue
            indicator = _direction_indicator(d["delta_hours"])
            lines.append(
                f"  {d['day']}  {d['old_hours']:5.1f}h -> {d['new_hours']:5.1f}h  "
                f"({_signed(d['delta_hours'])}h) {indicator}"
            )
        lines.append("")

    # --- Pending invites ---
    pc = diff["pending_changes"]
    any_pending_change = any(v["delta"] != 0 for v in pc.values())
    lines.append("-" * 64)
    lines.append("  PENDING INVITES")
    lines.append("-" * 64)
    if any_pending_change:
        lines.append(
            f"  Total pending:       {pc['total_pending']['old']} -> "
            f"{pc['total_pending']['new']}  ({_signed_int(pc['total_pending']['delta'])})"
        )
        lines.append(
            f"  Past unresponded:    {pc['past_unresponded']['old']} -> "
            f"{pc['past_unresponded']['new']}  ({_signed_int(pc['past_unresponded']['delta'])})"
        )
        lines.append(
            f"  Upcoming unanswered: {pc['upcoming_unresponded']['old']} -> "
            f"{pc['upcoming_unresponded']['new']}  ({_signed_int(pc['upcoming_unresponded']['delta'])})"
        )
    else:
        lines.append("  No change in pending invite counts.")
    lines.append("")

    return "\n".join(lines)


def _signed(val):
    """Format a float with explicit +/- sign."""
    return f"+{val:.1f}" if val >= 0 else f"{val:.1f}"


def _signed_int(val):
    """Format an int with explicit +/- sign."""
    return f"+{val}" if val >= 0 else f"{val}"


def _direction_indicator(delta):
    """Return a text arrow for the direction of change."""
    if delta > 0.25:
        return "^^" if delta > 2 else "^"
    elif delta < -0.25:
        return "vv" if delta < -2 else "v"
    return "="
