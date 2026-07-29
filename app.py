"""ResetPath mobile application.

Run locally:
    flet run app.py

Build Android:
    flet build apk
"""

from __future__ import annotations

import asyncio
from dataclasses import replace
from datetime import date, datetime, timedelta, timezone
from enum import StrEnum
import inspect
from typing import Callable

import flet as ft
import flet_charts as fch
import pandas as pd

from database import Database
from local_ai import classify_emotion, retrieve_diary_context
from logic import (
    SupportSettings,
    Task,
    Track,
    build_support_plan,
    contains_crisis_language,
    normalize_phone_for_uri,
    validate_phone,
    validate_task,
)
from wellbeing import parse_wearable_file, wearable_template_csv


# ResetPath's visual language is intentionally warm and grounded.  It borrows
# the generous spacing and playful geometry of the supplied references without
# copying their brand assets or layouts.
PRIMARY = "#F47B4A"
PRIMARY_DARK = "#4A2C2A"
PRIMARY_SOFT = "#FFF0E7"
SUN = "#F6C453"
SUN_SOFT = "#FFF6D8"
MINT = "#BFDCCF"
MINT_DARK = "#246456"
SURFACE = "#FBF8F4"
SURFACE_ALT = "#F3EDE7"
CARD = "#FFFFFF"
TEXT = "#2E2927"
MUTED = "#756C67"
BORDER = "#EAE2DB"
WARNING = "#A94335"
WARNING_SOFT = "#FCE9E5"
SHADOW = "#1A4A2C2A"
TELE_MANAS_PHONE = "14416"
TELE_MANAS_URL = "https://telemanas.mohfw.gov.in/home"


class ViewName(StrEnum):
    HOME = "home"
    TASKS = "tasks"
    JOURNAL = "journal"
    PROGRESS = "progress"
    HELP = "help"
    SETTINGS = "settings"
    RESET = "reset"
    MEDITATE = "meditate"


NAV_VIEWS = [
    ViewName.HOME,
    ViewName.TASKS,
    ViewName.JOURNAL,
    ViewName.PROGRESS,
    ViewName.HELP,
]

ROUTES_TO_VIEWS = {"/": ViewName.HOME, **{f"/{view.value}": view for view in ViewName if view != ViewName.HOME}}
VIEWS_TO_ROUTES = {view: route for route, view in ROUTES_TO_VIEWS.items()}


class ResetPathApp:
    def __init__(self, page: ft.Page) -> None:
        self.page = page
        self.database = Database()
        self.current_view = ViewName.HOME
        self.navigation_history: list[ViewName] = []
        self.task_filter = "today"
        self.progress_filter = "7"
        self.crisis_redirected = False
        self.view_stage: ft.Container | None = None
        self.evidence_cards: list[ft.Container] = []

        self.journal_step = 0
        self.journal_values = {
            "thought": "",
            "emotion": "",
            "action": "",
            "use_diary_context": False,
            "diary_context": (),
            "model_route": "",
        }
        self.journal_plan = None
        self.diary_editing_id: int | None = None
        self.diary_draft = ""

        self.meditation_minutes = 2
        self.meditation_running = False
        self.meditation_paused = False
        self.meditation_cancelled = False
        self.meditation_orb: ft.Container | None = None
        self.meditation_status: ft.Text | None = None
        self.meditation_timer: ft.Text | None = None
        self.meditation_start_button: ft.Button | None = None
        self.meditation_pause_button: ft.Button | None = None

        self.reset_step = 0
        self.reset_values: dict[str, object] = {
            "sights": ["", "", "", "", ""],
            "thought": "",
            "facts": "",
            "prediction": "",
            "action": "",
            "track": Track.DSA.value,
        }
        self.breathing_running = False
        self.breathing_paused = False
        self.breathing_cancelled = False
        self.breath_status: ft.Text | None = None
        self.breath_progress: ft.ProgressRing | None = None
        self.breath_orb: ft.Container | None = None
        self.breath_orb_label: ft.Text | None = None
        self.breath_start_button: ft.Button | None = None
        self.breath_pause_button: ft.Button | None = None

        self.url_launcher = ft.UrlLauncher()
        self.file_picker = ft.FilePicker()
        self.haptics = ft.HapticFeedback()

        self._configure_page()
        self.render()

    def _configure_page(self) -> None:
        self.page.title = "ResetPath"
        self.page.adaptive = True
        self._apply_theme_palette(self.database.get_settings().theme_mode)
        self.page.bgcolor = SURFACE
        self.page.padding = 0
        self.page.theme = ft.Theme(
            color_scheme_seed=PRIMARY,
            font_family="Segoe UI Variable Display",
        )
        self.page.dark_theme = ft.Theme(
            color_scheme_seed=PRIMARY,
            font_family="Segoe UI Variable Display",
        )
        self.page.theme_mode = (
            ft.ThemeMode.DARK if self.is_dark_theme else ft.ThemeMode.LIGHT
        )
        self.page.on_route_change = self._handle_route_change
        self.page.on_view_pop = self._handle_system_back
        try:
            self.page.window.width = 430
            self.page.window.height = 820
            self.page.window.min_width = 360
            self.page.window.min_height = 640
        except Exception:
            pass

    def _apply_theme_palette(self, mode: str) -> None:
        """Keep the app's custom surfaces coherent in both colour modes."""
        global PRIMARY_SOFT, SUN_SOFT, MINT, MINT_DARK, SURFACE, SURFACE_ALT
        global CARD, TEXT, MUTED, BORDER, WARNING_SOFT, SHADOW
        self.is_dark_theme = mode == "dark"
        if self.is_dark_theme:
            PRIMARY_SOFT, SUN_SOFT, MINT, MINT_DARK = "#3B2924", "#3A3322", "#28443D", "#A8D9C7"
            SURFACE, SURFACE_ALT, CARD = "#151917", "#202522", "#222825"
            TEXT, MUTED, BORDER, WARNING_SOFT, SHADOW = "#F4F0EB", "#C8C0B9", "#3A413D", "#402523", "#42000000"
        else:
            PRIMARY_SOFT, SUN_SOFT, MINT, MINT_DARK = "#FFF0E7", "#FFF6D8", "#BFDCCF", "#246456"
            SURFACE, SURFACE_ALT, CARD = "#FBF8F4", "#F3EDE7", "#FFFFFF"
            TEXT, MUTED, BORDER, WARNING_SOFT, SHADOW = "#2E2927", "#756C67", "#EAE2DB", "#FCE9E5", "#1A4A2C2A"

    def _set_theme(self, mode: str) -> None:
        settings = self.database.get_settings()
        self.database.save_settings(replace(settings, theme_mode=mode))
        self._apply_theme_palette(mode)
        self.page.theme_mode = ft.ThemeMode.DARK if self.is_dark_theme else ft.ThemeMode.LIGHT
        self.page.bgcolor = SURFACE
        self.render()

    def _handle_system_back(self, _event=None) -> None:
        """Android back follows the app's path before the OS can close it."""
        if self.navigation_history:
            self.go_to(self.navigation_history.pop(), remember=False)
        elif self.current_view != ViewName.HOME:
            self.go_to(ViewName.HOME, remember=False)

    def _handle_route_change(self, event) -> None:
        """Keep browser and Android navigation aligned with the visible screen."""
        route = getattr(event, "route", self.page.route)
        target = ROUTES_TO_VIEWS.get(route, ViewName.HOME)
        if target != self.current_view:
            if self.current_view in self.navigation_history:
                self.navigation_history.remove(self.current_view)
            self.current_view = target
        self.render()

    # ------------------------------------------------------------------
    # Rendering and common controls
    # ------------------------------------------------------------------

    def render(self) -> None:
        settings = self.database.get_settings()
        self.page.clean()

        if (
            settings.disclaimer_acknowledged_at is None
            and self.current_view != ViewName.HELP
        ):
            self.page.add(self._build_onboarding(settings))
            self.page.update()
            return

        body_builder: dict[ViewName, Callable[[], ft.Control]] = {
            ViewName.HOME: self._build_home,
            ViewName.TASKS: self._build_tasks,
            ViewName.JOURNAL: self._build_journal,
            ViewName.PROGRESS: self._build_progress,
            ViewName.HELP: self._build_help,
            ViewName.SETTINGS: self._build_settings,
            ViewName.RESET: self._build_reset,
            ViewName.MEDITATE: self._build_meditate,
        }
        body = body_builder[self.current_view]()
        self.view_stage = ft.Container(
            content=body,
            opacity=0,
            offset=ft.Offset(0, 0.025),
            animate_opacity=240,
            animate_offset=280,
            expand=True,
        )
        controls: list[ft.Control] = [
            self._build_header(),
            ft.Container(
                content=self.view_stage,
                padding=ft.Padding.only(left=18, right=18, top=8),
                alignment=ft.Alignment.TOP_CENTER,
                expand=True,
            ),
        ]
        if self.current_view in NAV_VIEWS:
            controls.append(self._build_navigation())

        self.page.add(
            ft.SafeArea(
                content=ft.Column(
                    controls=controls,
                    spacing=0,
                    expand=True,
                ),
                expand=True,
            )
        )
        self.page.update()
        self.page.run_task(self._reveal_stage, self.view_stage)
        if self.evidence_cards:
            self.page.run_task(self._reveal_evidence_cards)

    async def _reveal_stage(self, stage: ft.Container) -> None:
        await asyncio.sleep(0.02)
        try:
            stage.opacity = 1
            stage.offset = ft.Offset(0, 0)
            stage.update()
        except Exception:
            # A very fast navigation can replace the stage before it animates.
            pass

    async def _reveal_evidence_cards(self) -> None:
        for card in self.evidence_cards:
            await asyncio.sleep(0.055)
            try:
                card.opacity = 1
                card.offset = ft.Offset(0, 0)
                card.scale = 1
                card.update()
            except Exception:
                return

    def _haptic_handler(self, callback, strength: str = "light"):
        async def handle() -> None:
            try:
                method = {
                    "selection": self.haptics.selection_click,
                    "medium": self.haptics.medium_impact,
                }.get(strength, self.haptics.light_impact)
                await method()
            except Exception:
                # Desktop/web environments may not expose a vibration motor.
                pass
            result = callback()
            if inspect.isawaitable(result):
                await result

        return handle

    def _build_header(self) -> ft.Control:
        if self.current_view in (ViewName.RESET, ViewName.MEDITATE):
            title = (
                "Reset now"
                if self.current_view == ViewName.RESET
                else "Quiet practice"
            )
            leading = ft.IconButton(
                icon=ft.Icons.ARROW_BACK,
                icon_color=TEXT,
                tooltip="Back to home",
                on_click=self._handle_system_back,
            )
        elif self.current_view == ViewName.SETTINGS:
            title = "Settings"
            leading = ft.IconButton(
                icon=ft.Icons.ARROW_BACK,
                icon_color=TEXT,
                tooltip="Back to home",
                on_click=self._handle_system_back,
            )
        else:
            title = {
                ViewName.HOME: "Today",
                ViewName.TASKS: "Small steps",
                ViewName.JOURNAL: "Thought journal",
                ViewName.PROGRESS: "Your evidence",
                ViewName.HELP: "Human support",
            }[self.current_view]
            leading = (
                self._brand_mark(42)
                if self.current_view == ViewName.HOME
                else ft.Container(width=42)
            )

        actions: list[ft.Control] = []
        if self.current_view == ViewName.HOME:
            actions.append(
                ft.IconButton(
                    icon=ft.Icons.TUNE_ROUNDED,
                    icon_color=TEXT,
                    tooltip="Settings",
                    on_click=lambda: self.go_to(ViewName.SETTINGS),
                )
            )
            actions.append(
                ft.IconButton(
                    icon=(ft.Icons.LIGHT_MODE_ROUNDED if self.is_dark_theme else ft.Icons.DARK_MODE_ROUNDED),
                    icon_color=TEXT,
                    tooltip="Use light mode" if self.is_dark_theme else "Use dark mode",
                    on_click=lambda: self._set_theme("light" if self.is_dark_theme else "dark"),
                )
            )
        return ft.Container(
            content=ft.Row(
                [
                    leading,
                    ft.Text(
                        title,
                        size=24,
                        weight=ft.FontWeight.W_700,
                        color=TEXT,
                        expand=True,
                    ),
                    *actions,
                ],
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=ft.Padding.only(left=18, right=12, top=12, bottom=10),
            bgcolor=SURFACE,
        )

    def _build_navigation(self) -> ft.NavigationBar:
        selected_index = NAV_VIEWS.index(self.current_view)
        navigation = ft.NavigationBar(
            selected_index=selected_index,
            bgcolor=CARD,
            indicator_color=PRIMARY_SOFT,
            height=74,
            elevation=12,
            shadow_color=SHADOW,
            destinations=[
                ft.NavigationBarDestination(
                    icon=ft.Icons.HOME_OUTLINED,
                    selected_icon=ft.Icons.HOME_ROUNDED,
                    label="Today",
                ),
                ft.NavigationBarDestination(
                    icon=ft.Icons.CHECK_CIRCLE_OUTLINE,
                    selected_icon=ft.Icons.CHECK_CIRCLE_ROUNDED,
                    label="Tasks",
                ),
                ft.NavigationBarDestination(
                    icon=ft.Icons.EDIT_NOTE_OUTLINED,
                    selected_icon=ft.Icons.EDIT_NOTE_ROUNDED,
                    label="Journal",
                ),
                ft.NavigationBarDestination(
                    icon=ft.Icons.INSIGHTS_OUTLINED,
                    selected_icon=ft.Icons.INSIGHTS_ROUNDED,
                    label="Evidence",
                ),
                ft.NavigationBarDestination(
                    icon=ft.Icons.FAVORITE_BORDER_ROUNDED,
                    selected_icon=ft.Icons.FAVORITE_ROUNDED,
                    label="Help",
                ),
            ],
        )

        def navigate() -> None:
            self.go_to(NAV_VIEWS[navigation.selected_index])

        navigation.on_change = navigate
        return navigation

    def go_to(self, view: ViewName, *, remember: bool = True) -> None:
        if view == self.current_view:
            return
        if self.current_view == ViewName.RESET and self.breathing_running:
            self.breathing_cancelled = True
        if self.current_view == ViewName.MEDITATE and self.meditation_running:
            self.meditation_cancelled = True
            self.meditation_running = False
        if remember:
            self.navigation_history.append(self.current_view)
            self.navigation_history = self.navigation_history[-12:]
        self.current_view = view
        if view != ViewName.HELP:
            self.crisis_redirected = False
        try:
            self.page.run_task(self.haptics.selection_click)
        except Exception:
            pass
        # `navigate()` updates browser and Android navigation history and then
        # calls _handle_route_change(), which renders the destination.
        self.page.navigate(VIEWS_TO_ROUTES[view])

    def _scrolling_column(self, controls: list[ft.Control]) -> ft.Control:
        return ft.ListView(
            controls=controls,
            spacing=18,
            padding=ft.Padding.only(bottom=32),
            expand=True,
        )

    def _brand_mark(self, size: int = 46) -> ft.Control:
        return ft.Container(
            width=size,
            height=size,
            bgcolor=PRIMARY,
            border_radius=size * 0.34,
            alignment=ft.Alignment.CENTER,
            content=ft.Icon(
                ft.Icons.AIR_ROUNDED,
                color="#FFFFFF",
                size=size * 0.58,
            ),
            shadow=ft.BoxShadow(
                blur_radius=14,
                spread_radius=0,
                color="#33F47B4A",
                offset=ft.Offset(0, 5),
            ),
        )

    def _section_heading(
        self,
        title: str,
        subtitle: str = "",
        *,
        action: ft.Control | None = None,
    ) -> ft.Control:
        text_controls: list[ft.Control] = [
            ft.Text(
                title,
                size=23,
                weight=ft.FontWeight.W_700,
                color=TEXT,
            )
        ]
        if subtitle:
            text_controls.append(
                ft.Text(
                    subtitle,
                    size=14,
                    color=MUTED,
                )
            )
        return ft.Row(
            [
                ft.Column(text_controls, spacing=3, expand=True),
                *([action] if action else []),
            ],
            vertical_alignment=ft.CrossAxisAlignment.END,
        )

    def _calm_face(self, *, compact: bool = False) -> ft.Control:
        height = 128 if compact else 190
        face_size = 104 if compact else 154
        return ft.Container(
            width=128 if compact else 220,
            height=height,
            bgcolor=SUN_SOFT,
            border_radius=ft.BorderRadius.only(
                top_left=30,
                top_right=30,
                bottom_left=18,
                bottom_right=30,
            ),
            clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
            content=ft.Stack(
                [
                    ft.Container(
                        width=face_size,
                        height=face_size,
                        right=-12 if compact else -4,
                        bottom=-28 if compact else -38,
                        bgcolor=PRIMARY,
                        shape=ft.BoxShape.CIRCLE,
                    ),
                    ft.Icon(
                        ft.Icons.SENTIMENT_SATISFIED_ROUNDED,
                        color=PRIMARY_DARK,
                        size=64 if compact else 88,
                        right=10 if compact else 28,
                        bottom=5 if compact else 16,
                    ),
                    ft.Container(
                        width=46,
                        height=46,
                        left=18,
                        top=18,
                        bgcolor="#FFFFFFAA",
                        shape=ft.BoxShape.CIRCLE,
                        alignment=ft.Alignment.CENTER,
                        content=ft.Icon(
                            ft.Icons.SPA_ROUNDED,
                            color=MINT_DARK,
                            size=25,
                        ),
                    ),
                ]
            ),
        )

    def _quick_tile(
        self,
        title: str,
        subtitle: str,
        icon,
        color: str,
        on_click,
    ) -> ft.Control:
        tile = ft.Container(
            content=ft.Column(
                [
                    ft.Container(
                        width=42,
                        height=42,
                        bgcolor="#FFFFFFB8",
                        border_radius=14,
                        alignment=ft.Alignment.CENTER,
                        content=ft.Icon(icon, color=TEXT, size=23),
                    ),
                    ft.Text(
                        title,
                        size=17,
                        weight=ft.FontWeight.W_700,
                        color=TEXT,
                    ),
                    ft.Text(subtitle, size=12, color=PRIMARY_DARK),
                ],
                spacing=7,
            ),
            padding=16,
            height=146,
            bgcolor=color,
            border_radius=22,
            ink=True,
            ink_color="#1AFFFFFF",
            on_click=on_click,
            animate_scale=160,
            expand=True,
            shadow=ft.BoxShadow(
                blur_radius=18,
                spread_radius=-4,
                color="#164A2C2A",
                offset=ft.Offset(0, 7),
            ),
        )

        def hover(event) -> None:
            tile.scale = 1.018 if str(event.data).lower() == "true" else 1
            tile.update()

        tile.on_hover = hover
        return tile

    def _card(
        self,
        controls: list[ft.Control],
        *,
        bgcolor: str = CARD,
        border_color: str | None = None,
    ) -> ft.Control:
        return ft.Container(
            content=ft.Column(controls=controls, spacing=12),
            padding=18,
            bgcolor=bgcolor,
            border=ft.Border.all(1, border_color) if border_color else None,
            border_radius=22,
            shadow=ft.BoxShadow(
                blur_radius=22,
                spread_radius=-7,
                color=SHADOW,
                offset=ft.Offset(0, 8),
            ),
            animate=180,
        )

    def _primary_button(
        self,
        label: str,
        on_click,
        *,
        icon=None,
        expand: bool = False,
    ) -> ft.Button:
        return ft.Button(
            content=label,
            icon=icon,
            on_click=self._haptic_handler(on_click),
            height=52,
            expand=expand,
            style=ft.ButtonStyle(
                bgcolor={
                    ft.ControlState.DEFAULT: PRIMARY,
                    ft.ControlState.HOVERED: "#E96D3C",
                    ft.ControlState.PRESSED: "#D85F32",
                    ft.ControlState.DISABLED: "#D7C9C1",
                },
                color="#FFFFFF",
                overlay_color="#16FFFFFF",
                elevation={
                    ft.ControlState.DEFAULT: 3,
                    ft.ControlState.HOVERED: 6,
                    ft.ControlState.PRESSED: 1,
                },
                shadow_color="#44F47B4A",
                animation_duration=180,
                shape=ft.RoundedRectangleBorder(radius=17),
                text_style=ft.TextStyle(
                    size=15,
                    weight=ft.FontWeight.W_700,
                ),
            ),
        )

    def _secondary_button(
        self,
        label: str,
        on_click,
        *,
        icon=None,
        expand: bool = False,
        warning: bool = False,
    ) -> ft.Button:
        background = WARNING_SOFT if warning else "#FFFFFF"
        foreground = WARNING if warning else PRIMARY_DARK
        return ft.Button(
            content=label,
            icon=icon,
            on_click=self._haptic_handler(on_click),
            height=50,
            expand=expand,
            style=ft.ButtonStyle(
                bgcolor={
                    ft.ControlState.DEFAULT: background,
                    ft.ControlState.HOVERED: WARNING_SOFT if warning else PRIMARY_SOFT,
                    ft.ControlState.PRESSED: "#F7DED8" if warning else "#F9DED1",
                },
                color=foreground,
                overlay_color="#10000000",
                elevation={
                    ft.ControlState.DEFAULT: 0,
                    ft.ControlState.HOVERED: 2,
                    ft.ControlState.PRESSED: 0,
                },
                side=ft.BorderSide(1, "#E8DCD5"),
                animation_duration=180,
                shape=ft.RoundedRectangleBorder(radius=16),
                text_style=ft.TextStyle(
                    size=14,
                    weight=ft.FontWeight.W_600,
                ),
            ),
        )

    def _show_message(self, message: str, *, warning: bool = False) -> None:
        self.page.show_dialog(
            ft.SnackBar(
                content=ft.Text(message, color="#FFFFFF"),
                bgcolor=WARNING if warning else PRIMARY_DARK,
                show_close_icon=True,
            )
        )

    def _close_dialog(self) -> None:
        self.page.pop_dialog()
        self.page.update()

    def _redirect_for_crisis(self) -> None:
        self.reset_values = {
            "sights": ["", "", "", "", ""],
            "thought": "",
            "facts": "",
            "prediction": "",
            "action": "",
            "track": Track.DSA.value,
        }
        self.crisis_redirected = True
        self.current_view = ViewName.HELP
        self.render()

    # ------------------------------------------------------------------
    # Onboarding
    # ------------------------------------------------------------------

    def _build_onboarding(self, settings: SupportSettings) -> ft.Control:
        acknowledged = ft.Checkbox(value=False)
        trusted_name = ft.TextField(
            label="Trusted person’s name (optional)",
            value=settings.trusted_person_name,
            max_length=100,
        )
        trusted_phone = ft.TextField(
            label="Trusted person’s phone (optional)",
            value=settings.trusted_person_phone,
            keyboard_type=ft.KeyboardType.PHONE,
            max_length=30,
        )
        error_text = ft.Text("", color=WARNING)

        def finish_onboarding() -> None:
            if not acknowledged.value:
                error_text.value = "Please acknowledge the app’s limits to continue."
                self.page.update()
                return
            phone_result = validate_phone(trusted_phone.value)
            if not phone_result.is_valid:
                error_text.value = phone_result.message
                self.page.update()
                return
            self.database.save_settings(
                SupportSettings(
                    trusted_person_name=trusted_name.value.strip(),
                    trusted_person_phone=trusted_phone.value.strip(),
                    disclaimer_acknowledged_at=datetime.now(timezone.utc),
                )
            )
            self.current_view = ViewName.HOME
            self.render()

        return ft.SafeArea(
            content=ft.Container(
                padding=ft.Padding.only(left=20, right=20, top=16),
                content=self._scrolling_column(
                    [
                        ft.Row(
                            [
                                self._brand_mark(48),
                                ft.Text(
                                    "ResetPath",
                                    size=22,
                                    weight=ft.FontWeight.W_700,
                                    color=TEXT,
                                ),
                            ],
                            spacing=12,
                        ),
                        ft.Container(
                            content=ft.Column(
                                [
                                    ft.Text(
                                        "A softer place\nto start again.",
                                        size=38,
                                        weight=ft.FontWeight.W_700,
                                        color=TEXT,
                                    ),
                                    ft.Text(
                                        "Interrupt the spiral, choose one small action, "
                                        "and keep private evidence of your effort.",
                                        size=16,
                                        color=MUTED,
                                    ),
                                    self._calm_face(compact=True),
                                ],
                                spacing=16,
                            ),
                            padding=22,
                            bgcolor=SUN,
                            border_radius=30,
                        ),
                        self._card(
                            [
                                ft.Row(
                                    [
                                        ft.Container(
                                            width=42,
                                            height=42,
                                            bgcolor=SUN_SOFT,
                                            border_radius=14,
                                            alignment=ft.Alignment.CENTER,
                                            content=ft.Icon(
                                                ft.Icons.INFO_OUTLINE_ROUNDED,
                                                color=PRIMARY_DARK,
                                            ),
                                        ),
                                        ft.Text(
                                            "Before you continue",
                                            size=20,
                                            weight=ft.FontWeight.W_700,
                                            expand=True,
                                        ),
                                    ]
                                ),
                                ft.Text(
                                    "ResetPath supports reflection and progress tracking. "
                                    "It does not diagnose mental-health conditions, provide "
                                    "medical treatment, or assess whether you are safe.",
                                    color=MUTED,
                                ),
                                ft.Container(
                                    content=ft.Row(
                                        [
                                            acknowledged,
                                            ft.Text(
                                                "I understand these limits.",
                                                size=14,
                                                color=TEXT,
                                                weight=ft.FontWeight.W_600,
                                                expand=True,
                                            ),
                                        ]
                                    ),
                                    padding=ft.Padding.only(
                                        left=4, right=10, top=4, bottom=4
                                    ),
                                    bgcolor=SURFACE_ALT,
                                    border_radius=14,
                                ),
                            ]
                        ),
                        self._card(
                            [
                                self._section_heading(
                                    "Trusted contact",
                                    "Optional now, editable later in Settings.",
                                ),
                                trusted_name,
                                trusted_phone,
                            ]
                        ),
                        error_text,
                        self._primary_button(
                            "Enter ResetPath",
                            finish_onboarding,
                            icon=ft.Icons.ARROW_FORWARD_ROUNDED,
                        ),
                        self._secondary_button(
                            "Get human help now",
                            self._show_onboarding_help,
                            icon=ft.Icons.FAVORITE_OUTLINE_ROUNDED,
                        ),
                        ft.Text(
                            "Private by design · stored on this device",
                            size=12,
                            color=MUTED,
                            text_align=ft.TextAlign.CENTER,
                        ),
                    ]
                ),
            ),
            expand=True,
        )

    def _show_onboarding_help(self) -> None:
        self.page.show_dialog(
            ft.AlertDialog(
                modal=True,
                title="Human support",
                content=ft.Column(
                    [
                        ft.Text(
                            "ResetPath cannot evaluate whether you are safe. If "
                            "you may act on thoughts of self-harm, contact a "
                            "trusted person, professional support, or local "
                            "emergency service now."
                        ),
                        ft.Text(
                            "Tele-MANAS: 14416",
                            weight=ft.FontWeight.BOLD,
                        ),
                    ],
                    tight=True,
                ),
                actions=[
                    self._primary_button(
                        "Open dialler",
                        lambda: self.page.run_task(
                            self._launch_url, f"tel:{TELE_MANAS_PHONE}"
                        ),
                        icon=ft.Icons.PHONE,
                    ),
                    self._secondary_button("Close", self._close_dialog),
                ],
            )
        )

    # ------------------------------------------------------------------
    # Home
    # ------------------------------------------------------------------

    def _build_home(self) -> ft.Control:
        today_tasks = self.database.list_tasks(
            date_from=date.today(), date_to=date.today()
        )
        completed = [task for task in today_tasks if task.is_completed]
        incomplete = [task for task in today_tasks if not task.is_completed]
        evidence = [
            task.evidence_statement
            for task in self.database.list_tasks(completed=True)
            if task.evidence_statement
        ]

        task_controls: list[ft.Control]
        if incomplete:
            task_controls = [
                ft.Container(
                    content=ft.Row(
                        [
                            ft.Container(
                                width=30,
                                height=30,
                                border=ft.Border.all(2, PRIMARY),
                                shape=ft.BoxShape.CIRCLE,
                                alignment=ft.Alignment.CENTER,
                                content=ft.Text(
                                    str(index + 1),
                                    size=12,
                                    weight=ft.FontWeight.W_700,
                                    color=PRIMARY,
                                ),
                            ),
                            ft.Text(
                                task.title,
                                expand=True,
                                weight=ft.FontWeight.W_600,
                            ),
                            ft.Text(task.track.label, size=11, color=MUTED),
                        ]
                    ),
                    padding=ft.Padding.symmetric(vertical=5),
                )
                for index, task in enumerate(incomplete[:3])
            ]
        else:
            task_controls = [
                ft.Container(
                    content=ft.Row(
                        [
                            ft.Icon(
                                ft.Icons.CELEBRATION_ROUNDED,
                                color=MINT_DARK,
                            ),
                            ft.Text(
                                "Nothing is waiting. Add a tiny step when you are ready.",
                                color=MUTED,
                                expand=True,
                            ),
                        ]
                    ),
                    padding=12,
                    bgcolor="#EAF5F0",
                    border_radius=14,
                )
            ]

        controls = [
            ft.Container(
                content=ft.Column(
                    [
                        ft.Text(
                            "Need a reset?",
                            size=13,
                            color=PRIMARY_DARK,
                            weight=ft.FontWeight.W_600,
                        ),
                        ft.Text(
                            "I’m spiralling",
                            size=31,
                            weight=ft.FontWeight.W_700,
                            color=TEXT,
                        ),
                        ft.Text(
                            "One breath. One next step.",
                            color=PRIMARY_DARK,
                            size=14,
                        ),
                        self._primary_button(
                            "Reset now",
                            self._start_reset,
                            icon=ft.Icons.AIR_ROUNDED,
                        ),
                    ],
                    spacing=10,
                    width=215,
                ),
                padding=20,
                height=278,
                alignment=ft.Alignment.TOP_LEFT,
                bgcolor=SUN_SOFT,
                image=ft.DecorationImage(
                    src="calm_path_background.png",
                    fit=ft.BoxFit.COVER,
                    alignment=ft.Alignment.BOTTOM_CENTER,
                    opacity=0.48,
                ),
                border_radius=30,
                shadow=ft.BoxShadow(
                    blur_radius=28,
                    spread_radius=-8,
                    color="#3AF6C453",
                    offset=ft.Offset(0, 10),
                ),
            ),
            self._section_heading(
                "What would help?",
            ),
            ft.Row(
                [
                    self._quick_tile(
                        "Small step",
                        "Plan today",
                        ft.Icons.CHECK_CIRCLE_OUTLINE_ROUNDED,
                        MINT,
                        lambda: self.go_to(ViewName.TASKS),
                    ),
                    self._quick_tile(
                        "Untangle",
                        "Ground a thought",
                        ft.Icons.EDIT_NOTE_ROUNDED,
                        PRIMARY_SOFT,
                        lambda: self.go_to(ViewName.JOURNAL),
                    ),
                ],
                spacing=12,
                intrinsic_height=True,
            ),
            ft.Container(
                content=ft.Row(
                    [
                        ft.Container(
                            width=54,
                            height=54,
                            bgcolor="#FFFFFF88",
                            shape=ft.BoxShape.CIRCLE,
                            alignment=ft.Alignment.CENTER,
                            content=ft.Icon(
                                ft.Icons.PLAY_ARROW_ROUNDED,
                                color=PRIMARY_DARK,
                                size=30,
                            ),
                        ),
                        ft.Column(
                            [
                                ft.Text(
                                    "A quiet two minutes",
                                    size=18,
                                    weight=ft.FontWeight.W_700,
                                    color=TEXT,
                                ),
                                ft.Text("Quiet visual breathing.", size=12, color=PRIMARY_DARK),
                            ],
                            spacing=3,
                            expand=True,
                        ),
                        ft.Icon(
                            ft.Icons.ARROW_FORWARD_IOS_ROUNDED,
                            color=PRIMARY_DARK,
                            size=17,
                        ),
                    ]
                ),
                padding=16,
                bgcolor=SUN_SOFT,
                border_radius=21,
                ink=True,
                on_click=lambda: self.go_to(ViewName.MEDITATE),
                animate_scale=160,
            ),
            self._card(
                [
                    ft.Row(
                        [
                            ft.Text(
                                "Today’s three",
                                size=21,
                                weight=ft.FontWeight.W_700,
                                expand=True,
                            ),
                            ft.Container(
                                content=ft.Text(
                                    f"{len(completed)} done",
                                    color=MINT_DARK,
                                    weight=ft.FontWeight.W_700,
                                    size=12,
                                ),
                                padding=ft.Padding.symmetric(
                                    horizontal=10, vertical=6
                                ),
                                bgcolor="#EAF5F0",
                                border_radius=10,
                            ),
                        ]
                    ),
                    *task_controls,
                    self._secondary_button(
                        "See all tasks",
                        lambda: self.go_to(ViewName.TASKS),
                        icon=ft.Icons.ARROW_FORWARD_ROUNDED,
                    ),
                ]
            ),
            ft.Container(
                content=ft.Row(
                    [
                        ft.Container(
                            width=46,
                            height=46,
                            bgcolor="#FFFFFF99",
                            border_radius=15,
                            alignment=ft.Alignment.CENTER,
                            content=ft.Icon(
                                ft.Icons.AUTO_GRAPH_ROUNDED,
                                color=MINT_DARK,
                            ),
                        ),
                        ft.Column(
                            [
                                ft.Text(
                                    "Evidence from you",
                                    weight=ft.FontWeight.W_700,
                                    color=TEXT,
                                ),
                                ft.Text(
                                    evidence[0]
                                    if evidence
                                    else "Finished actions will become proof of your effort.",
                                    color=PRIMARY_DARK,
                                    size=13,
                                ),
                            ],
                            spacing=3,
                            expand=True,
                        ),
                    ]
                ),
                padding=17,
                bgcolor=MINT,
                border_radius=22,
                on_click=lambda: self.go_to(ViewName.PROGRESS),
                ink=True,
            ),
            ft.Container(
                content=ft.Row(
                    [
                        ft.Icon(
                            ft.Icons.FAVORITE_BORDER_ROUNDED,
                            color=WARNING,
                        ),
                        ft.Text(
                            "Need a person, not an app?",
                            weight=ft.FontWeight.W_600,
                            color=TEXT,
                            expand=True,
                        ),
                        ft.Icon(
                            ft.Icons.ARROW_FORWARD_IOS_ROUNDED,
                            color=MUTED,
                            size=16,
                        ),
                    ]
                ),
                padding=16,
                bgcolor=CARD,
                border_radius=18,
                on_click=lambda: self.go_to(ViewName.HELP),
                ink=True,
            ),
            ft.Text(
                "One manageable action is enough for today. ResetPath is not medical treatment.",
                size=12,
                color=MUTED,
                text_align=ft.TextAlign.CENTER,
            ),
        ]
        return self._scrolling_column(controls)

    # ------------------------------------------------------------------
    # Tasks
    # ------------------------------------------------------------------

    def _build_tasks(self) -> ft.Control:
        if self.task_filter == "today":
            tasks = self.database.list_tasks(
                date_from=date.today(), date_to=date.today()
            )
        else:
            tasks = self.database.list_tasks()

        filter_row = ft.Row(
            [
                self._primary_button(
                    "Today" if self.task_filter == "today" else "Show today",
                    lambda: self._set_task_filter("today"),
                    expand=True,
                )
                if self.task_filter == "today"
                else self._secondary_button(
                    "Today", lambda: self._set_task_filter("today"), expand=True
                ),
                self._primary_button(
                    "All" if self.task_filter == "all" else "Show all",
                    lambda: self._set_task_filter("all"),
                    expand=True,
                )
                if self.task_filter == "all"
                else self._secondary_button(
                    "All", lambda: self._set_task_filter("all"), expand=True
                ),
            ]
        )

        controls: list[ft.Control] = [
            ft.Container(
                content=ft.Row(
                    [
                        ft.Column(
                            [
                                ft.Text(
                                    "Make it tiny.",
                                    size=25,
                                    weight=ft.FontWeight.W_700,
                                    color=TEXT,
                                ),
                                ft.Text(
                                    "One problem. Ten minutes. One function.",
                                    color=PRIMARY_DARK,
                                    size=14,
                                ),
                            ],
                            spacing=4,
                            expand=True,
                        ),
                        ft.Container(
                            width=60,
                            height=60,
                            bgcolor="#FFFFFF88",
                            shape=ft.BoxShape.CIRCLE,
                            alignment=ft.Alignment.CENTER,
                            content=ft.Icon(
                                ft.Icons.BOLT_ROUNDED,
                                color=PRIMARY_DARK,
                                size=30,
                            ),
                        ),
                    ]
                ),
                padding=18,
                bgcolor=SUN,
                border_radius=24,
            ),
            self._primary_button(
                "Add a small step",
                lambda: self._show_task_dialog(),
                icon=ft.Icons.ADD_ROUNDED,
            ),
            filter_row,
        ]
        if not tasks:
            controls.append(
                self._card(
                    [
                        ft.Text(
                            "A clear page.",
                            size=22,
                            weight=ft.FontWeight.W_700,
                        ),
                        ft.Text(
                            "Add something small enough to start without waiting "
                            "to feel completely ready.",
                            color=MUTED,
                        ),
                        self._calm_face(compact=True),
                    ]
                )
            )
        else:
            controls.extend(self._build_task_card(task) for task in tasks)
        return self._scrolling_column(controls)

    def _set_task_filter(self, value: str) -> None:
        self.task_filter = value
        self.render()

    def _build_task_card(self, task: Task) -> ft.Control:
        subtitle = task.track.label
        if task.estimated_minutes:
            subtitle += f" • {task.estimated_minutes} min"
        if self.task_filter == "all":
            subtitle += f" • {task.planned_date.strftime('%d %b %Y')}"

        checkbox = ft.Checkbox(value=task.is_completed)

        def toggle() -> None:
            if checkbox.value:
                self._show_completion_dialog(task)
            else:
                self.database.set_task_completed(task.id, False)
                self.render()

        checkbox.on_change = toggle
        evidence_controls: list[ft.Control] = []
        if task.evidence_statement:
            evidence_controls.append(
                ft.Container(
                    content=ft.Row(
                        [
                            ft.Icon(
                                ft.Icons.AUTO_GRAPH_ROUNDED,
                                color=MINT_DARK,
                                size=18,
                            ),
                            ft.Text(
                                task.evidence_statement,
                                size=13,
                                color=PRIMARY_DARK,
                                expand=True,
                            ),
                        ]
                    ),
                    padding=12,
                    bgcolor="#EAF5F0",
                    border_radius=14,
                )
            )

        return self._card(
            [
                ft.Row(
                    [
                        checkbox,
                        ft.Column(
                            [
                                ft.Text(
                                    task.title,
                                    weight=ft.FontWeight.W_700,
                                    color=MUTED if task.is_completed else TEXT,
                                ),
                                ft.Container(
                                    content=ft.Text(
                                        subtitle,
                                        size=11,
                                        color=MINT_DARK,
                                        weight=ft.FontWeight.W_600,
                                    ),
                                    padding=ft.Padding.symmetric(
                                        horizontal=8, vertical=4
                                    ),
                                    bgcolor="#EAF5F0",
                                    border_radius=8,
                                ),
                            ],
                            spacing=7,
                            expand=True,
                        ),
                        ft.IconButton(
                            icon=ft.Icons.EDIT_OUTLINED,
                            tooltip="Edit task",
                            on_click=lambda: self._show_task_dialog(task),
                        ),
                        ft.IconButton(
                            icon=ft.Icons.DELETE_OUTLINE,
                            icon_color=WARNING,
                            tooltip="Delete task",
                            on_click=lambda: self._confirm_delete_task(task),
                        ),
                    ]
                ),
                *evidence_controls,
            ]
        )

    def _show_task_dialog(self, task: Task | None = None) -> None:
        title_field = ft.TextField(
            label="Small, specific task",
            value=task.title if task else "",
            max_length=200,
            autofocus=True,
        )
        track_field = ft.Dropdown(
            label="Track",
            value=(task.track.value if task else Track.DSA.value),
            options=[
                ft.DropdownOption(key=track.value, text=track.label) for track in Track
            ],
        )
        date_field = ft.TextField(
            label="Planned date",
            value=(task.planned_date if task else date.today()).isoformat(),
            helper="YYYY-MM-DD",
            max_length=10,
        )
        minutes_field = ft.TextField(
            label="Estimated minutes (optional)",
            value=str(task.estimated_minutes) if task and task.estimated_minutes else "",
            keyboard_type=ft.KeyboardType.NUMBER,
            max_length=3,
        )
        error = ft.Text("", color=WARNING)

        def save_task() -> None:
            if contains_crisis_language(title_field.value):
                self._close_dialog()
                self._redirect_for_crisis()
                return
            try:
                planned_date = date.fromisoformat(date_field.value.strip())
            except ValueError:
                error.value = "Use a valid date in YYYY-MM-DD format."
                self.page.update()
                return
            try:
                minutes = int(minutes_field.value) if minutes_field.value.strip() else None
            except ValueError:
                error.value = "Estimated minutes must be a number."
                self.page.update()
                return
            try:
                selected_track = Track(track_field.value or "")
            except ValueError:
                error.value = "Choose a valid progress track."
                self.page.update()
                return
            result = validate_task(title_field.value, selected_track, minutes)
            if not result.is_valid:
                error.value = result.message
                self.page.update()
                return
            if task:
                self.database.update_task(
                    task.id,
                    title_field.value,
                    selected_track,
                    planned_date,
                    minutes,
                )
            else:
                self.database.add_task(
                    title_field.value,
                    selected_track,
                    planned_date,
                    minutes,
                )
            self._close_dialog()
            self.render()

        self.page.show_dialog(
            ft.AlertDialog(
                modal=True,
                title="Edit task" if task else "Add a task",
                content=ft.Column(
                    [title_field, track_field, date_field, minutes_field, error],
                    tight=True,
                    scroll=ft.ScrollMode.AUTO,
                ),
                actions=[
                    self._secondary_button("Cancel", self._close_dialog),
                    self._primary_button("Save", save_task),
                ],
                scrollable=True,
            )
        )

    def _show_completion_dialog(self, task: Task) -> None:
        note = ft.TextField(
            label="What makes this action meaningful? (optional)",
            multiline=True,
            min_lines=2,
            max_lines=4,
            max_length=1_000,
        )

        def complete() -> None:
            if contains_crisis_language(note.value):
                self._close_dialog()
                self._redirect_for_crisis()
                return
            self.database.set_task_completed(task.id, True, note.value)
            self._close_dialog()
            self.render()

        self.page.show_dialog(
            ft.AlertDialog(
                modal=True,
                title="Turn this into evidence",
                content=ft.Column(
                    [
                        ft.Text(
                            f'You completed “{task.title}”.',
                            weight=ft.FontWeight.BOLD,
                        ),
                        note,
                    ],
                    tight=True,
                ),
                actions=[
                    self._secondary_button("Cancel", self._close_dialog),
                    self._primary_button("Complete task", complete),
                ],
            )
        )

    def _confirm_delete_task(self, task: Task) -> None:
        def delete() -> None:
            self.database.delete_task(task.id)
            self._close_dialog()
            self.render()

        self.page.show_dialog(
            ft.AlertDialog(
                modal=True,
                title="Delete this task?",
                content=ft.Text(
                    f'“{task.title}” and its evidence statement will be removed.'
                ),
                actions=[
                    self._secondary_button("Cancel", self._close_dialog),
                    self._secondary_button(
                        "Delete", delete, icon=ft.Icons.DELETE_OUTLINE, warning=True
                    ),
                ],
            )
        )

    # ------------------------------------------------------------------
    # Thought journal
    # ------------------------------------------------------------------

    def _build_journal(self) -> ft.Control:
        # The default journal is deliberately a blank page. Guided reframing is
        # available only when the person asks for it below.
        if self.journal_step == 0:
            return self._build_diary()
        entries = self.database.list_thought_entries(limit=5)
        controls: list[ft.Control] = [
            ft.Container(
                content=ft.Row(
                    [
                        ft.Column(
                            [
                                ft.Text(
                                    "Let’s untangle it.",
                                    size=25,
                                    weight=ft.FontWeight.W_700,
                                    color=TEXT,
                                ),
                                ft.Text(
                                    "One gentle question at a time.",
                                    color=PRIMARY_DARK,
                                    size=14,
                                ),
                            ],
                            spacing=5,
                            expand=True,
                        ),
                        ft.Container(
                            width=62,
                            height=62,
                            bgcolor="#FFFFFF90",
                            border_radius=20,
                            alignment=ft.Alignment.CENTER,
                            content=ft.Icon(
                                ft.Icons.CHAT_BUBBLE_OUTLINE_ROUNDED,
                                color=PRIMARY_DARK,
                                size=32,
                            ),
                        ),
                    ]
                ),
                padding=19,
                bgcolor=PRIMARY_SOFT,
                border_radius=25,
            ),
        ]

        if self.journal_step == 0:
            controls.extend(
                [
                    ft.Container(
                        content=ft.Column(
                            [
                                ft.Text(
                                    "Say the thought as it is.",
                                    size=21,
                                    weight=ft.FontWeight.W_700,
                                    color=TEXT,
                                ),
                                ft.Text(
                                    "We’ll slow it down together.",
                                    color=MUTED,
                                ),
                                self._primary_button(
                                    "Tell me what is happening",
                                    self._start_journal,
                                    icon=ft.Icons.ARROW_FORWARD_ROUNDED,
                                ),
                                self._secondary_button(
                                    "Use voice typing",
                                    self._show_voice_input_info,
                                    icon=ft.Icons.MIC_ROUNDED,
                                ),
                            ],
                            spacing=14,
                        ),
                        padding=21,
                        bgcolor=SUN_SOFT,
                        border_radius=26,
                    ),
                    ft.Text(
            "Private, local, and non-diagnostic.",
                        color=MUTED,
                        size=12,
                    ),
                    self._section_heading(
                        "Earlier reflections",
                        "Only entries saved on this device.",
                    ),
                ]
            )
            if not entries:
                controls.append(
                    ft.Container(
                        content=ft.Row(
                            [
                                ft.Icon(
                                    ft.Icons.EDIT_NOTE_ROUNDED,
                                    color=PRIMARY,
                                ),
                                ft.Text(
                                    "Your first reflection will appear here.",
                                    color=MUTED,
                                    expand=True,
                                ),
                            ]
                        ),
                        padding=17,
                        bgcolor=CARD,
                        border_radius=18,
                    )
                )
            else:
                for entry in entries:
                    controls.append(
                        ft.Container(
                            content=ft.Column(
                                [
                                    ft.Text(
                                        entry.created_at.astimezone().strftime(
                                            "%d %b · %I:%M %p"
                                        ),
                                        size=11,
                                        color=MUTED,
                                    ),
                                    ft.Text(
                                        entry.thought,
                                        weight=ft.FontWeight.W_700,
                                        size=16,
                                    ),
                                    ft.Text(
                                        entry.grounded_response,
                                        size=13,
                                        color=PRIMARY_DARK,
                                        max_lines=4,
                                        overflow=ft.TextOverflow.ELLIPSIS,
                                    ),
                                ],
                                spacing=8,
                            ),
                            padding=18,
                            bgcolor=SUN_SOFT,
                            border_radius=22,
                        )
                    )
        elif self.journal_step == 1:
            controls.extend(self._build_journal_thought_step())
        elif self.journal_step == 2:
            controls.extend(self._build_journal_emotion_step())
        else:
            controls.extend(self._build_journal_plan_step())

        return self._scrolling_column(controls)

    def _build_diary(self) -> ft.Control:
        """A calm free-form notebook, separate from the guided thought tool."""
        pages = self.database.list_diary_entries(limit=8)
        page = ft.TextField(
            value=self.diary_draft,
            hint_text="Write without fixing it. This page is yours.",
            multiline=True,
            min_lines=13,
            max_lines=20,
            max_length=8_000,
            autofocus=self.diary_editing_id is None,
            border=ft.InputBorder.NONE,
            bgcolor="transparent",
            text_size=17,
        )

        def save_page() -> None:
            if contains_crisis_language(page.value):
                self._redirect_for_crisis()
                return
            try:
                self.database.save_diary_entry(page.value, self.diary_editing_id)
            except ValueError as error:
                self._show_message(str(error), warning=True)
                return
            self.diary_draft = ""
            self.diary_editing_id = None
            self._show_message("Page saved privately.")
            self.render()

        def new_page() -> None:
            self.diary_editing_id = None
            self.diary_draft = ""
            self.render()

        def open_page(entry_id: int) -> None:
            entry = self.database.get_diary_entry(entry_id)
            if entry:
                self.diary_editing_id = entry.id
                self.diary_draft = entry.body
                self.render()

        controls: list[ft.Control] = [
            ft.Text("A page for today.", size=27, weight=ft.FontWeight.W_700, color=TEXT),
            ft.Text(
                "Private writing. No prompts, scores, or automatic analysis.",
                color=MUTED,
            ),
            ft.Container(
                content=page,
                padding=ft.Padding.only(left=18, right=18, top=16, bottom=10),
                bgcolor=CARD,
                border=ft.Border(left=ft.BorderSide(3, PRIMARY_SOFT)),
                border_radius=14,
                shadow=ft.BoxShadow(blur_radius=18, color=SHADOW, offset=ft.Offset(0, 5)),
            ),
            ft.Row(
                [
                    self._secondary_button("Voice type", self._show_voice_input_info, icon=ft.Icons.MIC_ROUNDED),
                    self._secondary_button("New", new_page, icon=ft.Icons.ADD_ROUNDED),
                    self._primary_button("Save page", save_page, icon=ft.Icons.SAVE_ROUNDED, expand=True),
                ],
                spacing=8,
            ),
            self._secondary_button(
                "Need structure? Unpack one thought",
                self._start_journal,
                icon=ft.Icons.AUTO_AWESOME_OUTLINED,
            ),
            self._section_heading("Previous pages", "Tap a page to continue writing."),
        ]
        if not pages:
            controls.append(ft.Text("Nothing saved yet. Start wherever you are.", color=MUTED))
        for entry in pages:
            preview = entry.body.replace("\n", " ").strip()
            controls.append(
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Text(entry.updated_at.astimezone().strftime("%d %b · %I:%M %p"), size=11, color=MUTED),
                            ft.Text(preview, size=15, max_lines=2, overflow=ft.TextOverflow.ELLIPSIS),
                        ],
                        spacing=5,
                    ),
                    padding=15,
                    bgcolor=SURFACE_ALT,
                    border_radius=15,
                    ink=True,
                    on_click=lambda _event, entry_id=entry.id: open_page(entry_id),
                )
            )
        return self._scrolling_column(controls)

    def _start_journal(self) -> None:
        self.journal_step = 1
        self.journal_values = {
            "thought": "", "emotion": "", "action": "",
            "use_diary_context": False, "diary_context": (), "model_route": "",
        }
        self.journal_plan = None
        self.render()

    def _journal_step_header(self, current: int, prompt: str) -> ft.Control:
        return ft.Column(
            [
                ft.Row(
                    [
                        ft.Text(
                            f"{current} / 3",
                            color=PRIMARY,
                            weight=ft.FontWeight.W_700,
                            expand=True,
                        ),
                        ft.Button(
                            content="Start over",
                            on_click=self._reset_journal,
                            style=ft.ButtonStyle(
                                color=MUTED,
                                elevation=0,
                                padding=4,
                            ),
                        ),
                    ]
                ),
                ft.ProgressBar(
                    value=current / 3,
                    height=6,
                    color=PRIMARY,
                    bgcolor="#E8DED7",
                    border_radius=4,
                ),
                ft.Text(
                    prompt,
                    size=26,
                    weight=ft.FontWeight.W_700,
                    color=TEXT,
                ),
            ],
            spacing=12,
        )

    def _build_journal_thought_step(self) -> list[ft.Control]:
        field = ft.TextField(
            hint_text="For example: Everyone is moving ahead and I am stuck…",
            value=str(self.journal_values["thought"]),
            multiline=True,
            min_lines=5,
            max_lines=8,
            max_length=2_000,
            autofocus=True,
            border_color="#DDCEC4",
            focused_border_color=PRIMARY,
            border_radius=20,
            bgcolor=CARD,
        )
        error = ft.Text("", color=WARNING)
        use_diary_context = ft.Checkbox(
            label="Use relevant private diary pages for this one response",
            value=bool(self.journal_values.get("use_diary_context", False)),
        )

        async def voice_type() -> None:
            try:
                await field.focus()
            except Exception:
                pass
            self._show_voice_input_info()

        def continue_flow() -> None:
            value = field.value.strip()
            if contains_crisis_language(value):
                field.value = ""
                self._reset_journal(render=False)
                self._redirect_for_crisis()
                return
            if len(value) < 3:
                error.value = "Add the thought in your own words."
                self.page.update()
                return
            self.journal_values["thought"] = value
            self.journal_values["use_diary_context"] = bool(use_diary_context.value)
            route = classify_emotion(value)
            self.journal_values["model_route"] = route.label if route else ""
            self.journal_values["diary_context"] = (
                retrieve_diary_context(
                    value,
                    [entry.body for entry in self.database.list_diary_entries(limit=50)],
                )
                if use_diary_context.value
                else ()
            )
            self.journal_step = 2
            self.render()

        return [
            self._journal_step_header(1, "What is your mind saying right now?"),
            ft.Container(
                content=ft.Row(
                    [
                        self._brand_mark(38),
                        ft.Text(
                            "It can be messy, short, or unfinished.",
                            color=PRIMARY_DARK,
                            size=14,
                            expand=True,
                        ),
                    ]
                ),
                padding=14,
                bgcolor=PRIMARY_SOFT,
                border_radius=18,
            ),
            field,
            use_diary_context,
            error,
            ft.Row(
                [
                    self._secondary_button(
                        "Voice type",
                        voice_type,
                        icon=ft.Icons.MIC_ROUNDED,
                    ),
                    self._primary_button(
                        "Continue",
                        continue_flow,
                        icon=ft.Icons.ARROW_FORWARD_ROUNDED,
                        expand=True,
                    ),
                ],
                spacing=10,
            ),
        ]

    def _build_journal_emotion_step(self) -> list[ft.Control]:
        choices = (
            ("Anxious", ft.Icons.WAVES_ROUNDED),
            ("Overwhelmed", ft.Icons.CLOUD_OUTLINED),
            ("Afraid", ft.Icons.VISIBILITY_OFF_OUTLINED),
            ("Frustrated", ft.Icons.FLASH_ON_ROUNDED),
            ("Sad", ft.Icons.WATER_DROP_OUTLINED),
            ("Uncertain", ft.Icons.HELP_OUTLINE_ROUNDED),
        )

        def choose(value: str) -> None:
            self.journal_values["emotion"] = value
            self.journal_plan = build_support_plan(
                str(self.journal_values["thought"]),
                value,
            )
            self.journal_step = 3
            try:
                self.page.run_task(self.haptics.selection_click)
            except Exception:
                pass
            self.render()

        def choose_callback(value: str):
            def callback() -> None:
                choose(value)

            return callback

        tiles: list[ft.Control] = []
        for label, icon in choices:
            tile = ft.Container(
                content=ft.Row(
                    [
                        ft.Icon(icon, color=PRIMARY_DARK, size=22),
                        ft.Text(
                            label,
                            weight=ft.FontWeight.W_600,
                            color=TEXT,
                            expand=True,
                        ),
                        ft.Icon(
                            ft.Icons.ARROW_FORWARD_IOS_ROUNDED,
                            color=MUTED,
                            size=14,
                        ),
                    ]
                ),
                padding=16,
                bgcolor=CARD,
                border_radius=18,
                ink=True,
                on_click=choose_callback(label),
                animate_scale=150,
            )
            tiles.append(tile)

        controls: list[ft.Control] = [
            self._journal_step_header(2, "Which feeling is closest?"),
            ft.Text(
                "You do not have to name it perfectly. Choose the nearest word.",
                color=MUTED,
            ),
        ]
        if route := str(self.journal_values.get("model_route", "")):
            controls.append(
                ft.Container(
                    content=ft.Text(
                        f"Private on-device tone signal: {route.title()}. You decide what fits.",
                        color=PRIMARY_DARK,
                        size=13,
                    ),
                    padding=12,
                    bgcolor=PRIMARY_SOFT,
                    border_radius=14,
                )
            )
        controls.extend(tiles)
        return controls

    def _build_journal_plan_step(self) -> list[ft.Control]:
        plan = self.journal_plan or build_support_plan(
            str(self.journal_values["thought"]),
            str(self.journal_values["emotion"] or "Uncertain"),
        )

        def select_action(action: str) -> None:
            self.journal_values["action"] = action
            try:
                self.page.run_task(self.haptics.selection_click)
            except Exception:
                pass
            self.render()

        def action_callback(action: str):
            def callback() -> None:
                select_action(action)

            return callback

        action_controls: list[ft.Control] = []
        for index, action in enumerate(plan.actions):
            selected = self.journal_values["action"] == action
            action_controls.append(
                ft.Container(
                    content=ft.Row(
                        [
                            ft.Container(
                                width=34,
                                height=34,
                                shape=ft.BoxShape.CIRCLE,
                                bgcolor=PRIMARY if selected else "#FFFFFF",
                                alignment=ft.Alignment.CENTER,
                                content=ft.Text(
                                    str(index + 1),
                                    color="#FFFFFF" if selected else PRIMARY,
                                    weight=ft.FontWeight.W_700,
                                ),
                            ),
                            ft.Text(
                                action,
                                color=TEXT,
                                weight=ft.FontWeight.W_600,
                                expand=True,
                            ),
                        ]
                    ),
                    padding=15,
                    bgcolor=PRIMARY_SOFT if selected else CARD,
                    border=ft.Border.all(2 if selected else 1, PRIMARY if selected else BORDER),
                    border_radius=18,
                    ink=True,
                    on_click=action_callback(action),
                    animate=180,
                )
            )

        save_button = self._primary_button(
            "Save this reflection",
            self._save_conversational_reflection,
            icon=ft.Icons.BOOKMARK_ADD_ROUNDED,
        )
        save_button.disabled = not bool(self.journal_values["action"])

        controls: list[ft.Control] = [
            self._journal_step_header(3, "Here is a steadier way to hold it."),
            ft.Container(
                content=ft.Column(
                    [
                        ft.Text(
                            plan.acknowledgement,
                            size=17,
                            weight=ft.FontWeight.W_600,
                            color=TEXT,
                        ),
                        ft.Container(height=1, bgcolor="#E7D7CC"),
                        ft.Text(
                            plan.grounded_reframe,
                            size=16,
                            color=PRIMARY_DARK,
                        ),
                    ],
                    spacing=14,
                ),
                padding=20,
                bgcolor=SUN_SOFT,
                border_radius=26,
            ),
            ft.Row(
                [
                    ft.Icon(ft.Icons.LIBRARY_BOOKS_OUTLINED, size=15, color=MUTED),
                    ft.Text(
                        f"Reviewed local guide · {plan.source_title}",
                        size=11,
                        color=MUTED,
                    ),
                ],
                spacing=6,
            ),
            self._section_heading(
                "What could help now?",
                "Choose one. You are not committing to the whole day.",
            ),
            *action_controls,
        ]
        context = tuple(self.journal_values.get("diary_context", ()))
        if context:
            controls.append(
                self._card(
                    [
                        ft.Text("Selected private context", weight=ft.FontWeight.W_700),
                        ft.Text(
                            "Matching words from pages you chose to use. This is context, not evidence or a diagnosis.",
                            color=MUTED,
                            size=12,
                        ),
                        *[ft.Text(f"“{snippet}”", color=PRIMARY_DARK, size=13) for snippet in context],
                    ],
                    bgcolor=SUN_SOFT,
                )
            )
        controls.extend([
            save_button,
            ft.Text(
                "Suggestions are supportive options, not medical advice.",
                size=11,
                color=MUTED,
                text_align=ft.TextAlign.CENTER,
            ),
        ])
        return controls

    def _save_conversational_reflection(self) -> None:
        plan = self.journal_plan
        action = str(self.journal_values["action"])
        if not plan or not action:
            return
        thought = str(self.journal_values["thought"])
        emotion = str(self.journal_values["emotion"])
        response = (
            f"{plan.acknowledgement}\n\n{plan.grounded_reframe}\n\n"
            f"One option for now: {action}"
        )
        self.database.save_thought_entry(
            thought,
            emotion,
            plan.evidence_for,
            plan.evidence_against,
            action,
            response,
        )
        self._reset_journal(render=False)
        self._show_message("Reflection saved privately.")
        self.render()

    def _reset_journal(self, _event=None, *, render: bool = True) -> None:
        self.journal_step = 0
        self.journal_values = {
            "thought": "", "emotion": "", "action": "",
            "use_diary_context": False, "diary_context": (), "model_route": "",
        }
        self.journal_plan = None
        if render:
            self.render()

    def _show_voice_input_info(self) -> None:
        self.page.show_dialog(
            ft.AlertDialog(
                modal=True,
                title="Voice typing",
                content=ft.Column(
                    [
                        ft.Text(
                            "Tap the microphone on your phone keyboard and speak. "
                            "Your keyboard provider performs the transcription."
                        ),
                        ft.Text(
                            "ResetPath receives only the resulting text. Check your "
                            "keyboard’s privacy settings if you require offline typing.",
                            color=MUTED,
                        ),
                        ft.Container(
                            content=ft.Text(
                                "ResetPath does not record or save microphone audio.",
                                size=13,
                                color=MINT_DARK,
                                weight=ft.FontWeight.W_600,
                            ),
                            padding=12,
                            bgcolor="#EAF5F0",
                            border_radius=14,
                        ),
                    ],
                    tight=True,
                    spacing=12,
                ),
                actions=[
                    self._primary_button("Understood", self._close_dialog),
                ],
            )
        )

    # ------------------------------------------------------------------
    # Reset flow
    # ------------------------------------------------------------------

    def _start_reset(self) -> None:
        self.reset_step = 0
        self.breathing_cancelled = False
        self.breathing_paused = False
        self.current_view = ViewName.RESET
        self.render()

    def _build_reset(self) -> ft.Control:
        step_titles = [
            "Slow down",
            "Notice five things",
            "Name the thought",
            "Facts and prediction",
            "Choose one action",
        ]
        controls: list[ft.Control] = [
            ft.Container(
                content=ft.Row(
                    [
                        ft.Container(
                            width=42,
                            height=42,
                            bgcolor=PRIMARY,
                            shape=ft.BoxShape.CIRCLE,
                            alignment=ft.Alignment.CENTER,
                            content=ft.Text(
                                str(self.reset_step + 1),
                                color="#FFFFFF",
                                weight=ft.FontWeight.W_700,
                            ),
                        ),
                        ft.Column(
                            [
                                ft.Text(
                                    f"Step {self.reset_step + 1} of 5",
                                    size=12,
                                    color=MUTED,
                                    weight=ft.FontWeight.W_600,
                                ),
                                ft.Text(
                                    step_titles[self.reset_step],
                                    size=21,
                                    color=TEXT,
                                    weight=ft.FontWeight.W_700,
                                ),
                            ],
                            spacing=1,
                            expand=True,
                        ),
                    ]
                ),
                padding=14,
                bgcolor=CARD,
                border_radius=19,
            ),
            ft.ProgressBar(
                value=(self.reset_step + 1) / 5,
                color=PRIMARY,
                bgcolor="#E8DED7",
                height=7,
                border_radius=4,
            ),
        ]
        controls.append(
            [
                self._build_breathing_step,
                self._build_sights_step,
                self._build_thought_step,
                self._build_facts_step,
                self._build_action_step,
            ][self.reset_step]()
        )
        return self._scrolling_column(controls)

    def _build_breathing_step(self) -> ft.Control:
        self.breath_status = ft.Text(
            "When you are ready, begin five gentle cycles.",
            size=18,
            weight=ft.FontWeight.W_600,
            text_align=ft.TextAlign.CENTER,
        )
        self.breath_progress = ft.ProgressRing(
            value=0,
            width=220,
            height=220,
            stroke_width=5,
            color=PRIMARY,
            bgcolor="#EADFD8",
        )
        self.breath_orb_label = ft.Text(
            "Ready",
            size=20,
            weight=ft.FontWeight.W_700,
            color=PRIMARY_DARK,
            text_align=ft.TextAlign.CENTER,
        )
        self.breath_orb = ft.Container(
            width=152,
            height=152,
            bgcolor=SUN,
            shape=ft.BoxShape.CIRCLE,
            alignment=ft.Alignment.CENTER,
            scale=0.88,
            animate_scale=900,
            animate=500,
            content=ft.Column(
                [
                    ft.Icon(
                        ft.Icons.SENTIMENT_SATISFIED_ROUNDED,
                        color=PRIMARY_DARK,
                        size=58,
                    ),
                    self.breath_orb_label,
                ],
                spacing=0,
                tight=True,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            shadow=ft.BoxShadow(
                blur_radius=36,
                spread_radius=2,
                color="#40F6C453",
                offset=ft.Offset(0, 10),
            ),
        )
        self.breath_start_button = self._primary_button(
            "Begin breathing",
            self._begin_breathing,
            icon=ft.Icons.PLAY_ARROW,
        )
        self.breath_pause_button = self._secondary_button(
            "Pause",
            self._toggle_breathing_pause,
            icon=ft.Icons.PAUSE,
        )
        self.breath_pause_button.disabled = True
        return self._card(
            [
                ft.Container(
                    content=ft.Stack(
                        [
                            self.breath_progress,
                            self.breath_orb,
                        ],
                        width=230,
                        height=230,
                        alignment=ft.Alignment.CENTER,
                    ),
                    alignment=ft.Alignment.CENTER,
                ),
                self.breath_status,
                ft.Text(
                    "Follow the circle without forcing your breath. There is no "
                    "breath hold. Stop if this feels uncomfortable.",
                    color=MUTED,
                    size=13,
                    text_align=ft.TextAlign.CENTER,
                ),
                self.breath_start_button,
                ft.Row(
                    [
                        self.breath_pause_button,
                        self._secondary_button(
                            "Skip",
                            lambda: self._cancel_breathing(advance=True),
                            expand=True,
                        ),
                        self._secondary_button(
                            "Stop",
                            lambda: self._cancel_breathing(advance=False),
                            expand=True,
                            warning=True,
                        ),
                    ]
                ),
            ]
        )

    async def _begin_breathing(self) -> None:
        if self.breathing_running:
            return
        self.breathing_running = True
        self.breathing_cancelled = False
        self.breathing_paused = False
        assert self.breath_pause_button is not None
        assert self.breath_start_button is not None
        self.breath_pause_button.disabled = False
        self.breath_start_button.disabled = True
        self.page.update()

        phases = (("Breathe in", 4), ("Breathe out", 6))
        elapsed = 0
        total = 50
        for cycle in range(1, 6):
            for phase, seconds in phases:
                if self.breath_orb:
                    self.breath_orb.animate_scale = seconds * 1000
                    self.breath_orb.scale = 1.16 if phase == "Breathe in" else 0.88
                    self.breath_orb.bgcolor = SUN if phase == "Breathe in" else PRIMARY_SOFT
                if self.breath_orb_label:
                    self.breath_orb_label.value = (
                        "Breathe in" if phase == "Breathe in" else "Breathe out"
                    )
                self.page.update()
                for remaining in range(seconds, 0, -1):
                    while self.breathing_paused and not self.breathing_cancelled:
                        await asyncio.sleep(0.2)
                    if self.breathing_cancelled:
                        self.breathing_running = False
                        return
                    assert self.breath_status is not None
                    assert self.breath_progress is not None
                    self.breath_status.value = (
                        f"{phase} • {remaining} • cycle {cycle} of 5"
                    )
                    self.breath_progress.value = elapsed / total
                    self.page.update()
                    await asyncio.sleep(1)
                    elapsed += 1

        self.breathing_running = False
        if self.breath_status:
            self.breath_status.value = "Breathing practice complete."
        if self.breath_progress:
            self.breath_progress.value = 1
        if self.breath_orb:
            self.breath_orb.animate_scale = 500
            self.breath_orb.scale = 1
            self.breath_orb.bgcolor = MINT
        if self.breath_orb_label:
            self.breath_orb_label.value = "Complete"
        self.page.update()
        await asyncio.sleep(0.7)
        self.reset_step = 1
        self.render()

    def _toggle_breathing_pause(self) -> None:
        if not self.breathing_running:
            return
        self.breathing_paused = not self.breathing_paused
        if self.breath_pause_button:
            self.breath_pause_button.content = (
                "Resume" if self.breathing_paused else "Pause"
            )
            self.breath_pause_button.icon = (
                ft.Icons.PLAY_ARROW if self.breathing_paused else ft.Icons.PAUSE
            )
        if self.breath_status and self.breathing_paused:
            self.breath_status.value = "Paused. Continue when you are ready."
        if self.breath_orb_label:
            self.breath_orb_label.value = (
                "Paused" if self.breathing_paused else "Continue"
            )
        self.page.update()

    def _cancel_breathing(self, *, advance: bool) -> None:
        self.breathing_cancelled = True
        self.breathing_running = False
        if advance:
            self.reset_step = 1
            self.render()
        else:
            self.go_to(ViewName.HOME)

    def _build_sights_step(self) -> ft.Control:
        fields = [
            ft.TextField(
                label=f"Thing {index + 1}",
                value=str(self.reset_values["sights"][index]),
                max_length=200,
            )
            for index in range(5)
        ]
        error = ft.Text("", color=WARNING)

        def next_step() -> None:
            values = [field.value.strip() for field in fields]
            if contains_crisis_language(*values):
                self._redirect_for_crisis()
                return
            if any(not value for value in values):
                error.value = "Name five things you can see, even very small ones."
                self.page.update()
                return
            self.reset_values["sights"] = values
            self.reset_step = 2
            self.render()

        return self._card(
            [
                ft.Text(
                    "Look around slowly and name five things you can see.",
                    size=18,
                    weight=ft.FontWeight.BOLD,
                ),
                *fields,
                error,
                self._wizard_navigation(next_step),
            ]
        )

    def _build_thought_step(self) -> ft.Control:
        field = ft.TextField(
            label="What frightening thought is your mind giving you?",
            value=str(self.reset_values["thought"]),
            multiline=True,
            min_lines=3,
            max_lines=5,
            max_length=2_000,
        )
        error = ft.Text("", color=WARNING)

        def next_step() -> None:
            if not field.value.strip():
                error.value = "Write the thought in your own words."
                self.page.update()
                return
            if contains_crisis_language(field.value):
                field.value = ""
                self._redirect_for_crisis()
                return
            self.reset_values["thought"] = field.value.strip()
            self.reset_step = 3
            self.render()

        return self._card(
            [
                ft.Text(
                    "Name the thought without treating it as a confirmed result.",
                    size=18,
                    weight=ft.FontWeight.BOLD,
                ),
                field,
                error,
                self._wizard_navigation(next_step),
            ]
        )

    def _build_facts_step(self) -> ft.Control:
        facts = ft.TextField(
            label="What facts do you know right now?",
            value=str(self.reset_values["facts"]),
            multiline=True,
            min_lines=3,
            max_lines=5,
            max_length=3_000,
        )
        prediction = ft.TextField(
            label="What is your mind predicting?",
            value=str(self.reset_values["prediction"]),
            multiline=True,
            min_lines=3,
            max_lines=5,
            max_length=3_000,
        )
        error = ft.Text("", color=WARNING)

        def next_step() -> None:
            if contains_crisis_language(facts.value, prediction.value):
                self._redirect_for_crisis()
                return
            if not facts.value.strip() or not prediction.value.strip():
                error.value = "Add both what is known and what is being predicted."
                self.page.update()
                return
            self.reset_values["facts"] = facts.value.strip()
            self.reset_values["prediction"] = prediction.value.strip()
            self.reset_step = 4
            self.render()

        return self._card(
            [
                ft.Text(
                    "Separate what is known from what fear is forecasting.",
                    size=18,
                    weight=ft.FontWeight.BOLD,
                ),
                facts,
                prediction,
                error,
                self._wizard_navigation(next_step),
            ]
        )

    def _build_action_step(self) -> ft.Control:
        action = ft.TextField(
            label="One realistic ten-minute action",
            value=str(self.reset_values["action"]),
            multiline=True,
            min_lines=2,
            max_lines=4,
            max_length=500,
        )
        track = ft.Dropdown(
            label="Track",
            value=str(self.reset_values["track"]),
            options=[
                ft.DropdownOption(key=item.value, text=item.label) for item in Track
            ],
        )
        error = ft.Text("", color=WARNING)

        def finish(save_task: bool) -> None:
            if contains_crisis_language(action.value):
                self._redirect_for_crisis()
                return
            if not action.value.strip():
                error.value = "Choose one action small enough to begin."
                self.page.update()
                return
            selected_track = Track(track.value or Track.DSA.value)
            if save_task:
                self.database.add_task(
                    action.value,
                    selected_track,
                    date.today(),
                    10,
                )
            self._show_reset_summary(action.value, save_task)

        return self._card(
            [
                ft.Text(
                    "Choose one action you control—not the whole outcome.",
                    size=18,
                    weight=ft.FontWeight.BOLD,
                ),
                action,
                track,
                error,
                self._primary_button(
                    "Save action to Today’s Tasks",
                    lambda: finish(True),
                    icon=ft.Icons.ADD_TASK,
                ),
                self._secondary_button(
                    "Finish without saving",
                    lambda: finish(False),
                ),
                self._secondary_button(
                    "Back",
                    lambda: self._move_reset_step(-1),
                    icon=ft.Icons.ARROW_BACK,
                ),
            ]
        )

    def _wizard_navigation(self, next_action) -> ft.Control:
        return ft.Row(
            [
                self._secondary_button(
                    "Back",
                    lambda: self._move_reset_step(-1),
                    icon=ft.Icons.ARROW_BACK,
                    expand=True,
                ),
                self._primary_button(
                    "Continue",
                    next_action,
                    icon=ft.Icons.ARROW_FORWARD,
                    expand=True,
                ),
            ]
        )

    def _move_reset_step(self, amount: int) -> None:
        self.reset_step = max(0, min(4, self.reset_step + amount))
        self.render()

    def _show_reset_summary(self, action: str, saved: bool) -> None:
        def finish() -> None:
            self._close_dialog()
            self.go_to(ViewName.TASKS if saved else ViewName.HOME)

        self.page.show_dialog(
            ft.AlertDialog(
                modal=True,
                title="You chose a next step",
                content=ft.Column(
                    [
                        ft.Text(
                            "Your thought is not being treated as a confirmed result.",
                            color=MUTED,
                        ),
                        ft.Container(
                            content=ft.Text(action, weight=ft.FontWeight.BOLD),
                            padding=12,
                            bgcolor=PRIMARY_SOFT,
                            border_radius=12,
                        ),
                    ],
                    tight=True,
                ),
                actions=[self._primary_button("Done", finish)],
            )
        )

    # ------------------------------------------------------------------
    # Quiet meditation
    # ------------------------------------------------------------------

    def _build_meditate(self) -> ft.Control:
        total_seconds = self.meditation_minutes * 60
        self.meditation_status = ft.Text(
            "Settle into a position that feels supportive.",
            size=19,
            weight=ft.FontWeight.W_600,
            color=TEXT,
            text_align=ft.TextAlign.CENTER,
        )
        self.meditation_timer = ft.Text(
            f"{self.meditation_minutes:02d}:00",
            size=32,
            weight=ft.FontWeight.W_700,
            color=PRIMARY_DARK,
        )
        self.meditation_orb = ft.Container(
            width=190,
            height=190,
            shape=ft.BoxShape.CIRCLE,
            bgcolor=SUN,
            scale=0.92,
            animate_scale=4000,
            animate=500,
            alignment=ft.Alignment.CENTER,
            content=ft.Column(
                [
                    ft.Icon(
                        ft.Icons.SPA_ROUNDED,
                        color=PRIMARY_DARK,
                        size=64,
                    ),
                    self.meditation_timer,
                ],
                tight=True,
                spacing=2,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            shadow=ft.BoxShadow(
                blur_radius=46,
                spread_radius=5,
                color="#45F6C453",
                offset=ft.Offset(0, 12),
            ),
        )
        self.meditation_start_button = self._primary_button(
            "Begin quietly",
            self._begin_meditation,
            icon=ft.Icons.PLAY_ARROW_ROUNDED,
        )
        self.meditation_pause_button = self._secondary_button(
            "Pause",
            self._toggle_meditation_pause,
            icon=ft.Icons.PAUSE_ROUNDED,
            expand=True,
        )
        self.meditation_pause_button.disabled = True

        def duration_callback(minutes: int):
            def callback() -> None:
                self._set_meditation_minutes(minutes)

            return callback

        duration_controls: list[ft.Control] = []
        for minutes in (2, 5, 10):
            selected = minutes == self.meditation_minutes
            button = (
                self._primary_button(
                    f"{minutes} min",
                    duration_callback(minutes),
                    expand=True,
                )
                if selected
                else self._secondary_button(
                    f"{minutes} min",
                    duration_callback(minutes),
                    expand=True,
                )
            )
            duration_controls.append(button)

        return self._scrolling_column(
            [
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Text(
                                "Nothing to achieve.",
                                size=28,
                                weight=ft.FontWeight.W_700,
                                color=TEXT,
                                text_align=ft.TextAlign.CENTER,
                            ),
                            ft.Text(
                                "Let the animation set the pace. Sounds, thoughts, "
                                "and feelings can come and go without being fixed.",
                                color=PRIMARY_DARK,
                                text_align=ft.TextAlign.CENTER,
                            ),
                            ft.Container(
                                content=self.meditation_orb,
                                height=250,
                                alignment=ft.Alignment.CENTER,
                            ),
                            self.meditation_status,
                        ],
                        spacing=16,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    padding=22,
                    bgcolor=SUN_SOFT,
                    border_radius=30,
                ),
                self._section_heading(
                    "Choose a length",
                    "You can stop at any time.",
                ),
                ft.Row(duration_controls, spacing=9),
                self.meditation_start_button,
                ft.Row(
                    [
                        self.meditation_pause_button,
                        self._secondary_button(
                            "Finish",
                            self._finish_meditation,
                            icon=ft.Icons.STOP_ROUNDED,
                            expand=True,
                        ),
                    ],
                    spacing=9,
                ),
                ft.Text(
                    f"This is a simple attention practice, not treatment. "
                    f"Selected duration: {total_seconds // 60} minutes.",
                    size=11,
                    color=MUTED,
                    text_align=ft.TextAlign.CENTER,
                ),
            ]
        )

    def _set_meditation_minutes(self, minutes: int) -> None:
        if self.meditation_running:
            return
        self.meditation_minutes = minutes
        self.render()

    async def _begin_meditation(self) -> None:
        if self.meditation_running:
            return
        self.meditation_running = True
        self.meditation_paused = False
        self.meditation_cancelled = False
        if self.meditation_start_button:
            self.meditation_start_button.disabled = True
        if self.meditation_pause_button:
            self.meditation_pause_button.disabled = False
        self.page.update()

        total = self.meditation_minutes * 60
        prompts = (
            "Notice where your body meets the chair or floor.",
            "Let your breathing find its own pace.",
            "If a thought pulls you away, notice it and return.",
            "Allow sounds to be present without following them.",
        )
        for elapsed in range(total + 1):
            while self.meditation_paused and not self.meditation_cancelled:
                await asyncio.sleep(0.2)
            if self.meditation_cancelled:
                self.meditation_running = False
                return

            remaining = total - elapsed
            if self.meditation_timer:
                self.meditation_timer.value = (
                    f"{remaining // 60:02d}:{remaining % 60:02d}"
                )
            if self.meditation_status:
                prompt_index = min(
                    len(prompts) - 1,
                    elapsed // max(1, total // len(prompts)),
                )
                self.meditation_status.value = prompts[prompt_index]
            if self.meditation_orb and elapsed % 4 == 0:
                self.meditation_orb.scale = (
                    1.08 if self.meditation_orb.scale == 0.92 else 0.92
                )
                self.meditation_orb.bgcolor = (
                    MINT if self.meditation_orb.scale == 1.08 else SUN
                )
            self.page.update()
            if remaining:
                await asyncio.sleep(1)

        self.meditation_running = False
        if self.meditation_status:
            self.meditation_status.value = (
                "Practice complete. Notice one thing you want to carry forward."
            )
        if self.meditation_orb:
            self.meditation_orb.scale = 1
            self.meditation_orb.bgcolor = MINT
        if self.meditation_start_button:
            self.meditation_start_button.disabled = False
        if self.meditation_pause_button:
            self.meditation_pause_button.disabled = True
        self.page.update()

    def _toggle_meditation_pause(self) -> None:
        if not self.meditation_running:
            return
        self.meditation_paused = not self.meditation_paused
        if self.meditation_pause_button:
            self.meditation_pause_button.content = (
                "Resume" if self.meditation_paused else "Pause"
            )
            self.meditation_pause_button.icon = (
                ft.Icons.PLAY_ARROW_ROUNDED
                if self.meditation_paused
                else ft.Icons.PAUSE_ROUNDED
            )
        if self.meditation_status and self.meditation_paused:
            self.meditation_status.value = "Paused. Continue when you are ready."
        self.page.update()

    def _finish_meditation(self) -> None:
        self.meditation_cancelled = True
        self.meditation_running = False
        self.go_to(ViewName.HOME)

    # ------------------------------------------------------------------
    # Progress
    # ------------------------------------------------------------------

    def _build_progress(self) -> ft.Control:
        self.evidence_cards = []
        rows = self.database.load_progress_rows()
        frame = pd.DataFrame(rows)
        now = pd.Timestamp.now(tz="UTC")
        if not frame.empty:
            frame["completed_at"] = pd.to_datetime(frame["completed_at"], utc=True)
            if self.progress_filter == "7":
                frame = frame[frame["completed_at"] >= now - pd.Timedelta(days=7)]
            elif self.progress_filter == "30":
                frame = frame[frame["completed_at"] >= now - pd.Timedelta(days=30)]

        controls: list[ft.Control] = [
            ft.Container(
                content=ft.Row(
                    [
                        ft.Column(
                            [
                                ft.Text(
                                    "Proof, not pressure.",
                                    size=25,
                                    weight=ft.FontWeight.W_700,
                                    color=TEXT,
                                ),
                                ft.Text(
                                    "Only your actions live here. Never rankings.",
                                    color=PRIMARY_DARK,
                                    size=14,
                                ),
                            ],
                            spacing=4,
                            expand=True,
                        ),
                        ft.Container(
                            width=62,
                            height=62,
                            bgcolor="#FFFFFF99",
                            shape=ft.BoxShape.CIRCLE,
                            alignment=ft.Alignment.CENTER,
                            content=ft.Icon(
                                ft.Icons.AUTO_GRAPH_ROUNDED,
                                color=MINT_DARK,
                                size=32,
                            ),
                        ),
                    ]
                ),
                padding=19,
                bgcolor=MINT,
                image=ft.DecorationImage(
                    src="evidence_steps_background.png",
                    fit=ft.BoxFit.COVER,
                    alignment=ft.Alignment.CENTER,
                    opacity=0.22,
                ),
                border_radius=25,
            ),
            ft.Row(
                [
                    self._progress_filter_button("7", "7 days"),
                    self._progress_filter_button("30", "30 days"),
                    self._progress_filter_button("all", "All"),
                ]
            ),
        ]
        if frame.empty:
            controls.append(
                self._card(
                    [
                        ft.Text(
                            "Your evidence starts small.",
                            size=22,
                            weight=ft.FontWeight.W_700,
                        ),
                        ft.Text(
                            "Complete a task when you are ready. Small actions count.",
                            color=MUTED,
                        ),
                    ]
                )
            )
            controls.extend(self._build_wellbeing_context())
            return self._scrolling_column(controls)

        minutes = int(frame["estimated_minutes"].fillna(0).sum())
        controls.append(
            ft.Row(
                [
                    self._metric_card("Completed", str(len(frame))),
                    self._metric_card("Planned minutes", str(minutes)),
                ]
            )
        )

        counts = frame.groupby("track").size().to_dict()
        max_count = max(counts.values()) if counts else 1
        groups: list[fch.BarChartGroup] = []
        labels: list[fch.ChartAxisLabel] = []
        colors = [PRIMARY, "#E8A642", MINT_DARK, "#C26C51"]
        for index, track in enumerate(Track):
            value = int(counts.get(track.value, 0))
            groups.append(
                fch.BarChartGroup(
                    x=index,
                    rods=[
                        fch.BarChartRod(
                            from_y=0,
                            to_y=value,
                            width=28,
                            color=colors[index],
                            border_radius=6,
                            tooltip=f"{track.label}: {value}",
                        )
                    ],
                )
            )
            labels.append(
                fch.ChartAxisLabel(
                    value=index,
                    label=ft.Text(
                        {
                            Track.DSA: "DSA",
                            Track.CORE_CS: "Core",
                            Track.PROJECT: "Project",
                            Track.APPLICATIONS: "Apply",
                        }[track],
                        size=11,
                    ),
                )
            )
        chart = fch.BarChart(
            groups=groups,
            min_y=0,
            max_y=max_count + 1,
            height=230,
            bgcolor=CARD,
            border=ft.Border.all(0, CARD),
            horizontal_grid_lines=fch.ChartGridLines(color="#EEE5DE", width=1),
            left_axis=fch.ChartAxis(
                title=ft.Text("Completed"),
                title_size=28,
                label_size=28,
            ),
            bottom_axis=fch.ChartAxis(labels=labels, label_size=38),
        )
        controls.extend(
            [
                ft.Text(
                    "Completed by track",
                    size=22,
                    weight=ft.FontWeight.W_700,
                ),
                ft.Container(
                    content=chart,
                    padding=12,
                    bgcolor=CARD,
                    border_radius=22,
                    shadow=ft.BoxShadow(
                        blur_radius=22,
                        spread_radius=-7,
                        color=SHADOW,
                        offset=ft.Offset(0, 8),
                    ),
                ),
                ft.Text(
                    "Evidence journal",
                    size=22,
                    weight=ft.FontWeight.W_700,
                ),
            ]
        )
        evidence_rows = frame.dropna(subset=["evidence_statement"]).sort_values(
            "completed_at", ascending=False
        )
        for _, row in evidence_rows.head(20).iterrows():
            card = ft.Container(
                content=ft.Column(
                    [
                        ft.Text(
                            row["completed_at"].to_pydatetime()
                            .astimezone()
                            .strftime("%d %b %Y"),
                            size=12,
                            color=MUTED,
                        ),
                        ft.Row(
                            [
                                ft.Icon(
                                    ft.Icons.CHECK_CIRCLE_ROUNDED,
                                    color=MINT_DARK,
                                    size=22,
                                ),
                                ft.Text(
                                    str(row["evidence_statement"]),
                                    expand=True,
                                ),
                            ],
                            vertical_alignment=ft.CrossAxisAlignment.START,
                        ),
                    ],
                    spacing=10,
                ),
                padding=18,
                bgcolor="#EAF5F0",
                border_radius=22,
                opacity=0.15,
                offset=ft.Offset(0, 0.08),
                scale=0.97,
                animate_opacity=260,
                animate_offset=320,
                animate_scale=300,
            )
            self.evidence_cards.append(card)
            controls.append(card)
        controls.extend(self._build_wellbeing_context())
        return self._scrolling_column(controls)

    def _progress_filter_button(self, value: str, label: str) -> ft.Button:
        if self.progress_filter == value:
            return self._primary_button(
                label,
                lambda: self._set_progress_filter(value),
                expand=True,
            )
        return self._secondary_button(
            label,
            lambda: self._set_progress_filter(value),
            expand=True,
        )

    def _set_progress_filter(self, value: str) -> None:
        self.progress_filter = value
        self.render()

    def _metric_card(self, label: str, value: str) -> ft.Control:
        return ft.Container(
            content=ft.Column(
                [
                    ft.Text(
                        value,
                        size=30,
                        weight=ft.FontWeight.W_700,
                        color=PRIMARY_DARK,
                    ),
                    ft.Text(label, size=12, color=MUTED),
                ],
                spacing=2,
            ),
            padding=16,
            bgcolor=SUN_SOFT,
            border_radius=18,
            expand=True,
        )

    def _build_wellbeing_context(self) -> list[ft.Control]:
        readings = self.database.list_wearable_readings(limit=30)
        moods = self.database.list_mood_checkins(limit=30)
        controls: list[ft.Control] = [
            self._section_heading(
                "Body & mood context",
                "Patterns for reflection, never a stress score.",
            ),
            ft.Container(
                content=ft.Column(
                    [
                        ft.Row(
                            [
                                ft.Icon(
                                    ft.Icons.WATCH_OUTLINED,
                                    color=MINT_DARK,
                                ),
                                ft.Text(
                                    "Wearable import",
                                    size=18,
                                    weight=ft.FontWeight.W_700,
                                    expand=True,
                                ),
                            ]
                        ),
                        ft.Text(
                            "Import sleep, resting heart rate, HRV, or steps from "
                            "a watch export. Data stays in SQLite.",
                            color=MUTED,
                            size=13,
                        ),
                        ft.Row(
                            [
                                self._primary_button(
                                    "Import",
                                    self._import_wearable_data,
                                    icon=ft.Icons.UPLOAD_FILE_ROUNDED,
                                    expand=True,
                                ),
                                self._secondary_button(
                                    "Check in",
                                    self._show_mood_checkin,
                                    icon=ft.Icons.MOOD_ROUNDED,
                                    expand=True,
                                ),
                            ],
                            spacing=10,
                        ),
                        self._secondary_button(
                            "Download CSV template",
                            self._download_wearable_template,
                            icon=ft.Icons.TABLE_VIEW_ROUNDED,
                        ),
                        ft.Button(
                            content="Direct Health Connect status",
                            icon=ft.Icons.LINK_ROUNDED,
                            on_click=self._haptic_handler(
                                self._show_health_connect_info
                            ),
                            style=ft.ButtonStyle(
                                color=MINT_DARK,
                                elevation=0,
                                padding=4,
                            ),
                        ),
                    ],
                    spacing=12,
                ),
                padding=18,
                bgcolor=CARD,
                border_radius=22,
            ),
        ]

        if readings:
            latest = readings[0]
            metrics: list[ft.Control] = []
            if latest.sleep_hours is not None:
                metrics.append(
                    self._context_metric("Sleep", f"{latest.sleep_hours:g} h")
                )
            if latest.resting_heart_rate is not None:
                metrics.append(
                    self._context_metric(
                        "Resting HR", f"{latest.resting_heart_rate:g}"
                    )
                )
            if latest.hrv_ms is not None:
                metrics.append(self._context_metric("HRV", f"{latest.hrv_ms:g} ms"))
            if latest.steps is not None:
                metrics.append(self._context_metric("Steps", f"{latest.steps:,}"))
            for index in range(0, len(metrics), 2):
                controls.append(ft.Row(metrics[index : index + 2], spacing=10))

            sleep_rows = [
                item for item in reversed(readings[:14]) if item.sleep_hours is not None
            ]
            if len(sleep_rows) >= 2:
                points = [
                    fch.LineChartDataPoint(
                        index,
                        item.sleep_hours or 0,
                        tooltip=(
                            f"{item.recorded_date.strftime('%d %b')}: "
                            f"{item.sleep_hours:g} h"
                        ),
                    )
                    for index, item in enumerate(sleep_rows)
                ]
                chart = fch.LineChart(
                    data_series=[
                        fch.LineChartData(
                            points=points,
                            curved=True,
                            color=MINT_DARK,
                            stroke_width=4,
                            point=True,
                            below_line_bgcolor="#22BFDCCF",
                        )
                    ],
                    min_x=0,
                    max_x=max(1, len(points) - 1),
                    min_y=0,
                    max_y=max(10, max(point.y for point in points) + 1),
                    height=190,
                    animation=450,
                    horizontal_grid_lines=fch.ChartGridLines(
                        color="#EEE5DE", width=1
                    ),
                    left_axis=fch.ChartAxis(label_size=34),
                    bottom_axis=fch.ChartAxis(label_size=22),
                )
                controls.append(
                    self._card(
                        [
                            ft.Text(
                                "Recent sleep context",
                                weight=ft.FontWeight.W_700,
                            ),
                            chart,
                        ]
                    )
                )

        if moods:
            controls.append(
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Text(
                                "Recent check-ins",
                                weight=ft.FontWeight.W_700,
                            ),
                            ft.Row(
                                [
                                    ft.Container(
                                        content=ft.Text(
                                            f"{item.mood} · {item.energy}/5",
                                            size=12,
                                            color=PRIMARY_DARK,
                                        ),
                                        padding=ft.Padding.symmetric(
                                            horizontal=10, vertical=7
                                        ),
                                        bgcolor=PRIMARY_SOFT,
                                        border_radius=12,
                                    )
                                    for item in moods[:3]
                                ],
                                wrap=True,
                            ),
                        ],
                        spacing=10,
                    ),
                    padding=16,
                    bgcolor=SUN_SOFT,
                    border_radius=18,
                )
            )

        if not readings and not moods:
            controls.append(
                ft.Text(
                    "No body or mood data yet. This section is optional.",
                    color=MUTED,
                    size=13,
                )
            )
        controls.append(
            ft.Text(
                "Wearable readings can vary by device. ResetPath does not use "
                "them to diagnose anxiety, infer safety, or tell you to ignore "
                "how you feel.",
                color=MUTED,
                size=11,
            )
        )
        return controls

    def _context_metric(self, label: str, value: str) -> ft.Control:
        return ft.Container(
            content=ft.Column(
                [
                    ft.Text(
                        value,
                        size=21,
                        weight=ft.FontWeight.W_700,
                        color=TEXT,
                    ),
                    ft.Text(label, size=11, color=MUTED),
                ],
                spacing=2,
            ),
            padding=14,
            bgcolor=PRIMARY_SOFT,
            border_radius=17,
            expand=True,
            animate_scale=220,
        )

    async def _import_wearable_data(self) -> None:
        try:
            selected = await self.file_picker.pick_files(
                dialog_title="Import wearable data",
                file_type=ft.FilePickerFileType.CUSTOM,
                allowed_extensions=["csv", "json"],
                allow_multiple=False,
                with_data=True,
            )
            if not selected:
                return
            picked = selected[0]
            if picked.bytes is None:
                self._show_message("This device did not return file data.", warning=True)
                return
            result = parse_wearable_file(picked.name, picked.bytes)
            if not result.rows:
                message = result.errors[0] if result.errors else "No usable rows found."
                self._show_message(message, warning=True)
                return
            imported = self.database.import_wearable_rows(result.rows)
            suffix = (
                f" {len(result.errors)} row(s) skipped."
                if result.errors
                else ""
            )
            self._show_message(f"Imported {imported} private reading(s).{suffix}")
            self.render()
        except Exception:
            self._show_message("The wearable file could not be imported.", warning=True)

    async def _download_wearable_template(self) -> None:
        try:
            path = await self.file_picker.save_file(
                dialog_title="Save wearable CSV template",
                file_name="resetpath-wearable-template.csv",
                file_type=ft.FilePickerFileType.CUSTOM,
                allowed_extensions=["csv"],
                src_bytes=wearable_template_csv(),
            )
            if path:
                self._show_message("Template saved.")
        except Exception:
            self._show_message("The template could not be saved.", warning=True)

    def _show_mood_checkin(self) -> None:
        mood = ft.Dropdown(
            label="Closest feeling",
            value="Okay",
            options=[
                ft.DropdownOption(key=value, text=value)
                for value in (
                    "Calm",
                    "Okay",
                    "Tense",
                    "Overwhelmed",
                    "Low",
                    "Energised",
                )
            ],
        )
        energy = ft.Slider(
            min=1,
            max=5,
            divisions=4,
            value=3,
            label="{value}/5",
        )
        note = ft.TextField(
            hint_text="Anything worth remembering? (optional)",
            multiline=True,
            min_lines=2,
            max_lines=3,
            max_length=500,
        )

        def save() -> None:
            if contains_crisis_language(note.value):
                self._close_dialog()
                self._redirect_for_crisis()
                return
            self.database.save_mood_checkin(
                mood.value or "Okay",
                int(energy.value or 3),
                note.value,
            )
            self._close_dialog()
            self._show_message("Check-in saved privately.")
            self.render()

        self.page.show_dialog(
            ft.AlertDialog(
                modal=True,
                title="How is this moment?",
                content=ft.Column(
                    [
                        mood,
                        ft.Text("Energy", size=12, color=MUTED),
                        energy,
                        note,
                    ],
                    tight=True,
                    spacing=10,
                ),
                actions=[
                    self._secondary_button("Cancel", self._close_dialog),
                    self._primary_button("Save", save),
                ],
            )
        )

    def _show_health_connect_info(self) -> None:
        self.page.show_dialog(
            ft.AlertDialog(
                modal=True,
                title="Health Connect",
                content=ft.Column(
                    [
                        ft.Text(
                            "This APK connects to watch data through a private "
                            "CSV or JSON export."
                        ),
                        ft.Text(
                            "One-tap Health Connect sync is not enabled in v0.1. "
                            "It requires a native Android bridge, read-only health "
                            "permissions, and an in-app privacy rationale.",
                            color=MUTED,
                        ),
                        ft.Container(
                            content=ft.Text(
                                "Planned direct fields: sleep, resting heart rate, "
                                "HRV, and steps. Never a diagnosis or safety score.",
                                color=MINT_DARK,
                                size=13,
                                weight=ft.FontWeight.W_600,
                            ),
                            padding=12,
                            bgcolor="#EAF5F0",
                            border_radius=14,
                        ),
                    ],
                    tight=True,
                    spacing=12,
                ),
                actions=[self._primary_button("Close", self._close_dialog)],
            )
        )

    # ------------------------------------------------------------------
    # Human help and settings
    # ------------------------------------------------------------------

    def _build_help(self) -> ft.Control:
        settings = self.database.get_settings()
        controls: list[ft.Control] = []
        if self.crisis_redirected:
            controls.append(
                self._card(
                    [
                        ft.Row(
                            [
                                ft.Icon(
                                    ft.Icons.WARNING_AMBER_ROUNDED,
                                    color=WARNING,
                                ),
                                ft.Text(
                                    "Please connect with a person now",
                                    size=18,
                                    weight=ft.FontWeight.BOLD,
                                    color=WARNING,
                                    expand=True,
                                ),
                            ]
                        ),
                        ft.Text(
                            "ResetPath cannot evaluate whether you are safe. The "
                            "text you entered was not saved or reframed.",
                        ),
                    ],
                    bgcolor=WARNING_SOFT,
                    border_color="#E8BEB6",
                )
            )

        controls.extend(
            [
                ft.Container(
                    content=ft.Row(
                        [
                            ft.Column(
                                [
                                    ft.Text(
                                        "Reach a person.",
                                        size=25,
                                        weight=ft.FontWeight.W_700,
                                        color=TEXT,
                                    ),
                                    ft.Text(
                                        "You do not have to handle a hard moment alone.",
                                        color=PRIMARY_DARK,
                                        size=14,
                                    ),
                                ],
                                spacing=5,
                                expand=True,
                            ),
                            ft.Container(
                                width=62,
                                height=62,
                                bgcolor="#FFFFFF90",
                                border_radius=20,
                                alignment=ft.Alignment.CENTER,
                                content=ft.Icon(
                                    ft.Icons.FAVORITE_ROUNDED,
                                    color=WARNING,
                                    size=31,
                                ),
                            ),
                        ]
                    ),
                    padding=19,
                    bgcolor=PRIMARY_SOFT,
                    border_radius=25,
                ),
                self._card(
                    [
                        ft.Text(
                            "If you may act on thoughts of self-harm or cannot "
                            "remain safe, contact a trusted person, professional "
                            "support, or local emergency service now.",
                            weight=ft.FontWeight.BOLD,
                        ),
                        ft.Text(
                            "ResetPath does not diagnose, assess risk, or decide "
                            "whether somebody is safe.",
                            color=MUTED,
                        ),
                    ],
                    bgcolor="#FFF9F2",
                    border_color="#EADBC5",
                ),
                self._support_card(
                    "Trusted person",
                    settings.trusted_person_name or "Not configured",
                    settings.trusted_person_phone,
                    "Add a trusted person in Settings."
                    if not settings.trusted_person_phone
                    else "",
                ),
                self._support_card(
                    "Campus counsellor",
                    settings.counsellor_name or "Not configured",
                    settings.counsellor_phone,
                    settings.counsellor_details
                    or "Add campus support information in Settings.",
                ),
                self._card(
                    [
                        ft.Text(
                            "Tele-MANAS",
                            size=22,
                            weight=ft.FontWeight.W_700,
                        ),
                        ft.Text(
                            "Government of India’s 24/7 free mental-health helpline.",
                            color=MUTED,
                        ),
                        ft.Text(
                            TELE_MANAS_PHONE,
                            size=32,
                            weight=ft.FontWeight.W_700,
                            color=MINT_DARK,
                        ),
                        self._primary_button(
                            "Open dialler",
                            lambda: self.page.run_task(
                                self._launch_url, f"tel:{TELE_MANAS_PHONE}"
                            ),
                            icon=ft.Icons.PHONE,
                        ),
                        self._secondary_button(
                            "Open official website",
                            lambda: self.page.run_task(
                                self._launch_url, TELE_MANAS_URL
                            ),
                            icon=ft.Icons.OPEN_IN_NEW,
                        ),
                    ],
                    bgcolor="#EAF5F0",
                ),
                self._secondary_button(
                    "Edit support contacts",
                    lambda: self.go_to(ViewName.SETTINGS),
                    icon=ft.Icons.SETTINGS,
                ),
                ft.Text(
                    "ResetPath is a support tool, not medical treatment.",
                    color=MUTED,
                    text_align=ft.TextAlign.CENTER,
                ),
            ]
        )
        return self._scrolling_column(controls)

    def _support_card(
        self,
        heading: str,
        name: str,
        phone: str,
        details: str,
    ) -> ft.Control:
        controls: list[ft.Control] = [
            ft.Text(heading, size=20, weight=ft.FontWeight.BOLD),
            ft.Text(name, weight=ft.FontWeight.BOLD),
        ]
        if details:
            controls.append(ft.Text(details, color=MUTED))
        if phone:
            controls.append(
                self._primary_button(
                    "Open dialler",
                    lambda: self.page.run_task(
                        self._launch_url,
                        f"tel:{normalize_phone_for_uri(phone)}",
                    ),
                    icon=ft.Icons.PHONE,
                )
            )
        else:
            controls.append(
                self._secondary_button(
                    "Configure contact",
                    lambda: self.go_to(ViewName.SETTINGS),
                    icon=ft.Icons.SETTINGS,
                )
            )
        return self._card(controls)

    async def _launch_url(self, url: str) -> None:
        try:
            await self.url_launcher.launch_url(
                url,
                mode=ft.LaunchMode.EXTERNAL_APPLICATION,
            )
        except Exception:
            self._show_message("This link could not be opened on this device.", warning=True)

    def _build_settings(self) -> ft.Control:
        settings = self.database.get_settings()
        trusted_name = ft.TextField(
            label="Trusted person’s name",
            value=settings.trusted_person_name,
            max_length=100,
        )
        trusted_phone = ft.TextField(
            label="Trusted person’s phone",
            value=settings.trusted_person_phone,
            keyboard_type=ft.KeyboardType.PHONE,
            max_length=30,
        )
        counsellor_name = ft.TextField(
            label="Campus counsellor/service name",
            value=settings.counsellor_name,
            max_length=150,
        )
        counsellor_phone = ft.TextField(
            label="Campus counsellor phone",
            value=settings.counsellor_phone,
            keyboard_type=ft.KeyboardType.PHONE,
            max_length=30,
        )
        counsellor_details = ft.TextField(
            label="Campus counsellor details",
            value=settings.counsellor_details,
            multiline=True,
            min_lines=2,
            max_lines=4,
            max_length=1_000,
        )
        error = ft.Text("", color=WARNING)

        def save_settings() -> None:
            for value in (trusted_phone.value, counsellor_phone.value):
                result = validate_phone(value)
                if not result.is_valid:
                    error.value = result.message
                    self.page.update()
                    return
            if contains_crisis_language(
                trusted_name.value,
                counsellor_name.value,
                counsellor_details.value,
            ):
                self._redirect_for_crisis()
                return
            self.database.save_settings(
                SupportSettings(
                    trusted_person_name=trusted_name.value.strip(),
                    trusted_person_phone=trusted_phone.value.strip(),
                    counsellor_name=counsellor_name.value.strip(),
                    counsellor_phone=counsellor_phone.value.strip(),
                    counsellor_details=counsellor_details.value.strip(),
                    theme_mode=settings.theme_mode,
                    disclaimer_acknowledged_at=settings.disclaimer_acknowledged_at,
                )
            )
            self._show_message("Settings saved.")
            self.render()

        return self._scrolling_column(
            [
                self._card(
                    [
                        ft.Text("Appearance", size=20, weight=ft.FontWeight.BOLD),
                        ft.Text("Choose what feels easiest on your eyes.", color=MUTED),
                        ft.Row(
                            [
                                self._secondary_button("Light", lambda: self._set_theme("light"), icon=ft.Icons.LIGHT_MODE_ROUNDED, expand=True),
                                self._secondary_button("Dark", lambda: self._set_theme("dark"), icon=ft.Icons.DARK_MODE_ROUNDED, expand=True),
                            ],
                            spacing=10,
                        ),
                    ]
                ),
                self._card(
                    [
                        ft.Text(
                            "Support contacts",
                            size=20,
                            weight=ft.FontWeight.BOLD,
                        ),
                        trusted_name,
                        trusted_phone,
                        counsellor_name,
                        counsellor_phone,
                        counsellor_details,
                        error,
                        self._primary_button(
                            "Save contacts",
                            save_settings,
                            icon=ft.Icons.SAVE,
                        ),
                    ]
                ),
                self._card(
                    [
                        ft.Text(
                            "Your local data",
                            size=20,
                            weight=ft.FontWeight.BOLD,
                        ),
                        ft.Text(
                            "Tasks and journal entries are stored in the app’s "
                            "private SQLite database. The database is not "
                            "additionally encrypted.",
                            color=MUTED,
                        ),
                        self._secondary_button(
                            "Export tasks and journal",
                            lambda: self.page.run_task(self._export_data),
                            icon=ft.Icons.DOWNLOAD,
                        ),
                        self._secondary_button(
                            "Delete all local data",
                            self._show_delete_all_dialog,
                            icon=ft.Icons.DELETE_FOREVER,
                            warning=True,
                        ),
                    ]
                ),
                self._card(
                    [
                        ft.Text(
                            "About ResetPath",
                            size=20,
                            weight=ft.FontWeight.BOLD,
                        ),
                        ft.Text(
                            "ResetPath is a personal support and progress-tracking "
                            "tool. It is not medical treatment, does not diagnose "
                            "conditions, and cannot determine whether someone is safe.",
                            color=MUTED,
                        ),
                        ft.Text(
                            "The grounding design is inspired by the World Health "
                            "Organization’s “Doing What Matters in Times of Stress.” "
                            "ResetPath is not affiliated with or endorsed by WHO.",
                            color=MUTED,
                        ),
                        self._secondary_button(
                            "Open WHO guide",
                            lambda: self.page.run_task(
                                self._launch_url,
                                "https://www.who.int/publications-detail-redirect/"
                                "9789240003927",
                            ),
                            icon=ft.Icons.OPEN_IN_NEW,
                        ),
                    ]
                ),
            ]
        )

    async def _export_data(self) -> None:
        try:
            archive = self.database.create_export_zip()
            file_name = f"resetpath-export-{datetime.now():%Y%m%d-%H%M}.zip"
            path = await self.file_picker.save_file(
                dialog_title="Export ResetPath data",
                file_name=file_name,
                file_type=ft.FilePickerFileType.CUSTOM,
                allowed_extensions=["zip"],
                src_bytes=archive,
            )
            if path:
                self._show_message("Export saved. It may contain sensitive information.")
        except Exception:
            self._show_message("The export could not be created.", warning=True)

    def _show_delete_all_dialog(self) -> None:
        confirmation = ft.TextField(
            label="Type DELETE to confirm",
            max_length=6,
        )
        error = ft.Text("", color=WARNING)

        def delete_all() -> None:
            if confirmation.value.strip() != "DELETE":
                error.value = "Type DELETE exactly to continue."
                self.page.update()
                return
            self.database.delete_all_data()
            self._close_dialog()
            self.current_view = ViewName.HOME
            self.render()

        self.page.show_dialog(
            ft.AlertDialog(
                modal=True,
                title="Delete every local entry?",
                content=ft.Column(
                    [
                        ft.Text(
                            "Tasks, evidence, journal entries, and support contacts "
                            "will be removed. Exported copies cannot be deleted by "
                            "ResetPath.",
                        ),
                        confirmation,
                        error,
                    ],
                    tight=True,
                ),
                actions=[
                    self._secondary_button("Cancel", self._close_dialog),
                    self._secondary_button(
                        "Delete everything",
                        delete_all,
                        icon=ft.Icons.DELETE_FOREVER,
                        warning=True,
                    ),
                ],
            )
        )


async def main(page: ft.Page) -> None:
    ResetPathApp(page)


if __name__ == "__main__":
    ft.run(main, assets_dir="assets")
