import os
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
import tifffile as tiff
import numpy as np
import matplotlib.pyplot as plt

# Extensiones permitidas para imágenes
EXT_PERMITIDAS = (".tif", ".tiff")

def seleccionar_archivo(titulo, filetypes=[("Imágenes", EXT_PERMITIDAS), ("Todos", "*.*")]):
    root = tk.Tk()
    root.withdraw()
    path = filedialog.askopenfilename(title=titulo, filetypes=filetypes)
    root.destroy()
    return path

def seleccionar_carpeta(titulo="Selecciona la carpeta con imágenes multispectrales"):
    root = tk.Tk()
    root.withdraw()
    carpeta = filedialog.askdirectory(title=titulo)
    root.destroy()
    return carpeta

def seleccionar_canal(titulo, canal_por_defecto):
    root = tk.Tk()
    root.withdraw()
    canal = simpledialog.askinteger(titulo, f"Introduce el número del canal (0-15):", initialvalue=canal_por_defecto)
    root.destroy()
    return canal

def ajustar_formato_imagen(imagen):
    """
    Si la imagen viene en formato channels-first (16 x H x W),
    la transpone para tener los canales en la última dimensión (H x W x 16).
    """
    if imagen.ndim == 3:
        if imagen.shape[0] == 16 and imagen.shape[2] != 16:
            imagen = np.transpose(imagen, (1, 2, 0))
    return imagen

def process_image(ruta, ref_vals_iso, ref_vals_hem, canal_isos, canal_hem, epsilon=1e-6):
    """
    Procesa la imagen en 'ruta' y calcula el índice de hemoglobina oxigenada.
    Se utiliza:
      reflectancia = (imagen - ref_negro) / (ref_blanco - ref_negro + epsilon)
      OD = -ln(reflectancia)
      Índice = OD_hem - OD_iso
    Retorna:
      - oxygenation_index: matriz con el índice (valores numéricos originales, en escala de grises).
      - canal_imagen_iso: imagen del canal isosbástico (para usar como fondo).
    """
    try:
        img = tiff.imread(ruta)
    except Exception as e:
        print(f"Error al cargar {ruta}: {e}")
        return None, None

    img = ajustar_formato_imagen(img)
    if img.ndim != 3 or img.shape[2] < 16:
        print(f"La imagen {ruta} no tiene 16 canales; se omite.")
        return None, None

    # Extraer los canales de interés
    canal_imagen_iso = img[:, :, canal_isos].astype(np.float64)
    canal_imagen_hem = img[:, :, canal_hem].astype(np.float64)

    # Calcular reflectancias usando valores de referencia (percentiles)
    reflectancia_iso = (canal_imagen_iso - ref_vals_iso[1]) / (ref_vals_iso[0] - ref_vals_iso[1] + epsilon)
    reflectancia_hem = (canal_imagen_hem - ref_vals_hem[1]) / (ref_vals_hem[0] - ref_vals_hem[1] + epsilon)
    reflectancia_iso = np.clip(reflectancia_iso, epsilon, 1)
    reflectancia_hem = np.clip(reflectancia_hem, epsilon, 1)

    # Calcular densidad óptica (OD)
    OD_iso = -np.log(reflectancia_iso)
    OD_hem = -np.log(reflectancia_hem)

    # Índice de hemoglobina oxigenada: diferencia de OD
    oxygenation_index = OD_hem - OD_iso

    return oxygenation_index, canal_imagen_iso

def main():
    epsilon = 1e-6

    # Seleccionar imágenes de referencia (blanca y negra)
    path_blanco = seleccionar_archivo("Selecciona la imagen de referencia BLANCA")
    if not path_blanco:
        messagebox.showerror("Error", "No se seleccionó la imagen de referencia blanca.")
        return

    path_negro = seleccionar_archivo("Selecciona la imagen de referencia NEGRA")
    if not path_negro:
        messagebox.showerror("Error", "No se seleccionó la imagen de referencia negra.")
        return

    try:
        img_blanco = tiff.imread(path_blanco)
        img_negro  = tiff.imread(path_negro)
    except Exception as e:
        messagebox.showerror("Error", f"Error al cargar las imágenes de referencia:\n{e}")
        return

    # Ajustar formato a channels-last
    img_blanco = ajustar_formato_imagen(img_blanco)
    img_negro  = ajustar_formato_imagen(img_negro)
    for img, nombre in zip([img_blanco, img_negro], ["blanca", "negra"]):
        if img.ndim != 3 or img.shape[2] < 16:
            messagebox.showerror("Error", f"La imagen de referencia {nombre} debe tener 16 canales.")
            return

    # Seleccionar canales a utilizar (por defecto: 6 para isosbástico y 5 para hemoglobina)
    canal_isos = seleccionar_canal("Canal Isosbástico", 6)
    if canal_isos is None or not (0 <= canal_isos < 16):
        messagebox.showerror("Error", "Canal isosbástico no válido.")
        return

    canal_hem = seleccionar_canal("Canal Hemoglobina", 5)
    if canal_hem is None or not (0 <= canal_hem < 16):
        messagebox.showerror("Error", "Canal de hemoglobina no válido.")
        return

    # Calcular valores de referencia usando percentiles
    ref_blanco_iso = np.percentile(img_blanco[:, :, canal_isos], 99)
    ref_negro_iso  = np.percentile(img_negro[:, :, canal_isos], 1)
    ref_vals_iso = (ref_blanco_iso, ref_negro_iso)

    ref_blanco_hem = np.percentile(img_blanco[:, :, canal_hem], 99)
    ref_negro_hem  = np.percentile(img_negro[:, :, canal_hem], 1)
    ref_vals_hem = (ref_blanco_hem, ref_negro_hem)

    print("Referencias Isosbástico: Blanco = {:.2f}, Negro = {:.2f}".format(ref_blanco_iso, ref_negro_iso))
    print("Referencias Hemoglobina: Blanco = {:.2f}, Negro = {:.2f}".format(ref_blanco_hem, ref_negro_hem))

    # Seleccionar carpeta con imágenes de muestra
    carpeta = seleccionar_carpeta("Selecciona la carpeta con imágenes multispectrales")
    if not carpeta:
        messagebox.showerror("Error", "No se seleccionó ninguna carpeta.")
        return

    rutas = [os.path.join(carpeta, f) for f in os.listdir(carpeta) if f.lower().endswith(EXT_PERMITIDAS)]
    if not rutas:
        messagebox.showerror("Error", "No se encontraron imágenes TIFF en la carpeta seleccionada.")
        return

    # Crear carpeta principal para guardar resultados
    carpeta_guardado = os.path.join(carpeta, "procesadas")
    os.makedirs(carpeta_guardado, exist_ok=True)
    # Crear subcarpetas para cada tipo de imagen
    carpeta_indice = os.path.join(carpeta_guardado, "Indice")
    carpeta_oxigenada = os.path.join(carpeta_guardado, "Oxigenada")
    carpeta_nonoxigenada = os.path.join(carpeta_guardado, "NoOxigenada")
    carpeta_visualizacion = os.path.join(carpeta_guardado, "Visualizacion")
    carpeta_fondo = os.path.join(carpeta_guardado, "Fondo")
    for folder in [carpeta_indice, carpeta_oxigenada, carpeta_nonoxigenada, carpeta_visualizacion, carpeta_fondo]:
        os.makedirs(folder, exist_ok=True)

    # Definir umbral para segmentar sangre oxigenada y no oxigenada
    threshold = 0.8

    for ruta in rutas:
        print(f"Procesando {ruta} ...")
        oxygenation_index, canal_imagen_iso = process_image(ruta, ref_vals_iso, ref_vals_hem, canal_isos, canal_hem, epsilon)
        if oxygenation_index is None:
            continue

        base_name = os.path.splitext(os.path.basename(ruta))[0]

        # Guardar el índice (escala de grises) en la carpeta "Indice" para mediciones ROI
        salida_index_tiff = os.path.join(carpeta_indice, f"{base_name}_ox_index.tif")
        tiff.imwrite(salida_index_tiff, oxygenation_index.astype(np.float32))
        print("Guardado índice en escala de grises en:", salida_index_tiff)

        # Guardar la imagen de fondo (canal isosbástico) en la carpeta "Fondo"
        salida_fondo_tiff = os.path.join(carpeta_fondo, f"{base_name}_fondo.tif")
        tiff.imwrite(salida_fondo_tiff, canal_imagen_iso.astype(np.float32))
        print("Guardado fondo en:", salida_fondo_tiff)

        # Crear imágenes segmentadas según el umbral
        ox_only = oxygenation_index.copy()
        ox_only[ox_only <= threshold] = 0

        nonox_only = oxygenation_index.copy()
        nonox_only[nonox_only > threshold] = 0

        salida_ox_tiff = os.path.join(carpeta_oxigenada, f"{base_name}_ox.tif")
        salida_nonox_tiff = os.path.join(carpeta_nonoxigenada, f"{base_name}_nonox.tif")
        tiff.imwrite(salida_ox_tiff, ox_only.astype(np.float32))
        tiff.imwrite(salida_nonox_tiff, nonox_only.astype(np.float32))
        print("Guardadas imágenes segmentadas en Oxigenada y NoOxigenada.")

        # Generar visualización: superponer el índice (falso color) sobre el fondo isosbástico atenuado
        fig, axs = plt.subplots(1, 3, figsize=(18, 6))
        axs[0].imshow(canal_imagen_iso, cmap='gray')
        im0 = axs[0].imshow(oxygenation_index, cmap='jet', alpha=0.5)
        axs[0].set_title("Índice de Hemoglobina Oxigenada\n(con fondo isosbástico)")
        fig.colorbar(im0, ax=axs[0])
        
        axs[1].imshow(canal_imagen_iso, cmap='gray')
        im1 = axs[1].imshow(ox_only, cmap='jet', alpha=0.5)
        axs[1].set_title("Sangre Oxigenada (> {:.1f})".format(threshold))
        fig.colorbar(im1, ax=axs[1])
        
        axs[2].imshow(canal_imagen_iso, cmap='gray')
        im2 = axs[2].imshow(nonox_only, cmap='jet', alpha=0.5)
        axs[2].set_title("Sangre No Oxigenada (<= {:.1f})".format(threshold))
        fig.colorbar(im2, ax=axs[2])
        
        plt.tight_layout()
        salida_png = os.path.join(carpeta_visualizacion, f"{base_name}_visualizacion.png")
        fig.savefig(salida_png, dpi=300, bbox_inches='tight')
        plt.close(fig)
        print("Guardada visualización en:", salida_png)

    messagebox.showinfo("Finalizado", "Se completó el procesamiento de las imágenes.")

if __name__ == '__main__':
    main()
