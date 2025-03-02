import numpy as np
import cv2
from PIL import Image
import time
import os
import tkinter as tk
from tkinter import filedialog
from ximea import xiapi

# 📌 Seleccionar carpeta de guardado con Tkinter
def seleccionar_carpeta():
    root = tk.Tk()
    root.withdraw()  # Ocultar la ventana principal de Tkinter
    carpeta = filedialog.askdirectory(title="Selecciona la carpeta donde guardar las imágenes")
    return carpeta if carpeta else None

# 📌 Obtener la ruta de almacenamiento
ruta_base = seleccionar_carpeta()
if not ruta_base:
    print("No se seleccionó ninguna carpeta. Saliendo...")
    exit()

# 📌 Crear subcarpetas para imágenes RGB y TIFF RAW
start_timestamp = time.strftime('%Y-%m-%d_%H-%M-%S')
ruta_rgb = os.path.join(ruta_base, f"{start_timestamp}_RGB")
ruta_tiff = os.path.join(ruta_base, f"{start_timestamp}_TIFF")

os.makedirs(ruta_rgb, exist_ok=True)
os.makedirs(ruta_tiff, exist_ok=True)

# 📌 Inicializar cámara
cam = xiapi.Camera()
try:
    cam.open_device()
except xiapi.Xi_error as e:
    if str(e) == "ERROR 57: Resource (device) or function locked by mutex":
        print("La cámara ya está abierta. Continuando...")
    else:
        raise e

cam.set_exposure(30000)  # Ajustar exposición
img = xiapi.Image()
cam.start_acquisition()

# 📌 Definir frecuencia de guardado en segundos
guardar_cada = 2  # Antes era 1s, ahora cada 2s
start_time = time.time()

# 📌 Crear ventana de ajuste
cv2.namedWindow("Ajustes")

# 📌 Función para ajustar el gamma
def adjust_gamma(image, gamma=1.0):
    invGamma = 1.0 / gamma
    table = np.array([(i / 255.0) ** invGamma * 255 for i in np.arange(0, 256)]).astype("uint8")
    return cv2.LUT(image, table)

# 📌 Función para cambiar el tono (Hue)
def adjust_hue(image, hue_shift):
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    hsv[:, :, 0] = (hsv[:, :, 0] + hue_shift) % 180  # Hue se ajusta en un rango de 0-179
    return cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)

# 📌 Trackbars para ajustar gamma y hue
cv2.createTrackbar("Gamma", "Ajustes", 10, 50, lambda x: None)  # Rango 0.1 - 5.0
cv2.createTrackbar("Hue", "Ajustes", 0, 180, lambda x: None)  # Hue shift entre 0 y 180

while True:
    # 📌 Capturar imagen de la cámara
    cam.get_image(img)
    data_raw = img.get_image_data_raw()
    image_np = np.frombuffer(data_raw, dtype=np.uint8).reshape(img.height, img.width)

    # 📌 Separar en 16 canales siguiendo patrón mosaico
    channels = np.zeros((img.height // 4, img.width // 4, 16), dtype=np.uint8)
    for y in range(4):
        for x in range(4):
            channels[:, :, y * 4 + x] = image_np[y::4, x::4]

    # 📌 Generar RGB falso usando canales 11, 7, 3
    false_rgb = np.stack((channels[:, :, 11], 
                          channels[:, :, 7], 
                          channels[:, :, 3]), axis=-1).astype(np.float32)

    # 📌 Normalizar para mejorar visualización
    false_rgb = 255 * (false_rgb - np.min(false_rgb)) / (np.max(false_rgb) - np.min(false_rgb))
    false_rgb = false_rgb.astype(np.uint8)

    # 📌 Obtener valores actuales de gamma y hue
    gamma_value = cv2.getTrackbarPos("Gamma", "Ajustes") / 5.0  # Convertir a 0.1 - 5.0
    hue_shift = cv2.getTrackbarPos("Hue", "Ajustes")

    # 📌 Aplicar ajustes
    false_rgb = adjust_gamma(false_rgb, gamma_value)
    false_rgb = adjust_hue(false_rgb, hue_shift)

    # 📌 Redimensionar para aumentar velocidad de visualización
    false_rgb_resized = cv2.resize(false_rgb, (1800, 850))
    cv2.imshow('RGB Falso (Canales 11, 7, 3)', false_rgb_resized)

    # 📌 Guardar imágenes más frecuentemente
    current_time = time.time()
    if current_time - start_time >= guardar_cada:
        frame_timestamp = time.strftime('%H-%M-%S-%f')[:-3]  # Más precisión en el tiempo

        # 📌 Guardar RGB como PNG
        rgb_filename = os.path.join(ruta_rgb, f"RGB_{frame_timestamp}.png")
        Image.fromarray(false_rgb).save(rgb_filename)

        # 📌 Guardar imagen TIFF RAW
        tiff_filename = os.path.join(ruta_tiff, f"RAW_{frame_timestamp}.tiff")
        raw_tiff = Image.fromarray(image_np)
        raw_tiff.save(tiff_filename, compression="tiff_deflate")

        print(f"Guardado: {rgb_filename} y {tiff_filename}")
        start_time = current_time

    # 📌 Reducir el tiempo de espera para aumentar velocidad
    if cv2.waitKey(1) & 0xFF == ord('q'):  # Antes era cv2.waitKey(1)
        break

# 📌 Detener adquisición y cerrar cámara
cam.stop_acquisition()
cam.close_device()
cv2.destroyAllWindows()
