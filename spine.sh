#!/bin/bash

APP_DIR="/home/alonso/Documents/GitHub/Spine--2025"
VENV_DIR="$APP_DIR/venv"
STREAMLIT_APP="app.py"
BROWSER="google-chrome"
STREAMLIT_URL="http://localhost:8501"
LOG_FILE="$APP_DIR/streamlit.log"

cd "$APP_DIR" || {
    echo "No se pudo entrar a $APP_DIR. Revisa la ruta, tal vez tu gato re-nombró la carpeta."
    exit 1
}

# Activar el entorno virtual
source "$VENV_DIR/bin/activate" || {
    echo "No se pudo activar el entorno virtual. ¿Estás seguro de que eres un pythonic sensei?"
    exit 1
}

# Matamos cualquier sesión previa de Streamlit
pkill -f "streamlit run $STREAMLIT_APP" 2>/dev/null

opened_browser=false

while true; do
    echo "Lanzando Streamlit en $STREAMLIT_APP..."
    # Iniciamos Streamlit en segundo plano, redirigiendo logs
    streamlit run "$STREAMLIT_APP" \
        --server.headless=true \
        --browser.gatherUsageStats=false \
        --server.port=8501 \
        --browser.serverAddress="localhost" \
        >> "$LOG_FILE" 2>&1 &

    # Esperamos un par de segundos para ver si Streamlit levanta
    sleep 3

    # Verificamos si está corriendo
    if pgrep -f "streamlit run $STREAMLIT_APP" > /dev/null; then
        # Solo abrimos navegador la primera vez
        if [ "$opened_browser" = false ]; then
            echo "Streamlit corriendo en $STREAMLIT_URL. Abriendo navegador (solo la primera vez)..."
            "$BROWSER" --app="$STREAMLIT_URL" &
            opened_browser=true
        else
            echo "Streamlit corriendo nuevamente, pero no abrimos más pestañas..."
        fi
        
        # Espera indefinida hasta que el proceso muera
        wait "$(pgrep -f "streamlit run $STREAMLIT_APP")"

        # Si llega aquí, es que Streamlit se cayó
        echo "¡Streamlit se cayó! Intentando revivirlo en 5 segundos..."
        sleep 5
    else
        echo "ERROR: Streamlit no se inició. Reintentando en 5 segundos..."
        sleep 5
    fi
done
