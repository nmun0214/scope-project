import pyvisa
import time
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime


def read_waveform_binary(scope):
    """
    Reads waveform data from a Tektronix MSO scope in RIBINARY format,
    parses the SCPI header, converts raw values to voltage.
    Returns: np.array of voltages
    """
    # Set proper binary mode
    scope.write("DATA:ENC RIBINARY")
    scope.write("DATA:WIDTH 2")  # 16-bit samples

    # Get vertical scaling parameters
    ymult = float(scope.query("WFMPRE:YMULT?"))
    yoff  = float(scope.query("WFMPRE:YOFF?"))
    yzero = float(scope.query("WFMPRE:YZERO?"))

    # Request waveform data
    scope.write("CURVE?")
    raw = scope.read_raw()

    # Parse SCPI binary block header
    if raw[0:1] != b'#':
        raise ValueError("Invalid binary block header")

    num_digits = int(raw[1:2])
    data_len = int(raw[2:2+num_digits])
    start_idx = 2 + num_digits
    data_block = raw[start_idx:start_idx + data_len]

    # Decode binary as big-endian 16-bit signed integers
    raw_vals = np.frombuffer(data_block, dtype='>h')

    # Convert to voltage using Tek formula
    voltages = (raw_vals - yoff) * ymult + yzero

    return voltages

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
scope.write("CH1:COUPLING DC")

scope.write("HOR:MODE MANUAL")
scope.write("HOR:RECORDLENGTH 100000")
scope.write("HOR:MAIN:SCALE 0.02")  # Adjust to match your RC curve
scope.write("ACQUIRE:MODE HIRES")
scope.write("ACQUIRE:STATE ON")

# Prepare binary waveform output
scope.write("DATA:SOURCE CH1")
scope.write("DATA:ENC RIBINARY")  # Big-endian 16-bit binary
scope.write("DATA:WIDTH 2")
scope.write("DATA:START 1")
scope.write("DATA:STOP 100000")

# Retrieve sample rate
fs = float(scope.query("HOR:SAMPLERATE?"))
print(f"Sampling rate: {fs:.0f} Hz")

# Wait for rising and falling edge
recording = []
triggered = True
falling_edge_detected = False
prev_v = 0

print("🟢 Scanning for rising edge to 2.0 V...")

while not falling_edge_detected:
    scope.write("CURVE?")

    voltages = read_waveform_binary(scope)

    for v in voltages:
        if not triggered and prev_v < 2.0 and v >= 2.0:
            print("✅ Rising edge detected. Starting recording...")
            triggered = True
        if triggered:
            recording.append(v)
        if triggered and prev_v > 0.2 and v <= 0.2:
            print("🔻 Falling edge to ≤0.2 V detected. Stopping.")
            falling_edge_detected = True
            break
        prev_v = v

    time.sleep(0.05)

scope.write("ACQUIRE:STATE OFF")
scope.close()

# Convert to time axis
time_axis = np.arange(len(recording)) / fs

# Plot
plt.figure(figsize=(10, 4))
plt.plot(time_axis, recording)
plt.xlabel("Time (s)")
plt.ylabel("Voltage (V)")
plt.title("CH1 Edge Capture (Rising to Falling, Binary Mode)")
plt.grid(True)
plt.tight_layout()
plt.show()

