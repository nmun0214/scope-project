import pyvisa
import time
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime

# Connect to scope
rm = pyvisa.ResourceManager()
scope = rm.open_resource("TCPIP0::169.254.5.104::INSTR")
scope.timeout = 20000
print("Connected to:", scope.query("*IDN?"))

# Reset and setup scope
scope.write("*CLS")
scope.write("*RST")
time.sleep(2)

scope.write("CH1:SCALE 1.0")
scope.write("CH1:POSITION 0")
scope.write("CH1:COUPLING DC")  # "CH1:COUPLING AC" is also an option


#horizontal config 
scope.write("HOR:MODE MANUAL")  # 
scope.write("HOR:RECORDLENGTH 1000")
scope.write("HOR:MAIN:SCALE 0.001")
scope.write("ACQUIRE:MODE HIRES")   # try scope.write("ACQUIRE:MODE SAMPLE") at some point, unfiltered
scope.write("ACQUIRE:STATE ON")

# Prepare waveform output
scope.write("DATA:SOURCE CH1")
scope.write("DATA:ENC ASCII")
scope.write("DATA:WIDTH 1")
scope.write("DATA:START 1")
scope.write("DATA:STOP 1000")

# retrieve sample rate
fs = float(scope.query("HOR:SAMPLERATE?"))
print(f"Sampling rate: {fs:.0f} Hz")

recording = []
triggered = False
falling_edge_detected = False
prev_v = 0

print("Waiting for rising edge to 2V")

while not falling_edge_detected:
    data = scope.query_ascii_values("CURVE?")
    ymult = float(scope.query("WFMPRE:YMULT?"))
    yoff = float(scope.query("WFMPRE:YOFF?"))
    yzero = float(scope.query("WFMPRE:YZERO?"))
    voltages = [(y - yoff) * ymult + yzero for y in data]       #Tektronix formula to convert from raw data to voltage reading

    for v in voltages:
        if not triggered and prev_v < 2.0 and v >= 2.0:
            print("Rising edge detected. Starting recording.")
            triggered = True
        if triggered:
            recording.append(v)
        if triggered and prev_v > 0.2 and v <= 0.2:
            print("Falling edge to ≤0.2 V detected. Stopping.")
            falling_edge_detected = True
            break
        prev_v = v

    time.sleep(0.05)    # is this too long..?

scope.write("ACQUIRE:STATE OFF")
scope.close()

# Convert to time axis
time_axis = np.arange(len(recording)) / fs

# Plot
plt.figure(figsize=(10, 4))
plt.plot(time_axis, recording)
plt.xlabel("Time (s)")
plt.ylabel("Voltage (V)")
plt.title("CH1 Edge Capture (Rising to Falling)")
plt.grid(True)
plt.tight_layout()
plt.show()
