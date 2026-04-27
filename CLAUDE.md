# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Setup & Running

Requires Python 3.10+.

```bash
python -m venv .venv
.venv\Scripts\activate       # Windows
pip install -r requirements.txt
python main.py
```

## Architecture

**Entry point**: `main.py` — creates the `ctk.CTk` root window and manages the top-level auth flow. After login, swaps `LoginView` for `AppView` and passes callbacks for logout and theme changes.

**Layer separation**:
- `database.py` — single source of truth for all SQL. All views call functions here; no view runs SQL directly.
- `auth.py` — PBKDF2 password hashing; calls `database.py` only.
- `views/` — all UI code. Each view is a `ctk.CTkFrame` subclass.
  - `app_view.py` — main shell: sidebar nav buttons + a content area. Calls `show(name)` to swap the active panel.
  - `calendar_view.py` — month grid; fetches shifts and highlights in bulk via `get_shifts_in_range` and `compute_highlights`.
  - `day_view.py` — modal (Toplevel) for editing a single day: log fields, checklist, activities, shifts.
  - `goals_view.py` — long-term goals + weekly goals (Fri–Thu week grouping).
  - `charts_view.py` — Matplotlib figures embedded in tkinter via `FigureCanvasTkAgg`.
  - `settings_view.py` — theme toggle, checklist item editor, CSV export.
  - `jobs_view.py` — job application tracker.
  - `utils.py` — time string parsing and shift label formatting helpers.

**Week boundary**: The app uses **Friday → Thursday** as its week boundary everywhere (calendar grid, weekly goals, weekly stats). `database.get_week_start(dt)` returns the most recent Friday on or before a given date. Wed/Thu are the user's "weekend" and render in amber on the calendar.

**Database**: SQLite file at `momentum.db` (or `$MOMENTUM_DB` env var). `database.init_db()` is called at startup and is idempotent — safe to call on an existing DB.

**Theme**: Stored per-user in `users.theme`. Applied at login via `ctk.set_appearance_mode()`. Theme changes trigger a re-render of the active view so matplotlib charts update colors.

**Checklist items** are soft-deleted (`active = 0`) to preserve historical streak data. `compute_highlights()` in `database.py` calculates streaks, weekly bests, and lowest weight in a single pass over all logs and checklist entries.

## Data Migration

```bash
python migrate_from_json.py /path/to/old/flask/project
```

Imports users (with placeholder password `changeme`), daily logs, activities, and checklist history from the old JSON-based Flask app. Shifts are not auto-extracted from legacy activity strings.
