"""Settings — checklist customization, theme toggle, CSV export."""
from __future__ import annotations

import csv
from datetime import datetime
from tkinter import filedialog, messagebox
from typing import Callable

import customtkinter as ctk

import database as db


class SettingsView(ctk.CTkFrame):
    def __init__(self, master, user_id: int, on_theme_change: Callable,
                 on_checklist_change: Callable):
        super().__init__(master, fg_color="transparent")
        self.user_id = user_id
        self.on_theme_change = on_theme_change
        self.on_checklist_change = on_checklist_change

        self.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            self, text="Settings",
            font=ctk.CTkFont(size=26, weight="bold"),
        ).grid(row=0, column=0, sticky="w", pady=(0, 14))

        self._build_appearance()
        self._build_checklist()
        self._build_export()

    # ---------- appearance ----------

    def _build_appearance(self):
        card = ctk.CTkFrame(self, corner_radius=12)
        card.grid(row=1, column=0, sticky="ew", pady=6)

        ctk.CTkLabel(
            card, text="Appearance",
            font=ctk.CTkFont(size=16, weight="bold"),
        ).pack(anchor="w", padx=16, pady=(14, 4))

        row = ctk.CTkFrame(card, fg_color="transparent")
        row.pack(fill="x", padx=16, pady=(0, 14))

        ctk.CTkLabel(row, text="Theme").pack(side="left", padx=(0, 10))
        current = ctk.get_appearance_mode().capitalize()
        seg = ctk.CTkSegmentedButton(
            row, values=["Light", "Dark", "System"],
            command=self._change_theme,
        )
        seg.set(current if current in ("Light", "Dark", "System") else "Dark")
        seg.pack(side="left")

    def _change_theme(self, value: str):
        ctk.set_appearance_mode(value.lower())
        db.set_theme(self.user_id, value.lower())
        self.on_theme_change()

    # ---------- checklist ----------

    def _build_checklist(self):
        card = ctk.CTkFrame(self, corner_radius=12)
        card.grid(row=2, column=0, sticky="ew", pady=6)
        card.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            card, text="Daily Checklist Items",
            font=ctk.CTkFont(size=16, weight="bold"),
        ).grid(row=0, column=0, sticky="w", padx=16, pady=(14, 4))
        ctk.CTkLabel(
            card, text="These are the habits tracked each day. Removing an item keeps past history intact.",
            text_color=("gray40", "gray60"),
        ).grid(row=1, column=0, sticky="w", padx=16, pady=(0, 8))

        self.checklist_list = ctk.CTkFrame(card, fg_color="transparent")
        self.checklist_list.grid(row=2, column=0, sticky="ew", padx=10)

        add_row = ctk.CTkFrame(card, fg_color="transparent")
        add_row.grid(row=3, column=0, sticky="ew", padx=16, pady=14)
        add_row.grid_columnconfigure(0, weight=1)

        self.new_item = ctk.CTkEntry(add_row, placeholder_text="Add a new habit…")
        self.new_item.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        self.new_item.bind("<Return>", lambda e: self._add_item())
        ctk.CTkButton(add_row, text="Add", width=60, command=self._add_item).grid(row=0, column=1)

        self._render_checklist()

    def _render_checklist(self):
        for w in self.checklist_list.winfo_children():
            w.destroy()

        items = db.get_checklist_items(self.user_id)
        if not items:
            ctk.CTkLabel(
                self.checklist_list,
                text="No checklist items yet — add some below.",
                text_color=("gray50", "gray55"),
            ).pack(anchor="w", pady=6, padx=6)
            return

        for item in items:
            row = ctk.CTkFrame(self.checklist_list, fg_color=("gray92", "gray20"), corner_radius=8)
            row.pack(fill="x", pady=3, padx=4)

            entry = ctk.CTkEntry(row, border_width=0, fg_color="transparent")
            entry.insert(0, item["name"])
            entry.pack(side="left", fill="x", expand=True, padx=8, pady=6)
            entry.bind(
                "<FocusOut>",
                lambda e, iid=item["id"], ent=entry: self._rename_item(iid, ent),
            )
            entry.bind(
                "<Return>",
                lambda e, iid=item["id"], ent=entry: self._rename_item(iid, ent),
            )

            ctk.CTkButton(
                row, text="Remove", width=80, height=26,
                fg_color="transparent", text_color=("gray40", "gray60"),
                hover_color=("#f5c6c6", "#553333"),
                command=lambda iid=item["id"]: self._remove_item(iid),
            ).pack(side="right", padx=6)

    def _add_item(self):
        name = self.new_item.get().strip()
        if not name:
            return
        db.add_checklist_item(self.user_id, name)
        self.new_item.delete(0, "end")
        self._render_checklist()
        self.on_checklist_change()

    def _rename_item(self, item_id: int, entry: ctk.CTkEntry):
        name = entry.get().strip()
        if name:
            db.rename_checklist_item(item_id, self.user_id, name)
            self.on_checklist_change()

    def _remove_item(self, item_id: int):
        db.deactivate_checklist_item(item_id, self.user_id)
        self._render_checklist()
        self.on_checklist_change()

    # ---------- export ----------

    def _build_export(self):
        card = ctk.CTkFrame(self, corner_radius=12)
        card.grid(row=3, column=0, sticky="ew", pady=6)

        ctk.CTkLabel(
            card, text="Export Data",
            font=ctk.CTkFont(size=16, weight="bold"),
        ).pack(anchor="w", padx=16, pady=(14, 4))
        ctk.CTkLabel(
            card, text="Download your logs and activities as CSV files.",
            text_color=("gray40", "gray60"),
        ).pack(anchor="w", padx=16, pady=(0, 10))

        btns = ctk.CTkFrame(card, fg_color="transparent")
        btns.pack(anchor="w", padx=16, pady=(0, 14))
        ctk.CTkButton(btns, text="Export Daily Logs", command=self._export_logs).pack(side="left", padx=(0, 10))
        ctk.CTkButton(btns, text="Export Activities", command=self._export_activities).pack(side="left")

    def _export_logs(self):
        logs = db.get_all_logs(self.user_id)
        if not logs:
            messagebox.showinfo("Export", "No daily logs to export yet.")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            initialfile=f"momentum_logs_{datetime.now():%Y%m%d}.csv",
            filetypes=[("CSV file", "*.csv")],
        )
        if not path:
            return
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["date", "weight", "calories", "miles", "jobs"])
            for r in logs:
                w.writerow([r["date"], r.get("weight"), r.get("calories"),
                            r.get("miles"), r.get("jobs")])
        messagebox.showinfo("Export", f"Saved {len(logs)} rows to\n{path}")

    def _export_activities(self):
        # gather all activities via a single pass
        with db.get_conn() as c:
            rows = c.execute(
                "SELECT date, activity FROM activities WHERE user_id = ? ORDER BY date, id",
                (self.user_id,),
            ).fetchall()

        if not rows:
            messagebox.showinfo("Export", "No activities to export yet.")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            initialfile=f"momentum_activities_{datetime.now():%Y%m%d}.csv",
            filetypes=[("CSV file", "*.csv")],
        )
        if not path:
            return
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["date", "activity"])
            for r in rows:
                w.writerow([r["date"], r["activity"]])
        messagebox.showinfo("Export", f"Saved {len(rows)} rows to\n{path}")
