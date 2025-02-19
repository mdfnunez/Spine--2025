import streamlit as st
import cv2
import numpy as np
import pandas as pd
import json
import os
from streamlit_drawable_canvas import st_canvas
from PIL import Image

# Función para guardar ROIs seleccionados en JSON
def guardar_rois(rois, archivo="roi.json"):
    with open(archivo, "w") as f:
        json.dump(rois, f, indent=4)
    st.success(f"ROIs guardados en '{archivo}'")

# Interfaz de Streamlit
st.title("Análisis de Intensidad de ROIs en Imágenes")

# Cargar imagen para seleccionar ROIs
imagen_path = st.file_uploader("Selecciona una imagen TIFF para definir ROIs", type=["tiff", "tif"])

if imagen_path:
    # Cargar la imagen con PIL y redimensionarla para que quepa en el canvas
    imagen = Image.open(imagen_path)
    ancho_maximo_canvas = 700  # Ancho máximo para la visualización en el canvas
    ancho_original, alto_original = imagen.size
    escala = ancho_maximo_canvas / ancho_original
    ancho_redimensionado = ancho_maximo_canvas
    alto_redimensionado = int(alto_original * escala)
    imagen_redimensionada = imagen.resize((ancho_redimensionado, alto_redimensionado))

    # Mostrar imagen redimensionada en el canvas de Streamlit para dibujar los ROIs
    st.write("Dibuja los rectángulos para definir los ROIs y presiona 'Asignar nombres y Guardar ROIs'")
    canvas_result = st_canvas(
        fill_color="rgba(0, 0, 0, 0)",  # Color de relleno transparente
        stroke_width=2,
        stroke_color="red",
        background_image=imagen_redimensionada,
        update_streamlit=True,
        height=alto_redimensionado,
        width=ancho_redimensionado,
        drawing_mode="rect",
        key="canvas"
    )

    # Mostrar los campos para ingresar nombres de ROIs después de dibujarlos
    if canvas_result.json_data and "objects" in canvas_result.json_data:
        rois = []
        st.write("Ingresa un nombre para cada ROI:")
        for i, obj in enumerate(canvas_result.json_data["objects"]):
            # Escalar coordenadas de vuelta al tamaño original
            x = int(obj["left"] / escala)
            y = int(obj["top"] / escala)
            w = int(obj["width"] / escala)
            h = int(obj["height"] / escala)
            
            nombre_roi = st.text_input(f"Nombre para ROI {i+1}", f"ROI_{i+1}")
            roi = {
                "nombre": nombre_roi,
                "x": x,
                "y": y,
                "w": w,
                "h": h,
            }
            rois.append(roi)
        
        # Guardar los ROIs con nombres personalizados
        if st.button("Guardar ROIs"):
            guardar_rois(rois)

# Cargar automáticamente los ROIs desde el archivo JSON si existe y mostrarlos en una tabla
if os.path.exists("roi.json"):
    with open("roi.json", "r") as f:
        roi_info = json.load(f)
    
    # Crear DataFrame para mostrar en una tabla
    roi_df = pd.DataFrame(roi_info)
    st.write("ROIs cargados desde 'roi.json':")
    st.dataframe(roi_df)  # Muestra los ROIs en una tabla interactiva

    # Selección del directorio de imágenes
    directorio = st.text_input("Directorio de imágenes:", "")

    # Ingreso del nombre de archivo de salida
    archivo_salida = st.text_input("Nombre del archivo de salida (sin extensión):", "resultado")

    # Función para procesar imágenes y calcular intensidades
    def procesar_imagenes(roi_info, directorio, archivo_salida):
        resultados = pd.DataFrame(columns=['Archivo', 'ROI', 'Media_Gris'])
        imagenes = [os.path.join(directorio, archivo) for archivo in os.listdir(directorio) if archivo.endswith('.tif')]
        imagenes.sort()

        trackers = [cv2.TrackerKCF_create() for _ in roi_info]
        primer_frame = cv2.imread(imagenes[0])

        for i, roi_data in enumerate(roi_info):
            x, y, w, h = roi_data['x'], roi_data['y'], roi_data['w'], roi_data['h']
            trackers[i].init(primer_frame, (x, y, w, h))

        for archivo in imagenes:
            frame = cv2.imread(archivo)
            for i, tracker in enumerate(trackers):
                success, roi = tracker.update(frame)
                if success:
                    x, y, w, h = map(int, roi)
                    roi_frame = frame[y:y+h, x:x+w]
                    media_gris = np.mean(cv2.cvtColor(roi_frame, cv2.COLOR_BGR2GRAY))
                    resultados = resultados.append({'Archivo': archivo, 'ROI': roi_info[i]['nombre'], 'Media_Gris': media_gris}, ignore_index=True)
                else:
                    st.warning(f"Fallo en el seguimiento del ROI {roi_info[i]['nombre']}")

        resultados.to_excel(f"{archivo_salida}.xlsx", index=False)
        st.success(f"Resultados guardados en '{archivo_salida}.xlsx'.")

    # Botón para procesar imágenes
    if st.button("Procesar Imágenes"):
        if directorio and archivo_salida:
            procesar_imagenes(roi_info, directorio, archivo_salida)
        else:
            st.warning("Por favor, ingresa un directorio de imágenes y un nombre de archivo de salida.")
else:
    st.warning("Selecciona primero los ROIs para continuar.")
