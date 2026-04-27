"""Budget view — savings accounts and monthly income/expense tracking."""
from __future__ import annotations

from datetime import date, datetime

import customtkinter as ctk

import database as db


class BudgetView(ctk.CTkFrame):
    def __init__(self, master, user_id: int):
        super().__init__(master, fg_color="transparent")
        self.user_id = user_id
        today = date.today()
        self._year = today.year
        self._month = today.month

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(5, weight=1)

        self._build_accounts_header()   # row 0
        self._build_accounts_body()     # row 1
        self._build_yearly_overview()   # row 2
        self._build_txn_header()        # row 3
        self._build_summary()           # row 4
        self._build_txn_list()          # row 5 — expands

        self._render_accounts()
        self._render_transactions()

    # ── accounts section ───────────────────────────────────────────────────────

    def _build_accounts_header(self):
        hdr = ctk.CTkFrame(self, fg_color="transparent")
        hdr.grid(row=0, column=0, sticky="ew", pady=(0, 6))
        hdr.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            hdr, text="Accounts",
            font=ctk.CTkFont(size=18, weight="bold"),
        ).grid(row=0, column=0, sticky="w")
        ctk.CTkButton(
            hdr, text="+ Add Account", width=130,
            command=self._open_add_account,
        ).grid(row=0, column=1, sticky="e")

    def _build_accounts_body(self):
        self.accounts_frame = ctk.CTkScrollableFrame(
            self, orientation="horizontal", height=170, fg_color="transparent",
        )
        self.accounts_frame.grid(row=1, column=0, sticky="ew", pady=(0, 14))

    def _render_accounts(self):
        for w in self.accounts_frame.winfo_children():
            w.destroy()

        accounts = db.list_accounts(self.user_id)
        if not accounts:
            ctk.CTkLabel(
                self.accounts_frame,
                text='No accounts yet. Click "+ Add Account" to get started.',
                text_color=("gray50", "gray55"),
            ).pack(side="left", padx=12, pady=20)
            return

        for acct in accounts:
            self._render_account_card(acct)

    def _render_account_card(self, acct: dict):
        is_debt = acct["account_type"] == "debt"
        bal_color = ("#c62828", "#ef9a9a") if is_debt else ("gray10", "gray90")

        card = ctk.CTkFrame(
            self.accounts_frame, fg_color=("gray92", "gray20"),
            corner_radius=10, width=210,
        )
        card.pack(side="left", padx=6, pady=4, fill="y")
        card.pack_propagate(False)

        ctk.CTkLabel(
            card, text=acct["name"],
            font=ctk.CTkFont(size=13, weight="bold"), anchor="w",
        ).pack(anchor="w", padx=12, pady=(10, 2))

        ctk.CTkLabel(
            card, text=f"${acct['balance']:,.2f}",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=bal_color, anchor="w",
        ).pack(anchor="w", padx=12)

        goal = acct["goal"]
        if goal is not None:
            progress = self._account_progress(acct)
            pct = round(progress * 100, 1)
            pct_str = f"{pct:.0f}%" if pct == int(pct) else f"{pct:.1f}%"
            label = (
                f"{pct_str} paid off  (goal ${goal:,.0f})"
                if is_debt
                else f"{pct_str} of ${goal:,.0f}"
            )
            ctk.CTkLabel(
                card, text=label, font=ctk.CTkFont(size=11),
                text_color=("gray40", "gray60"), anchor="w",
            ).pack(anchor="w", padx=12, pady=(2, 2))
            bar_color = ("#c62828", "#ef9a9a") if is_debt else ("#2e7d32", "#81c784")
            bar = ctk.CTkProgressBar(card, progress_color=bar_color, height=8)
            bar.set(progress)
            bar.pack(fill="x", padx=12, pady=(0, 6))
        else:
            ctk.CTkLabel(
                card, text="No goal set", font=ctk.CTkFont(size=11),
                text_color=("gray50", "gray55"),
            ).pack(anchor="w", padx=12, pady=(2, 8))

        btn_row = ctk.CTkFrame(card, fg_color="transparent")
        btn_row.pack(anchor="w", padx=8, pady=(0, 8))

        ctk.CTkButton(
            btn_row, text="Update", width=60, height=24,
            fg_color="transparent", border_width=1,
            text_color=("gray10", "gray90"), hover_color=("gray80", "gray30"),
            command=lambda a=acct: self._open_update_balance(a),
        ).pack(side="left", padx=2)
        ctk.CTkButton(
            btn_row, text="Edit", width=50, height=24,
            fg_color="transparent", border_width=1,
            text_color=("gray10", "gray90"), hover_color=("gray80", "gray30"),
            command=lambda a=acct: self._open_edit_account(a),
        ).pack(side="left", padx=2)
        ctk.CTkButton(
            btn_row, text="✕", width=28, height=24,
            fg_color="transparent", text_color=("gray40", "gray60"),
            hover_color=("#f5c6c6", "#553333"),
            command=lambda aid=acct["id"]: self._delete_account(aid),
        ).pack(side="left", padx=2)

    @staticmethod
    def _account_progress(acct: dict) -> float:
        balance = acct["balance"] or 0.0
        goal = acct["goal"]
        starting = acct["starting_balance"] or 0.0
        if goal is None:
            return 0.0
        if acct["account_type"] == "savings":
            if goal <= 0:
                return 1.0 if balance >= goal else 0.0
            return max(0.0, min(1.0, balance / goal))
        # debt: goal = amount to pay off; progress = how much paid / goal
        if goal <= 0:
            return 0.0
        amount_paid = max(0.0, starting - balance)
        return max(0.0, min(1.0, amount_paid / goal))

    # ── yearly overview section ────────────────────────────────────────────────

    def _build_yearly_overview(self):
        container = ctk.CTkFrame(self, fg_color="transparent")
        container.grid(row=2, column=0, sticky="ew", pady=(0, 14))
        container.grid_columnconfigure(0, weight=1)

        self._year_title = ctk.CTkLabel(
            container, text="",
            font=ctk.CTkFont(size=15, weight="bold"), anchor="w",
        )
        self._year_title.grid(row=0, column=0, sticky="w", pady=(0, 6))

        cards = ctk.CTkFrame(container, fg_color="transparent")
        cards.grid(row=1, column=0, sticky="ew")
        cards.grid_columnconfigure((0, 1, 2), weight=1)
        self._yr_income_lbl = self._make_summary_card(cards, 0, "Total Income")
        self._yr_expense_lbl = self._make_summary_card(cards, 1, "Total Expenses")
        self._yr_net_lbl = self._make_summary_card(cards, 2, "Total Net")

    def _render_yearly_overview(self):
        self._year_title.configure(text=f"{self._year} Overview")
        s = db.get_yearly_summary(self.user_id, self._year)
        income, expenses = s["income"], s["expenses"]
        net = income - expenses
        self._yr_income_lbl.configure(
            text=f"${income:,.2f}", text_color=("#2e7d32", "#81c784"))
        self._yr_expense_lbl.configure(
            text=f"${expenses:,.2f}", text_color=("#c62828", "#ef9a9a"))
        self._yr_net_lbl.configure(
            text=f"${net:,.2f}",
            text_color=("#2e7d32", "#81c784") if net >= 0 else ("#c62828", "#ef9a9a"),
        )

    # ── transactions section ───────────────────────────────────────────────────

    def _build_txn_header(self):
        hdr = ctk.CTkFrame(self, fg_color="transparent")
        hdr.grid(row=3, column=0, sticky="ew", pady=(0, 8))
        hdr.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            hdr, text="Transactions",
            font=ctk.CTkFont(size=18, weight="bold"),
        ).grid(row=0, column=0, sticky="w", padx=(0, 16))

        nav = ctk.CTkFrame(hdr, fg_color="transparent")
        nav.grid(row=0, column=1)
        ctk.CTkButton(
            nav, text="◀", width=28, height=28,
            fg_color="transparent", text_color=("gray20", "gray80"),
            hover_color=("gray80", "gray30"), command=self._prev_month,
        ).pack(side="left")
        self._month_label = ctk.CTkLabel(nav, text="", font=ctk.CTkFont(size=14, weight="bold"))
        self._month_label.pack(side="left", padx=10)
        ctk.CTkButton(
            nav, text="▶", width=28, height=28,
            fg_color="transparent", text_color=("gray20", "gray80"),
            hover_color=("gray80", "gray30"), command=self._next_month,
        ).pack(side="left")

        ctk.CTkButton(
            hdr, text="+ Add Transaction", width=150,
            command=self._open_add_txn,
        ).grid(row=0, column=2, sticky="e")

    def _build_summary(self):
        frame = ctk.CTkFrame(self, fg_color="transparent")
        frame.grid(row=4, column=0, sticky="ew", pady=(0, 8))
        frame.grid_columnconfigure((0, 1, 2), weight=1)
        self._income_lbl = self._make_summary_card(frame, 0, "Income")
        self._expense_lbl = self._make_summary_card(frame, 1, "Expenses")
        self._net_lbl = self._make_summary_card(frame, 2, "Net Balance")

    def _make_summary_card(self, parent, col, title):
        card = ctk.CTkFrame(parent, fg_color=("gray92", "gray20"), corner_radius=10)
        card.grid(row=0, column=col, padx=4, sticky="ew")
        ctk.CTkLabel(card, text=title, font=ctk.CTkFont(size=12),
                     text_color=("gray40", "gray60")).pack(pady=(8, 2))
        val = ctk.CTkLabel(card, text="$0.00", font=ctk.CTkFont(size=18, weight="bold"))
        val.pack(pady=(0, 8))
        return val

    def _build_txn_list(self):
        card = ctk.CTkFrame(self, corner_radius=12)
        card.grid(row=5, column=0, sticky="nsew")
        card.grid_columnconfigure(0, weight=1)
        card.grid_rowconfigure(1, weight=1)

        cols = ctk.CTkFrame(card, fg_color=("gray85", "gray22"), corner_radius=8)
        cols.grid(row=0, column=0, sticky="ew", padx=12, pady=(12, 4))
        cols.grid_columnconfigure(0, weight=2)
        cols.grid_columnconfigure(1, weight=2)
        cols.grid_columnconfigure(2, weight=4)
        cols.grid_columnconfigure(3, weight=2)
        cols.grid_columnconfigure(4, weight=1)
        cols.grid_columnconfigure(5, minsize=80)

        for col, text in enumerate(["Date", "Category", "Description", "Amount", "Type", ""]):
            ctk.CTkLabel(cols, text=text, font=ctk.CTkFont(size=12, weight="bold"),
                         text_color=("gray30", "gray70")).grid(
                row=0, column=col, sticky="w", padx=10, pady=6)

        self.list_frame = ctk.CTkScrollableFrame(card, fg_color="transparent")
        self.list_frame.grid(row=1, column=0, sticky="nsew", padx=8, pady=(0, 12))
        self.list_frame.grid_columnconfigure(0, weight=1)

    def _render_transactions(self):
        self._render_yearly_overview()
        self._month_label.configure(
            text=datetime(self._year, self._month, 1).strftime("%B %Y"))

        summary = db.get_budget_summary(self.user_id, self._year, self._month)
        income, expenses = summary["income"], summary["expenses"]
        net = income - expenses

        self._income_lbl.configure(text=f"${income:,.2f}", text_color=("#2e7d32", "#81c784"))
        self._expense_lbl.configure(text=f"${expenses:,.2f}", text_color=("#c62828", "#ef9a9a"))
        self._net_lbl.configure(
            text=f"${net:,.2f}",
            text_color=("#2e7d32", "#81c784") if net >= 0 else ("#c62828", "#ef9a9a"),
        )

        for w in self.list_frame.winfo_children():
            w.destroy()

        txns = db.list_transactions(self.user_id, self._year, self._month)
        if not txns:
            ctk.CTkLabel(
                self.list_frame,
                text='No transactions this month. Click "+ Add Transaction" to get started.',
                text_color=("gray50", "gray55"),
            ).pack(anchor="w", pady=20, padx=12)
            return
        for txn in txns:
            self._render_txn_row(txn)

    def _render_txn_row(self, txn: dict):
        row = ctk.CTkFrame(self.list_frame, fg_color=("gray92", "gray20"), corner_radius=8)
        row.pack(fill="x", pady=3, padx=4)
        row.grid_columnconfigure(0, weight=2)
        row.grid_columnconfigure(1, weight=2)
        row.grid_columnconfigure(2, weight=4)
        row.grid_columnconfigure(3, weight=2)
        row.grid_columnconfigure(4, weight=1)
        row.grid_columnconfigure(5, minsize=80)

        is_income = txn["type"] == "income"
        amt_color = ("#2e7d32", "#81c784") if is_income else ("#c62828", "#ef9a9a")

        ctk.CTkLabel(row, text=txn["date"], anchor="w").grid(
            row=0, column=0, sticky="ew", padx=10, pady=8)
        ctk.CTkLabel(row, text=txn["category"] or "—", anchor="w").grid(
            row=0, column=1, sticky="ew", padx=10)
        ctk.CTkLabel(row, text=txn["description"] or "—", anchor="w").grid(
            row=0, column=2, sticky="ew", padx=10)
        ctk.CTkLabel(
            row, text=f"{'+'if is_income else'-'}${txn['amount']:,.2f}",
            anchor="w", text_color=amt_color, font=ctk.CTkFont(weight="bold"),
        ).grid(row=0, column=3, sticky="ew", padx=10)
        ctk.CTkLabel(
            row, text="Income" if is_income else "Expense",
            anchor="w", text_color=amt_color,
        ).grid(row=0, column=4, sticky="ew", padx=10)

        btn_frame = ctk.CTkFrame(row, fg_color="transparent")
        btn_frame.grid(row=0, column=5, padx=6, pady=4)
        ctk.CTkButton(
            btn_frame, text="Edit", width=38, height=26,
            fg_color="transparent", text_color=("gray30", "gray70"),
            hover_color=("gray80", "gray30"),
            command=lambda t=txn: self._open_edit_txn(t),
        ).pack(side="left", padx=2)
        ctk.CTkButton(
            btn_frame, text="✕", width=28, height=26,
            fg_color="transparent", text_color=("gray40", "gray60"),
            hover_color=("#f5c6c6", "#553333"),
            command=lambda tid=txn["id"]: self._delete_txn(tid),
        ).pack(side="left", padx=2)

    # ── month nav ──────────────────────────────────────────────────────────────

    def _prev_month(self):
        if self._month == 1:
            self._month, self._year = 12, self._year - 1
        else:
            self._month -= 1
        self._render_transactions()

    def _next_month(self):
        if self._month == 12:
            self._month, self._year = 1, self._year + 1
        else:
            self._month += 1
        self._render_transactions()

    # ── account actions ────────────────────────────────────────────────────────

    def _open_add_account(self):
        _AccountDialog(self, self.user_id, acct=None, on_save=self._render_accounts)

    def _open_edit_account(self, acct: dict):
        _AccountDialog(self, self.user_id, acct=acct, on_save=self._render_accounts)

    def _open_update_balance(self, acct: dict):
        _BalanceDialog(self, self.user_id, acct=acct, on_save=self._render_accounts)

    def _delete_account(self, acct_id: int):
        db.delete_account(acct_id, self.user_id)
        self._render_accounts()

    # ── transaction actions ────────────────────────────────────────────────────

    def _open_add_txn(self):
        _TxnDialog(self, self.user_id, txn=None, on_save=self._render_transactions)

    def _open_edit_txn(self, txn: dict):
        _TxnDialog(self, self.user_id, txn=txn, on_save=self._render_transactions)

    def _delete_txn(self, txn_id: int):
        db.delete_transaction(txn_id, self.user_id)
        self._render_transactions()


# ── dialogs ────────────────────────────────────────────────────────────────────

class _AccountDialog(ctk.CTkToplevel):
    """Add / edit a savings or debt account."""

    def __init__(self, master, user_id: int, acct: dict | None, on_save):
        super().__init__(master)
        self.user_id = user_id
        self.acct = acct
        self.on_save = on_save

        self.title("Edit Account" if acct else "Add Account")
        self.geometry("420x310")
        self.resizable(False, False)
        self.grab_set()
        self._build()
        if acct:
            self._populate(acct)

    def _build(self):
        frame = ctk.CTkFrame(self, fg_color="transparent")
        frame.pack(fill="both", expand=True, padx=24, pady=20)
        frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(frame, text="Type", anchor="w").grid(
            row=0, column=0, sticky="w", padx=(0, 12), pady=6)
        self._type_var = ctk.StringVar(value="savings")
        ctk.CTkSegmentedButton(
            frame, values=["savings", "debt"], variable=self._type_var,
        ).grid(row=0, column=1, sticky="ew", pady=6)

        fields = [
            ("Account Name", "name"),
            ("Current Balance ($)", "balance"),
            ("Goal ($)", "goal"),
        ]
        self._entries: dict[str, ctk.CTkEntry] = {}
        for i, (label, key) in enumerate(fields, start=1):
            ctk.CTkLabel(frame, text=label, anchor="w").grid(
                row=i, column=0, sticky="w", padx=(0, 12), pady=6)
            entry = ctk.CTkEntry(frame, width=240)
            entry.grid(row=i, column=1, sticky="ew", pady=6)
            self._entries[key] = entry

        ctk.CTkLabel(
            frame,
            text="Goal is optional. For debt, enter the amount you want to pay off.",
            font=ctk.CTkFont(size=11), text_color=("gray45", "gray60"),
        ).grid(row=4, column=0, columnspan=2, sticky="w", pady=(0, 4))

        self.err_label = ctk.CTkLabel(frame, text="", text_color=("#b33", "#f88"))
        self.err_label.grid(row=5, column=0, columnspan=2, sticky="w")

        btn_row = ctk.CTkFrame(frame, fg_color="transparent")
        btn_row.grid(row=6, column=0, columnspan=2, pady=(10, 0), sticky="e")
        ctk.CTkButton(
            btn_row, text="Cancel", width=90,
            fg_color="transparent", border_width=1,
            text_color=("gray10", "gray90"), hover_color=("gray85", "gray25"),
            command=self.destroy,
        ).pack(side="left", padx=(0, 8))
        ctk.CTkButton(btn_row, text="Save", width=90, command=self._save).pack(side="left")

    def _populate(self, acct: dict):
        self._type_var.set(acct["account_type"])
        self._entries["name"].insert(0, acct["name"] or "")
        self._entries["balance"].insert(
            0, str(acct["balance"]) if acct["balance"] is not None else "")
        self._entries["goal"].insert(
            0, str(acct["goal"]) if acct["goal"] is not None else "")

    def _save(self):
        name = self._entries["name"].get().strip()
        account_type = self._type_var.get()
        balance_str = self._entries["balance"].get().strip()
        goal_str = self._entries["goal"].get().strip()

        if not name:
            self.err_label.configure(text="Account name is required.")
            return
        try:
            balance = float(balance_str.replace(",", "").lstrip("$"))
        except ValueError:
            self.err_label.configure(text="Balance must be a number.")
            return
        goal = None
        if goal_str:
            try:
                goal = float(goal_str.replace(",", "").lstrip("$"))
            except ValueError:
                self.err_label.configure(text="Goal must be a number.")
                return

        if self.acct:
            db.update_account(
                self.acct["id"], self.user_id, name, account_type, balance, goal)
        else:
            db.add_account(self.user_id, name, account_type, balance, goal)

        self.on_save()
        self.destroy()


class _BalanceDialog(ctk.CTkToplevel):
    """Quick balance update — shows current value, asks for new one."""

    def __init__(self, master, user_id: int, acct: dict, on_save):
        super().__init__(master)
        self.user_id = user_id
        self.acct = acct
        self.on_save = on_save

        self.title(f"Update — {acct['name']}")
        self.geometry("360x190")
        self.resizable(False, False)
        self.grab_set()
        self._build()

    def _build(self):
        frame = ctk.CTkFrame(self, fg_color="transparent")
        frame.pack(fill="both", expand=True, padx=24, pady=24)
        frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            frame,
            text=f"Current balance: ${self.acct['balance']:,.2f}",
            text_color=("gray40", "gray60"),
        ).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 12))

        ctk.CTkLabel(frame, text="New Balance ($)", anchor="w").grid(
            row=1, column=0, sticky="w", padx=(0, 12), pady=6)
        self._entry = ctk.CTkEntry(frame, width=180)
        self._entry.grid(row=1, column=1, sticky="ew", pady=6)
        self._entry.focus()

        self.err_label = ctk.CTkLabel(frame, text="", text_color=("#b33", "#f88"))
        self.err_label.grid(row=2, column=0, columnspan=2, sticky="w")

        btn_row = ctk.CTkFrame(frame, fg_color="transparent")
        btn_row.grid(row=3, column=0, columnspan=2, pady=(16, 0), sticky="e")
        ctk.CTkButton(
            btn_row, text="Cancel", width=90,
            fg_color="transparent", border_width=1,
            text_color=("gray10", "gray90"), hover_color=("gray85", "gray25"),
            command=self.destroy,
        ).pack(side="left", padx=(0, 8))
        ctk.CTkButton(btn_row, text="Save", width=90, command=self._save).pack(side="left")

    def _save(self):
        try:
            balance = float(self._entry.get().strip().replace(",", "").lstrip("$"))
            if balance < 0:
                raise ValueError
        except ValueError:
            self.err_label.configure(text="Enter a valid non-negative number.")
            return
        db.update_account_balance(self.acct["id"], self.user_id, balance)
        self.on_save()
        self.destroy()


class _TxnDialog(ctk.CTkToplevel):
    """Add / edit a budget transaction."""

    def __init__(self, master, user_id: int, txn: dict | None, on_save):
        super().__init__(master)
        self.user_id = user_id
        self.txn = txn
        self.on_save = on_save

        self.title("Edit Transaction" if txn else "Add Transaction")
        self.geometry("440x340")
        self.resizable(False, False)
        self.grab_set()
        self._build()
        if txn:
            self._populate(txn)

    def _build(self):
        frame = ctk.CTkFrame(self, fg_color="transparent")
        frame.pack(fill="both", expand=True, padx=24, pady=20)
        frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(frame, text="Type", anchor="w").grid(
            row=0, column=0, sticky="w", padx=(0, 12), pady=6)
        self._type_var = ctk.StringVar(value="expense")
        ctk.CTkSegmentedButton(
            frame, values=["income", "expense"], variable=self._type_var,
        ).grid(row=0, column=1, sticky="ew", pady=6)

        fields = [
            ("Date (YYYY-MM-DD)", "date"),
            ("Category", "category"),
            ("Description", "description"),
            ("Amount ($)", "amount"),
        ]
        self._entries: dict[str, ctk.CTkEntry] = {}
        for i, (label, key) in enumerate(fields, start=1):
            ctk.CTkLabel(frame, text=label, anchor="w").grid(
                row=i, column=0, sticky="w", padx=(0, 12), pady=6)
            entry = ctk.CTkEntry(frame, width=260)
            entry.grid(row=i, column=1, sticky="ew", pady=6)
            self._entries[key] = entry

        self._entries["date"].insert(0, date.today().isoformat())

        self.err_label = ctk.CTkLabel(frame, text="", text_color=("#b33", "#f88"))
        self.err_label.grid(row=5, column=0, columnspan=2, sticky="w", pady=(4, 0))

        btn_row = ctk.CTkFrame(frame, fg_color="transparent")
        btn_row.grid(row=6, column=0, columnspan=2, pady=(12, 0), sticky="e")
        ctk.CTkButton(
            btn_row, text="Cancel", width=90,
            fg_color="transparent", border_width=1,
            text_color=("gray10", "gray90"), hover_color=("gray85", "gray25"),
            command=self.destroy,
        ).pack(side="left", padx=(0, 8))
        ctk.CTkButton(btn_row, text="Save", width=90, command=self._save).pack(side="left")

    def _populate(self, txn: dict):
        self._type_var.set(txn["type"])
        self._entries["date"].delete(0, "end")
        self._entries["date"].insert(0, txn["date"] or "")
        self._entries["category"].insert(0, txn["category"] or "")
        self._entries["description"].insert(0, txn["description"] or "")
        self._entries["amount"].insert(
            0, str(txn["amount"]) if txn["amount"] is not None else "")

    def _save(self):
        txn_type = self._type_var.get()
        txn_date = self._entries["date"].get().strip()
        category = self._entries["category"].get().strip()
        description = self._entries["description"].get().strip()
        amount_str = self._entries["amount"].get().strip()

        if not txn_date:
            txn_date = date.today().isoformat()
        else:
            try:
                date.fromisoformat(txn_date)
            except ValueError:
                self.err_label.configure(text="Date must be YYYY-MM-DD.")
                return

        if not amount_str:
            self.err_label.configure(text="Amount is required.")
            return
        try:
            amount = float(amount_str.replace(",", "").lstrip("$"))
            if amount <= 0:
                raise ValueError
        except ValueError:
            self.err_label.configure(text="Amount must be a positive number.")
            return

        if self.txn:
            db.update_transaction(
                self.txn["id"], self.user_id,
                txn_date, txn_type, category, description, amount,
            )
        else:
            db.add_transaction(
                self.user_id, txn_date, txn_type, category, description, amount,
            )

        self.on_save()
        self.destroy()
