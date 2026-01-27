from __future__ import annotations

import tkinter as tk
from dataclasses import dataclass
from tkinter import ttk, font

_THEME_INSTANCE: "GlassTheme | None" = None


def get_theme(root: tk.Misc) -> "GlassTheme":
    """Return a shared GlassTheme instance and apply it to the given window."""
    global _THEME_INSTANCE
    if _THEME_INSTANCE is None:
        _THEME_INSTANCE = GlassTheme(root)
    else:
        _THEME_INSTANCE.apply_to_window(root)
    return _THEME_INSTANCE


@dataclass(frozen=True)
class GlassPalette:
    bg: str
    surface: str
    surface_alt: str
    card: str
    card_hover: str
    stroke: str
    stroke_soft: str
    text: str
    text_muted: str
    accent: str
    accent_hover: str
    accent_soft: str
    accent_cyan: str
    accent_purple: str
    accent_pink: str
    accent_green: str
    accent_orange: str
    success: str
    success_hover: str
    warning: str
    warning_hover: str
    danger: str
    danger_hover: str
    ghost: str
    ghost_hover: str
    input_bg: str
    selection_bg: str


class GlassTheme:
    """Liquid-glass inspired theme helpers for tkinter."""

    def __init__(self, root: tk.Misc) -> None:
        self.root = root
        self.colors = GlassPalette(
            bg="#EAF0F7",
            surface="#F7FAFF",
            surface_alt="#EEF4FB",
            card="#FFFFFF",
            card_hover="#F2F6FF",
            stroke="#D6E0EF",
            stroke_soft="#E2EAF5",
            text="#1C2430",
            text_muted="#6B7B92",
            accent="#3D7BFF",
            accent_hover="#356BE0",
            accent_soft="#DCE8FF",
            accent_cyan="#49C7F2",
            accent_purple="#8B7CFF",
            accent_pink="#F06BA7",
            accent_green="#30C790",
            accent_orange="#FF9F43",
            success="#27C28B",
            success_hover="#22AD7A",
            warning="#F5B73C",
            warning_hover="#E0A233",
            danger="#FF6B6B",
            danger_hover="#E55B5B",
            ghost="#F3F7FF",
            ghost_hover="#E6EEFF",
            input_bg="#FCFDFF",
            selection_bg="#D7E4FF",
        )
        self.alpha = 0.985
        self.font_family = self._pick_font(
            root,
            [
                "Segoe UI Variable Display",
                "Segoe UI Variable Text",
                "Segoe UI",
                "Microsoft YaHei UI",
            ],
            "Segoe UI",
        )
        self.mono_family = self._pick_font(
            root,
            ["Cascadia Code", "Consolas", "Source Code Pro", "Courier New"],
            "Consolas",
        )
        self.fonts = {
            "hero": (self.font_family, 32, "bold"),
            "title": (self.font_family, 22, "bold"),
            "section": (self.font_family, 14, "bold"),
            "body": (self.font_family, 11),
            "body_bold": (self.font_family, 11, "bold"),
            "small": (self.font_family, 10),
            "tiny": (self.font_family, 9),
            "mono": (self.mono_family, 10),
        }
        self.button_styles = {
            "primary": {
                "bg": self.colors.accent,
                "hover": self.colors.accent_hover,
                "fg": "#FFFFFF",
                "border": self.colors.accent,
            },
            "secondary": {
                "bg": self.colors.surface_alt,
                "hover": self.colors.ghost_hover,
                "fg": self.colors.text,
                "border": self.colors.stroke,
            },
            "ghost": {
                "bg": self.colors.ghost,
                "hover": self.colors.ghost_hover,
                "fg": self.colors.text,
                "border": self.colors.stroke_soft,
            },
            "success": {
                "bg": self.colors.success,
                "hover": self.colors.success_hover,
                "fg": "#FFFFFF",
                "border": self.colors.success,
            },
            "warning": {
                "bg": self.colors.warning,
                "hover": self.colors.warning_hover,
                "fg": "#FFFFFF",
                "border": self.colors.warning,
            },
            "danger": {
                "bg": self.colors.danger,
                "hover": self.colors.danger_hover,
                "fg": "#FFFFFF",
                "border": self.colors.danger,
            },
        }
        self.apply_to_window(root, is_root=True)

    def apply_to_window(self, window: tk.Misc, is_root: bool = False) -> None:
        """Apply background and window attributes."""
        window.configure(bg=self.colors.bg)
        try:
            window.attributes("-alpha", self.alpha)
        except tk.TclError:
            pass
        if is_root:
            self._apply_option_db(window)
            self._configure_ttk(window)

    def _apply_option_db(self, root: tk.Misc) -> None:
        root.option_add("*Font", self.fonts["body"])
        root.option_add("*Foreground", self.colors.text)
        root.option_add("*insertBackground", self.colors.text)
        root.option_add("*selectBackground", self.colors.selection_bg)
        root.option_add("*selectForeground", self.colors.text)

    def _configure_ttk(self, root: tk.Misc) -> None:
        style = ttk.Style(root)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        style.configure(
            "TFrame",
            background=self.colors.bg,
        )
        style.configure(
            "TLabel",
            background=self.colors.bg,
            foreground=self.colors.text,
            font=self.fonts["body"],
        )
        style.configure(
            "Muted.TLabel",
            background=self.colors.bg,
            foreground=self.colors.text_muted,
            font=self.fonts["small"],
        )
        style.configure(
            "Card.TFrame",
            background=self.colors.surface,
        )
        style.configure(
            "TEntry",
            fieldbackground=self.colors.input_bg,
            foreground=self.colors.text,
            bordercolor=self.colors.stroke,
            lightcolor=self.colors.stroke,
            darkcolor=self.colors.stroke,
            padding=6,
        )
        style.configure(
            "Glass.TCombobox",
            fieldbackground=self.colors.input_bg,
            background=self.colors.surface_alt,
            foreground=self.colors.text,
            arrowcolor=self.colors.accent,
            bordercolor=self.colors.stroke,
            lightcolor=self.colors.stroke,
            darkcolor=self.colors.stroke,
            padding=6,
        )
        style.map(
            "Glass.TCombobox",
            fieldbackground=[("readonly", self.colors.input_bg)],
            background=[("active", self.colors.ghost_hover), ("pressed", self.colors.ghost_hover)],
            foreground=[("readonly", self.colors.text)],
            arrowcolor=[("active", self.colors.accent_hover), ("pressed", self.colors.accent_hover)],
        )
        style.configure(
            "Horizontal.TProgressbar",
            troughcolor=self.colors.surface_alt,
            background=self.colors.accent,
            thickness=8,
            bordercolor=self.colors.surface_alt,
            lightcolor=self.colors.surface_alt,
            darkcolor=self.colors.surface_alt,
        )
        style.configure(
            "TScrollbar",
            background=self.colors.stroke,
            troughcolor=self.colors.surface,
            bordercolor=self.colors.surface,
            lightcolor=self.colors.surface,
            darkcolor=self.colors.surface,
            arrowcolor=self.colors.text_muted,
        )

    def _pick_font(self, root: tk.Misc, candidates: list[str], fallback: str) -> str:
        try:
            available = set(font.families(root))
        except tk.TclError:
            return fallback
        for name in candidates:
            if name in available:
                return name
        return fallback

    def style_frame(self, frame: tk.Misc, *, surface: str | None = None) -> None:
        frame.configure(bg=surface or self.colors.surface)

    def style_card(self, frame: tk.Misc) -> None:
        frame.configure(
            bg=self.colors.surface,
            highlightbackground=self.colors.stroke,
            highlightthickness=1,
            bd=0,
        )

    def style_section(self, frame: tk.Misc) -> None:
        frame.configure(
            bg=self.colors.surface_alt,
            highlightbackground=self.colors.stroke_soft,
            highlightthickness=1,
            bd=0,
        )

    def style_entry(self, entry: tk.Entry) -> None:
        entry.configure(
            bg=self.colors.input_bg,
            fg=self.colors.text,
            insertbackground=self.colors.text,
            relief="flat",
            highlightthickness=1,
            highlightbackground=self.colors.stroke,
            highlightcolor=self.colors.accent,
        )

    def style_spinbox(self, spinbox: tk.Spinbox) -> None:
        spinbox.configure(
            bg=self.colors.input_bg,
            fg=self.colors.text,
            insertbackground=self.colors.text,
            relief="flat",
            highlightthickness=1,
            highlightbackground=self.colors.stroke,
            highlightcolor=self.colors.accent,
        )

    def style_listbox(self, listbox: tk.Listbox) -> None:
        listbox.configure(
            bg=self.colors.input_bg,
            fg=self.colors.text,
            selectbackground=self.colors.selection_bg,
            selectforeground=self.colors.text,
            relief="flat",
            highlightthickness=1,
            highlightbackground=self.colors.stroke,
        )

    def style_text(self, text: tk.Text) -> None:
        text.configure(
            bg=self.colors.input_bg,
            fg=self.colors.text,
            insertbackground=self.colors.text,
            relief="flat",
            highlightthickness=1,
            highlightbackground=self.colors.stroke,
            highlightcolor=self.colors.accent,
        )

    def style_checkbutton(self, checkbutton: tk.Checkbutton) -> None:
        checkbutton.configure(
            bg=self.colors.surface,
            fg=self.colors.text,
            activebackground=self.colors.surface,
            selectcolor=self.colors.surface,
        )

    def style_button(self, button: tk.Button, variant: str = "primary") -> None:
        style = self.button_styles.get(variant, self.button_styles["primary"])
        button.configure(
            bg=style["bg"],
            fg=style["fg"],
            activebackground=style["hover"],
            activeforeground=style["fg"],
            relief="flat",
            bd=0,
            highlightthickness=1,
            highlightbackground=style["border"],
        )
        self._bind_hover(button, style["bg"], style["hover"])

    def style_segment_button(self, button: tk.Button, active: bool) -> None:
        if active:
            self.style_button(button, variant="primary")
        else:
            self.style_button(button, variant="ghost")

    def _bind_hover(self, button: tk.Button, normal_bg: str, hover_bg: str) -> None:
        button.bind("<Enter>", lambda _e: button.configure(bg=hover_bg))
        button.bind("<Leave>", lambda _e: button.configure(bg=normal_bg))
