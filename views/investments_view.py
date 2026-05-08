"""Investments view — track accounts and holdings with live prices via yfinance."""
from __future__ import annotations

import threading

import customtkinter as ctk

import database as db

# Column layout shared between header and data rows
_COL_WEIGHTS   = (0, 1, 0, 0, 0, 0, 0)
_COL_MINSIZES  = (85, 140, 105, 115, 150, 140, 78)
_COL_HEADERS   = ("Ticker", "Fund Name", "Invested", "Current", "Gain / Loss", "Today", "")


def _configure_cols(frame: ctk.CTkFrame) -> None:
    for i, (w, ms) in enumerate(zip(_COL_WEIGHTS, _COL_MINSIZES)):
        frame.grid_columnconfigure(i, weight=w, minsize=ms)


def _gain_color(value: float) -> tuple:
    return ("#1a7a3c", "#4caf7d") if value >= 0 else ("#b33", "#f88")


class InvestmentsView(ctk.CTkFrame):
    def __init__(self, master, user_id: int):
        super().__init__(master, fg_color="transparent")
        self.user_id = user_id
        self._quotes: dict[str, dict] = {}
        self._loading = False

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        self._build_header()
        self._build_body()
        self._render()
        self._refresh_quotes()

    # ---------- layout ----------

    def _build_header(self):
        hdr = ctk.CTkFrame(self, fg_color="transparent")
        hdr.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        hdr.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            hdr, text="Investments",
            font=ctk.CTkFont(size=24, weight="bold"),
        ).grid(row=0, column=0, sticky="w")

        btn_row = ctk.CTkFrame(hdr, fg_color="transparent")
        btn_row.grid(row=0, column=1, sticky="e")

        self._refresh_btn = ctk.CTkButton(
            btn_row, text="↻ Refresh", width=110,
            command=self._refresh_quotes,
        )
        self._refresh_btn.pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            btn_row, text="+ Add Account", width=130,
            command=self._open_add_account,
        ).pack(side="left")

    def _build_body(self):
        self._summary_frame = ctk.CTkFrame(self, corner_radius=10)
        self._summary_frame.grid(row=1, column=0, sticky="ew", pady=(0, 12))

        self._scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self._scroll.grid(row=2, column=0, sticky="nsew")
        self._scroll.grid_columnconfigure(0, weight=1)

    # ---------- rendering ----------

    def _render(self):
        for w in self._summary_frame.winfo_children():
            w.destroy()
        for w in self._scroll.winfo_children():
            w.destroy()

        accounts = db.list_investment_accounts(self.user_id)

        total_invested = 0.0
        total_current = 0.0
        total_day_chg = 0.0
        for acct in accounts:
            for h in db.list_investment_holdings(acct["id"]):
                total_invested += h["amount_invested"]
                q = self._quotes.get(h["ticker"].upper())
                if q:
                    total_current += h["shares"] * q["price"]
                    total_day_chg += h["shares"] * q["day_change"]

        self._render_summary(total_invested, total_current, total_day_chg)

        if not accounts:
            ctk.CTkLabel(
                self._scroll,
                text='No accounts yet. Click "+ Add Account" to get started.',
                text_color=("gray50", "gray55"),
            ).pack(anchor="w", pady=20, padx=4)
            return

        for acct in accounts:
            self._render_account_card(acct)

    def _render_summary(self, total_invested: float, total_current: float, total_day_chg: float):
        frm = self._summary_frame
        frm.grid_columnconfigure((0, 1, 2, 3), weight=1)

        def stat(col: int, label: str, value: str, color=None):
            cell = ctk.CTkFrame(frm, fg_color="transparent")
            cell.grid(row=0, column=col, padx=20, pady=12, sticky="w")
            ctk.CTkLabel(
                cell, text=label,
                text_color=("gray40", "gray60"),
                font=ctk.CTkFont(size=11),
            ).pack(anchor="w")
            lbl = ctk.CTkLabel(cell, text=value, font=ctk.CTkFont(size=18, weight="bold"))
            if color:
                lbl.configure(text_color=color)
            lbl.pack(anchor="w")

        if self._quotes and total_current:
            gain = total_current - total_invested
            gain_pct = (gain / total_invested * 100) if total_invested else 0
            prev = total_current - total_day_chg
            day_pct = (total_day_chg / prev * 100) if prev else 0

            stat(0, "Portfolio Value", f"${total_current:,.2f}")
            stat(1, "Total Invested", f"${total_invested:,.2f}")
            stat(2, "Total Gain / Loss",
                 f"{'+'if gain>=0 else ''}{gain:,.2f}  ({gain_pct:+.2f}%)",
                 color=_gain_color(gain))
            stat(3, "Today's Change",
                 f"{'+'if total_day_chg>=0 else ''}{total_day_chg:,.2f}  ({day_pct:+.2f}%)",
                 color=_gain_color(total_day_chg))
        else:
            stat(0, "Portfolio Value", "Loading..." if self._loading else "—")
            stat(1, "Total Invested", f"${total_invested:,.2f}")
            stat(2, "Total Gain / Loss", "—")
            stat(3, "Today's Change", "—")

    def _render_account_card(self, acct: dict):
        holdings = db.list_investment_holdings(acct["id"])
        acct_invested = sum(h["amount_invested"] for h in holdings)
        acct_current = sum(
            h["shares"] * self._quotes[h["ticker"].upper()]["price"]
            for h in holdings if h["ticker"].upper() in self._quotes
        )
        acct_day = sum(
            h["shares"] * self._quotes[h["ticker"].upper()]["day_change"]
            for h in holdings if h["ticker"].upper() in self._quotes
        )

        card = ctk.CTkFrame(self._scroll, corner_radius=12)
        card.pack(fill="x", pady=(0, 12))
        card.grid_columnconfigure(0, weight=1)

        # account header bar
        hdr = ctk.CTkFrame(card, fg_color=("gray85", "gray22"), corner_radius=8)
        hdr.grid(row=0, column=0, sticky="ew", padx=12, pady=(12, 6))
        hdr.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            hdr, text=acct["name"],
            font=ctk.CTkFont(size=15, weight="bold"),
        ).grid(row=0, column=0, padx=12, pady=8, sticky="w")

        stats = ctk.CTkFrame(hdr, fg_color="transparent")
        stats.grid(row=0, column=1, padx=8, sticky="w")

        if self._quotes and acct_current:
            gain = acct_current - acct_invested
            gain_pct = (gain / acct_invested * 100) if acct_invested else 0
            prev = acct_current - acct_day
            day_pct = (acct_day / prev * 100) if prev else 0
            for text, kw in [
                (f"${acct_current:,.2f}", {"font": ctk.CTkFont(size=13, weight="bold")}),
                (f"   Invested: ${acct_invested:,.2f}", {"text_color": ("gray40", "gray60")}),
                (f"   {'+'if gain>=0 else ''}{gain:,.2f} ({gain_pct:+.2f}%)", {"text_color": _gain_color(gain)}),
                (f"   Today: {'+'if acct_day>=0 else ''}{acct_day:,.2f} ({day_pct:+.2f}%)", {"text_color": _gain_color(acct_day)}),
            ]:
                ctk.CTkLabel(stats, text=text, **kw).pack(side="left")
        else:
            ctk.CTkLabel(
                stats,
                text=f"Invested: ${acct_invested:,.2f}",
                text_color=("gray40", "gray60"),
            ).pack(side="left")

        btn_cell = ctk.CTkFrame(hdr, fg_color="transparent")
        btn_cell.grid(row=0, column=2, padx=6, pady=4)
        ctk.CTkButton(
            btn_cell, text="Edit", width=38, height=26,
            fg_color="transparent", text_color=("gray30", "gray70"),
            hover_color=("gray80", "gray30"),
            command=lambda a=acct: self._open_edit_account(a),
        ).pack(side="left", padx=2)
        ctk.CTkButton(
            btn_cell, text="✕", width=28, height=26,
            fg_color="transparent", text_color=("gray40", "gray60"),
            hover_color=("#f5c6c6", "#553333"),
            command=lambda aid=acct["id"]: self._delete_account(aid),
        ).pack(side="left", padx=2)

        if holdings:
            # column headers
            col_hdr = ctk.CTkFrame(card, fg_color="transparent")
            col_hdr.grid(row=1, column=0, sticky="ew", padx=16, pady=(2, 0))
            _configure_cols(col_hdr)
            for i, text in enumerate(_COL_HEADERS):
                ctk.CTkLabel(
                    col_hdr, text=text,
                    font=ctk.CTkFont(size=11, weight="bold"),
                    text_color=("gray30", "gray70"),
                    anchor="w",
                ).grid(row=0, column=i, sticky="ew", padx=4, pady=(4, 0))

            # holding rows
            rows_frame = ctk.CTkFrame(card, fg_color="transparent")
            rows_frame.grid(row=2, column=0, sticky="ew", padx=12, pady=(0, 4))
            rows_frame.grid_columnconfigure(0, weight=1)
            for h in holdings:
                self._render_holding_row(rows_frame, h)
            add_row = 3
        else:
            add_row = 1

        ctk.CTkButton(
            card, text="+ Add Holding", height=30,
            fg_color="transparent", border_width=1,
            text_color=("gray30", "gray70"),
            hover_color=("gray85", "gray25"),
            command=lambda aid=acct["id"]: self._open_add_holding(aid),
        ).grid(row=add_row, column=0, padx=16, pady=(4, 12), sticky="w")

    def _render_holding_row(self, parent: ctk.CTkFrame, h: dict):
        q = self._quotes.get(h["ticker"].upper())
        current_val = h["shares"] * q["price"] if q else None
        day_chg = h["shares"] * q["day_change"] if q else None
        day_pct = q["day_change_pct"] if q else None
        gain = (current_val - h["amount_invested"]) if current_val is not None else None
        gain_pct = (gain / h["amount_invested"] * 100) if gain is not None and h["amount_invested"] else None
        fund_name = h.get("fund_name") or h["ticker"].upper()
        blank = "..." if self._loading else "—"

        row = ctk.CTkFrame(parent, fg_color=("gray92", "gray20"), corner_radius=8)
        row.pack(fill="x", pady=2)
        _configure_cols(row)

        ctk.CTkLabel(
            row, text=h["ticker"].upper(),
            font=ctk.CTkFont(size=13, weight="bold"), anchor="w",
        ).grid(row=0, column=0, padx=10, pady=8, sticky="w")

        ctk.CTkLabel(
            row, text=fund_name, anchor="w",
            text_color=("gray40", "gray60"),
        ).grid(row=0, column=1, padx=4, pady=8, sticky="ew")

        ctk.CTkLabel(
            row, text=f"${h['amount_invested']:,.2f}", anchor="w",
        ).grid(row=0, column=2, padx=4, pady=8, sticky="w")

        ctk.CTkLabel(
            row,
            text=f"${current_val:,.2f}" if current_val is not None else blank,
            anchor="w",
        ).grid(row=0, column=3, padx=4, pady=8, sticky="w")

        g_col = _gain_color(gain) if gain is not None else ("gray50", "gray55")
        g_text = (f"{'+'if gain>=0 else ''}{gain:,.2f} ({gain_pct:+.2f}%)"
                  if gain is not None and gain_pct is not None else blank)
        ctk.CTkLabel(row, text=g_text, anchor="w", text_color=g_col).grid(
            row=0, column=4, padx=4, pady=8, sticky="w")

        d_col = _gain_color(day_chg) if day_chg is not None else ("gray50", "gray55")
        d_text = (f"{'+'if day_chg>=0 else ''}{day_chg:,.2f} ({day_pct:+.2f}%)"
                  if day_chg is not None and day_pct is not None else blank)
        ctk.CTkLabel(row, text=d_text, anchor="w", text_color=d_col).grid(
            row=0, column=5, padx=4, pady=8, sticky="w")

        btn_cell = ctk.CTkFrame(row, fg_color="transparent")
        btn_cell.grid(row=0, column=6, padx=6, pady=4)
        ctk.CTkButton(
            btn_cell, text="Edit", width=38, height=26,
            fg_color="transparent", text_color=("gray30", "gray70"),
            hover_color=("gray80", "gray30"),
            command=lambda hh=h: self._open_edit_holding(hh),
        ).pack(side="left", padx=2)
        ctk.CTkButton(
            btn_cell, text="✕", width=28, height=26,
            fg_color="transparent", text_color=("gray40", "gray60"),
            hover_color=("#f5c6c6", "#553333"),
            command=lambda hid=h["id"]: self._delete_holding(hid),
        ).pack(side="left", padx=2)

    # ---------- quote fetching ----------

    def _refresh_quotes(self):
        if self._loading:
            return

        accounts = db.list_investment_accounts(self.user_id)
        tickers = list({
            h["ticker"].upper()
            for acct in accounts
            for h in db.list_investment_holdings(acct["id"])
        })
        if not tickers:
            return

        self._loading = True
        self._refresh_btn.configure(text="Loading...", state="disabled")

        def fetch():
            try:
                import yfinance as yf
                quotes = {}
                for t in tickers:
                    try:
                        hist = yf.Ticker(t).history(period="2d")
                        if not hist.empty:
                            price = float(hist["Close"].iloc[-1])
                            prev = float(hist["Close"].iloc[-2]) if len(hist) >= 2 else price
                            day_chg = price - prev
                            day_pct = (day_chg / prev * 100) if prev else 0
                            quotes[t] = {"price": price, "day_change": day_chg, "day_change_pct": day_pct}
                    except Exception:
                        pass
            except Exception:
                quotes = {}
            self.after(0, lambda q=quotes: self._on_quotes_loaded(q))

        threading.Thread(target=fetch, daemon=True).start()

    def _on_quotes_loaded(self, quotes: dict):
        if not self.winfo_exists():
            return
        self._quotes = quotes
        self._loading = False
        self._refresh_btn.configure(text="↻ Refresh", state="normal")
        self._render()

    # ---------- account actions ----------

    def _open_add_account(self):
        _AccountDialog(self, self.user_id, acct=None, on_save=self._render)

    def _open_edit_account(self, acct: dict):
        _AccountDialog(self, self.user_id, acct=acct, on_save=self._render)

    def _delete_account(self, acct_id: int):
        db.delete_investment_account(acct_id, self.user_id)
        self._render()

    # ---------- holding actions ----------

    def _open_add_holding(self, account_id: int):
        _HoldingDialog(self, account_id=account_id, holding=None, on_save=self._render)

    def _open_edit_holding(self, holding: dict):
        q = self._quotes.get(holding["ticker"].upper())
        hint = holding["shares"] * q["price"] if q else None
        _HoldingDialog(self, account_id=holding["account_id"], holding=holding,
                       current_value_hint=hint, on_save=self._render)

    def _delete_holding(self, holding_id: int):
        db.delete_investment_holding(holding_id)
        self._render()


# ---------- dialogs ----------

class _AccountDialog(ctk.CTkToplevel):
    def __init__(self, master, user_id: int, acct: dict | None, on_save):
        super().__init__(master)
        self.user_id = user_id
        self.acct = acct
        self.on_save = on_save

        self.title("Edit Account" if acct else "Add Account")
        self.geometry("360x190")
        self.resizable(False, False)
        self.grab_set()

        self._build()
        if acct:
            self._name_entry.insert(0, acct["name"])

    def _build(self):
        frm = ctk.CTkFrame(self, fg_color="transparent")
        frm.pack(fill="both", expand=True, padx=24, pady=20)
        frm.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(frm, text="Account Name *", anchor="w").grid(
            row=0, column=0, sticky="w", padx=(0, 12), pady=8)
        self._name_entry = ctk.CTkEntry(frm, width=200, placeholder_text="e.g. Roth IRA")
        self._name_entry.grid(row=0, column=1, sticky="ew", pady=8)

        self._err_lbl = ctk.CTkLabel(frm, text="", text_color=("#b33", "#f88"))
        self._err_lbl.grid(row=1, column=0, columnspan=2, sticky="w")

        btn_row = ctk.CTkFrame(frm, fg_color="transparent")
        btn_row.grid(row=2, column=0, columnspan=2, sticky="e", pady=(12, 0))
        ctk.CTkButton(
            btn_row, text="Cancel", width=90,
            fg_color="transparent", border_width=1,
            text_color=("gray10", "gray90"),
            hover_color=("gray85", "gray25"),
            command=self.destroy,
        ).pack(side="left", padx=(0, 8))
        ctk.CTkButton(btn_row, text="Save", width=90, command=self._save).pack(side="left")

    def _save(self):
        name = self._name_entry.get().strip()
        if not name:
            self._err_lbl.configure(text="Account name is required.")
            return
        if self.acct:
            db.update_investment_account(self.acct["id"], self.user_id, name)
        else:
            db.add_investment_account(self.user_id, name)
        self.on_save()
        self.destroy()


class _HoldingDialog(ctk.CTkToplevel):
    def __init__(self, master, account_id: int, holding: dict | None,
                 current_value_hint: float | None = None, on_save=None):
        super().__init__(master)
        self.account_id = account_id
        self.holding = holding
        self.on_save = on_save

        self.title("Edit Holding" if holding else "Add Holding")
        self.geometry("430x295")
        self.resizable(False, False)
        self.grab_set()

        self._build()
        if holding:
            self._entries["ticker"].insert(0, holding["ticker"].upper())
            self._entries["amount"].insert(0, f"{holding['amount_invested']:.2f}")
            if current_value_hint is not None:
                self._entries["current"].insert(0, f"{current_value_hint:.2f}")

    def _build(self):
        frm = ctk.CTkFrame(self, fg_color="transparent")
        frm.pack(fill="both", expand=True, padx=24, pady=20)
        frm.grid_columnconfigure(1, weight=1)

        self._entries: dict[str, ctk.CTkEntry] = {}
        fields = [
            ("Ticker Symbol *",       "ticker",  "e.g. FNILX"),
            ("Amount Invested ($) *", "amount",  "e.g. 999.81"),
            ("Current Value ($) *",   "current", "What it's worth today"),
        ]
        for i, (label, key, placeholder) in enumerate(fields):
            ctk.CTkLabel(frm, text=label, anchor="w").grid(
                row=i, column=0, sticky="w", padx=(0, 12), pady=6)
            entry = ctk.CTkEntry(frm, width=230, placeholder_text=placeholder)
            entry.grid(row=i, column=1, sticky="ew", pady=6)
            self._entries[key] = entry

        self._err_lbl = ctk.CTkLabel(frm, text="", text_color=("#b33", "#f88"), wraplength=370)
        self._err_lbl.grid(row=len(fields), column=0, columnspan=2, sticky="w", pady=(4, 0))

        btn_row = ctk.CTkFrame(frm, fg_color="transparent")
        btn_row.grid(row=len(fields) + 1, column=0, columnspan=2, sticky="e", pady=(12, 0))
        ctk.CTkButton(
            btn_row, text="Cancel", width=90,
            fg_color="transparent", border_width=1,
            text_color=("gray10", "gray90"),
            hover_color=("gray85", "gray25"),
            command=self.destroy,
        ).pack(side="left", padx=(0, 8))
        self._save_btn = ctk.CTkButton(btn_row, text="Save", width=90, command=self._save)
        self._save_btn.pack(side="left")

    def _save(self):
        ticker = self._entries["ticker"].get().strip().upper()
        amount_str = self._entries["amount"].get().strip().replace("$", "").replace(",", "")
        current_str = self._entries["current"].get().strip().replace("$", "").replace(",", "")

        if not ticker or not amount_str or not current_str:
            self._err_lbl.configure(text="All fields are required.")
            return
        try:
            amount = float(amount_str)
            current = float(current_str)
        except ValueError:
            self._err_lbl.configure(text="Amount and current value must be numbers.")
            return
        if amount <= 0 or current <= 0:
            self._err_lbl.configure(text="Amounts must be greater than zero.")
            return

        self._save_btn.configure(text="Saving...", state="disabled")
        self._err_lbl.configure(text="")

        def fetch_and_save():
            try:
                import yfinance as yf
                data = yf.Ticker(ticker)
                hist = data.history(period="2d")
                if hist.empty:
                    self.after(0, lambda: self._err_lbl.configure(
                        text=f"No price data found for '{ticker}'. Check the ticker symbol."))
                    self.after(0, lambda: self._save_btn.configure(text="Save", state="normal"))
                    return
                price = float(hist["Close"].iloc[-1])
                shares = current / price
                try:
                    info = data.info
                    fund_name = info.get("longName") or info.get("shortName") or ticker
                except Exception:
                    fund_name = ticker
                self.after(0, lambda: self._commit(ticker, fund_name, shares, amount))
            except Exception as exc:
                self.after(0, lambda: self._err_lbl.configure(text=f"Error fetching price: {exc}"))
                self.after(0, lambda: self._save_btn.configure(text="Save", state="normal"))

        threading.Thread(target=fetch_and_save, daemon=True).start()

    def _commit(self, ticker: str, fund_name: str, shares: float, amount: float):
        if not self.winfo_exists():
            return
        if self.holding:
            db.update_investment_holding(self.holding["id"], ticker, fund_name, shares, amount)
        else:
            db.add_investment_holding(self.account_id, ticker, fund_name, shares, amount)
        if self.on_save:
            self.on_save()
        self.destroy()
