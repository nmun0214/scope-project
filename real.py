import pyvisa
import time

# Initialize VISA connection
rm = pyvisa.ResourceManager()
print(rm.list_resources())

scope = rm.open_resource("TCPIP0::169.254.5.104::INSTR")  # Update if needed
scope.timeout = 10000  # 10-second timeout