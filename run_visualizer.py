"""Standalone visualizer launcher script.

This script launches the visualizer as an independent web application.
You can access it via a web browser at http://127.0.0.1:5500

Usage:
    python run_visualizer.py [port] [host]

Examples:
    python run_visualizer.py                  # Run on default port 5500
    python run_visualizer.py 8080             # Run on port 8080
    python run_visualizer.py 8080 0.0.0.0     # Run on all interfaces
"""

from visualizer.server import main

if __name__ == "__main__":
    main()
