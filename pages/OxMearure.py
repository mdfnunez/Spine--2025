import os
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
import tifffile as tiff
import numpy as np
import matplotlib.pyplot as plt

def select_file(title, filetypes=[("Images", ("*.tif", "*.tiff", "*.png", "*.jpg", "*.jpeg")), ("All Files", "*.*")]):
    root = tk.Tk()
    root.withdraw()
    path = filedialog.askopenfilename(title=title, filetypes=filetypes)
    root.destroy()
    return path

def select_channel(title, default_channel):
    root = tk.Tk()
    root.withdraw()
    channel = simpledialog.askinteger(title, f"Enter the channel number (0-15):", initialvalue=default_channel)
    root.destroy()
    return channel

def adjust_image_format(image):
    """
    If the image is in channels-first format (16 x H x W),
    it transposes it to have channels in the last dimension (H x W x 16).
    """
    if image.ndim == 3:
        if image.shape[0] == 16 and image.shape[2] != 16:
            image = np.transpose(image, (1, 2, 0))
    return image

def main():
    epsilon = 1e-6  # To avoid division by zero
    
    # ---------------------------
    # Calibration and adjustment parameters:
    # ---------------------------
    # For the isosbestic channel (tissue sensitivity)
    iso_white_percentile = 95  # Adjust white reference percentile (e.g., 97 or 95)
    iso_black_percentile = 5  # Adjust black reference percentile (e.g., 3 or 5)
    
    # For the hemoglobin channel
    hem_white_percentile = 95  # You can also test with a lower value if needed
    hem_black_percentile = 5
    
    # Threshold to create the hemoglobin mask.
    # Lowering this value can help reveal lower signals (e.g., 0.3)
    threshold = 0.2
    
    # Gamma correction: values < 1 brighten the dark regions.
    gamma_correction = 0.7
    
    # Amplification factor for the oxygenation index.
    # Increase (e.g., to 2.0) to enhance small differences, especially in tissue areas.
    amplification_factor = 5.0
    # ---------------------------
    
    # Select reference images (white and black) and the sample image
    white_path = select_file("Select the WHITE reference image")
    if not white_path:
        messagebox.showerror("Error", "White reference image not selected.")
        return

    black_path = select_file("Select the BLACK reference image")
    if not black_path:
        messagebox.showerror("Error", "Black reference image not selected.")
        return

    sample_path = select_file("Select the multi-tiff sample image")
    if not sample_path:
        messagebox.showerror("Error", "No sample image selected.")
        return

    # Select channels (you can change the default values if desired)
    isos_channel = select_channel("Isosbestic Channel", 6)
    if isos_channel is None or not (0 <= isos_channel < 16):
        messagebox.showerror("Error", "Invalid isosbestic channel.")
        return

    hem_channel = select_channel("Hemoglobin Channel", 5)
    if hem_channel is None or not (0 <= hem_channel < 16):
        messagebox.showerror("Error", "Invalid hemoglobin channel.")
        return

    # Load images (assumed to be multi-tiff with 16 channels)
    try:
        white_img = tiff.imread(white_path)
        black_img = tiff.imread(black_path)
        sample_img = tiff.imread(sample_path)
    except Exception as e:
        messagebox.showerror("Error", f"Error loading images:\n{e}")
        return

    # Adjust format to channels-last if necessary
    white_img = adjust_image_format(white_img)
    black_img = adjust_image_format(black_img)
    sample_img = adjust_image_format(sample_img)

    # Verify that the images have 16 channels
    for img, name in zip([white_img, black_img, sample_img],
                         ["white", "black", "sample"]):
        if img.ndim != 3 or img.shape[2] < 16:
            messagebox.showerror("Error", f"The {name} image must have 16 channels.")
            return

    # --- Calculations for the isosbestic channel ---
    white_val_iso = np.percentile(white_img[:, :, isos_channel], iso_white_percentile)
    black_val_iso = np.percentile(black_img[:, :, isos_channel], iso_black_percentile)
    sample_channel_iso = sample_img[:, :, isos_channel].astype(np.float64)
    reflectance_iso = (sample_channel_iso - black_val_iso) / (white_val_iso - black_val_iso + epsilon)
    reflectance_iso = np.clip(reflectance_iso, epsilon, 1)
    OD_iso = -np.log(reflectance_iso)

    # --- Calculations for the hemoglobin channel ---
    white_val_hem = np.percentile(white_img[:, :, hem_channel], hem_white_percentile)
    black_val_hem = np.percentile(black_img[:, :, hem_channel], hem_black_percentile)
    sample_channel_hem = sample_img[:, :, hem_channel].astype(np.float64)
    reflectance_hem = (sample_channel_hem - black_val_hem) / (white_val_hem - black_val_hem + epsilon)
    reflectance_hem = np.clip(reflectance_hem, epsilon, 1)
    OD_hem = -np.log(reflectance_hem)

    # --- Calculation of the oxygenation index ---
    oxygenation_index = amplification_factor * (OD_hem - OD_iso)

    # --- Generate mask over the oxygenation index ---
    hem_mask = oxygenation_index > threshold

    # --- Apply gamma correction to enhance brightness in visualization ---
    # Use gamma < 1 to brighten the image
    reflectance_iso_bright = np.power(reflectance_iso, gamma_correction)
    reflectance_hem_bright = np.power(reflectance_hem, gamma_correction)

    # --- Visualization ---
    fig, axs = plt.subplots(2, 2, figsize=(12, 10))
    
    # 1. Isosbestic Channel Reflectance (with enhanced brightness)
    im0 = axs[0, 0].imshow(reflectance_iso_bright, cmap='gray', aspect='equal', vmin=0, vmax=1)
    axs[0, 0].set_title("Isosbestic Channel\n(Enhanced Reflectance)")
    fig.colorbar(im0, ax=axs[0, 0])
    
    # 2. Hemoglobin Channel Reflectance (with enhanced brightness)
    im1 = axs[0, 1].imshow(reflectance_hem_bright, cmap='gray', aspect='equal', vmin=0, vmax=1)
    axs[0, 1].set_title("Hemoglobin Channel\n(Enhanced Reflectance)")
    fig.colorbar(im1, ax=axs[0, 1])
    
    # 3. Oxygenation Index (OD Hem - OD Iso)
    im2 = axs[1, 0].imshow(oxygenation_index, cmap='jet', aspect='equal')
    axs[1, 0].set_title("Oxygenation Index\n(OD Hem - OD Iso)")
    fig.colorbar(im2, ax=axs[1, 0])
    
    # 4. Oxygenated Hemoglobin Mask over the isosbestic channel (brightened)
    axs[1, 1].imshow(reflectance_iso_bright, cmap='gray', aspect='equal', vmin=0, vmax=1)
    axs[1, 1].imshow(hem_mask, cmap='Reds', alpha=0.3, aspect='equal')
    axs[1, 1].set_title("Oxygenated Hemoglobin Mask")
    
    plt.tight_layout()
    plt.show()

if __name__ == '__main__':
    main()
