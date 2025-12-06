#!/usr/bin/env python3
"""
Test simple pour vérifier si la fenêtre du visualiseur s'affiche.

Exécuter: .venv/bin/python tests/test_visualizer_window.py
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_basic_qt_window():
    """Test if a basic Qt window appears."""
    from PySide6 import QtWidgets, QtCore

    app = QtWidgets.QApplication(sys.argv)

    window = QtWidgets.QMainWindow()
    window.setWindowTitle("TEST - Fenêtre Qt Basique")
    window.resize(400, 200)

    label = QtWidgets.QLabel("Si vous voyez cette fenêtre, Qt fonctionne!")
    label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
    window.setCentralWidget(label)

    window.show()
    print(f"Fenêtre créée: {window.width()}x{window.height()} à ({window.x()}, {window.y()})")
    print("La fenêtre devrait être visible. Appuyez sur Ctrl+C pour fermer.")

    # Close after 10 seconds
    QtCore.QTimer.singleShot(10000, app.quit)
    return app.exec()


def test_visualizer_window():
    """Test if the visualizer window appears."""
    from PySide6 import QtWidgets, QtCore
    from ui.visualizer_app import VisualizerEnhanced

    app = QtWidgets.QApplication(sys.argv)

    print("Création du visualiseur...")
    vis = VisualizerEnhanced(sse_port=5433)

    print(f"Position: ({vis.x()}, {vis.y()})")
    print(f"Taille: {vis.width()}x{vis.height()}")
    print(f"Visible: {vis.isVisible()}")

    vis.show()
    vis.raise_()

    print("La fenêtre du visualiseur devrait être visible.")
    print("Fermez-la manuellement ou attendez 15 secondes.")

    # Close after 15 seconds
    QtCore.QTimer.singleShot(15000, app.quit)
    return app.exec()


def test_subprocess_visualizer():
    """Test if visualizer launched as subprocess appears."""
    import subprocess
    import time

    env = os.environ.copy()
    env["QT_XCB_GL_INTEGRATION"] = "none"
    env["QT_QUICK_BACKEND"] = "software"
    env["QTWEBENGINE_CHROMIUM_FLAGS"] = "--disable-gpu --disable-gpu-compositing --disable-software-rasterizer --disable-gpu-sandbox"

    print("Lancement du visualiseur en subprocess...")
    print(f"DISPLAY={env.get('DISPLAY', 'non défini')}")

    proc = subprocess.Popen(
        [sys.executable, "-m", "ui.visualizer_app", "5433"],
        env=env,
    )
    print(f"PID: {proc.pid}")

    time.sleep(5)

    if proc.poll() is None:
        print("✅ Le subprocess tourne toujours")
        print("La fenêtre devrait être visible!")
        print("Appuyez sur Entrée pour terminer...")
        try:
            input()
        except KeyboardInterrupt:
            pass
        proc.terminate()
    else:
        print(f"❌ Le subprocess s'est terminé avec code: {proc.poll()}")


if __name__ == "__main__":
    print("=" * 60)
    print("TEST DU VISUALISEUR")
    print("=" * 60)

    if len(sys.argv) > 1:
        test_name = sys.argv[1]
        if test_name == "basic":
            sys.exit(test_basic_qt_window())
        elif test_name == "visualizer":
            sys.exit(test_visualizer_window())
        elif test_name == "subprocess":
            test_subprocess_visualizer()
        else:
            print(f"Test inconnu: {test_name}")
            print("Tests disponibles: basic, visualizer, subprocess")
            sys.exit(1)
    else:
        print("\nUsage: python tests/test_visualizer_window.py [test_name]")
        print("Tests disponibles:")
        print("  basic      - Test une fenêtre Qt basique")
        print("  visualizer - Test le visualiseur directement")
        print("  subprocess - Test le visualiseur en subprocess")
        print()
        print("Exemple: .venv/bin/python tests/test_visualizer_window.py basic")
