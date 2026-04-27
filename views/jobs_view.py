"""Job Applications view — track companies, roles, salary, and links."""
from __future__ import annotations

from datetime import date

import customtkinter as ctk

import database as db


class JobsView(ctk.CTkFrame):
    def __init__(self, master, user_id: int):
        super().__init__(master, fg_color="transparent")
        self.user_id = user_id

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._build_header()
        self._build_list()
        self._render()

    # ---------- layout ----------

    def _build_header(self):
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        header.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            header, text="Job Applications",
            font=ctk.CTkFont(size=24, weight="bold"),
        ).grid(row=0, column=0, sticky="w")

        ctk.CTkButton(
            header, text="+ Add Application", width=160,
            command=self._open_add_dialog,
        ).grid(row=0, column=1, sticky="e")

    def _build_list(self):
        card = ctk.CTkFrame(self, corner_radius=12)
        card.grid(row=1, column=0, sticky="nsew")
        card.grid_columnconfigure(0, weight=1)
        card.grid_rowconfigure(1, weight=1)

        # column headers
        cols = ctk.CTkFrame(card, fg_color=("gray85", "gray22"), corner_radius=8)
        cols.grid(row=0, column=0, sticky="ew", padx=12, pady=(12, 4))
        cols.grid_columnconfigure(0, weight=3)
        cols.grid_columnconfigure(1, weight=3)
        cols.grid_columnconfigure(2, weight=2)
        cols.grid_columnconfigure(3, weight=2)
        cols.grid_columnconfigure(4, weight=3)
        cols.grid_columnconfigure(5, minsize=80)

        for col, (text, idx) in enumerate([
            ("Company", 0), ("Job Title", 1), ("Date Applied", 2),
            ("Salary", 3), ("Req Link", 4), ("", 5),
        ]):
            ctk.CTkLabel(
                cols, text=text,
                font=ctk.CTkFont(size=12, weight="bold"),
                text_color=("gray30", "gray70"),
            ).grid(row=0, column=col, sticky="w", padx=10, pady=6)

        self.list_frame = ctk.CTkScrollableFrame(card, fg_color="transparent")
        self.list_frame.grid(row=1, column=0, sticky="nsew", padx=8, pady=(0, 12))
        self.list_frame.grid_columnconfigure(0, weight=1)

    def _render(self):
        for w in self.list_frame.winfo_children():
            w.destroy()

        apps = db.list_job_applications(self.user_id)
        if not apps:
            ctk.CTkLabel(
                self.list_frame,
                text="No applications yet. Click \"+ Add Application\" to get started.",
                text_color=("gray50", "gray55"),
            ).pack(anchor="w", pady=20, padx=12)
            return

        for app in apps:
            self._render_row(app)

    def _render_row(self, app: dict):
        row = ctk.CTkFrame(
            self.list_frame,
            fg_color=("gray92", "gray20"), corner_radius=8,
        )
        row.pack(fill="x", pady=3, padx=4)
        row.grid_columnconfigure(0, weight=3)
        row.grid_columnconfigure(1, weight=3)
        row.grid_columnconfigure(2, weight=2)
        row.grid_columnconfigure(3, weight=2)
        row.grid_columnconfigure(4, weight=3)
        row.grid_columnconfigure(5, minsize=80)

        ctk.CTkLabel(
            row, text=app["company"],
            font=ctk.CTkFont(size=13, weight="bold"),
            anchor="w",
        ).grid(row=0, column=0, sticky="ew", padx=10, pady=8)

        ctk.CTkLabel(row, text=app["job_title"] or "—", anchor="w").grid(
            row=0, column=1, sticky="ew", padx=10)

        ctk.CTkLabel(row, text=app["date_applied"] or "—", anchor="w").grid(
            row=0, column=2, sticky="ew", padx=10)

        ctk.CTkLabel(row, text=app["salary"] or "—", anchor="w").grid(
            row=0, column=3, sticky="ew", padx=10)

        link_text = app["req_link"] or "—"
        if app["req_link"]:
            link_lbl = ctk.CTkLabel(
                row, text=link_text, anchor="w",
                text_color=("#1a73e8", "#7ab4f5"),
                cursor="hand2",
            )
            link_lbl.grid(row=0, column=4, sticky="ew", padx=10)
            link_lbl.bind("<Button-1>", lambda e, url=app["req_link"]: self._open_url(url))
        else:
            ctk.CTkLabel(row, text="—", anchor="w").grid(
                row=0, column=4, sticky="ew", padx=10)

        btn_frame = ctk.CTkFrame(row, fg_color="transparent")
        btn_frame.grid(row=0, column=5, padx=6, pady=4)

        ctk.CTkButton(
            btn_frame, text="Edit", width=38, height=26,
            fg_color="transparent", text_color=("gray30", "gray70"),
            hover_color=("gray80", "gray30"),
            command=lambda a=app: self._open_edit_dialog(a),
        ).pack(side="left", padx=2)

        ctk.CTkButton(
            btn_frame, text="✕", width=28, height=26,
            fg_color="transparent", text_color=("gray40", "gray60"),
            hover_color=("#f5c6c6", "#553333"),
            command=lambda aid=app["id"]: self._delete(aid),
        ).pack(side="left", padx=2)

    # ---------- actions ----------

    def _open_add_dialog(self):
        _AppDialog(self, self.user_id, app=None, on_save=self._render)

    def _open_edit_dialog(self, app: dict):
        _AppDialog(self, self.user_id, app=app, on_save=self._render)

    def _delete(self, app_id: int):
        db.delete_job_application(app_id, self.user_id)
        self._render()

    @staticmethod
    def _open_url(url: str):
        import webbrowser
        webbrowser.open(url)


class _AppDialog(ctk.CTkToplevel):
    """Add / edit a job application."""

    def __init__(self, master, user_id: int, app: dict | None, on_save):
        super().__init__(master)
        self.user_id = user_id
        self.app = app
        self.on_save = on_save

        self.title("Edit Application" if app else "Add Application")
        self.geometry("480x360")
        self.resizable(False, False)
        self.grab_set()

        self._build()
        if app:
            self._populate(app)

    def _build(self):
        frame = ctk.CTkFrame(self, fg_color="transparent")
        frame.pack(fill="both", expand=True, padx=24, pady=20)
        frame.grid_columnconfigure(1, weight=1)

        fields = [
            ("Company *", "company"),
            ("Job Title *", "job_title"),
            ("Date Applied (YYYY-MM-DD) *", "date_applied"),
            ("Salary", "salary"),
            ("Job Req Link", "req_link"),
        ]

        self._entries: dict[str, ctk.CTkEntry] = {}
        for i, (label, key) in enumerate(fields):
            ctk.CTkLabel(frame, text=label, anchor="w").grid(
                row=i, column=0, sticky="w", padx=(0, 12), pady=6)
            entry = ctk.CTkEntry(frame, width=260)
            entry.grid(row=i, column=1, sticky="ew", pady=6)
            self._entries[key] = entry

        self.err_label = ctk.CTkLabel(frame, text="", text_color=("#b33", "#f88"))
        self.err_label.grid(row=len(fields), column=0, columnspan=2, sticky="w", pady=(4, 0))

        btn_row = ctk.CTkFrame(frame, fg_color="transparent")
        btn_row.grid(row=len(fields) + 1, column=0, columnspan=2, pady=(12, 0), sticky="e")

        ctk.CTkButton(btn_row, text="Cancel", width=90,
                      fg_color="transparent", border_width=1,
                      text_color=("gray10", "gray90"),
                      hover_color=("gray85", "gray25"),
                      command=self.destroy).pack(side="left", padx=(0, 8))

        ctk.CTkButton(btn_row, text="Save", width=90,
                      command=self._save).pack(side="left")

    def _populate(self, app: dict):
        self._entries["company"].insert(0, app["company"] or "")
        self._entries["job_title"].insert(0, app["job_title"] or "")
        self._entries["date_applied"].insert(0, app["date_applied"] or "")
        self._entries["salary"].insert(0, app["salary"] or "")
        self._entries["req_link"].insert(0, app["req_link"] or "")

    def _save(self):
        company = self._entries["company"].get().strip()
        job_title = self._entries["job_title"].get().strip()
        date_applied = self._entries["date_applied"].get().strip()
        salary = self._entries["salary"].get().strip() or None
        req_link = self._entries["req_link"].get().strip() or None

        if not company or not job_title:
            self.err_label.configure(text="Company and Job Title are required.")
            return

        if not date_applied:
            date_applied = date.today().isoformat()
        else:
            try:
                date.fromisoformat(date_applied)
            except ValueError:
                self.err_label.configure(text="Date must be YYYY-MM-DD.")
                return

        if self.app:
            db.update_job_application(
                self.app["id"], self.user_id,
                company, job_title, date_applied, salary, req_link,
            )
        else:
            db.add_job_application(
                self.user_id, company, job_title, date_applied, salary, req_link,
            )

        self.on_save()
        self.destroy()
