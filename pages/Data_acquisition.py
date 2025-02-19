import streamlit as st
import pandas as pd
import datetime
import os
import threading
import time
import cv2

# Define la ruta de la carpeta
folder = "Data"
if not os.path.exists(folder):
    os.makedirs(folder)

# Variables globales para manejar el hilo y el evento de parada
if 'stop_event' not in st.session_state:
    st.session_state.stop_event = None
if 'recording_thread' not in st.session_state:
    st.session_state.recording_thread = None

# Inicializar otras variables en st.session_state
if 'is_recording' not in st.session_state:
    st.session_state.is_recording = False
if 'table_name' not in st.session_state:
    st.session_state.table_name = ''
if 'images' not in st.session_state:
    st.session_state.images = []

# Función para crear el archivo Excel
def create_excel_file(table_name):
    excel_file_path = os.path.join(folder, table_name + ".xlsx")
    df = pd.DataFrame(columns=['Time', 'Sys', 'MAP', 'Dias', 'Cardiac rate', 'RR', 'Temp', 'Sat', 'Observations'])
    with pd.ExcelWriter(excel_file_path, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='VitalSigns', index=False)
        # Crear una segunda hoja vacía para el reporte
        df_report = pd.DataFrame(columns=['Report'])
        df_report.to_excel(writer, sheet_name='Report', index=False)
    st.success('Database created')

# Función para agregar datos al archivo Excel
def append_data(table_name):
    excel_file_path = os.path.join(folder, table_name + ".xlsx")

    if os.path.exists(excel_file_path):
        df_existing = pd.read_excel(excel_file_path, sheet_name='VitalSigns')
        current_timestamp = datetime.datetime.now()
        timestamp_str = current_timestamp.strftime('%Y-%m-%d %H:%M:%S')

        systolic = st.session_state.get('systolic', '')
        diastolic = st.session_state.get('diastolic', '')
        MAP = st.session_state.get('MAP', '')
        temperature = st.session_state.get('temperature', '')
        hr = st.session_state.get('hr', '')
        rr = st.session_state.get('rr', '')
        sat = st.session_state.get('sat', '')
        observations = st.session_state.get('observations', '')

        new_data = {'Time': timestamp_str, 'Sys': systolic, 'MAP': MAP, 'Dias': diastolic,
                    'Cardiac rate': hr, 'RR': rr, 'Temp': temperature, 'Sat': sat, 'Observations': observations}
        df_new = pd.DataFrame([new_data])

        df_combined = pd.concat([df_existing, df_new], ignore_index=True)

        with pd.ExcelWriter(excel_file_path, engine='openpyxl', mode='a', if_sheet_exists='replace') as writer:
            df_combined.to_excel(writer, sheet_name='VitalSigns', index=False)
        st.info('Data recorded successfully.')
    else:
        st.error(f'The table {table_name} does not exist.')

# Función que se ejecuta en segundo plano para registrar datos cada segundo
def background_task(table_name, stop_event):
    while not stop_event.is_set():
        append_data(table_name)
        time.sleep(1)

# Pestañas
t1, t2, t3 = st.tabs(['Record data', 'Report', 'Images'])

with t1:
    # Crear el archivo Excel si se hace clic en el botón "Create database"
    with st.form('Tables'):
        table_name = st.text_input('Name of the experiment')
        table_create_button = st.form_submit_button('Create database')

        if table_create_button:
            create_excel_file(table_name)
            st.session_state.table_name = table_name

    # Iniciar o detener grabación
    if st.session_state.is_recording:
        stop_button = st.button('Stop recording')
        if stop_button:
            st.session_state.stop_event.set()
            st.session_state.recording_thread.join()
            st.session_state.is_recording = False
            st.success('Recording stopped.')
    else:
        start_button = st.button('Start recording')
        if start_button:
            if st.session_state.table_name == '':
                st.error('Please create or select a database first.')
            else:
                stop_event = threading.Event()
                st.session_state.stop_event = stop_event
                recording_thread = threading.Thread(target=background_task, args=(st.session_state.table_name, stop_event))
                recording_thread.start()
                st.session_state.recording_thread = recording_thread
                st.session_state.is_recording = True
                st.success('Recording started.')

    # Formulario para ingresar signos vitales
    with st.form('Vital signs', clear_on_submit=True):
        sol1, sol2 = st.columns(2)
        with sol1:
            systolic = st.number_input('Systolic', step=1, key='systolic_input')
            diastolic = st.number_input('Diastolic', step=1, key='diastolic_input')
            MAP = st.number_input('MAP', step=1, key='MAP_input')
            observations = st.text_area('Observations', key='observations_input')
        with sol2:
            temperature = st.number_input('Temperature', step=0.1, key='temperature_input')
            hr = st.number_input('Heart rate', step=1, min_value=0, key='hr_input')
            rr = st.number_input('Respiratory rate', step=1, key='rr_input')
            sat = st.number_input('Saturation', step=1, key='sat_input')
        record_vitals = st.form_submit_button('Record vital signs')

    if record_vitals:
        if st.session_state.table_name == '':
            st.error('Please create or select a database first.')
        else:
            st.session_state.systolic = systolic
            st.session_state.diastolic = diastolic
            st.session_state.MAP = MAP
            st.session_state.temperature = temperature
            st.session_state.hr = hr
            st.session_state.rr = rr
            st.session_state.sat = sat
            st.session_state.observations = observations
            append_data(st.session_state.table_name)

            # Captura de imagen de la cámara
            cap = cv2.VideoCapture('192.168.4.1')
            ret, frame = cap.read()
            if ret:
                image_filename = os.path.join(folder, f'image_{timestamp_str}.jpg')
                cv2.imwrite(image_filename, frame)
                st.session_state.images.append(image_filename)
            cap.release()

with t2:
    with st.form('Experiment report'):
        report = st.text_area('Experiment report', height=600)
        save_report = st.form_submit_button('Save experiment report')

    if save_report:
        if st.session_state.table_name == '':
            st.error('Please create or select a database first.')
        else:
            excel_file_path = os.path.join(folder, st.session_state.table_name + ".xlsx")
            if os.path.exists(excel_file_path):
                df_report = pd.DataFrame({'Report': [report]})
                with pd.ExcelWriter(excel_file_path, engine='openpyxl', mode='a', if_sheet_exists='replace') as writer:
                    df_report.to_excel(writer, sheet_name='Report', index=False)
                st.success('Report saved successfully.')
            else:
                st.error(f'The table {st.session_state.table_name} does not exist. Please create the database first.')

with t3:
    st.header('Images')
    if os.path.exists(folder):
        images = os.listdir(folder)
        for img in images:
            if img.endswith(".jpg"):
                st.image(os.path.join(folder, img), caption=img, use_column_width=True)