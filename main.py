"""Momentum — desktop app entry point."""
from __future__ import annotations

import os
import sys

import customtkinter as ctk

import database as db


def _resource(name: str) -> str:
    if getattr(sys, "frozen", False):
        return os.path.join(sys._MEIPASS, name)
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), name)
from views.app_view import AppView
from views.login_view import LoginView


class MomentumApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Momentum")
        self.geometry("1200x780")
        self.minsize(980, 640)
        try:
            self.iconbitmap(_resource("logo.ico"))
        except Exception:
            pass

        self.current_frame = None
        self.user_id: int | None = None
        self.username: str | None = None

        self._show_login()

    # ---------- navigation ----------

    def _swap(self, new_frame):
        if self.current_frame is not None:
            self.current_frame.destroy()
        self.current_frame = new_frame
        self.current_frame.pack(fill="both", expand=True)

    def _show_login(self):
        self._swap(LoginView(self, on_login=self._on_login))

    def _on_login(self, user_id: int):
        self.user_id = user_id
        user = db.get_user(user_id)
        self.username = user["username"]

        theme = user["theme"] or "dark"
        ctk.set_appearance_mode(theme)

        self._swap(AppView(
            self,
            user_id=user_id,
            username=self.username,
            on_logout=self._on_logout,
            on_theme_change=self._on_theme_change,
        ))

    def _on_logout(self):
        self.user_id = None
        self.username = None
        self._show_login()

    def _on_theme_change(self):
        # Redraw current view so matplotlib/figure colors update
        if isinstance(self.current_frame, AppView):
            # Re-show the currently active nav tab to re-render charts etc.
            active = next(
                (n for n, b in self.current_frame.nav_buttons.items()
                 if b.cget("fg_color") != "transparent"),
                "Calendar",
            )
            self.current_frame.show(active)


def main():
    db.init_db()
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")
    app = MomentumApp()
    app.mainloop()


if __name__ == "__main__":
    main()
