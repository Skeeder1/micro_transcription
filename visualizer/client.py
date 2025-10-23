"""HTTP client for interacting with the visualizer API."""

from __future__ import annotations

import json
from typing import Any, Optional

try:
    import requests
except ImportError:
    requests = None  # type: ignore

from . import config


class VisualizerClient:
    """Client for making requests to the visualizer REST API."""

    def __init__(self, host: Optional[str] = None, port: Optional[int] = None):
        """Initialize the client with the visualizer server address.

        Args:
            host: Server hostname (default: from config)
            port: Server port (default: from config)
        """
        self.host = host or config.HOST
        self.port = port or config.PORT
        self.base_url = f"http://{self.host}:{self.port}"
        self.api_url = f"{self.base_url}{config.API_PREFIX}"

        if requests is None:
            raise ImportError(
                "The 'requests' library is required. Install it with: pip install requests"
            )

    def _post(self, endpoint: str, data: dict) -> dict[str, Any]:
        """Make a POST request to the visualizer API.

        Args:
            endpoint: API endpoint (without prefix)
            data: JSON data to send

        Returns:
            Response JSON as dict

        Raises:
            requests.exceptions.RequestException: If request fails
        """
        url = f"{self.api_url}/{endpoint}"
        response = requests.post(url, json=data, timeout=5)
        response.raise_for_status()
        return response.json()

    def _get(self, endpoint: str) -> dict[str, Any]:
        """Make a GET request to the visualizer API.

        Args:
            endpoint: API endpoint (without prefix)

        Returns:
            Response JSON as dict

        Raises:
            requests.exceptions.RequestException: If request fails
        """
        url = f"{self.api_url}/{endpoint}"
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        return response.json()

    def send_preview(self, text: str, silent: bool = True) -> bool:
        """Send preview text to the visualizer.

        Args:
            text: Preview text to display
            silent: If True, suppress error messages (default: True)

        Returns:
            True if successful, False otherwise
        """
        try:
            self._post("preview", {"text": text})
            return True
        except Exception as e:
            if not silent:
                print(f"[VisualizerClient] Error sending preview: {e}")
            return False

    def set_state(self, state: str, silent: bool = True) -> bool:
        """Set the visualizer state.

        Args:
            state: State to set ("active" or "sleep")
            silent: If True, suppress error messages (default: True)

        Returns:
            True if successful, False otherwise
        """
        if state not in ["active", "sleep"]:
            raise ValueError(f"Invalid state: {state}. Must be 'active' or 'sleep'")

        try:
            self._post("state", {"state": state})
            return True
        except Exception as e:
            if not silent:
                print(f"[VisualizerClient] Error setting state: {e}")
            return False

    def get_status(self) -> Optional[dict[str, Any]]:
        """Get the current visualizer status.

        Returns:
            Status dict or None if failed
        """
        try:
            return self._get("status")
        except Exception as e:
            print(f"[VisualizerClient] Error getting status: {e}")
            return None

    def clear_preview(self) -> bool:
        """Clear the preview text.

        Returns:
            True if successful, False otherwise
        """
        try:
            self._post("clear", {})
            return True
        except Exception as e:
            print(f"[VisualizerClient] Error clearing preview: {e}")
            return False

    def ping(self) -> bool:
        """Check if the visualizer server is running.

        Returns:
            True if server is reachable, False otherwise
        """
        try:
            response = requests.get(f"{self.base_url}/ping", timeout=2)
            return response.text == "pong"
        except Exception:
            return False


# Convenience functions for backward compatibility
_default_client: Optional[VisualizerClient] = None


def get_client(host: Optional[str] = None, port: Optional[int] = None) -> VisualizerClient:
    """Get or create a default visualizer client instance."""
    global _default_client
    if _default_client is None or host is not None or port is not None:
        _default_client = VisualizerClient(host, port)
    return _default_client


def send_preview(text: str, host: Optional[str] = None, port: Optional[int] = None) -> bool:
    """Send preview text (convenience function)."""
    return get_client(host, port).send_preview(text)


def set_state(state: str, host: Optional[str] = None, port: Optional[int] = None) -> bool:
    """Set visualizer state (convenience function)."""
    return get_client(host, port).set_state(state)


def get_status(host: Optional[str] = None, port: Optional[int] = None) -> Optional[dict[str, Any]]:
    """Get visualizer status (convenience function)."""
    return get_client(host, port).get_status()


def ping(host: Optional[str] = None, port: Optional[int] = None) -> bool:
    """Ping visualizer server (convenience function)."""
    return get_client(host, port).ping()
