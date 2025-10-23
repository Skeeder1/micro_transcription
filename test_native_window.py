"""Test rapide de la fenêtre native du visualiseur.

Lance la fenêtre pour 5 secondes puis la ferme automatiquement.
"""

import sys
from PySide6 import QtCore, QtWidgets
from visualizer_window import VisualizerWindow


def main():
    """Test de la fenêtre."""
    print("[TEST] Lancement de la fenêtre native...")
    
    app = QtWidgets.QApplication(sys.argv)
    window = VisualizerWindow()
    window.show()
    
    print("[TEST] Fenêtre affichée pour 5 secondes...")
    print("[TEST] - Devrait être toujours au premier plan")
    print("[TEST] - Appuyez sur ESC pour fermer manuellement")
    
    # Timer pour fermer automatiquement après 5 secondes
    timer = QtCore.QTimer()
    timer.timeout.connect(lambda: [
        print("[TEST] ✅ Test terminé - fermeture automatique"),
        app.quit()
    ])
    timer.setSingleShot(True)
    timer.start(5000)
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
