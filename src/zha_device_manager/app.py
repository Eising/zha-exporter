"""The textual-based app."""

from typing import final
from textual.app import App, ComposeResult
from textual.widgets import Header


class ZDMApp(App):
    """ZHA Device Manager app."""

    def compose(self) -> ComposeResult:
        """Compose app.."""
        yield Header()

    def on_mount(self) -> None:
        """Run on mount."""
        self.title = "ZHA Device Manager"
