from ximea import xiapi
import numpy as np
import cv2
from PIL import Image
import time
import os

# Crear una instancia para la primera cámara conectada
cam = xiapi.Camera()

# Abrir la cámara
cam.open_device()

# Ajustar la exposición
cam.set_exposure(50000)

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

    # Añadir los 16 canales como páginas separadas en un archivo multitiff
    frames = []
    for i in range(16):
        # Convertir cada canal a formato PIL Image
        pil_image = Image.fromarray(channels[:, :, i])
        # Agregar a la lista de frames
        frames.append(pil_image)

    # Guardar las imágenes en un archivo multitiff cada segundo
    current_time = time.time()
    if current_time - start_time >= 1:
        # Obtener el timestamp actual para el nombre del archivo
        frame_timestamp = time.strftime('%H h, %M min, %S seg')

        # Generar un nombre de archivo con timestamp
        tiff_filename = f'{start_timestamp}/frame_{frame_timestamp}.tiff'

        # Guardar los 16 canales en un archivo multitiff
        frames[0].save(tiff_filename, save_all=True, append_images=frames[1:], compression="tiff_deflate")

        # Resetear el tiempo
        start_time = current_time

    # Mostrar la imagen del primer canal como referencia
    image_resized = cv2.resize(channels[:, :, 0], (640, 360))  # Mostrar solo el primer canal
    flipped_image = cv2.flip(image_resized, -1)  # -1 para voltear en ambas direcciones

    # Mostrar la imagen invertida en la misma ventana OpenCV
    cv2.imshow('Video continuo - Canal 1', flipped_image)

    # Esperar 1 ms y capturar la tecla presionada
    key = cv2.waitKey(1) & 0xFF
    if key == ord('q'):  # Salir si se presiona 'q'
        break

# Detener la adquisición de datos y cerrar la cámara
cam.stop_acquisition()
cam.close_device()

# Cerrar todas las ventanas
cv2.destroyAllWindows()
