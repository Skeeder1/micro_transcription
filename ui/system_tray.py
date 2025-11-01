"""System tray icon manager for Ubuntu/Linux desktop integration."""

from __future__ import annotations

import sys
from typing import Callable, Optional, TYPE_CHECKING

try:
    from PySide6.QtWidgets import QApplication, QSystemTrayIcon, QMenu
    from PySide6.QtGui import QIcon, QAction
    from PySide6.QtCore import QTimer
except ImportError:
    # Fallback if PySide6 not available
    QApplication = None  # type: ignore
    QSystemTrayIcon = None  # type: ignore

if TYPE_CHECKING:
    from shared.context import AppContext


class SystemTrayManager:
    """
    Manages system tray icon with menu for controlling the transcription app.

    Features:
    - Start/Stop transcription
    - Toggle sleep mode
    - Show/Hide visualizer
    - Quit application
    """

    def __init__(
        self,
        ctx: AppContext,
        on_sleep_toggle: Callable[[], None],
        on_quit: Callable[[], None],
    ):
        """
        Initialize system tray manager.

        Args:
            ctx: Application context
            on_sleep_toggle: Callback to toggle sleep mode
            on_quit: Callback to quit application
        """
        if QSystemTrayIcon is None:
            raise ImportError("PySide6 not available, cannot create system tray")

        self.ctx = ctx
        self.on_sleep_toggle = on_sleep_toggle
        self.on_quit = on_quit

        # Create QApplication instance if not exists
        self.app = QApplication.instance()
        if self.app is None:
            self.app = QApplication(sys.argv)

        # Create tray icon
        self.tray_icon = QSystemTrayIcon()
        self.tray_icon.setToolTip("Système de Dictée Vocale v2.0")

        # Set icon (use default mic icon or custom)
        icon = self._load_icon()
        if icon:
            self.tray_icon.setIcon(icon)

        # Create context menu
        self.menu = QMenu()
        self._create_menu()

        self.tray_icon.setContextMenu(self.menu)

        # Connect activation (left-click)
        self.tray_icon.activated.connect(self._on_tray_activated)

        # Status update timer (refresh menu every 2 seconds)
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self._update_menu)
        self.update_timer.start(2000)  # 2 seconds

    def _load_icon(self) -> Optional[QIcon]:
        """Load tray icon from file or use default."""
        import os

        # Try to load custom icon
        icon_path = os.path.join(
            os.path.dirname(__file__),
            "assets",
            "tray_icon.png"
        )

        if os.path.exists(icon_path):
            return QIcon(icon_path)

        # Use Qt built-in icon as fallback
        from PySide6.QtWidgets import QStyle
        if self.app:
            return self.app.style().standardIcon(QStyle.SP_MediaVolume)

        return None

    def _create_menu(self) -> None:
        """Create the context menu with actions."""
        # Status label (non-clickable)
        self.status_action = QAction("🎤 Système actif")
        self.status_action.setEnabled(False)
        self.menu.addAction(self.status_action)

        self.menu.addSeparator()

        # Toggle sleep mode
        self.sleep_action = QAction("💤 Mettre en veille")
        self.sleep_action.triggered.connect(self._on_sleep_clicked)
        self.menu.addAction(self.sleep_action)

        self.menu.addSeparator()

        # Show visualizer (if hidden)
        show_viz_action = QAction("👁️ Afficher visualiseur")
        show_viz_action.triggered.connect(self._on_show_visualizer)
        self.menu.addAction(show_viz_action)

        self.menu.addSeparator()

        # Quit
        quit_action = QAction("❌ Quitter")
        quit_action.triggered.connect(self._on_quit_clicked)
        self.menu.addAction(quit_action)

    def _update_menu(self) -> None:
        """Update menu items based on current state."""
        with self.ctx.sleep_lock:
            is_sleeping = self.ctx.is_sleeping

        # Update status text
        if is_sleeping:
            self.status_action.setText("💤 En veille")
            self.sleep_action.setText("▶️ Réactiver")
        else:
            self.status_action.setText("🎤 Système actif")
            self.sleep_action.setText("💤 Mettre en veille")

    def _on_tray_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        """Handle tray icon activation (click)."""
        if reason == QSystemTrayIcon.ActivationReason.Trigger:  # Left-click
            # Toggle sleep on left-click
            self._on_sleep_clicked()

    def _on_sleep_clicked(self) -> None:
        """Handle sleep toggle action."""
        self.on_sleep_toggle()
        self._update_menu()

    def _on_show_visualizer(self) -> None:
        """Handle show visualizer action."""
        # Import here to avoid circular imports
        from ui.manager import start_visualizer

        start_visualizer(self.ctx)

    def _on_quit_clicked(self) -> None:
        """Handle quit action."""
        self.on_quit()

    def show(self) -> None:
        """Show the tray icon."""
        if not self.tray_icon.isVisible():
            self.tray_icon.show()

    def hide(self) -> None:
        """Hide the tray icon."""
        if self.tray_icon.isVisible():
            self.tray_icon.hide()

    def cleanup(self) -> None:
        """Cleanup resources."""
        self.update_timer.stop()
        self.tray_icon.hide()


def is_system_tray_available() -> bool:
    """
    Check if system tray is available on this platform.

    Returns:
        True if system tray can be used
    """
    if QSystemTrayIcon is None:
        return False

    # Check if system supports tray icons
    return QSystemTrayIcon.isSystemTrayAvailable()
