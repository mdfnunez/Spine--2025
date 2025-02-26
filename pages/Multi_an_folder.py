import streamlit as st
import numpy as np
import tifffile
import matplotlib.pyplot as plt
import glob
import io
import re
import tkinter as tk
from tkinter import filedialog

# Configurar la interfaz de Streamlit
st.title("Procesamiento Multiespectral - ROI Única con Nombre de Hora Original")

st.markdown(
    """
    Esta aplicación permite:
    - Cargar imágenes de referencia blanca y oscura (multi-TIFF).
    - Seleccionar una carpeta de imágenes de muestra usando Tkinter.
    - Procesar la primera imagen de la carpeta para calcular la reflectancia e índice de oxigenación.
    - Definir una ROI mediante coordenadas y crear una máscara.
    - Mostrar la imagen con la ROI resaltada y calcular las estadísticas de la ROI.
    - Generar un nombre de salida basado en la hora original del archivo (formato: HH-MM-SS-mmm.tiff).
    """
)

# --- Carga de imágenes de referencia ---
st.markdown("### Carga de Imágenes de Referencia")
white_file = st.file_uploader("Carga la imagen de referencia blanca (multi-TIFF)", type=["tif", "tiff"])
dark_file  = st.file_uploader("Carga la imagen de referencia oscura (multi-TIFF)", type=["tif", "tiff"])

# --- Selección de Carpeta de Imágenes de Muestra usando Tkinter ---
st.markdown("### Selección de Carpeta de Imágenes de Muestra")
if st.button("Seleccionar carpeta de imágenes de muestra"):
    root = tk.Tk()
    root.withdraw()
    # Abrir desde la raíz para acceder a discos externos (Linux/Mac: "/", Windows: "C:\\")
    folder_path = filedialog.askdirectory(initialdir="/")
    if folder_path:
        st.session_state["folder_path"] = folder_path
        st.success(f"Carpeta seleccionada: {folder_path}")
    else:
        st.warning("No se seleccionó ninguna carpeta.")

sample_files = []
if "folder_path" in st.session_state:
    folder_path = st.session_state["folder_path"]
    sample_files = glob.glob(f"{folder_path}/*.tif") + glob.glob(f"{folder_path}/*.tiff")
    st.write(f"Se encontraron **{len(sample_files)}** archivos en la carpeta.")

# --- Procesamiento si se han cargado las imágenes de referencia y se seleccionó una carpeta ---
if white_file is not None and dark_file is not None and len(sample_files) > 0:
    # Cargar las imágenes de referencia (blanca y oscura)
    white = tifffile.imread(white_file).astype(np.float32)
    dark  = tifffile.imread(dark_file).astype(np.float32)
    st.write(f"Dimensiones imagen blanca: {white.shape}")
    st.write(f"Dimensiones imagen oscura: {dark.shape}")
    
    # --- Parámetros para ROI y selección de bandas (barra lateral) ---
    st.markdown("### Parámetros de ROI y Selección de Bandas")
    st.sidebar.header("Parámetros")
    # Coordenadas de la ROI (en píxeles)
    x0 = st.sidebar.number_input("Coordenada x0 (inicio)", value=50, min_value=0)
    x1 = st.sidebar.number_input("Coordenada x1 (fin)", value=150, min_value=0)
    y0 = st.sidebar.number_input("Coordenada y0 (inicio)", value=100, min_value=0)
    y1 = st.sidebar.number_input("Coordenada y1 (fin)", value=200, min_value=0)
    
    # Usamos la primera imagen de la carpeta como referencia
    first_sample_file = sample_files[0]
    st.write(f"Procesando la primera imagen: {first_sample_file}")
    
    # Cargar la primera imagen de muestra
    sample = tifffile.imread(first_sample_file).astype(np.float32)
    # Ajustar dimensiones: se asume que la imagen es (bandas, alto, ancho). Si no, se transpone.
    if sample.ndim == 3:
        if sample.shape[0] < sample.shape[-1]:
            # Ya está en formato (bandas, alto, ancho)
            pass
        else:
            sample = np.transpose(sample, (2, 0, 1))
    else:
        st.error("La imagen de muestra no tiene 3 dimensiones.")
        st.stop()
    
    # Número de bandas disponibles y selección de las bandas para HbO₂ y Hb
    n_bands = sample.shape[0]
    band_hbo2 = st.sidebar.number_input("Índice de banda para HbO₂ (ej. 3 para 545 nm)", min_value=0, max_value=n_bands-1, value=3, step=1)
    band_hb   = st.sidebar.number_input("Índice de banda para Hb (ej. 4 para 560 nm)", min_value=0, max_value=n_bands-1, value=4, step=1)
    
    epsilon = 1e-6
    # Calcular la reflectancia: (muestra - oscura) / (blanca - oscura + epsilon)
    reflectance = (sample - dark) / (white - dark + epsilon)
    reflectance = np.clip(reflectance, 0, 1)
    
    # Seleccionar las bandas de interés
    img_hbo2 = reflectance[int(band_hbo2), :, :]
    img_hb   = reflectance[int(band_hb), :, :]
    
    # Para evitar divisiones por valores cercanos a cero en Hb, aplicamos un umbral mínimo
    umbral = 0.01
    img_hb_safe = np.where(img_hb < umbral, umbral, img_hb)
    
    # Calcular el índice de oxigenación
    oxy_index = img_hbo2 / (img_hb_safe + epsilon)
    
    # Verificar que la ROI esté dentro de las dimensiones de la imagen
    height, width = oxy_index.shape
    if x1 > width or y1 > height:
        st.error(f"La ROI excede las dimensiones de la imagen ({height}x{width}).")
        st.stop()
    
    # Crear la máscara de la ROI (True en la región y False en el resto)
    mask = np.zeros_like(oxy_index, dtype=bool)
    mask[int(y0):int(y1), int(x0):int(x1)] = True
    
    # Calcular estadísticas en la ROI
    roi_values = oxy_index[mask]
    media_roi = roi_values.mean()
    std_roi   = roi_values.std()
    
    # --- Extracción de la hora original del nombre del archivo ---
    def generar_nombre_solo_hora(original_filename):
        """
        Extrae la parte de la hora en formato HH-MM-SS-mmm del nombre del archivo.
        Ejemplo: '20241019_16-17-50-805_imagen_0.tiff' -> '16-17-50-805.tiff'
        """
        patron_hora = r"(\d{2}-\d{2}-\d{2}-\d{3})"
        match = re.search(patron_hora, original_filename)
        if match:
            hora_str = match.group(1)
            nuevo_nombre = f"{hora_str}.tiff"
            return nuevo_nombre
        else:
            return "output.tiff"
    
    nuevo_nombre = generar_nombre_solo_hora(first_sample_file)
    
    # --- Visualización ---
    st.markdown("### Imagen de Índice de Oxigenación con ROI")
    fig, ax = plt.subplots()
    cax = ax.imshow(oxy_index, cmap="jet")
    ax.contour(mask, colors='white', linewidths=1)
    ax.set_title(f"{nuevo_nombre}\nMedia ROI: {media_roi:.3f}")
    fig.colorbar(cax, ax=ax)
    st.pyplot(fig)
    
    st.markdown("### Estadísticas de la ROI")
    st.write(f"**Media:** {media_roi:.3f}")
    st.write(f"**Desviación Estándar:** {std_roi:.3f}")
    
    # --- Opción de guardar la imagen de salida con el nombre basado en la hora original ---
    buf = io.BytesIO()
    tifffile.imwrite(buf, oxy_index.astype(np.float32))
    buf.seek(0)
    st.download_button("Descargar imagen de salida (TIFF)", buf, file_name=nuevo_nombre, mime="image/tiff")
    
else:
    st.info("Por favor, carga las imágenes de referencia (blanca y oscura) y selecciona una carpeta con imágenes de muestra para comenzar.")
