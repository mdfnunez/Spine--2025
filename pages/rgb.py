import os
import numpy as np
from PIL import Image
import tkinter as tk
from tkinter import filedialog

# Función para seleccionar carpetas
def seleccionar_carpeta(mensaje):
    root = tk.Tk()
    root.withdraw()  # Ocultar ventana de Tkinter
    carpeta = filedialog.askdirectory(title=mensaje)  # Abrir diálogo para seleccionar carpeta
    return carpeta if carpeta else None  # Devolver la carpeta seleccionada o None si se cancela

# Seleccionar la carpeta de entrada (imágenes originales)
ruta_entrada = seleccionar_carpeta("Seleccione la carpeta con las imágenes originales")
if not ruta_entrada:
    print("❌ No se seleccionó ninguna carpeta de entrada. Saliendo...")
    exit()

# Seleccionar la carpeta de salida (donde se guardarán las imágenes corregidas)
ruta_salida = seleccionar_carpeta("Seleccione la carpeta donde se guardarán las imágenes corregidas")
if not ruta_salida:
    print("❌ No se seleccionó ninguna carpeta de salida. Saliendo...")
    exit()

# Crear la carpeta de salida si no existe
if not os.path.exists(ruta_salida):
    os.makedirs(ruta_salida)

# Obtener la lista de imágenes PNG en la carpeta de entrada
imagenes = [f for f in os.listdir(ruta_entrada) if f.lower().endswith(".png")]

if not imagenes:
    print("❌ No se encontraron imágenes PNG en la carpeta seleccionada. Saliendo...")
    exit()

# Iterar sobre todas las imágenes en la carpeta de entrada
for imagen_nombre in imagenes:
    ruta_completa = os.path.join(ruta_entrada, imagen_nombre)

    # Cargar la imagen con PIL y convertirla en un array NumPy
    imagen = Image.open(ruta_completa)
    imagen_array = np.array(imagen)

    # Verificar si la imagen tiene 3 canales (RGB) o 4 canales (RGBA)
    if imagen_array.shape[-1] == 3:  # Imagen RGB
        imagen_corregida = imagen_array[:, :, [2, 1, 0]]  # Intercambiar Rojo y Azul
    elif imagen_array.shape[-1] == 4:  # Imagen RGBA (con transparencia)
        rgb = imagen_array[:, :, :3]  # Extraer los primeros 3 canales (RGB)
        alpha = imagen_array[:, :, 3]  # Extraer canal Alfa
        rgb_corregido = rgb[:, :, [2, 1, 0]]  # Corregir RGB ↔ BGR
        imagen_corregida = np.dstack((rgb_corregido, alpha))  # Juntar con el canal Alfa
    else:
        print(f"⚠️ {imagen_nombre} no es RGB ni RGBA, se omitió.")
        continue  # Saltar imágenes que no sean RGB/RGBA

    # Convertir de nuevo a imagen PIL y guardar
    imagen_final = Image.fromarray(imagen_corregida)
    ruta_guardado = os.path.join(ruta_salida, imagen_nombre)
    imagen_final.save(ruta_guardado)

    print(f"✅ Imagen corregida y guardada: {ruta_guardado}")

print("🎉 Proceso completado para todas las imágenes.")