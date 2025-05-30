import blosc2
try:
    s = blosc2.open("/home/alonso/Desktop/Collateral_data/SICNSCI/3----Spine 1 08.03.25/SC/mono/mono.b2nd")
    print("Abierto correctamente:", s.shape)
except Exception as e:
    print("Error:", e)
#                     media_gris = cv2.mean(roi_frame)[0]