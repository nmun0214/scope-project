import pyvisa
import time
import numpy as np
from datetime import datetime

rm = pyvisa.ResourceManager()
scope = rm.open_resource("TCPIP0::169.254.5.104::INSTR")
scope.timeout = 20000
print("Connected to:", scope.query("*IDN?"))

scope.write("*CLS")
scope.write("*RST")
time.sleep(2)

# Setup CH1
scope.write("CH1:SCALE 1.0")
scope.write("CH1:POSITION 0")
scope.write("CH1:COUPLING DC")

scope.write("HOR:MODE MANUAL")
scope.write("HOR:RECORDLENGTH 1000")
scope.write("HOR:MAIN:SCALE 0.001")

scope.write("ACQUIRE:MODE HIRES")
scope.write("ACQUIRE:STATE ON")

scope.write("DATA:SOURCE CH1")
scope.write("DATA:ENC ASCII")
scope.write("DATA:WIDTH 1")
scope.write("DATA:START 1")
scope.write("DATA:STOP 1000")

print("🟢 Scanning for rising edge to 2.0 V...")

recording = []
triggered = False
falling_edge_detected = False
prev_v = 0

print("🟢 Scanning for rising edge to 2.0 V...")

while not falling_edge_detected:
    data = scope.query_ascii_values("CURVE?")
    ymult = float(scope.query("WFMPRE:YMULT?"))
    yoff = float(scope.query("WFMPRE:YOFF?"))
    yzero = float(scope.query("WFMPRE:YZERO?"))
    voltages = [(y - yoff) * ymult + yzero for y in data]

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

# Save result
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
filename = f"CH1_edge_capture_{timestamp}.csv"
np.savetxt(filename, recording, delimiter=',')
print(f"✅ Saved to {filename}")

scope.close()
