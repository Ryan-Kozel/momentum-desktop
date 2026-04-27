"""Calendar view — month grid with streak highlighting, work shifts, achievements."""
from __future__ import annotations

import calendar as pycalendar
from datetime import date, timedelta

import customtkinter as ctk

import database as db
from views.day_view import DayDialog
from views.utils import fmt_shift


class CalendarView(ctk.CTkFrame):
    def __init__(self, master, user_id: int):
        super().__init__(master, fg_color="transparent")
        self.user_id = user_id
        today = date.today()
        self.year = today.year
        self.month = today.month

        self.grid_columnconfigure(0, weight=2)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._build_header()
        self._build_body()
        self._refresh()

    def _build_header(self):
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 10))

        self.title_label = ctk.CTkLabel(
            header, text="", font=ctk.CTkFont(size=26, weight="bold")
        )
        self.title_label.pack(side="left")

        nav = ctk.CTkFrame(header, fg_color="transparent")
        nav.pack(side="right")
        ctk.CTkButton(nav, text="◀", width=40, command=self._prev_month).pack(side="left", padx=4)
        ctk.CTkButton(nav, text="Today", width=80, command=self._goto_today).pack(side="left", padx=4)
        ctk.CTkButton(nav, text="▶", width=40, command=self._next_month).pack(side="left", padx=4)

    def _build_body(self):
        self.grid_frame = ctk.CTkFrame(self, corner_radius=12)
        self.grid_frame.grid(row=1, column=0, sticky="nsew", padx=(0, 10))

        self.highlights_frame = ctk.CTkScrollableFrame(
            self, corner_radius=12, label_text="Best Achievements"
        )
        self.highlights_frame.grid(row=1, column=1, sticky="nsew")

    # ---------- navigation ----------

    def _prev_month(self):
        self.month -= 1
        if self.month == 0:
            self.month = 12
            self.year -= 1
        self._refresh()

    def _next_month(self):
        self.month += 1
        if self.month == 13:
            self.month = 1
            self.year += 1
        self._refresh()

    def _goto_today(self):
        t = date.today()
        self.year, self.month = t.year, t.month
        self._refresh()

    # ---------- render ----------

    def _refresh(self):
        month_name = pycalendar.month_name[self.month]
        self.title_label.configure(text=f"{month_name} {self.year}")
        self._render_grid()
        self._render_highlights()

    def _render_grid(self):
        for w in self.grid_frame.winfo_children():
            w.destroy()

        # Friday-first week (user's personal week = Fri -> Thu)
        cal = pycalendar.Calendar(firstweekday=pycalendar.FRIDAY)
        weeks = cal.monthdayscalendar(self.year, self.month)
        weekday_names = ["Fri", "Sat", "Sun", "Mon", "Tue", "Wed", "Thu"]
        # Wed/Thu are the user's "weekend" — highlight the column headers differently
        weekend_cols = {5, 6}  # indices of Wed, Thu in the new ordering

        today = date.today()
        highlights = db.compute_highlights(self.user_id)
        full_dates: set[str] = highlights["full_streak_dates"]

        # Pull shifts for the whole visible month in one query
        first = f"{self.year:04d}-{self.month:02d}-01"
        if self.month == 12:
            next_first = date(self.year + 1, 1, 1)
        else:
            next_first = date(self.year, self.month + 1, 1)
        last = (next_first - timedelta(days=1)).isoformat()
        shifts_by_date = db.get_shifts_in_range(self.user_id, first, last)

        # Header row
        for col in range(7):
            self.grid_frame.grid_columnconfigure(col, weight=1, uniform="day")
            is_weekend = col in weekend_cols
            ctk.CTkLabel(
                self.grid_frame, text=weekday_names[col],
                font=ctk.CTkFont(size=12, weight="bold"),
                text_color=("#b45309", "#f59e0b") if is_weekend else ("gray40", "gray60"),
            ).grid(row=0, column=col, padx=4, pady=(10, 4), sticky="n")

        for r, week in enumerate(weeks, start=1):
            self.grid_frame.grid_rowconfigure(r, weight=1, uniform="week")
            for c, day in enumerate(week):
                if day == 0:
                    empty = ctk.CTkFrame(self.grid_frame, fg_color="transparent")
                    empty.grid(row=r, column=c, padx=3, pady=3, sticky="nsew")
                    continue

                d_str = f"{self.year:04d}-{self.month:02d}-{day:02d}"
                is_today = (today.year == self.year and today.month == self.month and today.day == day)
                is_full = d_str in full_dates
                day_shifts = shifts_by_date.get(d_str, [])

                self._build_day_cell(
                    parent=self.grid_frame, row=r, col=c, day=day,
                    d_str=d_str, is_today=is_today, is_full=is_full,
                    shifts=day_shifts,
                )

    def _build_day_cell(self, *, parent, row, col, day, d_str, is_today, is_full, shifts):
        if is_full:
            base = ("#c8e6c9", "#2e5d3a")
            hover = ("#b8dcb9", "#3a7050")
        elif is_today:
            base = ("#cfe2ff", "#1e3a5f")
            hover = ("#bcd4f5", "#2a4a75")
        else:
            base = ("gray88", "gray22")
            hover = ("gray80", "gray28")

        cell = ctk.CTkFrame(parent, fg_color=base, corner_radius=8)
        cell.grid(row=row, column=col, padx=3, pady=3, sticky="nsew")

        day_lbl = ctk.CTkLabel(
            cell, text=str(day),
            font=ctk.CTkFont(size=15, weight="bold" if is_today else "normal"),
            text_color=("gray10", "gray95"),
        )
        day_lbl.pack(anchor="nw", padx=8, pady=(4, 0))

        children = [day_lbl]

        # Show up to 3 shifts; collapse the rest into "+N more"
        max_shifts = 3
        for s in shifts[:max_shifts]:
            lbl = ctk.CTkLabel(
                cell, text=fmt_shift(s),
                font=ctk.CTkFont(size=11),
                text_color=("#1e40af", "#93c5fd"),
                anchor="w",
            )
            lbl.pack(anchor="w", padx=8)
            children.append(lbl)

        if len(shifts) > max_shifts:
            more_lbl = ctk.CTkLabel(
                cell, text=f"+{len(shifts) - max_shifts} more",
                font=ctk.CTkFont(size=10),
                text_color=("gray40", "gray60"),
            )
            more_lbl.pack(anchor="w", padx=8)
            children.append(more_lbl)

        # Make whole cell clickable (including its children)
        def on_click(_evt=None, ds=d_str):
            self._open_day(ds)

        def on_enter(_evt=None):
            cell.configure(fg_color=hover)

        def on_leave(_evt=None):
            cell.configure(fg_color=base)

        for w in (cell, *children):
            w.bind("<Button-1>", on_click)
            w.bind("<Enter>", on_enter)
            w.bind("<Leave>", on_leave)
            try:
                w.configure(cursor="hand2")
            except Exception:
                pass

    def _render_highlights(self):
        for w in self.highlights_frame.winfo_children():
            w.destroy()

        h = db.compute_highlights(self.user_id)

        def row(label, value):
            frame = ctk.CTkFrame(self.highlights_frame, fg_color="transparent")
            frame.pack(fill="x", padx=8, pady=6)
            ctk.CTkLabel(
                frame, text=label, text_color=("gray40", "gray60"),
                font=ctk.CTkFont(size=12),
            ).pack(anchor="w")
            ctk.CTkLabel(
                frame, text=value,
                font=ctk.CTkFont(size=16, weight="bold"),
            ).pack(anchor="w")

        row("Current Streak", f"{h['current_streak']} days")
        row("Best Streak", f"{h['best_streak']} days")

        if h["lowest_weight"] is not None:
            row("Lowest Weight", f"{h['lowest_weight']:.1f} lbs")

        if h["lowest_calories_week"]:
            row(
                "Lowest Weekly Calories",
                f"{h['lowest_calories']} (wk of {_pretty(h['lowest_calories_week'])})",
            )

        if h["most_miles_week"]:
            row(
                "Most Weekly Miles",
                f"{h['most_miles']:.2f} (wk of {_pretty(h['most_miles_week'])})",
            )

        if h["most_jobs_week"]:
            row(
                "Most Weekly Jobs",
                f"{h['most_jobs']} (wk of {_pretty(h['most_jobs_week'])})",
            )

    def _open_day(self, d_str: str):
        d = date.fromisoformat(d_str)
        dlg = DayDialog(self, self.user_id, d, on_close=self._refresh)
        dlg.grab_set()


def _pretty(iso: str) -> str:
    return date.fromisoformat(iso).strftime("%b %d, %Y")
