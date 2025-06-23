import socket
import pyvisa
import time
import numpy as np
from datetime import datetime
from power import GWInstekPSW
from scope import TekMSO64

psu = GWInstekPSW()
scope = TekMSO64()

# Connect to and identify scope and PSU
scope.connect()
PSU_idn = psu.connect()


