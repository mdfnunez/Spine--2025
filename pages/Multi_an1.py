import os
import tifffile as tiff
import numpy as np
import matplotlib.pyplot as plt
import tkinter as tk
from tkinter import filedialog, messagebox

# Diccionarios para almacenar rutas y datos
rutas = {"basal": None, "compresion": None, "post": None, "blanco": None, "negro": None}
imagenes = {"basal": None, "compresion": None, "post": None, "blanco": None, "negro": None}

# Función para seleccionar archivos (permite ver todos, pero solo carga TIFF)
def seleccionar_archivo(tipo):
    archivo = filedialog.askopenfilename(title=f"Selecciona la imagen {tipo}",
                                         filetypes=[("Todos los archivos", "*.*"), ("TIFF Files", "*.tif;*.tiff")])
    if archivo:
        try:
            imagen_test = tiff.imread(archivo)  # Intentar leer el archivo para verificar que es válido
            rutas[tipo] = archivo
            etiquetas[tipo].config(text=f"{tipo.capitalize()}: {archivo.split('/')[-1]}")
            print(f"✅ {tipo.capitalize()} seleccionado: {archivo}")
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo cargar el archivo {archivo}. No es un TIFF válido.\n{str(e)}")

# Función para cargar imágenes MultiTIFF
def cargar_imagenes():
    global imagenes
    for tipo in rutas.keys():
        if rutas[tipo]:
            try:
                imagenes[tipo] = tiff.imread(rutas[tipo])
                print(f"✅ {tipo.capitalize()} cargado: {imagenes[tipo].shape}")
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo cargar {tipo}: {str(e)}")
                return
    etiqueta_info.config(text="Imágenes cargadas correctamente.")

# Función para calcular reflectancia normalizada
def calcular_reflectancia(muestra, blanco, negro):
    blanco = np.maximum(blanco, negro + 1e-6)  # Evitar divisiones por 0
    reflectancia = (muestra - negro) / (blanco - negro)
    reflectancia = np.clip(reflectancia, 0, 1)  # Limitar valores entre 0 y 1
    return reflectancia

# Función para visualizar mapas de diferencias con la basal como referencia y una máscara
def visualizar_diferencias():
    if any(imagenes[tipo] is None for tipo in ["basal", "compresion", "post", "blanco", "negro"]):
        messagebox.showwarning("Advertencia", "Primero debes cargar todas las imágenes.")
        return

    try:
        banda = int(entry_banda.get())

        # Aplicar corrección de reflectancia
        reflectancia_basal = calcular_reflectancia(imagenes["basal"], imagenes["blanco"], imagenes["negro"])
        reflectancia_compresion = calcular_reflectancia(imagenes["compresion"], imagenes["blanco"], imagenes["negro"])
        reflectancia_post = calcular_reflectancia(imagenes["post"], imagenes["blanco"], imagenes["negro"])

        # Calcular diferencias con la basal como referencia
        diferencia_basal_compresion = reflectancia_compresion - reflectancia_basal
        diferencia_basal_post = reflectancia_post - reflectancia_basal

        # Crear una máscara de la imagen basal (resaltamos las zonas con valores altos)
        mascara = np.where(reflectancia_basal[banda] > np.percentile(reflectancia_basal[banda], 80), 1, 0)

        # Ajustar la escala de color si las diferencias son muy pequeñas
        vmin_dif = np.min([diferencia_basal_compresion[banda], diferencia_basal_post[banda]])
        vmax_dif = np.max([diferencia_basal_compresion[banda], diferencia_basal_post[banda]])

        if np.abs(vmin_dif) < 0.1 and np.abs(vmax_dif) < 0.1:
            vmin_dif, vmax_dif = -0.1, 0.1  # Ajustar escala para hacer los cambios más visibles

        # Graficar las imágenes
        fig, axes = plt.subplots(1, 4, figsize=(20, 5))

        # Imagen original con la máscara de la basal
        axes[0].imshow(imagenes["basal"][banda], cmap='gray')
        axes[0].imshow(mascara, cmap='jet', alpha=0.5)  # Superponer máscara en azul-rojo
        axes[0].set_title(f'Original con Máscara Basal - Banda {banda}')
        axes[0].axis("off")

        # Imagen basal en escala de grises
        axes[1].imshow(reflectancia_basal[banda], cmap='gray', vmin=0, vmax=1)
        axes[1].set_title(f'Basal - Banda {banda}')
        axes[1].axis("off")

        # Diferencia entre Basal y Compresión
        im1 = axes[2].imshow(diferencia_basal_compresion[banda], cmap='bwr', vmin=vmin_dif, vmax=vmax_dif)
        axes[2].set_title('Cambio: Basal → Compresión')
        plt.colorbar(im1, ax=axes[2])
        axes[2].axis("off")

        # Diferencia entre Basal y Post-Compresión
        im2 = axes[3].imshow(diferencia_basal_post[banda], cmap='bwr', vmin=vmin_dif, vmax=vmax_dif)
        axes[3].set_title('Cambio: Basal → Post-Compresión')
        plt.colorbar(im2, ax=axes[3])
        axes[3].axis("off")

        plt.show()

    except Exception as e:
        messagebox.showerror("Error", f"No se pudo visualizar la banda: {str(e)}")

# Crear interfaz gráfica
root = tk.Tk()
root.title("Cargar imágenes MultiTIFF y calcular reflectancia")

# Etiquetas y botones para selección de archivos
etiquetas = {}
for tipo in rutas.keys():
    frame = tk.Frame(root)
    frame.pack(pady=5)
    etiquetas[tipo] = tk.Label(frame, text=f"{tipo.capitalize()}: No seleccionado")
    etiquetas[tipo].pack(side=tk.LEFT)
    btn = tk.Button(frame, text="Seleccionar", command=lambda t=tipo: seleccionar_archivo(t))
    btn.pack(side=tk.RIGHT)

# Botón para cargar imágenes
btn_cargar = tk.Button(root, text="Cargar Imágenes", command=cargar_imagenes)
btn_cargar.pack(pady=5)

# Etiqueta de información de imágenes cargadas
etiqueta_info = tk.Label(root, text="Esperando carga de imágenes...")
etiqueta_info.pack(pady=5)

# Entrada y botón para visualizar mapas de diferencias
frame_banda = tk.Frame(root)
frame_banda.pack(pady=5)
tk.Label(frame_banda, text="Banda a visualizar:").pack(side=tk.LEFT)
entry_banda = tk.Entry(frame_banda, width=5)
entry_banda.pack(side=tk.LEFT)
entry_banda.insert(0, "5")  # Banda por defecto
btn_ver = tk.Button(frame_banda, text="Ver Diferencias", command=visualizar_diferencias)
btn_ver.pack(side=tk.LEFT)

# Iniciar GUI
root.mainloop()
