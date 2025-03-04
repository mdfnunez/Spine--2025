import numpy as np
import cv2
from PIL import Image
import time
import os
import tkinter as tk
from tkinter import filedialog
from ximea import xiapi

def seleccionar_carpeta():
    root = tk.Tk()
    root.withdraw()
    carpeta = filedialog.askdirectory(title="Selecciona la carpeta donde guardar las imágenes")
    return carpeta if carpeta else None

ruta_base = seleccionar_carpeta()
if not ruta_base:
    print("No se seleccionó ninguna carpeta. Saliendo...")
    exit()

start_timestamp = time.strftime('%Y-%m-%d_%H-%M-%S')
ruta_rgb = os.path.join(ruta_base, f"{start_timestamp}_RGB")
ruta_tiff = os.path.join(ruta_base, f"{start_timestamp}_TIFF")
os.makedirs(ruta_rgb, exist_ok=True)
os.makedirs(ruta_tiff, exist_ok=True)

# Inicializar cámara
cam = xiapi.Camera()
try:
    cam.open_device()
except xiapi.Xi_error as e:
    if str(e) == "ERROR 57: Resource (device) or function locked by mutex":
        print("La cámara ya está abierta. Continuando...")
    else:
        raise e

cam.set_exposure(30000)
img = xiapi.Image()
cam.start_acquisition()

# Tiempo para guardado automático (en segundos)
guardar_cada = 2
start_time = time.time()

# Ventana para imagen + trackbars
cv2.namedWindow("RGB en vivo", cv2.WINDOW_NORMAL)

# --- Trackbars para Ajustes ---
# Los valores iniciales van en la 3ra posición:
cv2.createTrackbar("Gamma",       "RGB en vivo", 15,  50,  lambda x: None)  # (15/5=3.0)
cv2.createTrackbar("Hue",         "RGB en vivo",  3, 100,  lambda x: None)  # 3
cv2.createTrackbar("Saturación",  "RGB en vivo", 157,300,  lambda x: None)  # 157/100=1.57
cv2.createTrackbar("Contraste",   "RGB en vivo",  80,300,  lambda x: None)  # 80/100=0.8

# --- Trackbars para elegir canales (0 - 15) ---
# con tus estándares R=12, G=5, B=2
cv2.createTrackbar("Canal R", "RGB en vivo", 12, 15, lambda x: None)
cv2.createTrackbar("Canal G", "RGB en vivo",  5, 15, lambda x: None)
cv2.createTrackbar("Canal B", "RGB en vivo",  2, 15, lambda x: None)

# --- Trackbar para (Des)activar Ajustes ---
cv2.createTrackbar("Activar Ajustes", "RGB en vivo", 1, 1, lambda x: None)
# (0 = OFF, 1 = ON)

def adjust_gamma(image, gamma=1.0):
    invGamma = 1.0 / gamma
    table = np.array([(i / 255.0) ** invGamma * 255 
                      for i in np.arange(0, 256)]).astype("uint8")
    return cv2.LUT(image, table)

def adjust_hue(image, hue_shift):
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    hsv[:, :, 0] = (hsv[:, :, 0] + hue_shift) % 180
    return cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)

def adjust_saturation(image, saturation_factor):
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    hsv[:, :, 1] = np.clip(hsv[:, :, 1].astype(np.float32)*saturation_factor, 0, 255).astype(np.uint8)
    return cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)

while True:
    cam.get_image(img)
    data_raw = img.get_image_data_raw()
    image_np = np.frombuffer(data_raw, dtype=np.uint8).reshape(img.height, img.width)

    # Separar en 16 canales (patrón mosaico 4x4)
    channels = np.zeros((img.height // 4, img.width // 4, 16), dtype=np.uint8)
    for y in range(4):
        for x in range(4):
            channels[:, :, y * 4 + x] = image_np[y::4, x::4]

    # Leemos la posición del "switch" de ajustes
    activar = cv2.getTrackbarPos("Activar Ajustes", "RGB en vivo")

    # Canales para R, G, B
    r_ch = cv2.getTrackbarPos("Canal R", "RGB en vivo")
    g_ch = cv2.getTrackbarPos("Canal G", "RGB en vivo")
    b_ch = cv2.getTrackbarPos("Canal B", "RGB en vivo")

    # Generar el "falso" RGB con los canales indicados
    false_rgb = np.stack((channels[:, :, r_ch],
                          channels[:, :, g_ch],
                          channels[:, :, b_ch]), axis=-1).astype(np.float32)

    # Normalizar para visualización
    min_val, max_val = np.min(false_rgb), np.max(false_rgb)
    false_rgb = 255 * (false_rgb - min_val) / (max_val - min_val)
    false_rgb = false_rgb.astype(np.uint8)

    # Si la casilla está ON, aplicamos los ajustes
    if activar == 1:
        gamma_value = cv2.getTrackbarPos("Gamma",       "RGB en vivo") / 5.0
        hue_shift   = cv2.getTrackbarPos("Hue",         "RGB en vivo")
        sat_factor  = cv2.getTrackbarPos("Saturación",  "RGB en vivo") / 100.0
        contraste   = cv2.getTrackbarPos("Contraste",   "RGB en vivo") / 100.0

        # Aplicar ajustes
        false_rgb = adjust_gamma(false_rgb, gamma_value)
        false_rgb = adjust_hue(false_rgb, hue_shift)
        false_rgb = adjust_saturation(false_rgb, sat_factor)

        # Ajuste de contraste
        false_rgb = cv2.convertScaleAbs(false_rgb, alpha=contraste, beta=0)
    
    # Mostrar la imagen
    false_rgb_resized = cv2.resize(false_rgb, (1800, 850))
    cv2.imshow("RGB en vivo", false_rgb_resized)

    # Guardado automático
    current_time = time.time()
    if current_time - start_time >= guardar_cada:
        frame_timestamp = time.strftime('%H-%M-%S-%f')[:-3]
        
        false_rgb_corrected = cv2.cvtColor(false_rgb, cv2.COLOR_BGR2RGB)
        rgb_filename = os.path.join(ruta_rgb, f"RGB_{frame_timestamp}.png")
        Image.fromarray(false_rgb_corrected).save(rgb_filename)

        tiff_filename = os.path.join(ruta_tiff, f"RAW_{frame_timestamp}.tiff")
        raw_tiff = Image.fromarray(image_np)
        raw_tiff.save(tiff_filename, compression="tiff_deflate")

        print(f"Guardado: {rgb_filename} y {tiff_filename}")
        start_time = current_time

    # Salir con 'q'
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cam.stop_acquisition()
cam.close_device()
cv2.destroyAllWindows()
