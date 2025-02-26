import streamlit as st
import json
import cv2
import pytesseract
import pandas as pd
import os
from glob import glob
import subprocess
from concurrent.futures import ThreadPoolExecutor

# Función para cargar ROIs desde JSON
def cargar_rois():
    if os.path.exists("roi.json"):
        with open("roi.json", "r") as f:
            rois = json.load(f)
        return rois
    else:
        st.warning("No se encontraron ROIs. Ejecuta la selección de ROIs primero.")
        return None

# Función para procesar una sola ROI con Tesseract
def ocr_en_roi(roi_imagen, roi_nombre):
    try:
        # Configuración de Tesseract para detectar solo números
        config = "--psm 7 -c tessedit_char_whitelist=0123456789"
        
        # Realizar OCR y limpiar el texto
        texto = pytesseract.image_to_string(roi_imagen, config=config).strip()
        
        return {roi_nombre: texto}
    except pytesseract.TesseractError as e:
        print(f"Error al procesar la ROI '{roi_nombre}': {e}")
        return {roi_nombre: "Error de OCR"}

# Función para procesar todas las imágenes en la carpeta
def procesar_imagenes(carpeta, rois, nombre_csv):
    archivos = sorted(glob(os.path.join(carpeta, "*.tiff")))
    resultados = []
    
    # Crear barra de progreso en Streamlit
    progress_bar = st.progress(0)
    
    for i, archivo in enumerate(archivos, start=1):
        imagen = cv2.imread(archivo, cv2.IMREAD_GRAYSCALE)
        datos_imagen = {"Archivo": os.path.basename(archivo)}
        
        # Procesar cada ROI en paralelo
        with ThreadPoolExecutor() as executor:
            resultados_roi = executor.map(
                lambda roi: ocr_en_roi(imagen[roi["y"]:roi["y"] + roi["h"], roi["x"]:roi["x"] + roi["w"]], roi["nombre"]),
                rois
            )
        
        # Combinar los resultados de cada ROI
        for resultado_roi in resultados_roi:
            datos_imagen.update(resultado_roi)

        resultados.append(datos_imagen)
        
        # Actualizar barra de progreso en Streamlit
        progress_bar.progress(i / len(archivos))

    # Crear la carpeta signos_vitales si no existe
    output_folder = "signos_vitales"
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    # Guardar resultados en CSV en la carpeta signos_vitales
    output_path = os.path.join(output_folder, f"{nombre_csv}.csv")
    df = pd.DataFrame(resultados)
    df.to_csv(output_path, index=False)
    return df, output_path

# Interfaz de Streamlit
st.title("Extracción OCR en Imágenes TIFF con Múltiples ROIs")

# Botón para seleccionar una nueva ROI
if st.button("Seleccionar nueva ROI"):
    st.write("Abriendo herramienta de selección de ROI...")
    subprocess.run(["python", "seleccionar_roi.py"])

# Cargar las ROIs desde el archivo JSON
rois = cargar_rois()
if rois:
    roi_names = [roi["nombre"] for roi in rois]
    st.write("Variables seleccionadas como ROI a ser medidas:", ", ".join(roi_names))

    # Seleccionar carpeta de imágenes
    carpeta = st.text_input("Introduce la ruta de la carpeta con las imágenes TIFF:")
    nombre_csv = st.text_input("Introduce el nombre para el archivo CSV:", "resultados_ocr")
    
    # Procesar imágenes y guardar con el nombre especificado en la carpeta signos_vitales
    if carpeta and nombre_csv and st.button("Procesar imágenes"):
        df, output_path = procesar_imagenes(carpeta, rois, nombre_csv)
        st.success("Extracción completa. El archivo de resultados está listo para descargar.")
        
        # Botón para descargar el archivo CSV
        with open(output_path, "rb") as file:
            btn = st.download_button(
                label="Descargar archivo CSV",
                data=file,
                file_name=f"{nombre_csv}.csv",
                mime="text/csv"
            )
else:
    st.warning("No se encontraron ROIs en 'roi.json'. Ejecuta la selección de ROIs primero.")
