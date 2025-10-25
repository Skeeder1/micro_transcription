"""Système de logging persistant pour diagnostiquer les problèmes de démarrage.

Ce module permet de logger à la fois en console ET dans un fichier,
même quand l'application tourne avec pythonw.exe (sans console).
"""

from __future__ import annotations

import sys
import datetime
from pathlib import Path
from typing import Optional, TextIO


class DualLogger:
    """Logger qui écrit à la fois en console et dans un fichier."""

    def __init__(self, log_file_path: str):
        """Initialize dual logger.

        Args:
            log_file_path: Chemin vers le fichier de log
        """
        self.log_file_path = Path(log_file_path)
        self.log_file: Optional[TextIO] = None
        self._ensure_log_directory()
        self._open_log_file()

    def _ensure_log_directory(self) -> None:
        """Créer le répertoire logs/ s'il n'existe pas."""
        self.log_file_path.parent.mkdir(parents=True, exist_ok=True)

    def _open_log_file(self) -> None:
        """Ouvrir le fichier de log en mode append."""
        try:
            # CORRECTIF: Utiliser utf-8-sig pour éviter les problèmes d'encodage avec emojis
            # utf-8-sig écrit le BOM au début du fichier pour une meilleure compatibilité
            self.log_file = open(self.log_file_path, 'a', encoding='utf-8-sig', errors='replace')
            # Écrire un header de session
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.log_file.write(f"\n{'=' * 70}\n")
            self.log_file.write(f"SESSION DEMARREE : {timestamp}\n")
            self.log_file.write(f"{'=' * 70}\n")
            self.log_file.flush()
        except Exception as exc:
            print(f"[WARN] Impossible d'ouvrir le fichier de log: {exc}")
            self.log_file = None

    def log(self, message: str, level: str = "INFO") -> None:
        """Log un message en console ET dans le fichier.

        Args:
            message: Message à logger
            level: Niveau de log (INFO, WARN, ERROR)
        """
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        formatted = f"[{timestamp}] [{level}] {message}"

        # Écrire en console si disponible
        if sys.stdout is not None:
            try:
                print(formatted)
            except Exception:
                pass  # Console pas disponible (pythonw.exe)

        # Écrire dans le fichier
        if self.log_file is not None:
            try:
                self.log_file.write(formatted + "\n")
                self.log_file.flush()  # Flush immédiat pour voir les logs même en cas de crash
            except Exception:
                pass  # Fichier fermé ou erreur I/O

    def info(self, message: str) -> None:
        """Log un message de niveau INFO."""
        self.log(message, "INFO")

    def warn(self, message: str) -> None:
        """Log un message de niveau WARN."""
        self.log(message, "WARN")

    def error(self, message: str) -> None:
        """Log un message de niveau ERROR."""
        self.log(message, "ERROR")

    def close(self) -> None:
        """Fermer le fichier de log."""
        if self.log_file is not None:
            try:
                self.log_file.close()
            except Exception:
                pass
            self.log_file = None


# Instance globale de logger
_logger: Optional[DualLogger] = None


def init_logger(log_file: str = "logs/startup.log") -> DualLogger:
    """Initialiser le logger global.

    Args:
        log_file: Chemin vers le fichier de log

    Returns:
        Instance du logger
    """
    global _logger
    _logger = DualLogger(log_file)
    return _logger


def get_logger() -> DualLogger:
    """Obtenir le logger global (l'initialise si besoin).

    Returns:
        Instance du logger
    """
    global _logger
    if _logger is None:
        _logger = init_logger()
    return _logger


def log_info(message: str) -> None:
    """Raccourci pour logger un message INFO."""
    get_logger().info(message)


def log_warn(message: str) -> None:
    """Raccourci pour logger un message WARN."""
    get_logger().warn(message)


def log_error(message: str) -> None:
    """Raccourci pour logger un message ERROR."""
    get_logger().error(message)
