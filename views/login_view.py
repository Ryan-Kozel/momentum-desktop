"""Login / register screens."""
from __future__ import annotations

import customtkinter as ctk

import auth


class LoginView(ctk.CTkFrame):
    def __init__(self, master, on_login):
        super().__init__(master, fg_color="transparent")
        self.on_login = on_login
        self._build()

    def _build(self):
        # Center a card in the window
        card = ctk.CTkFrame(self, corner_radius=16)
        card.place(relx=0.5, rely=0.5, anchor="center")

        ctk.CTkLabel(card, text="Momentum", font=ctk.CTkFont(size=32, weight="bold")).pack(pady=(30, 6), padx=40)
        ctk.CTkLabel(card, text="Track your goals. Build momentum.",
                     text_color=("gray40", "gray60")).pack(pady=(0, 20), padx=40)

        self.tabs = ctk.CTkTabview(card, width=340, height=260)
        self.tabs.pack(padx=30, pady=(0, 30))
        self.tabs.add("Login")
        self.tabs.add("Register")

        self._build_login(self.tabs.tab("Login"))
        self._build_register(self.tabs.tab("Register"))

    def _build_login(self, parent):
        ctk.CTkLabel(parent, text="Username").pack(anchor="w", pady=(10, 2))
        self.login_user = ctk.CTkEntry(parent, width=280)
        self.login_user.pack()

        ctk.CTkLabel(parent, text="Password").pack(anchor="w", pady=(12, 2))
        self.login_pass = ctk.CTkEntry(parent, width=280, show="•")
        self.login_pass.pack()
        self.login_pass.bind("<Return>", lambda e: self._do_login())

        ctk.CTkButton(parent, text="Log in", width=280, command=self._do_login).pack(pady=(20, 4))

        self.login_msg = ctk.CTkLabel(parent, text="", text_color=("#b33", "#f88"))
        self.login_msg.pack()

    def _build_register(self, parent):
        ctk.CTkLabel(parent, text="Username").pack(anchor="w", pady=(10, 2))
        self.reg_user = ctk.CTkEntry(parent, width=280)
        self.reg_user.pack()

        ctk.CTkLabel(parent, text="Password").pack(anchor="w", pady=(12, 2))
        self.reg_pass = ctk.CTkEntry(parent, width=280, show="•")
        self.reg_pass.pack()
        self.reg_pass.bind("<Return>", lambda e: self._do_register())

        ctk.CTkButton(parent, text="Create account", width=280, command=self._do_register).pack(pady=(20, 4))

        self.reg_msg = ctk.CTkLabel(parent, text="")
        self.reg_msg.pack()

    def _do_login(self):
        ok, msg, uid = auth.login(self.login_user.get(), self.login_pass.get())
        if ok:
            self.on_login(uid)
        else:
            self.login_msg.configure(text=msg, text_color=("#b33", "#f88"))

    def _do_register(self):
        ok, msg = auth.register(self.reg_user.get(), self.reg_pass.get())
        color = ("#2a7", "#6d8") if ok else ("#b33", "#f88")
        self.reg_msg.configure(text=msg, text_color=color)
        if ok:
            # auto-switch to login tab and prefill
            self.tabs.set("Login")
            self.login_user.delete(0, "end")
            self.login_user.insert(0, self.reg_user.get())
            self.login_pass.focus_set()
