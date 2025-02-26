import json
from tkinter import Tk, Toplevel, filedialog, Canvas, Button, simpledialog
from PIL import Image, ImageTk

def seleccionar_varias_rois():
    # Ocultar la ventana principal de Tkinter
    root = Tk()
    root.withdraw()
    
    # Seleccionar la imagen TIFF
    imagen_path = filedialog.askopenfilename(title="Selecciona una imagen TIFF", filetypes=[("TIFF files", "*.tiff *.tif")])
    if not imagen_path:
        print("No se seleccionó ninguna imagen.")
        root.quit()  # Asegurarse de cerrar Tkinter si no se selecciona una imagen
        return

    # Cargar la imagen
    imagen = Image.open(imagen_path)
    rois = []  # Lista para almacenar las ROIs

    # Crear ventana para seleccionar ROIs
    ventana = Toplevel(root)
    ventana.title("Selecciona ROIs")
    
    # Crear Canvas y añadir la imagen
    canvas = Canvas(ventana, width=imagen.width, height=imagen.height)
    canvas.pack()
    imagen_tk = ImageTk.PhotoImage(imagen)
    canvas.create_image(0, 0, anchor="nw", image=imagen_tk)

    # Variables de selección
    x0, y0, rect = None, None, None

    # Funciones para seleccionar y guardar ROIs
    def on_click(event):
        nonlocal x0, y0, rect
        x0, y0 = event.x, event.y
        rect = canvas.create_rectangle(x0, y0, x0, y0, outline="red")

    def on_drag(event):
        nonlocal rect
        canvas.coords(rect, x0, y0, event.x, event.y)

    def on_release(event):
        nonlocal x0, y0, rect
        x1, y1 = event.x, event.y
        # Solicitar nombre de ROI
        nombre = simpledialog.askstring("Nombre de ROI", "Ingresa el nombre para esta ROI:", parent=ventana)
        if nombre:
            roi_coords = {"nombre": nombre, "x": min(x0, x1), "y": min(y0, y1), "w": abs(x1 - x0), "h": abs(y1 - y0)}
            rois.append(roi_coords)
            print(f"ROI '{nombre}' guardada: {roi_coords}")
        canvas.delete(rect)
        x0, y0, rect = None, None, None

    # Función para guardar y cerrar ambas ventanas
    def finalizar_seleccion():
        if rois:
            with open("roi.json", "w") as f:
                json.dump(rois, f, indent=4)
            print("Todas las ROIs guardadas en 'roi.json':", rois)
        else:
            print("No se capturaron ROIs para guardar.")
        ventana.destroy()
        root.quit()  # Cerrar completamente Tkinter

    # Vincular eventos de mouse
    canvas.bind("<ButtonPress-1>", on_click)
    canvas.bind("<B1-Motion>", on_drag)
    canvas.bind("<ButtonRelease-1>", on_release)

    # Botón para finalizar y guardar justo debajo del Canvas
    finalizar_btn = Button(ventana, text="Finalizar y Guardar", command=finalizar_seleccion)
    finalizar_btn.pack(pady=10)

    # Vincular tecla Escape y Enter para finalizar y guardar
    ventana.bind("<Escape>", lambda event: finalizar_seleccion())
    ventana.bind("<Return>", lambda event: finalizar_seleccion())

    ventana.mainloop()
    root.quit()  # Cerrar la raíz al finalizar

if __name__ == "__main__":
    seleccionar_varias_rois()
