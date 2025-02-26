from ximea import xiapi
import numpy as np
import cv2
from PIL import Image
import time
import os

# Crear una instancia para la primera cámara conectada
cam = xiapi.Camera()

try:
    cam.open_device()
except xiapi.Xi_error as e:
    if str(e) == "ERROR 57: Resource (device) or function locked by mutex":
        print("La cámara ya está abierta. Continuando...")
    else:
        raise e

# Configuración inicial
cam.set_exposure(10000)  # Reducir exposición
img = xiapi.Image()
cam.start_acquisition()

# Crear ventana de configuración interactiva
cv2.namedWindow("Configuración", cv2.WINDOW_NORMAL)
cv2.resizeWindow("Configuración", 400, 300)

# Crear barras deslizantes
cv2.createTrackbar("Brillo", "Configuración", 50, 100, lambda x: None)
cv2.createTrackbar("Contraste", "Configuración", 3, 10, lambda x: None)
cv2.createTrackbar("Saturación", "Configuración", 50, 100, lambda x: None)

while True:
    # Capturar imagen
    cam.get_image(img)
    data_raw = img.get_image_data_raw()
    image_np = np.frombuffer(data_raw, dtype=np.uint8).reshape(img.height, img.width)

    # Separar en 16 canales
    channels = np.zeros((img.height // 4, img.width // 4, 16), dtype=np.uint8)
    for y in range(4):
        for x in range(4):
            channels[:, :, y * 4 + x] = image_np[y::4, x::4]

    # Seleccionar los canales para falso color RGB
    false_rgb = np.stack((channels[:, :, 11],  # Rojo
                          channels[:, :, 7],   # Verde
                          channels[:, :, 3]), axis=-1).astype(np.float32)

    # Obtener valores de los sliders
    brillo = cv2.getTrackbarPos("Brillo", "Configuración") / 50  # Rango 0.5 - 2.0
    contraste = cv2.getTrackbarPos("Contraste", "Configuración")  # Rango 1 - 10
    saturacion = cv2.getTrackbarPos("Saturación", "Configuración") / 50  # Rango 0.5 - 2.0

    # Normalizar cada canal (Brillo automático)
    for i in range(3):
        min_val, max_val = np.min(false_rgb[:, :, i]), np.max(false_rgb[:, :, i])
        false_rgb[:, :, i] = 255 * (false_rgb[:, :, i] - min_val) / (max_val - min_val + 1e-6)

    # Aplicar ajuste de contraste con CLAHE
    clahe = cv2.createCLAHE(clipLimit=contraste, tileGridSize=(8, 8))
    for i in range(3):
        false_rgb[:, :, i] = clahe.apply(false_rgb[:, :, i].astype(np.uint8))

    # Convertir a uint8 y ajustar brillo
    false_rgb = np.clip(false_rgb * brillo, 0, 255).astype(np.uint8)

    # Convertir a HSV y ajustar saturación
    false_rgb_hsv = cv2.cvtColor(false_rgb, cv2.COLOR_RGB2HSV)
    false_rgb_hsv[:, :, 1] = np.clip(false_rgb_hsv[:, :, 1] * saturacion, 0, 255)
    false_rgb = cv2.cvtColor(false_rgb_hsv, cv2.COLOR_HSV2RGB)

    # Redimensionar imagen y mostrar
    false_rgb_resized = cv2.resize(false_rgb, (1280, 720))
    cv2.imshow("RGB Falso (Canales 11, 7, 3)", false_rgb_resized)

    # Salir con 'q'
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# Detener adquisición y cerrar cámara
cam.stop_acquisition()
cam.close_device()
cv2.destroyAllWindows()
