#!/bin/bash
# Cambia a la carpeta donde tienes tu aplicación de Streamlit
cd /home/alonso/Documents/GitHub/SPINE-EXP-2024
# Activa el entorno virtual
source /home/alonso/Documents/GitHub/SPINE-EXP-2024/venv/bin/activate
# Ejecuta la aplicación de Streamlit en segundo plano sin abrir el navegador automáticamente
streamlit run app.py --browser.serverAddress="localhost" --server.headless=true &

# Espera unos segundos para que Streamlit se inicie completamente
sleep 2

# Abre Google Chrome en modo aplicación apuntando a la dirección local de Streamlit
google-chrome --app=http://localhost:8501
