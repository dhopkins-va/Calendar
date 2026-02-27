# Google Calendar Analyzer

Analyze how your time is actually being spent and catch meeting invites you haven't responded to.

## What it does

1. **Time Analysis** — Categorizes all your calendar events (1:1s, team meetings, focus time, etc.) and shows a breakdown of where your hours go, by category and day of week.

2. **Pending Invites Report** — Finds every event where you haven't explicitly accepted or declined. Separates past events (you never responded and they already happened) from upcoming ones (you still have time to respond). This solves the problem where people assume you'll attend unless you explicitly decline.

## Setup

### 1. Enable the Google Calendar API

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project (or select an existing one)
3. Go to **APIs & Services > Library**
4. Search for "Google Calendar API" and enable it
5. Go to **APIs & Services > Credentials**
6. Click **Create Credentials > OAuth 2.0 Client ID**
7. Choose **Desktop application** as the application type
8. Download the JSON file and save it as `credentials.json` in this directory

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Run it

```bash
# Full report (2 weeks back and forward)
python calendar_analyzer.py

# Analyze a wider window
python calendar_analyzer.py --weeks 4

# Only pending invites
python calendar_analyzer.py --pending

# Only time breakdown
python calendar_analyzer.py --time

# Include all calendars (not just primary)
python calendar_analyzer.py --all-calendars
```

On first run, a browser window opens for Google OAuth. After that, your token is cached in `token.json`.

## Snapshots and diffing

Save snapshots over time and diff them to answer "what changed since last time?"

```bash
# Save a snapshot of the current analysis
python calendar_analyzer.py --save
python calendar_analyzer.py --save "week-of-feb-24"

# List all saved snapshots
python calendar_analyzer.py --list-snapshots

# Diff current calendar vs most recent snapshot
python calendar_analyzer.py --diff

# Diff current calendar vs a specific snapshot
python calendar_analyzer.py --diff snapshots/20260220_143000.json

# Diff two specific snapshots against each other
python calendar_analyzer.py --diff snapshots/20260213.json snapshots/20260220.json
```

The diff report shows changes in total hours, per-category shifts, day-of-week changes, and whether your pending invite count improved or worsened.

## Daily and weekly reviews

```bash
# Daily review: what's on for tomorrow + pending invites to act on
python calendar_analyzer.py daily

# Weekly review: last week vs goals + plan for the week ahead
python calendar_analyzer.py weekly
```

See [Daily and weekly review commands](#daily-and-weekly-review-commands) below for details.

## Customizing categories

On first run, a `categories.json` file is created with default categories. Edit it to match your actual meeting types:

```json
{
  "1:1": {
    "description": "One-on-one meetings",
    "patterns": ["1:1", "1-1", "one on one", "sync with"]
  },
  "Team meetings": {
    "description": "Recurring team syncs, standups, retros",
    "patterns": ["standup", "retro", "sprint", "team sync", "all hands"]
  }
}
```

Events are matched by checking if any pattern appears (case-insensitive) in the event title. Events that don't match any category go into "Other".

## Example output

```
============================================================
  TIME ANALYSIS REPORT
  (past 2 weeks + upcoming 2 weeks)
============================================================

Total scheduled time:       32.5 hours across 47 events
Average per working day:    3.3 hours
Busiest day of the week:    Tue

------------------------------------------------------------
  BREAKDOWN BY CATEGORY
------------------------------------------------------------
  1:1                      8.5h  (  9 events)   26.2%  #############
  Team meetings            7.0h  ( 12 events)   21.5%  ##########
  Other                    6.5h  ( 10 events)   20.0%  ##########
  External                 5.0h  (  6 events)   15.4%  #######
  Focus time               3.5h  (  5 events)   10.8%  #####
  Interview                2.0h  (  5 events)    6.2%  ###

============================================================
  PENDING INVITES — ACTION NEEDED
============================================================

You have 5 event(s) without an explicit accept/decline.

------------------------------------------------------------
  UPCOMING — NEEDS YOUR RESPONSE (5)
  (Others may expect you unless you explicitly decline)
------------------------------------------------------------
  [ NO RESPONSE ]  Wed Mar 04  10:00 AM (1.0h)
                    Product Review  [8 attendees]  from: alice@company.com
                    https://calendar.google.com/...
```

## Daily and weekly review commands

### `daily` — "What's on for tomorrow?"

Shows tomorrow's schedule with pending invites highlighted. Designed to run at the end of each workday.

- Lists every event for tomorrow in chronological order
- Flags events you haven't accepted/declined so you can respond before the day starts
- Shows total meeting hours and free blocks

### `weekly` — "How did last week go? How should I adjust?"

Compares last week against your time goals and previews the week ahead. Designed to run on Monday morning (or Friday afternoon).

- Shows last week's time breakdown vs your goals (set in `goals.json`)
- Highlights where you're over/under your target allocation
- Auto-saves a snapshot so you can track trends over time
- Previews the coming week's load

### Setting time goals

Create a `goals.json` to define your ideal time allocation:

```json
{
  "total_meeting_hours_per_week": 20,
  "category_targets": {
    "1:1": 5,
    "Team meetings": 4,
    "Focus time": 8,
    "External": 2,
    "Interview": 1
  }
}
```

The weekly review will compare actual hours against these targets.

## Files

| File | Purpose |
|---|---|
| `calendar_analyzer.py` | Main CLI entry point |
| `auth.py` | Google OAuth2 authentication |
| `fetch_events.py` | Fetch and normalize calendar events |
| `analyze.py` | Categorize events and compute time breakdowns |
| `pending_invites.py` | Detect unanswered invites |
| `snapshots_store.py` | Save/load analysis snapshots |
| `diff_snapshots.py` | Compare two snapshots and produce a diff report |
| `daily_review.py` | Daily "what's on tomorrow" review |
| `weekly_review.py` | Weekly retrospective and planning review |
| `categories.json` | Customizable event categories (auto-created on first run) |
| `goals.json` | Your ideal time allocation targets |
| `snapshots/` | Saved analysis snapshots (gitignored) |
