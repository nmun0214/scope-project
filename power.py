import socket

class GWInstekPSW:
    def __init__(self, ip="169.254.5.130", port=2268, timeout=5):
        self.ip = ip
        self.port = port
        self.timeout = timeout
        self.sock = None

    def connect(self):
        
        """
        Opens a TCP socket to the power supply and sends an *IDN? query to confirm connection

        Returns: 
            str: Device's identity string returned by the identification query

        """

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.settimeout(self.timeout)
        self.sock.connect((self.ip, self.port))
        print("Connected to power supply:", self.query("*IDN?"))

    def send(self, command):

        """ 
        Send raw SCPI commands over socket

        Parameters: 
            command (str): the SCPI command 

        Ex: self.send("VOLT 5") 
        sets voltage to 5V 
        """
        self.sock.sendall((command + '\n').encode())

    def query(self, command):
        
        """
        Sends a SCPI command and waits for a response

        Parameters:
            command (str): SCPI command
        
        Ex: self.query("MEAS:VOLT?")
        returns measured voltage
        """

        self.send(command)
        return self.sock.recv(1024).decode().strip()

    def set_voltage(self, volts):
        self.send(f"VOLT {volts}")
        print(f"Voltage set to {volts} V")

    def set_current(self, amps):
        self.send(f"CURR {amps}")
        print(f"Current limit set to {amps} A")

    def output_on(self):
        self.send("OUTP ON")
        print("Output enabled")

    def output_off(self):
        self.send("OUTP OFF")
        print("Output disabled")

    def measure_voltage(self):
        return float(self.query("MEAS:VOLT?"))

    def measure_current(self):
        return float(self.query("MEAS:CURR?"))

    def close(self):
        if self.sock:
            self.sock.close()
            print("PSU Disconnected")


if __name__ == "__main__":
    psu = GWInstekPSW()

    try:
        psu.connect()
        psu.set_voltage(5.0)       # Set output voltage
        psu.set_current(2.0)       # Set current limit
        psu.output_on()            # Enable output

        # Optional: Read measurements
        v = psu.measure_voltage()
        i = psu.measure_current()
        print(f"Measured Voltage: {v:.2f} V")
        print(f"Measured Current: {i:.2f} A")

        # psu.output_off()  # Uncomment to turn off after test

    finally:
        psu.close()
