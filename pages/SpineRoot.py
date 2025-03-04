import numpy as np
import cv2
from PIL import Image
import time
import os
import tkinter as tk
from tkinter import filedialog
from ximea import xiapi
import streamlit as st

import subprocess

st.image('/home/alonso/Documents/GitHub/Spine--2025/Images/spinalroot.jpeg')

st.info('Remember to select a external drive for saving the images')

st.markdown('Best to do a short recording to verify that the images are being recorded')
if st.button("Start recording"):
    subprocess.Popen(["python", "xcamera2.py"])
    st.write("Se ha lanzado la grabación en otra ventana.")
    st.success('Good luck with the recording!')
    st.balloons()

