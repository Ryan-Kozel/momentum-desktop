"""Stats / charts view — matplotlib trends embedded in CustomTkinter."""
from __future__ import annotations

from datetime import date, datetime

import customtkinter as ctk
import matplotlib
matplotlib.use("TkAgg")
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

import database as db


class ChartsView(ctk.CTkFrame):
    def __init__(self, master, user_id: int):
        super().__init__(master, fg_color="transparent")
        self.user_id = user_id

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", pady=(0, 10))

        ctk.CTkLabel(
            header, text="Trends",
            font=ctk.CTkFont(size=26, weight="bold"),
        ).pack(side="left")

        self.metric = ctk.CTkSegmentedButton(
            header, values=["Weight", "Calories", "Miles", "Jobs"],
            command=self._render,
        )
        self.metric.set("Weight")
        self.metric.pack(side="right")

        self.chart_frame = ctk.CTkFrame(self, corner_radius=12)
        self.chart_frame.grid(row=1, column=0, sticky="nsew")

        self._mpl_canvas = None
        self._render("Weight")

    def _render(self, metric: str):
        for w in self.chart_frame.winfo_children():
            w.destroy()

        logs = db.get_all_logs(self.user_id)
        key = metric.lower()

        # Pull valid points. For weight, treat 0 as "no entry".
        points: list[tuple[date, float]] = []
        for r in logs:
            val = r.get(key)
            if val is None:
                continue
            if key == "weight" and val == 0:
                continue
            try:
                points.append((date.fromisoformat(r["date"]), float(val)))
            except (ValueError, TypeError):
                continue
        points.sort()

        if not points:
            ctk.CTkLabel(
                self.chart_frame,
                text=f"No {metric.lower()} data yet. Log some days to see a trend here.",
                text_color=("gray50", "gray55"),
                font=ctk.CTkFont(size=14),
            ).pack(pady=40)
            return

        # Figure with theme-matched background
        is_dark = ctk.get_appearance_mode().lower() == "dark"
        bg = "#1f1f1f" if is_dark else "#f5f5f5"
        fg = "#e5e5e5" if is_dark else "#222222"
        grid_c = "#444" if is_dark else "#ccc"
        line_c = "#4aa3ff" if is_dark else "#0066cc"

        fig = Figure(figsize=(7, 4), dpi=100, facecolor=bg)
        ax = fig.add_subplot(111)
        ax.set_facecolor(bg)

        xs = [p[0] for p in points]
        ys = [p[1] for p in points]

        ax.plot(xs, ys, marker="o", linewidth=2, markersize=5, color=line_c)
        ax.set_title(f"{metric} over time", color=fg, fontsize=14, pad=12)
        ax.set_ylabel(metric, color=fg)
        ax.tick_params(colors=fg)
        ax.grid(True, color=grid_c, alpha=0.4, linestyle="--")
        for spine in ax.spines.values():
            spine.set_color(grid_c)

        fig.autofmt_xdate()
        fig.tight_layout()

        self._mpl_canvas = FigureCanvasTkAgg(fig, master=self.chart_frame)
        self._mpl_canvas.draw()
        self._mpl_canvas.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=10)

        # summary stats strip
        stats = ctk.CTkFrame(self.chart_frame, fg_color="transparent")
        stats.pack(fill="x", padx=10, pady=(0, 10))

        def stat(label, value):
            col = ctk.CTkFrame(stats, fg_color=("gray92", "gray20"), corner_radius=8)
            col.pack(side="left", padx=4, fill="x", expand=True)
            ctk.CTkLabel(col, text=label, text_color=("gray40", "gray60"),
                         font=ctk.CTkFont(size=11)).pack(pady=(6, 0))
            ctk.CTkLabel(col, text=value,
                         font=ctk.CTkFont(size=14, weight="bold")).pack(pady=(0, 6))

        fmt = (lambda v: f"{v:.1f}") if key in ("weight", "miles") else (lambda v: f"{int(v)}")
        stat("Entries", str(len(ys)))
        stat("Min", fmt(min(ys)))
        stat("Max", fmt(max(ys)))
        stat("Avg", fmt(sum(ys) / len(ys)))
        if len(ys) >= 2:
            stat("Change", fmt(ys[-1] - ys[0]))
