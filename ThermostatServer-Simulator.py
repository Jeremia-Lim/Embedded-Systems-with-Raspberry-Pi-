#
# ThermostatServer-Simulator.py
#
# This Python script simulates a Thermostat Server.
# It reads data sent by the Thermostat over the serial
# port (UART) and prints it to the console.
#
# The script will continue to run until the user
# presses CTRL-C.
#

import time
import serial

# --------------------------------------------------
# Configure the serial connection
# --------------------------------------------------
# This assumes you are using the USB -> TTL cable
# provided with the Raspberry Pi kit.
#
# On Raspberry Pi 4B, this is usually /dev/ttyUSB0
#
ser = serial.Serial(
    port='/dev/ttyUSB0',      # USB -> TTL cable
    baudrate=115200,          # Must match Thermostat.py
    parity=serial.PARITY_NONE,
    stopbits=serial.STOPBITS_ONE,
    bytesize=serial.EIGHTBITS,
    timeout=1
)

print("Thermostat Server Simulator started.")
print("Waiting for data from Thermostat...\n")

# --------------------------------------------------
# Main loop
# --------------------------------------------------
repeat = True

while repeat:
    try:
        # Read a line from the serial port
        dataline = ser.readline().decode("utf-8").strip().lower()

        # Only print non-empty lines
        if len(dataline) > 0:
            print(dataline)

        time.sleep(0.1)

    except KeyboardInterrupt:
        print("\nShutting down Thermostat Server Simulator...")
        repeat = False

# --------------------------------------------------
# Cleanup
# --------------------------------------------------
ser.close()
print("Serial connection closed.")



