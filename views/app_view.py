"""Main application shell — sidebar navigation + swappable content area."""
from __future__ import annotations

import customtkinter as ctk

import database as db
from views.budget_view import BudgetView
from views.calendar_view import CalendarView
from views.charts_view import ChartsView
from views.goals_view import GoalsView
from views.investments_view import InvestmentsView
from views.jobs_view import JobsView
from views.settings_view import SettingsView


class AppView(ctk.CTkFrame):
    def __init__(self, master, user_id: int, username: str, on_logout, on_theme_change):
        super().__init__(master, fg_color="transparent")
        self.user_id = user_id
        self.username = username
        self.on_logout = on_logout
        self.on_theme_change = on_theme_change

        self.current_view: ctk.CTkFrame | None = None
        self.nav_buttons: dict[str, ctk.CTkButton] = {}

        self._build()
        self.show("Calendar")

    # ---------- layout ----------

    def _build(self):
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Sidebar
        self.sidebar = ctk.CTkFrame(self, width=200, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsw")
        self.sidebar.grid_rowconfigure(9, weight=1)

        ctk.CTkLabel(
            self.sidebar, text="Momentum",
            font=ctk.CTkFont(size=22, weight="bold"),
        ).grid(row=0, column=0, padx=20, pady=(22, 4), sticky="w")

        ctk.CTkLabel(
            self.sidebar, text=f"@{self.username}",
            text_color=("gray40", "gray60"),
        ).grid(row=1, column=0, padx=20, pady=(0, 20), sticky="w")

        for i, name in enumerate(["Calendar", "Goals", "Jobs", "Budget", "Investments", "Stats", "Settings"], start=2):
            btn = ctk.CTkButton(
                self.sidebar, text=name, anchor="w", height=40,
                corner_radius=8, fg_color="transparent",
                text_color=("gray10", "gray90"),
                hover_color=("gray80", "gray25"),
                command=lambda n=name: self.show(n),
            )
            btn.grid(row=i, column=0, padx=10, pady=2, sticky="ew")
            self.nav_buttons[name] = btn

        ctk.CTkButton(
            self.sidebar, text="Log out", height=36,
            fg_color="transparent", text_color=("gray10", "gray90"),
            hover_color=("gray80", "gray25"),
            command=self.on_logout,
        ).grid(row=9, column=0, padx=10, pady=14, sticky="ews")

        # Content container
        self.content = ctk.CTkFrame(self, corner_radius=0, fg_color=("gray95", "gray14"))
        self.content.grid(row=0, column=1, sticky="nsew")
        self.content.grid_columnconfigure(0, weight=1)
        self.content.grid_rowconfigure(0, weight=1)

    # ---------- navigation ----------

    def show(self, name: str):
        # highlight active nav button
        for n, btn in self.nav_buttons.items():
            if n == name:
                btn.configure(fg_color=("gray85", "gray25"))
            else:
                btn.configure(fg_color="transparent")

        if self.current_view is not None:
            self.current_view.destroy()

        if name == "Calendar":
            self.current_view = CalendarView(self.content, self.user_id)
        elif name == "Goals":
            self.current_view = GoalsView(self.content, self.user_id)
        elif name == "Jobs":
            self.current_view = JobsView(self.content, self.user_id)
        elif name == "Budget":
            self.current_view = BudgetView(self.content, self.user_id)
        elif name == "Investments":
            self.current_view = InvestmentsView(self.content, self.user_id)
        elif name == "Stats":
            self.current_view = ChartsView(self.content, self.user_id)
        elif name == "Settings":
            self.current_view = SettingsView(
                self.content, self.user_id,
                on_theme_change=self.on_theme_change,
                on_checklist_change=self._refresh_if_calendar,
            )
        else:
            return
        self.current_view.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)

    def _refresh_if_calendar(self):
        # After checklist changes in Settings, refresh Calendar when user goes back.
        pass
