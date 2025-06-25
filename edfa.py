# Ciena EDFA Serial Command Encoder
# Assumes UART serial: 115200 baud, 8 data bits, no parity, 1 stop bit
# Supports encoding of GET commands based on provided frame format

import struct
import serial
import crcmod

# WORK IN PROGRESS, UNTESTED CODE

# CRC-16/CCITT-FALSE (poly 0x1021, init 0xFFFF)
crc16 = crcmod.mkCrcFun(0x11021, initCrc=0xFFFF, rev=False)

class EDFACommand:
    def __init__(self, port='COM3'):
        self.ser = serial.Serial(
            port=port,
            baudrate=115200,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=1
        )

    def _build_frame(self, cmd_id: int, args: list[int]) -> bytes:
        header = 0xAA
        length = 2 + len(args)  # cmd_id + args
        payload = [cmd_id] + args
        frame_wo_crc = bytes([header, length] + payload)
        crc = crc16(frame_wo_crc)
        crc_bytes = struct.pack('>H', crc)  # big-endian
        return frame_wo_crc + crc_bytes

    def send_command(self, cmd_id: int, args: list[int]) -> bytes:
        frame = self._build_frame(cmd_id, args)
        print(f"Sending: {frame.hex().upper()}")
        
        self.ser.write(frame)
        time.sleep(0.1)  # Brief delay for device processing
        
        # Read response
        response = self.ser.read(expected_response_size)
        print(f"Received ({len(response)} bytes): {response.hex().upper()}")
        
        if len(response) == 0:
            raise TimeoutError("No response received from device")
            
        return response

    # TEST FUNCTIONS, REFER TO CIENA EDFA MANUAL

    def get_pump_laser_status(self, amp_index: int, laser_index: int):
        # Command 0x3A: Get Pump Laser Status
        return self.send_command(0x3A, [amp_index, laser_index])

    def get_mode_status(self, amp_index: int):
        # Command 0x31: Get Mode Status
        return self.send_command(0x31, [amp_index])

    def close(self):
        self.ser.close()

# Example usage:
if __name__ == '__main__':
    edfa = EDFACommand(port='COM3')
    try:
        if edfa.ser.is_open:
            print("Serial connection established on COM3.")

        # status = edfa.get_pump_laser_status(1, 1)
        # print("Pump Status:", status.hex())

        # mode_status = edfa.get_mode_status(1)
        # print("Mode Status:", mode_status.hex())
    finally:
        edfa.close()
