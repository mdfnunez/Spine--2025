import machine
import onewire
import ds18x20
import time

# Configuración del pin GPIO para el DS18B20
ds_pin = machine.Pin(14)  # Cambia este pin según tu configuración
ds_sensor = ds18x20.DS18X20(onewire.OneWire(ds_pin))

# Buscar dispositivos DS18B20 en el bus OneWire
roms = ds_sensor.scan()
print("Dispositivos encontrados:", roms)

# Leer la temperatura de los sensores conectados
while True:
    ds_sensor.convert_temp()  # Iniciar la conversión de temperatura
    time.sleep(1)  # Tiempo para que el sensor complete la medición
    
    for rom in roms:
        temp = ds_sensor.read_temp(rom)  # Leer la temperatura de cada sensor
        print(f"Temperatura ({rom}): {temp:.2f} °C")
    time.sleep(2)