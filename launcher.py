import os
import subprocess
import sys

def run_streamlit():
    """Ejecuta la aplicación de Streamlit desde un ejecutable"""
    script_path = os.path.abspath("app.py")  # Ruta absoluta al script de la app
    subprocess.run([sys.executable, "-m", "streamlit", "run", script_path])

if __name__ == "__main__":
    run_streamlit()
