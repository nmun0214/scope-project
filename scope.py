import pyvisa
import numpy as np
import time

class TekMSO64:
    
    def __init__(self, ip="169.254.5.104", timeout=10000):
        self.ip = ip
        self.timeout = timeout
        self.scope = None

    def connect(self):
        """
        Connect to scope using pyVISA using the given IP from init, prints the corresponding *IDN? string
        """

        rm = pyvisa.ResourceManager()
        self.scope = rm.open_resource(f"TCPIP0::{self.ip}::INSTR")
        self.scope.timeout = self.timeout
        print("Connected to:", self.scope.query("*IDN?"))

    def send(self, command):
        """Send raw SCPI command over socket, does not expect a response

        Arguments:
            command {str} -- in SCPI format
        """        
        self.scope.write(command)

    def query(self, command):
        """Sends raw SCPI command over socket, expects response and returns as string

        Arguments:
            command {str} -- in SCPI format

        Returns:
            output {str} -- scope query output
        """        
        return self.scope.query(command).strip()

    def reset(self):
        """Resets and clears scope
        """        
        self.send("*CLS")
        self.send("*RST")
        time.sleep(2)

    def configure_channel(self, channel="CH1", scale=1.0, position=0.0, coupling="DC"):
        """Sets up a single channel's display config

        Arguments:
            channel {str} -- Select which channel to configure (default: {"CH1"})
            scale {float} -- Voltage scale in V/div, vertical axis.  (default: {1.0})
            position {float} -- Set the vertical position where the reading is centered about  (default: {0.0})
            coupling {str} -- Set coupling (DC/AC/GND) (default: {"DC"})
        """        
        self.send(f"{channel}:SCALE {scale}")
        self.send(f"{channel}:POSITION {position}")
        self.send(f"{channel}:COUPLING {coupling}")

    def configure_timebase(self, scale=0.001, record_length=1000):
        """Set the horizontal axis and acqusition length

        Keyword Arguments:
            scale {float} -- _description_ (default: {0.001})
            record_length {int} -- _description_ (default: {1000})
        """        
        self.send("HOR:MODE MANUAL")
        self.send(f"HOR:MAIN:SCALE {scale}")
        self.send(f"HOR:RECORDLENGTH {record_length}")

    def configure_trigger(self, source="CH1", level=0.1, slope="RISE", mode="NORMAL"):

        """ Set the configuration of trigger
        
        Arguments:
            source {str} -- select channel for trigger to read (CH1-CH4), default CH1
            level {float} -- the trigger voltage in volts, default 0.1 V
            slope {str} -- select rising ("RISE") or falling ("FALL") edge, default rising edge
            mode {str} -- select mode, 
                ("AUTO") will trigger when condition is met, but if it doesn't see condition within timeout it'll trigger anyway. 
                ("NORMAL") always waits until the trigger is satisfied
                default "NORMAL"

        """        
        self.send(f"TRIG:MODE {mode}")
        self.send(f"TRIG:EDGE:SOURCE {source}")
        self.send(f"TRIG:EDGE:SLOPE {slope}")
        self.send(f"TRIG:EDGE:LEVEL {level}")

    def start_acquisition(self, mode="HIRES"):
        """Begins acquisition with an optional acquisition mode

        Keyword Arguments:
            mode {str} -- can choose between "HIRES" "SAMPLE" and "PEAKDETECT" (default: {"HIRES"})
                "HIRES" -- uses oversampling and averaging to reduce noise, improve vertical res
                "SAMPLE" -- stores raw samples from ADC
                "PEAKDETECT" --  
        """        
        self.send(f"ACQUIRE:MODE {mode}")
        self.send("ACQUIRE:STATE ON")

    def stop_acquisition(self):
        self.send("ACQUIRE:STATE OFF")

    def wait_for_trigger(self, check_interval=0.1):
        print("Waiting for trigger...")
        while self.query("BUSY?") == '1':
            time.sleep(check_interval)
        print("Trigger detected.")

    def fetch_waveform(self, channel="CH1", start=1, stop=1000):
        self.send(f"DATA:SOURCE {channel}")
        self.send("DATA:ENC ASCII")
        self.send("DATA:WIDTH 1")
        self.send(f"DATA:START {start}")
        self.send(f"DATA:STOP {stop}")

        data = self.scope.query("CURVE?")
        raw = np.array([float(x) for x in data.split(',')])

        ymult = float(self.query("WFMPRE:YMULT?"))
        yoff = float(self.query("WFMPRE:YOFF?"))
        yzero = float(self.query("WFMPRE:YZERO?"))

        voltages = (raw - yoff) * ymult + yzero
        return voltages

    def close(self):
        if self.scope:
            self.scope.close()
            print("Scope connection closed.")
