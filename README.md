# Momentum Desktop

Personal productivity & goal tracker built as a Python desktop app.

Migrated from the original Flask web version with the following upgrades:

- **CustomTkinter UI** with dark/light themes
- **SQLite** storage (from JSON files)
- **PBKDF2** password hashing (from plain SHA-256)
- **Matplotlib charts** for weight / calories / miles / jobs trends
- **Long-term & weekly goals** (Fri–Thu week grouping)
- **Editable & deletable activities** (previously append-only)
- **Customizable daily checklist** per user
- **Work schedule** — shifts (label + start/end time) shown directly on each calendar cell
- **Fri → Thu week** boundary for weekly goals and all weekly stats (Wed/Thu rendered in amber)
- **CSV export** for daily logs and activities
- **Budget tracker** — savings/debt accounts with progress tracking, monthly income/expense transactions, and yearly overview
- **Job application tracker** — log applications with status, company, role, and notes

---

## Setup

Requires Python 3.10+.

```bash
python -m venv .venv
.venv\Scripts\activate       # Windows
pip install -r requirements.txt
python main.py
```

---

## Work Schedule

Open any day by clicking its cell. The **Work Schedule** section takes a short label (e.g. `CC`, `D`) and optional start/end times. Times are forgiving — all of these parse fine:

- `6:30am`, `6am`, `6:30`, `06:30`, `6:30 pm`, `7:15pm`, `12pm`

Shifts show on the calendar as `CC 6:30a-12p` under the day number. Up to three shifts per day are shown; extras collapse to `+N more`.

---

## Week boundary

This build uses a **Friday → Thursday** week across the app:

- Calendar grid starts each row on Friday
- Weekly goals group under a Friday week-start
- "Best Achievements" weekly stats bucket days into Fri–Thu weeks

Daily streak behavior is unchanged — a day counts toward the streak if all active checklist items are completed, regardless of day of the week.

---

## Migrating data from the old Flask app

```bash
python migrate_from_json.py /path/to/old/flask/project
```

1. Creates users with a placeholder password: `changeme`
2. Imports all daily logs, activities, and checklist history

**After migrating, log in with `changeme` and change your password.**

> Shifts are not auto-extracted from legacy activity strings — you can retype them as proper shifts.

---

## Building the executable

```bash
pip install pyinstaller
pyinstaller --noconfirm Momentum.spec
```

Output is at `dist/Momentum.exe`. The database (`momentum.db`) is created next to the exe on first run.

---

## Project Structure

```
momentum_desktop_v2/
├── main.py                  # Entry point — root window, auth flow
├── database.py              # SQLite schema + all data queries
├── auth.py                  # PBKDF2 password hashing
├── migrate_from_json.py     # One-time migration from old Flask project
├── Momentum.spec            # PyInstaller build spec
├── requirements.txt
└── views/
    ├── app_view.py          # Main shell — sidebar nav + content area
    ├── calendar_view.py     # Month grid with shifts + achievements panel
    ├── day_view.py          # Modal for editing a single day
    ├── goals_view.py        # Long-term + weekly goals
    ├── charts_view.py       # Matplotlib trend charts
    ├── budget_view.py       # Savings/debt accounts + income/expense tracking
    ├── jobs_view.py         # Job application tracker
    ├── settings_view.py     # Theme, checklist editor, CSV export
    └── utils.py             # Time parsing + shift formatting helpers
```

---

## Ideas for future iterations

- Recurring shift templates (e.g. "every Mon 6:30am–12pm")
- Hours-worked totals per week and month
- Change-password dialog
- Reminders / notifications (system tray icon)
- Drag-to-reorder checklist items and shifts
- Per-habit streak tracking (not just all-items-completed)
- Correlations view (weight vs. miles, etc.)
- Backup/restore DB from the Settings page
