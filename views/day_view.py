"""Day detail dialog — activities, daily log, and checklist."""
from __future__ import annotations

from datetime import date
from typing import Callable

import customtkinter as ctk

import database as db
from views.utils import fmt_time, parse_time


class DayDialog(ctk.CTkToplevel):
    def __init__(self, master, user_id: int, d: date, on_close: Callable):
        super().__init__(master)
        self.user_id = user_id
        self.d = d
        self.d_str = d.isoformat()
        self.on_close = on_close

        self.title(d.strftime("%A, %B %d, %Y"))
        self.geometry("620x720")
        self.minsize(520, 600)
        self.protocol("WM_DELETE_WINDOW", self._close)

        self._build()
        self._load()

    def _build(self):
        container = ctk.CTkScrollableFrame(self)
        container.pack(fill="both", expand=True, padx=16, pady=16)

        ctk.CTkLabel(
            container, text=self.d.strftime("%A, %B %d, %Y"),
            font=ctk.CTkFont(size=22, weight="bold"),
        ).pack(anchor="w", pady=(0, 16))

        self._build_shifts(container)
        self._build_activities(container)
        self._build_log(container)
        self._build_checklist(container)

    # ---------- work schedule ----------

    def _build_shifts(self, parent):
        card = ctk.CTkFrame(parent, corner_radius=10)
        card.pack(fill="x", pady=8)

        ctk.CTkLabel(
            card, text="Work Schedule", font=ctk.CTkFont(size=16, weight="bold"),
        ).pack(anchor="w", padx=16, pady=(14, 6))

        self.shifts_list = ctk.CTkFrame(card, fg_color="transparent")
        self.shifts_list.pack(fill="x", padx=16, pady=(0, 8))

        add_row = ctk.CTkFrame(card, fg_color="transparent")
        add_row.pack(fill="x", padx=16, pady=(4, 14))
        add_row.grid_columnconfigure(0, weight=2)
        add_row.grid_columnconfigure(1, weight=1)
        add_row.grid_columnconfigure(2, weight=1)

        self.new_shift_label = ctk.CTkEntry(add_row, placeholder_text="Label (e.g. CC, D)")
        self.new_shift_label.grid(row=0, column=0, sticky="ew", padx=(0, 6))

        self.new_shift_start = ctk.CTkEntry(add_row, placeholder_text="Start (6:30am)")
        self.new_shift_start.grid(row=0, column=1, sticky="ew", padx=(0, 6))

        self.new_shift_end = ctk.CTkEntry(add_row, placeholder_text="End (12pm)")
        self.new_shift_end.grid(row=0, column=2, sticky="ew", padx=(0, 6))

        ctk.CTkButton(add_row, text="Add", width=60, command=self._add_shift).grid(
            row=0, column=3
        )

        for entry in (self.new_shift_label, self.new_shift_start, self.new_shift_end):
            entry.bind("<Return>", lambda e: self._add_shift())

        self.shift_msg = ctk.CTkLabel(card, text="", text_color=("#b33", "#f88"))
        self.shift_msg.pack(anchor="w", padx=16, pady=(0, 8))

    def _render_shifts(self):
        for w in self.shifts_list.winfo_children():
            w.destroy()

        shifts = db.get_shifts(self.user_id, self.d_str)
        if not shifts:
            ctk.CTkLabel(
                self.shifts_list, text="No shifts scheduled.",
                text_color=("gray50", "gray55"),
            ).pack(anchor="w", pady=4)
            return

        for s in shifts:
            self._render_shift_row(s)

    def _render_shift_row(self, s: dict):
        row = ctk.CTkFrame(self.shifts_list, fg_color=("gray92", "gray20"), corner_radius=6)
        row.pack(fill="x", pady=2)
        row.grid_columnconfigure(0, weight=2)
        row.grid_columnconfigure(1, weight=1)
        row.grid_columnconfigure(2, weight=1)

        label_e = ctk.CTkEntry(row, border_width=0, fg_color="transparent")
        label_e.insert(0, s["label"] or "")
        label_e.grid(row=0, column=0, sticky="ew", padx=(8, 4), pady=4)

        start_e = ctk.CTkEntry(row, border_width=0, fg_color="transparent")
        start_e.insert(0, fmt_time(s["start_time"]))
        start_e.grid(row=0, column=1, sticky="ew", padx=4, pady=4)

        end_e = ctk.CTkEntry(row, border_width=0, fg_color="transparent")
        end_e.insert(0, fmt_time(s["end_time"]))
        end_e.grid(row=0, column=2, sticky="ew", padx=4, pady=4)

        def save(_evt=None, sid=s["id"], le=label_e, se=start_e, ee=end_e):
            label = le.get().strip()
            if not label:
                return
            start = parse_time(se.get())
            end = parse_time(ee.get())
            db.update_shift(sid, self.user_id, label, start, end, None)

        for entry in (label_e, start_e, end_e):
            entry.bind("<FocusOut>", save)
            entry.bind("<Return>", save)

        ctk.CTkButton(
            row, text="✕", width=30, height=26,
            fg_color="transparent", text_color=("gray40", "gray60"),
            hover_color=("#f5c6c6", "#553333"),
            command=lambda sid=s["id"]: self._delete_shift(sid),
        ).grid(row=0, column=3, padx=4)

    def _add_shift(self):
        label = self.new_shift_label.get().strip()
        if not label:
            self.shift_msg.configure(text="Label is required.")
            return
        start_raw = self.new_shift_start.get().strip()
        end_raw = self.new_shift_end.get().strip()
        start = parse_time(start_raw) if start_raw else None
        end = parse_time(end_raw) if end_raw else None
        if start_raw and start is None:
            self.shift_msg.configure(text=f"Couldn't parse start time: {start_raw!r}")
            return
        if end_raw and end is None:
            self.shift_msg.configure(text=f"Couldn't parse end time: {end_raw!r}")
            return

        db.add_shift(self.user_id, self.d_str, label, start, end, None)

        self.new_shift_label.delete(0, "end")
        self.new_shift_start.delete(0, "end")
        self.new_shift_end.delete(0, "end")
        self.shift_msg.configure(text="")
        self._render_shifts()

    def _delete_shift(self, shift_id: int):
        db.delete_shift(shift_id, self.user_id)
        self._render_shifts()

    # ---------- activities ----------

    def _build_activities(self, parent):
        card = ctk.CTkFrame(parent, corner_radius=10)
        card.pack(fill="x", pady=8)

        ctk.CTkLabel(
            card, text="Activities", font=ctk.CTkFont(size=16, weight="bold"),
        ).pack(anchor="w", padx=16, pady=(14, 6))

        self.activities_list = ctk.CTkFrame(card, fg_color="transparent")
        self.activities_list.pack(fill="x", padx=16, pady=(0, 8))

        add_row = ctk.CTkFrame(card, fg_color="transparent")
        add_row.pack(fill="x", padx=16, pady=(4, 14))

        self.new_activity = ctk.CTkEntry(add_row, placeholder_text="Add activity or note…")
        self.new_activity.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.new_activity.bind("<Return>", lambda e: self._add_activity())
        ctk.CTkButton(add_row, text="Add", width=70, command=self._add_activity).pack(side="right")

    def _render_activities(self):
        for w in self.activities_list.winfo_children():
            w.destroy()

        activities = db.get_activities(self.user_id, self.d_str)
        if not activities:
            ctk.CTkLabel(
                self.activities_list, text="No activities yet.",
                text_color=("gray50", "gray55"),
            ).pack(anchor="w", pady=4)
            return

        for a in activities:
            row = ctk.CTkFrame(self.activities_list, fg_color=("gray92", "gray20"), corner_radius=6)
            row.pack(fill="x", pady=2)

            entry = ctk.CTkEntry(row, border_width=0, fg_color="transparent")
            entry.insert(0, a["activity"])
            entry.pack(side="left", fill="x", expand=True, padx=8, pady=4)
            entry.bind(
                "<FocusOut>",
                lambda e, aid=a["id"], ent=entry: self._save_activity_edit(aid, ent),
            )
            entry.bind(
                "<Return>",
                lambda e, aid=a["id"], ent=entry: self._save_activity_edit(aid, ent),
            )

            ctk.CTkButton(
                row, text="✕", width=30, height=26,
                fg_color="transparent", text_color=("gray40", "gray60"),
                hover_color=("#f5c6c6", "#553333"),
                command=lambda aid=a["id"]: self._delete_activity(aid),
            ).pack(side="right", padx=4)

    def _add_activity(self):
        text = self.new_activity.get().strip()
        if not text:
            return
        db.add_activity(self.user_id, self.d_str, text)
        self.new_activity.delete(0, "end")
        self._render_activities()

    def _save_activity_edit(self, activity_id: int, entry: ctk.CTkEntry):
        text = entry.get().strip()
        if text:
            db.update_activity(activity_id, self.user_id, text)

    def _delete_activity(self, activity_id: int):
        db.delete_activity(activity_id, self.user_id)
        self._render_activities()

    # ---------- daily log ----------

    def _build_log(self, parent):
        card = ctk.CTkFrame(parent, corner_radius=10)
        card.pack(fill="x", pady=8)

        ctk.CTkLabel(
            card, text="Daily Log", font=ctk.CTkFont(size=16, weight="bold"),
        ).pack(anchor="w", padx=16, pady=(14, 8))

        grid = ctk.CTkFrame(card, fg_color="transparent")
        grid.pack(fill="x", padx=16, pady=(0, 14))
        grid.grid_columnconfigure(1, weight=1)
        grid.grid_columnconfigure(3, weight=1)

        self.weight_entry = self._log_field(grid, "Weight (lbs)", 0, 0)
        self.calories_entry = self._log_field(grid, "Calories", 0, 2)
        self.miles_entry = self._log_field(grid, "Miles", 1, 0)
        self.jobs_entry = self._log_field(grid, "Jobs Applied", 1, 2)

        ctk.CTkButton(card, text="Save Log", command=self._save_log).pack(
            anchor="e", padx=16, pady=(0, 14)
        )

    def _log_field(self, parent, label, row, col):
        ctk.CTkLabel(parent, text=label, text_color=("gray40", "gray60")).grid(
            row=row, column=col, sticky="w", padx=(0, 8), pady=6
        )
        entry = ctk.CTkEntry(parent, width=100)
        entry.grid(row=row, column=col + 1, sticky="ew", padx=(0, 16), pady=6)
        return entry

    def _save_log(self):
        def _f(s, cast, default=None):
            s = s.strip()
            if not s:
                return default
            try:
                return cast(s)
            except ValueError:
                return default

        weight = _f(self.weight_entry.get(), float)
        calories = _f(self.calories_entry.get(), int)
        miles = _f(self.miles_entry.get(), float)
        jobs = _f(self.jobs_entry.get(), int)
        db.upsert_log(self.user_id, self.d_str, weight, calories, miles, jobs)
        self._flash_save()

    def _flash_save(self):
        # tiny visual confirmation
        lbl = ctk.CTkLabel(self, text="Saved ✓", text_color=("#2a7", "#6d8"))
        lbl.place(relx=0.5, rely=0.96, anchor="center")
        self.after(1200, lbl.destroy)

    # ---------- checklist ----------

    def _build_checklist(self, parent):
        card = ctk.CTkFrame(parent, corner_radius=10)
        card.pack(fill="x", pady=8)

        ctk.CTkLabel(
            card, text="Daily Checklist", font=ctk.CTkFont(size=16, weight="bold"),
        ).pack(anchor="w", padx=16, pady=(14, 8))

        self.checklist_container = ctk.CTkFrame(card, fg_color="transparent")
        self.checklist_container.pack(fill="x", padx=16, pady=(0, 14))

    def _render_checklist(self):
        for w in self.checklist_container.winfo_children():
            w.destroy()

        items = db.get_checklist_items(self.user_id)
        if not items:
            ctk.CTkLabel(
                self.checklist_container,
                text="No checklist items. Add some in Settings.",
                text_color=("gray50", "gray55"),
            ).pack(anchor="w", pady=4)
            return

        entries = db.get_checklist_entries(self.user_id, self.d_str)
        for item in items:
            var = ctk.BooleanVar(value=entries.get(item["id"], False))
            cb = ctk.CTkCheckBox(
                self.checklist_container,
                text=item["name"],
                variable=var,
                command=lambda iid=item["id"], v=var: db.set_checklist_entry(
                    self.user_id, iid, self.d_str, v.get()
                ),
            )
            cb.pack(anchor="w", pady=4)

    # ---------- load / close ----------

    def _load(self):
        log = db.get_log(self.user_id, self.d_str)
        if log.get("weight") is not None:
            self.weight_entry.insert(0, str(log["weight"]))
        if log.get("calories") is not None:
            self.calories_entry.insert(0, str(log["calories"]))
        if log.get("miles") is not None:
            self.miles_entry.insert(0, str(log["miles"]))
        if log.get("jobs") is not None:
            self.jobs_entry.insert(0, str(log["jobs"]))

        self._render_activities()
        self._render_checklist()
        self._render_shifts()

    def _close(self):
        # save log on close too
        self._save_log()
        self.on_close()
        self.destroy()
