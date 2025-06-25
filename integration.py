from power import GWInstekPSW
from scope import TekMSO64
import matplotlib.pyplot as plt


## WARNING ##
# UNTESTED GPT CODE

# --- Initialize instruments ---
psu = GWInstekPSW(ip="169.254.5.130", port=2268)
scope = TekMSO64(ip="169.254.5.104")

try:
    # --- Connect to PSU and Scope ---
    psu.connect()
    scope.connect()

    # --- Power supply configuration ---
    psu.set_voltage(5.0)
    psu.set_current(0.5)
    psu.output_on()

    # --- Scope configuration ---
    scope.reset()
    scope.configure_channel(channel="CH1", scale=1.0, position=0, coupling="DC")
    scope.configure_timebase(scale=0.001, record_length=1000)
    scope.configure_trigger(source="CH1", level=4.5, slope="RISE", mode="NORMAL")
    scope.start_acquisition()

    # --- Wait for signal ---
    scope.wait_for_trigger()
    scope.stop_acquisition()

    # --- Get waveform ---
    waveform = scope.fetch_waveform(channel="CH1", start=1, stop=1000)

    # --- Plot result ---
    plt.plot(waveform)
    plt.title("Captured Waveform from CH1")
    plt.xlabel("Sample #")
    plt.ylabel("Voltage (V)")
    plt.grid(True)
    plt.show()

finally:
    # --- Cleanup ---
    psu.output_off()
    psu.close()
    scope.close()
