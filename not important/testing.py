import pyvisa
import time


# Initialize VISA connection
rm = pyvisa.ResourceManager()
scope = rm.open_resource("TCPIP0::169.254.5.104::INSTR")  # Update if needed
scope.timeout = 10000  # 10-second timeout

# Identify instrument
print("Connecting...")
idn = scope.query("*IDN?")
print("Connected to:", idn)

# Configure data format
scope.write("HEADER OFF")
scope.write("DATA:SOURCE CH1")
scope.write("DATA:ENC ASCII")
scope.write("DATA:WIDTH 1")
scope.write("DATA:START 1")
scope.write("DATA:STOP 1000")

# Trigger config — AUTO mode
scope.write("TRIG:MODE AUTO")              # Automatically trigger, even with no signal
scope.write("TRIG:EDGE:SOURCE CH1")        # Use CH1
scope.write("TRIG:EDGE:SLOPE RISE")
scope.write("TRIG:EDGE:LEVEL 0.1")

# Set to acquire once, then stop
scope.write("ACQUIRE:STOPAFTER SEQUENCE")
scope.write("ACQUIRE:STATE ON")

print("Waiting for acquisition (AUTO mode)...")
time.sleep(3)  # Let the scope auto-trigger and capture

# Check trigger state
state = scope.query("TRIG:STATE?").strip()
print("Trigger state:", state)

# Retrieve waveform data
try:
    print("Fetching waveform...")
    data = scope.query_ascii_values("CURVE?")
    print("Waveform captured.")
    print("First 10 points:", data[:10])
except pyvisa.errors.VisaIOError as e:
    print("Timeout or VISA error:", e)

print(scope.query("SYSTEM:ERR?"))


scope.close()
