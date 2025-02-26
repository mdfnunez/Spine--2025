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
    print("Cámara abierta con éxito.")
except xiapi.Xi_error as e:
    if str(e) == "ERROR 57: Resource (device) or function locked by mutex":
        print("La cámara ya está abierta. Continuando...")
    else:
        print(f"Error al abrir la cámara: {e}")
        raise e

try:
    # Disminuir la exposición
    cam.set_exposure(5000)  # Reducir a 10 ms
    print("Exposición ajustada.")
except Exception as e:
    print(f"Error al ajustar la exposición: {e}")
    raise e

try:
    # Crear una instancia de Image para almacenar los datos
    img = xiapi.Image()

    # Iniciar la adquisición de datos
    cam.start_acquisition()
    print("Adquisición de datos iniciada.")
except Exception as e:
    print(f"Error al iniciar la adquisición de datos: {e}")
    raise e

# Obtener el timestamp del inicio de la grabación y crear una carpeta con ese nombre
start_timestamp = time.strftime('%Y-%m-%d_%H h, %M min, %S seg')
os.makedirs(start_timestamp, exist_ok=True)
print(f"Carpeta creada: {start_timestamp}")

# Configurar el tiempo de inicio para los archivos de frames
start_time = time.time()

# Crear una ventana para los controles
cv2.namedWindow('Controles')

# Funciones de callback para los trackbars
def nothing(x):
    pass

# Crear trackbars para ajustar la saturación y los colores
cv2.createTrackbar('Saturación', 'Controles', 100, 200, nothing)
cv2.createTrackbar('Rojo', 'Controles', 100, 200, nothing)
cv2.createTrackbar('Verde', 'Controles', 100, 200, nothing)
cv2.createTrackbar('Azul', 'Controles', 100, 200, nothing)
print("Trackbars creados.")

try:
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
                              channels[:, :, 3]), axis=-1).astype(np.float32)

        # Normalizar los valores a 0-255 en cada canal
        for i in range(3):
            false_rgb[:, :, i] = 255 * (false_rgb[:, :, i] - np.min(false_rgb[:, :, i])) / (np.max(false_rgb[:, :, i]) - np.min(false_rgb[:, :, i]))

        false_rgb = false_rgb.astype(np.uint8)  # Convertir de nuevo a uint8

        # Obtener los valores de los trackbars
        saturation = cv2.getTrackbarPos('Saturación', 'Controles') / 100.0
        red = cv2.getTrackbarPos('Rojo', 'Controles') / 100.0
        green = cv2.getTrackbarPos('Verde', 'Controles') / 100.0
        blue = cv2.getTrackbarPos('Azul', 'Controles') / 100.0

        # Aplicar la saturación y los ajustes de color
        hsv = cv2.cvtColor(false_rgb, cv2.COLOR_BGR2HSV)
        hsv[:, :, 1] = np.clip(hsv[:, :, 1] * saturation, 0, 255)
        false_rgb = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)
        false_rgb[:, :, 0] = np.clip(false_rgb[:, :, 0] * blue, 0, 255)
        false_rgb[:, :, 1] = np.clip(false_rgb[:, :, 1] * green, 0, 255)
        false_rgb[:, :, 2] = np.clip(false_rgb[:, :, 2] * red, 0, 255)

        # Redimensionar para visualización
        false_rgb_resized = cv2.resize(false_rgb, (1280, 720))
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
except Exception as e:
    print(f"Error durante la adquisición de imágenes: {e}")
finally:
    # Detener la adquisición de datos y cerrar la cámara
    cam.stop_acquisition()
    cam.close_device()
    print("Cámara cerrada.")

    # Cerrar todas las ventanas
    cv2.destroyAllWindows()
    print("Ventanas destruidas.")
