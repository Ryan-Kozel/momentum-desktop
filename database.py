"""SQLite database layer for Momentum.

Single source of truth for schema + queries. All UI code goes through the
functions in this module rather than running SQL directly.
"""
from __future__ import annotations

import os
import sqlite3
import sys
from contextlib import contextmanager
from datetime import date, datetime, timedelta
from typing import Any, Iterable

if getattr(sys, "frozen", False):
    _base_dir = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "Momentum")
    os.makedirs(_base_dir, exist_ok=True)
else:
    _base_dir = os.path.dirname(os.path.abspath(__file__))

DB_PATH = os.environ.get("MOMENTUM_DB", os.path.join(_base_dir, "momentum.db"))

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    username      TEXT UNIQUE NOT NULL COLLATE NOCASE,
    password_hash TEXT NOT NULL,
    salt          TEXT NOT NULL,
    theme         TEXT DEFAULT 'dark',
    created_at    TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS daily_logs (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id   INTEGER NOT NULL,
    date      TEXT NOT NULL,
    weight    REAL,
    calories  INTEGER,
    miles     REAL,
    jobs      INTEGER,
    UNIQUE(user_id, date),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS activities (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER NOT NULL,
    date       TEXT NOT NULL,
    activity   TEXT NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS checklist_items (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER NOT NULL,
    name       TEXT NOT NULL,
    sort_order INTEGER DEFAULT 0,
    active     INTEGER DEFAULT 1,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS checklist_entries (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id           INTEGER NOT NULL,
    checklist_item_id INTEGER NOT NULL,
    date              TEXT NOT NULL,
    completed         INTEGER DEFAULT 0,
    UNIQUE(user_id, checklist_item_id, date),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (checklist_item_id) REFERENCES checklist_items(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS long_term_goals (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL,
    title       TEXT NOT NULL,
    description TEXT,
    target_date TEXT,
    completed   INTEGER DEFAULT 0,
    created_at  TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS weekly_goals (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER NOT NULL,
    week_start TEXT NOT NULL,
    title      TEXT NOT NULL,
    completed  INTEGER DEFAULT 0,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS shifts (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER NOT NULL,
    date       TEXT NOT NULL,
    label      TEXT NOT NULL,
    start_time TEXT,
    end_time   TEXT,
    notes      TEXT,
    sort_order INTEGER DEFAULT 0,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS job_applications (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id      INTEGER NOT NULL,
    company      TEXT NOT NULL,
    job_title    TEXT NOT NULL,
    date_applied TEXT NOT NULL,
    salary       TEXT,
    req_link     TEXT,
    created_at   TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_logs_user_date       ON daily_logs(user_id, date);
CREATE INDEX IF NOT EXISTS idx_activities_user_date ON activities(user_id, date);
CREATE INDEX IF NOT EXISTS idx_checklist_user_date  ON checklist_entries(user_id, date);
CREATE INDEX IF NOT EXISTS idx_weekly_user_week     ON weekly_goals(user_id, week_start);
CREATE INDEX IF NOT EXISTS idx_shifts_user_date     ON shifts(user_id, date);
CREATE INDEX IF NOT EXISTS idx_jobs_user_date       ON job_applications(user_id, date_applied);

CREATE TABLE IF NOT EXISTS budget_transactions (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL,
    date        TEXT NOT NULL,
    type        TEXT NOT NULL CHECK(type IN ('income', 'expense')),
    category    TEXT NOT NULL DEFAULT '',
    description TEXT NOT NULL DEFAULT '',
    amount      REAL NOT NULL,
    created_at  TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_budget_user_date ON budget_transactions(user_id, date);

CREATE TABLE IF NOT EXISTS savings_accounts (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id          INTEGER NOT NULL,
    name             TEXT NOT NULL,
    account_type     TEXT NOT NULL DEFAULT 'savings' CHECK(account_type IN ('savings', 'debt')),
    balance          REAL NOT NULL DEFAULT 0,
    goal             REAL,
    starting_balance REAL NOT NULL DEFAULT 0,
    sort_order       INTEGER DEFAULT 0,
    created_at       TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS investment_accounts (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER NOT NULL,
    name       TEXT NOT NULL,
    sort_order INTEGER DEFAULT 0,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS investment_holdings (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id      INTEGER NOT NULL,
    ticker          TEXT NOT NULL,
    fund_name       TEXT,
    shares          REAL NOT NULL,
    amount_invested REAL NOT NULL,
    created_at      TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (account_id) REFERENCES investment_accounts(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_inv_accounts_user    ON investment_accounts(user_id);
CREATE INDEX IF NOT EXISTS idx_inv_holdings_account ON investment_holdings(account_id);
"""

DEFAULT_CHECKLIST = ["Make Bed", "Code", "Read", "Move Body", "Brush Teeth 2x"]


# ---------- connection helpers ----------

def init_db(db_path: str = DB_PATH) -> None:
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(SCHEMA)
    conn.commit()
    conn.close()


@contextmanager
def get_conn(db_path: str = DB_PATH):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ---------- week helpers ----------

def get_week_start(dt: date) -> date:
    """Return the most recent Friday on or before dt.

    The user's personal week runs Friday -> Thursday (Wed/Thu are their
    weekend). weekday(): Mon=0 ... Fri=4 ... Sun=6. We want Fri as day 0.
    """
    return dt - timedelta(days=(dt.weekday() - 4) % 7)


# ---------- user queries ----------

def get_user_by_username(username: str) -> sqlite3.Row | None:
    with get_conn() as c:
        return c.execute(
            "SELECT * FROM users WHERE username = ?", (username,)
        ).fetchone()


def get_user(user_id: int) -> sqlite3.Row | None:
    with get_conn() as c:
        return c.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()


def create_user(username: str, password_hash: str, salt: str) -> int:
    with get_conn() as c:
        cur = c.execute(
            "INSERT INTO users (username, password_hash, salt) VALUES (?, ?, ?)",
            (username, password_hash, salt),
        )
        user_id = cur.lastrowid
        # seed default checklist for new user
        for i, name in enumerate(DEFAULT_CHECKLIST):
            c.execute(
                "INSERT INTO checklist_items (user_id, name, sort_order) VALUES (?, ?, ?)",
                (user_id, name, i),
            )
        return user_id


def set_theme(user_id: int, theme: str) -> None:
    with get_conn() as c:
        c.execute("UPDATE users SET theme = ? WHERE id = ?", (theme, user_id))


# ---------- daily log queries ----------

def get_log(user_id: int, d: str) -> dict:
    with get_conn() as c:
        row = c.execute(
            "SELECT weight, calories, miles, jobs FROM daily_logs WHERE user_id = ? AND date = ?",
            (user_id, d),
        ).fetchone()
        return dict(row) if row else {}


def upsert_log(user_id: int, d: str, weight, calories, miles, jobs) -> None:
    with get_conn() as c:
        c.execute(
            """
            INSERT INTO daily_logs (user_id, date, weight, calories, miles, jobs)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id, date) DO UPDATE SET
                weight = excluded.weight,
                calories = excluded.calories,
                miles = excluded.miles,
                jobs = excluded.jobs
            """,
            (user_id, d, weight, calories, miles, jobs),
        )


def get_all_logs(user_id: int) -> list[dict]:
    with get_conn() as c:
        rows = c.execute(
            "SELECT date, weight, calories, miles, jobs FROM daily_logs WHERE user_id = ? ORDER BY date",
            (user_id,),
        ).fetchall()
        return [dict(r) for r in rows]


# ---------- activity queries ----------

def get_activities(user_id: int, d: str) -> list[dict]:
    with get_conn() as c:
        rows = c.execute(
            "SELECT id, activity FROM activities WHERE user_id = ? AND date = ? ORDER BY id",
            (user_id, d),
        ).fetchall()
        return [dict(r) for r in rows]


def add_activity(user_id: int, d: str, activity: str) -> int:
    with get_conn() as c:
        cur = c.execute(
            "INSERT INTO activities (user_id, date, activity) VALUES (?, ?, ?)",
            (user_id, d, activity),
        )
        return cur.lastrowid


def update_activity(activity_id: int, user_id: int, text: str) -> None:
    with get_conn() as c:
        c.execute(
            "UPDATE activities SET activity = ? WHERE id = ? AND user_id = ?",
            (text, activity_id, user_id),
        )


def delete_activity(activity_id: int, user_id: int) -> None:
    with get_conn() as c:
        c.execute(
            "DELETE FROM activities WHERE id = ? AND user_id = ?",
            (activity_id, user_id),
        )


# ---------- checklist queries ----------

def get_checklist_items(user_id: int, active_only: bool = True) -> list[dict]:
    with get_conn() as c:
        q = "SELECT id, name, sort_order, active FROM checklist_items WHERE user_id = ?"
        if active_only:
            q += " AND active = 1"
        q += " ORDER BY sort_order, id"
        rows = c.execute(q, (user_id,)).fetchall()
        return [dict(r) for r in rows]


def add_checklist_item(user_id: int, name: str) -> int:
    with get_conn() as c:
        max_order = c.execute(
            "SELECT COALESCE(MAX(sort_order), -1) FROM checklist_items WHERE user_id = ?",
            (user_id,),
        ).fetchone()[0]
        cur = c.execute(
            "INSERT INTO checklist_items (user_id, name, sort_order) VALUES (?, ?, ?)",
            (user_id, name, max_order + 1),
        )
        return cur.lastrowid


def rename_checklist_item(item_id: int, user_id: int, name: str) -> None:
    with get_conn() as c:
        c.execute(
            "UPDATE checklist_items SET name = ? WHERE id = ? AND user_id = ?",
            (name, item_id, user_id),
        )


def deactivate_checklist_item(item_id: int, user_id: int) -> None:
    """Soft-delete: keep history, hide from new entries."""
    with get_conn() as c:
        c.execute(
            "UPDATE checklist_items SET active = 0 WHERE id = ? AND user_id = ?",
            (item_id, user_id),
        )


def get_checklist_entries(user_id: int, d: str) -> dict[int, bool]:
    """Return {item_id: completed_bool} for a given date."""
    with get_conn() as c:
        rows = c.execute(
            "SELECT checklist_item_id, completed FROM checklist_entries WHERE user_id = ? AND date = ?",
            (user_id, d),
        ).fetchall()
        return {r["checklist_item_id"]: bool(r["completed"]) for r in rows}


def set_checklist_entry(user_id: int, item_id: int, d: str, completed: bool) -> None:
    with get_conn() as c:
        c.execute(
            """
            INSERT INTO checklist_entries (user_id, checklist_item_id, date, completed)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id, checklist_item_id, date) DO UPDATE SET
                completed = excluded.completed
            """,
            (user_id, item_id, d, 1 if completed else 0),
        )


# ---------- streak / highlight queries ----------

def compute_highlights(user_id: int) -> dict:
    """Compute stats shown on the calendar: lowest weight, weekly bests, streaks."""
    with get_conn() as c:
        logs = c.execute(
            "SELECT date, weight, calories, miles, jobs FROM daily_logs WHERE user_id = ?",
            (user_id,),
        ).fetchall()

        items = c.execute(
            "SELECT id FROM checklist_items WHERE user_id = ? AND active = 1",
            (user_id,),
        ).fetchall()
        active_item_ids = {row["id"] for row in items}

        entries = c.execute(
            "SELECT date, checklist_item_id, completed FROM checklist_entries WHERE user_id = ?",
            (user_id,),
        ).fetchall()

    # lowest weight (ignore 0)
    weights = [r["weight"] for r in logs if r["weight"] and r["weight"] > 0]
    lowest_weight = min(weights) if weights else None

    # weekly aggregates
    week_sums: dict[str, dict[str, Any]] = {}
    logged_dates = set()
    for r in logs:
        logged_dates.add(r["date"])
        dt = date.fromisoformat(r["date"])
        wk = get_week_start(dt).isoformat()
        ws = week_sums.setdefault(
            wk, {"calories": 0, "miles": 0.0, "jobs": 0, "dates": set()}
        )
        ws["dates"].add(r["date"])
        ws["calories"] += r["calories"] or 0
        ws["miles"] += r["miles"] or 0
        ws["jobs"] += r["jobs"] or 0

    lowest_cal = None
    lowest_cal_week = None
    most_miles = 0.0
    most_miles_week = None
    most_jobs = 0
    most_jobs_week = None

    for wk, s in week_sums.items():
        ws_date = date.fromisoformat(wk)
        full_week = {(ws_date + timedelta(days=i)).isoformat() for i in range(7)}
        complete = full_week.issubset(logged_dates)
        if complete and (lowest_cal is None or s["calories"] < lowest_cal):
            if s["calories"] > 0:  # skip empty weeks
                lowest_cal = s["calories"]
                lowest_cal_week = wk
        if s["miles"] > most_miles:
            most_miles = s["miles"]
            most_miles_week = wk
        if s["jobs"] > most_jobs:
            most_jobs = s["jobs"]
            most_jobs_week = wk

    # streaks — a day counts if every active checklist item is completed that day
    entries_by_date: dict[str, set[int]] = {}
    for e in entries:
        if e["completed"] and e["checklist_item_id"] in active_item_ids:
            entries_by_date.setdefault(e["date"], set()).add(e["checklist_item_id"])

    def full_day(d_str: str) -> bool:
        return bool(active_item_ids) and entries_by_date.get(d_str, set()) >= active_item_ids

    full_streak_dates = {d for d in entries_by_date if full_day(d)}

    # current streak: count back from today
    current_streak = 0
    d_cursor = date.today()
    while full_day(d_cursor.isoformat()):
        current_streak += 1
        d_cursor -= timedelta(days=1)

    # best streak: sort all full dates, count longest consecutive run
    best_streak = 0
    if full_streak_dates:
        sorted_dates = sorted(date.fromisoformat(x) for x in full_streak_dates)
        run = 1
        best_streak = 1
        for i in range(1, len(sorted_dates)):
            if (sorted_dates[i] - sorted_dates[i - 1]).days == 1:
                run += 1
                best_streak = max(best_streak, run)
            else:
                run = 1

    return {
        "lowest_weight": lowest_weight,
        "lowest_calories": lowest_cal,
        "lowest_calories_week": lowest_cal_week,
        "most_miles": most_miles,
        "most_miles_week": most_miles_week,
        "most_jobs": most_jobs,
        "most_jobs_week": most_jobs_week,
        "current_streak": current_streak,
        "best_streak": best_streak,
        "full_streak_dates": full_streak_dates,
    }


# ---------- goal queries ----------

def list_long_term_goals(user_id: int) -> list[dict]:
    with get_conn() as c:
        rows = c.execute(
            "SELECT * FROM long_term_goals WHERE user_id = ? ORDER BY completed, COALESCE(target_date, '9999'), id",
            (user_id,),
        ).fetchall()
        return [dict(r) for r in rows]


def add_long_term_goal(user_id: int, title: str, description: str, target_date: str | None) -> int:
    with get_conn() as c:
        cur = c.execute(
            "INSERT INTO long_term_goals (user_id, title, description, target_date) VALUES (?, ?, ?, ?)",
            (user_id, title, description, target_date),
        )
        return cur.lastrowid


def update_long_term_goal(goal_id: int, user_id: int, title: str, description: str, target_date: str | None) -> None:
    with get_conn() as c:
        c.execute(
            "UPDATE long_term_goals SET title = ?, description = ?, target_date = ? WHERE id = ? AND user_id = ?",
            (title, description, target_date, goal_id, user_id),
        )


def toggle_long_term_goal(goal_id: int, user_id: int, completed: bool) -> None:
    with get_conn() as c:
        c.execute(
            "UPDATE long_term_goals SET completed = ? WHERE id = ? AND user_id = ?",
            (1 if completed else 0, goal_id, user_id),
        )


def delete_long_term_goal(goal_id: int, user_id: int) -> None:
    with get_conn() as c:
        c.execute("DELETE FROM long_term_goals WHERE id = ? AND user_id = ?", (goal_id, user_id))


def list_weekly_goals(user_id: int, week_start: str) -> list[dict]:
    with get_conn() as c:
        rows = c.execute(
            "SELECT * FROM weekly_goals WHERE user_id = ? AND week_start = ? ORDER BY id",
            (user_id, week_start),
        ).fetchall()
        return [dict(r) for r in rows]


def add_weekly_goal(user_id: int, week_start: str, title: str) -> int:
    with get_conn() as c:
        cur = c.execute(
            "INSERT INTO weekly_goals (user_id, week_start, title) VALUES (?, ?, ?)",
            (user_id, week_start, title),
        )
        return cur.lastrowid


def toggle_weekly_goal(goal_id: int, user_id: int, completed: bool) -> None:
    with get_conn() as c:
        c.execute(
            "UPDATE weekly_goals SET completed = ? WHERE id = ? AND user_id = ?",
            (1 if completed else 0, goal_id, user_id),
        )


def delete_weekly_goal(goal_id: int, user_id: int) -> None:
    with get_conn() as c:
        c.execute("DELETE FROM weekly_goals WHERE id = ? AND user_id = ?", (goal_id, user_id))


# ---------- shift / work schedule queries ----------

def get_shifts(user_id: int, d: str) -> list[dict]:
    with get_conn() as c:
        rows = c.execute(
            """SELECT id, label, start_time, end_time, notes, sort_order
               FROM shifts WHERE user_id = ? AND date = ?
               ORDER BY COALESCE(start_time, '99:99'), sort_order, id""",
            (user_id, d),
        ).fetchall()
        return [dict(r) for r in rows]


def get_shifts_in_range(user_id: int, start: str, end: str) -> dict[str, list[dict]]:
    """Return {date_str: [shifts]} for every date in [start, end] that has shifts."""
    with get_conn() as c:
        rows = c.execute(
            """SELECT id, date, label, start_time, end_time, notes, sort_order
               FROM shifts WHERE user_id = ? AND date BETWEEN ? AND ?
               ORDER BY date, COALESCE(start_time, '99:99'), sort_order, id""",
            (user_id, start, end),
        ).fetchall()
    grouped: dict[str, list[dict]] = {}
    for r in rows:
        grouped.setdefault(r["date"], []).append(dict(r))
    return grouped


def add_shift(user_id: int, d: str, label: str,
              start_time: str | None, end_time: str | None,
              notes: str | None = None) -> int:
    with get_conn() as c:
        max_order = c.execute(
            "SELECT COALESCE(MAX(sort_order), -1) FROM shifts WHERE user_id = ? AND date = ?",
            (user_id, d),
        ).fetchone()[0]
        cur = c.execute(
            """INSERT INTO shifts (user_id, date, label, start_time, end_time, notes, sort_order)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (user_id, d, label, start_time, end_time, notes, max_order + 1),
        )
        return cur.lastrowid


def update_shift(shift_id: int, user_id: int, label: str,
                 start_time: str | None, end_time: str | None,
                 notes: str | None = None) -> None:
    with get_conn() as c:
        c.execute(
            """UPDATE shifts SET label = ?, start_time = ?, end_time = ?, notes = ?
               WHERE id = ? AND user_id = ?""",
            (label, start_time, end_time, notes, shift_id, user_id),
        )


def delete_shift(shift_id: int, user_id: int) -> None:
    with get_conn() as c:
        c.execute("DELETE FROM shifts WHERE id = ? AND user_id = ?", (shift_id, user_id))


# ---------- job application queries ----------

def list_job_applications(user_id: int) -> list[dict]:
    with get_conn() as c:
        rows = c.execute(
            """SELECT id, company, job_title, date_applied, salary, req_link
               FROM job_applications WHERE user_id = ?
               ORDER BY date_applied DESC, id DESC""",
            (user_id,),
        ).fetchall()
        return [dict(r) for r in rows]


def add_job_application(user_id: int, company: str, job_title: str,
                        date_applied: str, salary: str | None, req_link: str | None) -> int:
    with get_conn() as c:
        cur = c.execute(
            """INSERT INTO job_applications (user_id, company, job_title, date_applied, salary, req_link)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (user_id, company, job_title, date_applied, salary, req_link),
        )
        return cur.lastrowid


def update_job_application(app_id: int, user_id: int, company: str, job_title: str,
                           date_applied: str, salary: str | None, req_link: str | None) -> None:
    with get_conn() as c:
        c.execute(
            """UPDATE job_applications
               SET company = ?, job_title = ?, date_applied = ?, salary = ?, req_link = ?
               WHERE id = ? AND user_id = ?""",
            (company, job_title, date_applied, salary, req_link, app_id, user_id),
        )


def delete_job_application(app_id: int, user_id: int) -> None:
    with get_conn() as c:
        c.execute(
            "DELETE FROM job_applications WHERE id = ? AND user_id = ?",
            (app_id, user_id),
        )


# ---------- budget queries ----------

def list_transactions(user_id: int, year: int, month: int) -> list[dict]:
    prefix = f"{year:04d}-{month:02d}"
    with get_conn() as c:
        rows = c.execute(
            """SELECT id, date, type, category, description, amount
               FROM budget_transactions
               WHERE user_id = ? AND date LIKE ?
               ORDER BY date DESC, id DESC""",
            (user_id, f"{prefix}-%"),
        ).fetchall()
        return [dict(r) for r in rows]


def get_yearly_summary(user_id: int, year: int) -> dict:
    prefix = f"{year:04d}"
    with get_conn() as c:
        rows = c.execute(
            """SELECT type, COALESCE(SUM(amount), 0) AS total
               FROM budget_transactions
               WHERE user_id = ? AND date LIKE ?
               GROUP BY type""",
            (user_id, f"{prefix}-%"),
        ).fetchall()
    income, expenses = 0.0, 0.0
    for r in rows:
        if r["type"] == "income":
            income = r["total"]
        else:
            expenses = r["total"]
    return {"income": income, "expenses": expenses}


def get_budget_summary(user_id: int, year: int, month: int) -> dict:
    prefix = f"{year:04d}-{month:02d}"
    with get_conn() as c:
        rows = c.execute(
            """SELECT type, COALESCE(SUM(amount), 0) AS total
               FROM budget_transactions
               WHERE user_id = ? AND date LIKE ?
               GROUP BY type""",
            (user_id, f"{prefix}-%"),
        ).fetchall()
    income, expenses = 0.0, 0.0
    for r in rows:
        if r["type"] == "income":
            income = r["total"]
        else:
            expenses = r["total"]
    return {"income": income, "expenses": expenses}


def add_transaction(user_id: int, date: str, txn_type: str,
                    category: str, description: str, amount: float) -> int:
    with get_conn() as c:
        cur = c.execute(
            """INSERT INTO budget_transactions (user_id, date, type, category, description, amount)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (user_id, date, txn_type, category, description, amount),
        )
        return cur.lastrowid


def update_transaction(txn_id: int, user_id: int, date: str, txn_type: str,
                       category: str, description: str, amount: float) -> None:
    with get_conn() as c:
        c.execute(
            """UPDATE budget_transactions
               SET date = ?, type = ?, category = ?, description = ?, amount = ?
               WHERE id = ? AND user_id = ?""",
            (date, txn_type, category, description, amount, txn_id, user_id),
        )


def delete_transaction(txn_id: int, user_id: int) -> None:
    with get_conn() as c:
        c.execute(
            "DELETE FROM budget_transactions WHERE id = ? AND user_id = ?",
            (txn_id, user_id),
        )


# ---------- savings account queries ----------

def list_accounts(user_id: int) -> list[dict]:
    with get_conn() as c:
        rows = c.execute(
            "SELECT * FROM savings_accounts WHERE user_id = ? ORDER BY sort_order, id",
            (user_id,),
        ).fetchall()
        return [dict(r) for r in rows]


def add_account(user_id: int, name: str, account_type: str,
                balance: float, goal: float | None) -> int:
    with get_conn() as c:
        cur = c.execute(
            """INSERT INTO savings_accounts
               (user_id, name, account_type, balance, goal, starting_balance)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (user_id, name, account_type, balance, goal, balance),
        )
        return cur.lastrowid


def update_account(acct_id: int, user_id: int, name: str, account_type: str,
                   balance: float, goal: float | None) -> None:
    with get_conn() as c:
        c.execute(
            """UPDATE savings_accounts
               SET name = ?, account_type = ?, balance = ?, goal = ?
               WHERE id = ? AND user_id = ?""",
            (name, account_type, balance, goal, acct_id, user_id),
        )


def update_account_balance(acct_id: int, user_id: int, balance: float) -> None:
    with get_conn() as c:
        c.execute(
            "UPDATE savings_accounts SET balance = ? WHERE id = ? AND user_id = ?",
            (balance, acct_id, user_id),
        )


def delete_account(acct_id: int, user_id: int) -> None:
    with get_conn() as c:
        c.execute(
            "DELETE FROM savings_accounts WHERE id = ? AND user_id = ?",
            (acct_id, user_id),
        )


# ---------- investment account queries ----------

def list_investment_accounts(user_id: int) -> list[dict]:
    with get_conn() as c:
        rows = c.execute(
            "SELECT id, name, sort_order FROM investment_accounts WHERE user_id = ? ORDER BY sort_order, id",
            (user_id,),
        ).fetchall()
        return [dict(r) for r in rows]


def add_investment_account(user_id: int, name: str) -> int:
    with get_conn() as c:
        max_order = c.execute(
            "SELECT COALESCE(MAX(sort_order), -1) FROM investment_accounts WHERE user_id = ?",
            (user_id,),
        ).fetchone()[0]
        cur = c.execute(
            "INSERT INTO investment_accounts (user_id, name, sort_order) VALUES (?, ?, ?)",
            (user_id, name, max_order + 1),
        )
        return cur.lastrowid


def update_investment_account(acct_id: int, user_id: int, name: str) -> None:
    with get_conn() as c:
        c.execute(
            "UPDATE investment_accounts SET name = ? WHERE id = ? AND user_id = ?",
            (name, acct_id, user_id),
        )


def delete_investment_account(acct_id: int, user_id: int) -> None:
    with get_conn() as c:
        c.execute(
            "DELETE FROM investment_accounts WHERE id = ? AND user_id = ?",
            (acct_id, user_id),
        )


# ---------- investment holding queries ----------

def list_investment_holdings(account_id: int) -> list[dict]:
    with get_conn() as c:
        rows = c.execute(
            """SELECT id, account_id, ticker, fund_name, shares, amount_invested
               FROM investment_holdings WHERE account_id = ? ORDER BY id""",
            (account_id,),
        ).fetchall()
        return [dict(r) for r in rows]


def add_investment_holding(account_id: int, ticker: str, fund_name: str | None,
                           shares: float, amount_invested: float) -> int:
    with get_conn() as c:
        cur = c.execute(
            """INSERT INTO investment_holdings (account_id, ticker, fund_name, shares, amount_invested)
               VALUES (?, ?, ?, ?, ?)""",
            (account_id, ticker.upper(), fund_name, shares, amount_invested),
        )
        return cur.lastrowid


def update_investment_holding(holding_id: int, ticker: str, fund_name: str | None,
                              shares: float, amount_invested: float) -> None:
    with get_conn() as c:
        c.execute(
            """UPDATE investment_holdings
               SET ticker = ?, fund_name = ?, shares = ?, amount_invested = ?
               WHERE id = ?""",
            (ticker.upper(), fund_name, shares, amount_invested, holding_id),
        )


def delete_investment_holding(holding_id: int) -> None:
    with get_conn() as c:
        c.execute("DELETE FROM investment_holdings WHERE id = ?", (holding_id,))
