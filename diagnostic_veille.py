"""
Script de diagnostic pour vérifier l'état du système de veille.
Affiche les flags, locks, et processus actifs.
"""

import subprocess
import time

def check_visualizer_processes():
    """Vérifie les processus visualizer en cours."""
    print("\n🔍 Processus mic_visualizer_enhanced.py actifs:")
    print("=" * 60)
    
    try:
        # Windows: utiliser tasklist
        result = subprocess.run(
            ['powershell', '-Command', 
             "Get-Process | Where-Object {$_.CommandLine -like '*mic_visualizer_enhanced.py*'} | Select-Object Id, ProcessName, CommandLine"],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.stdout.strip():
            print(result.stdout)
        else:
            print("   ✅ Aucun processus visualizer trouvé")
            
    except Exception as e:
        print(f"   ⚠️ Erreur: {e}")
        # Fallback simple
        result = subprocess.run(['tasklist'], capture_output=True, text=True)
        pythonw_count = result.stdout.count('pythonw.exe')
        print(f"   Processus pythonw.exe: {pythonw_count}")


def check_port_usage():
    """Vérifie si le port SSE est utilisé."""
    print("\n🔌 Port SSE (5432) - État:")
    print("=" * 60)
    
    try:
        result = subprocess.run(
            ['powershell', '-Command', 'netstat -ano | Select-String ":5432"'],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.stdout.strip():
            print(result.stdout)
            print("   ⚠️ Port 5432 est utilisé")
        else:
            print("   ✅ Port 5432 est libre")
            
    except Exception as e:
        print(f"   ⚠️ Erreur: {e}")


def main():
    """Exécute tous les diagnostics."""
    print("\n" + "=" * 60)
    print(" 🔧 DIAGNOSTIC SYSTÈME DE VEILLE")
    print("=" * 60)
    
    check_visualizer_processes()
    check_port_usage()
    
    print("\n" + "=" * 60)
    print("💡 Recommandations:")
    print("=" * 60)
    print("   • Si des processus visualizer sont bloqués : tuer manuellement")
    print("   • Si port 5432 occupé : redémarrer le système principal")
    print("   • Vérifier les messages d'erreur dans la console principale")
    print("=" * 60 + "\n")


if __name__ == '__main__':
    main()
