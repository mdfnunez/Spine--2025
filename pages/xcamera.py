from ximea import xiapi
import numpy as np
import cv2
from PIL import Image
import time
import os

# Crear una instancia para la primera cámara conectada
cam = xiapi.Camera()

try:
    # Abrir la cámara
    cam.open_device()
except xiapi.Xi_error as e:
    if str(e) == "ERROR 57: Resource (device) or function locked by mutex":
        print("La cámara ya está abierta. Continuando...")
    else:
        raise e

# Disminuir la exposición
cam.set_exposure(5000)  # Reducir a 10 ms

# Crear una instancia de Image para almacenar los datos
img = xiapi.Image()

# Iniciar la adquisición de datos
cam.start_acquisition()

# Obtener el timestamp del inicio de la grabación y crear una carpeta con ese nombre
start_timestamp = time.strftime('%Y-%m-%d_%H h, %M min, %S seg')
os.makedirs(start_timestamp, exist_ok=True)

# Configurar el tiempo de inicio para los archivos de frames
start_time = time.time()

while True:
    # Capturar una imagen
    cam.get_image(img)
    data_raw = img.get_image_data_raw()

    # Convertir los datos crudos a un array de NumPy
    image_np = np.frombuffer(data_raw, dtype=np.uint8).reshape(img.height, img.width)

    # Ahora vamos a dividir la imagen en 16 canales siguiendo un patrón mosaico
    channels = np.zeros((img.height // 4, img.width // 4, 16), dtype=np.uint8)

    # Reorganizar los píxeles en los 16 canales
    for y in range(4):
        for x in range(4):
            # Extraer los sub-píxeles que corresponden a cada canal en el mosaico
            channels[:, :, y * 4 + x] = image_np[y::4, x::4]

    # Crear una imagen en falso color combinando los canales 2, 8 y 15
    false_rgb = np.stack((channels[:, :, 11],  # Rojo
                      channels[:, :, 7],   # Verde
                      channels[:, :, 3]), axis=-1)  # Azul

    # Redimensionar para visualización
    false_rgb_resized = cv2.resize(false_rgb, (640, 360))
    flipped_rgb = cv2.flip(false_rgb_resized, -1)  # -1 para voltear en ambas direcciones

    # Mostrar la imagen RGB falsa
    cv2.imshow('RGB Falso (Canales 2, 8, 15)', flipped_rgb)

    # Guardar cada segundo en un archivo TIFF
    current_time = time.time()
    if current_time - start_time >= 1:
        frame_timestamp = time.strftime('%H h, %M min, %S seg')
        tiff_filename = f'{start_timestamp}/frame_{frame_timestamp}.tiff'
        Image.fromarray(false_rgb).save(tiff_filename, compression="tiff_deflate")
        start_time = current_time

    # Esperar 1 ms y capturar la tecla presionada
    key = cv2.waitKey(1) & 0xFF
    if key == ord('q'):  # Salir si se presiona 'q'
        break

# Detener la adquisición de datos y cerrar la cámara
cam.stop_acquisition()
cam.close_device()

# Cerrar todas las ventanas
cv2.destroyAllWindows()
