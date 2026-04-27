"""Goals view — long-term goals and week-by-week weekly goals."""
from __future__ import annotations

from datetime import date, timedelta

import customtkinter as ctk

import database as db


class GoalsView(ctk.CTkFrame):
    def __init__(self, master, user_id: int):
        super().__init__(master, fg_color="transparent")
        self.user_id = user_id
        self.week_start = db.get_week_start(date.today())

        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._build_long_term()
        self._build_weekly()

    # ---------- long-term ----------

    def _build_long_term(self):
        card = ctk.CTkFrame(self, corner_radius=12)
        card.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        card.grid_rowconfigure(2, weight=1)
        card.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            card, text="Long-term Goals",
            font=ctk.CTkFont(size=20, weight="bold"),
        ).grid(row=0, column=0, sticky="w", padx=16, pady=(16, 4))

        add_row = ctk.CTkFrame(card, fg_color="transparent")
        add_row.grid(row=1, column=0, sticky="ew", padx=16, pady=(6, 10))
        add_row.grid_columnconfigure(0, weight=1)

        self.lt_entry = ctk.CTkEntry(add_row, placeholder_text="New long-term goal…")
        self.lt_entry.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        self.lt_entry.bind("<Return>", lambda e: self._add_long_term())

        self.lt_date = ctk.CTkEntry(add_row, placeholder_text="Target (YYYY-MM-DD)", width=160)
        self.lt_date.grid(row=0, column=1, padx=(0, 8))

        ctk.CTkButton(add_row, text="Add", width=60, command=self._add_long_term).grid(row=0, column=2)

        self.lt_list = ctk.CTkScrollableFrame(card, fg_color="transparent")
        self.lt_list.grid(row=2, column=0, sticky="nsew", padx=10, pady=(0, 14))

        self._render_long_term()

    def _render_long_term(self):
        for w in self.lt_list.winfo_children():
            w.destroy()

        goals = db.list_long_term_goals(self.user_id)
        if not goals:
            ctk.CTkLabel(
                self.lt_list, text="No long-term goals yet. Add one above.",
                text_color=("gray50", "gray55"),
            ).pack(anchor="w", pady=10, padx=8)
            return

        for g in goals:
            row = ctk.CTkFrame(self.lt_list, fg_color=("gray92", "gray20"), corner_radius=8)
            row.pack(fill="x", pady=4, padx=4)

            var = ctk.BooleanVar(value=bool(g["completed"]))
            cb = ctk.CTkCheckBox(
                row, text="", variable=var, width=24,
                command=lambda gid=g["id"], v=var: (
                    db.toggle_long_term_goal(gid, self.user_id, v.get()),
                    self._render_long_term(),
                ),
            )
            cb.pack(side="left", padx=(10, 4), pady=8)

            text_frame = ctk.CTkFrame(row, fg_color="transparent")
            text_frame.pack(side="left", fill="x", expand=True, padx=4)

            title_color = ("gray40", "gray55") if g["completed"] else ("gray10", "gray95")
            ctk.CTkLabel(
                text_frame, text=g["title"],
                font=ctk.CTkFont(size=14, weight="bold"),
                text_color=title_color,
            ).pack(anchor="w")

            if g["target_date"]:
                ctk.CTkLabel(
                    text_frame, text=f"by {g['target_date']}",
                    text_color=("gray50", "gray55"), font=ctk.CTkFont(size=12),
                ).pack(anchor="w")

            ctk.CTkButton(
                row, text="✕", width=30, height=26,
                fg_color="transparent", text_color=("gray40", "gray60"),
                hover_color=("#f5c6c6", "#553333"),
                command=lambda gid=g["id"]: (
                    db.delete_long_term_goal(gid, self.user_id),
                    self._render_long_term(),
                ),
            ).pack(side="right", padx=8)

    def _add_long_term(self):
        title = self.lt_entry.get().strip()
        if not title:
            return
        target = self.lt_date.get().strip() or None
        if target:
            try:
                date.fromisoformat(target)
            except ValueError:
                target = None
        db.add_long_term_goal(self.user_id, title, "", target)
        self.lt_entry.delete(0, "end")
        self.lt_date.delete(0, "end")
        self._render_long_term()

    # ---------- weekly ----------

    def _build_weekly(self):
        card = ctk.CTkFrame(self, corner_radius=12)
        card.grid(row=0, column=1, sticky="nsew")
        card.grid_rowconfigure(3, weight=1)
        card.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            card, text="Weekly Goals",
            font=ctk.CTkFont(size=20, weight="bold"),
        ).grid(row=0, column=0, sticky="w", padx=16, pady=(16, 4))

        nav = ctk.CTkFrame(card, fg_color="transparent")
        nav.grid(row=1, column=0, sticky="ew", padx=16, pady=(4, 8))
        ctk.CTkButton(nav, text="◀", width=36, command=lambda: self._shift_week(-7)).pack(side="left", padx=2)
        self.week_label = ctk.CTkLabel(nav, text="", font=ctk.CTkFont(size=13, weight="bold"))
        self.week_label.pack(side="left", padx=10)
        ctk.CTkButton(nav, text="▶", width=36, command=lambda: self._shift_week(7)).pack(side="left", padx=2)
        ctk.CTkButton(nav, text="This week", width=90,
                      command=self._goto_this_week).pack(side="right")

        add_row = ctk.CTkFrame(card, fg_color="transparent")
        add_row.grid(row=2, column=0, sticky="ew", padx=16, pady=(0, 10))
        add_row.grid_columnconfigure(0, weight=1)

        self.wk_entry = ctk.CTkEntry(add_row, placeholder_text="Goal for this week…")
        self.wk_entry.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        self.wk_entry.bind("<Return>", lambda e: self._add_weekly())
        ctk.CTkButton(add_row, text="Add", width=60, command=self._add_weekly).grid(row=0, column=1)

        self.wk_list = ctk.CTkScrollableFrame(card, fg_color="transparent")
        self.wk_list.grid(row=3, column=0, sticky="nsew", padx=10, pady=(0, 14))

        self._render_weekly()

    def _shift_week(self, days: int):
        self.week_start = self.week_start + timedelta(days=days)
        self._render_weekly()

    def _goto_this_week(self):
        self.week_start = db.get_week_start(date.today())
        self._render_weekly()

    def _render_weekly(self):
        week_end = self.week_start + timedelta(days=6)
        self.week_label.configure(
            text=f"{self.week_start.strftime('%b %d')} – {week_end.strftime('%b %d, %Y')}"
        )

        for w in self.wk_list.winfo_children():
            w.destroy()

        goals = db.list_weekly_goals(self.user_id, self.week_start.isoformat())
        if not goals:
            ctk.CTkLabel(
                self.wk_list, text="No goals for this week yet.",
                text_color=("gray50", "gray55"),
            ).pack(anchor="w", pady=10, padx=8)
            return

        for g in goals:
            row = ctk.CTkFrame(self.wk_list, fg_color=("gray92", "gray20"), corner_radius=8)
            row.pack(fill="x", pady=4, padx=4)

            var = ctk.BooleanVar(value=bool(g["completed"]))
            ctk.CTkCheckBox(
                row, text=g["title"], variable=var,
                command=lambda gid=g["id"], v=var: (
                    db.toggle_weekly_goal(gid, self.user_id, v.get()),
                    self._render_weekly(),
                ),
            ).pack(side="left", padx=10, pady=8, fill="x", expand=True)

            ctk.CTkButton(
                row, text="✕", width=30, height=26,
                fg_color="transparent", text_color=("gray40", "gray60"),
                hover_color=("#f5c6c6", "#553333"),
                command=lambda gid=g["id"]: (
                    db.delete_weekly_goal(gid, self.user_id),
                    self._render_weekly(),
                ),
            ).pack(side="right", padx=8)

    def _add_weekly(self):
        title = self.wk_entry.get().strip()
        if not title:
            return
        db.add_weekly_goal(self.user_id, self.week_start.isoformat(), title)
        self.wk_entry.delete(0, "end")
        self._render_weekly()
