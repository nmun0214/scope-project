# Ciena EDFA Serial Command Encoder
# Assumes UART serial: 115200 baud, 8 data bits, no parity, 1 stop bit
# Supports encoding of GET and SET commands based on provided frame format

import struct
import serial
import crcmod

# CRC-16/CCITT-FALSE (poly 0x1021, init 0xFFFF)
crc16 = crcmod.mkCrcFun(0x11021, initCrc=0xFFFF, rev=False)

class EDFACommand:
    def __init__(self, port='COM8'):
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
        self.ser.write(frame)
        response = self.ser.read(64)  # or expected response length
        return response

    def get_pump_laser_status(self, amp_index: int, laser_index: int):
        return self.send_command(0x3A, [amp_index, laser_index])

    def get_mode_status(self, amp_index: int):
        return self.send_command(0x31, [amp_index])

    def get_input_power(self, amp_index: int):
        return self.send_command(0x35, [amp_index])

    def get_output_power(self, amp_index: int):
        return self.send_command(0x36, [amp_index])

    def get_output_signal_power(self, amp_index: int):
        return self.send_command(0x37, [amp_index])

    def get_signal_gain(self, amp_index: int):
        return self.send_command(0x38, [amp_index])

    def get_amp_temperature(self, amp_index: int):
        return self.send_command(0x34, [amp_index])

    # i advise not using the ones below until confident with the above ones

    def set_mode(self, amp_index: int, mode: int):
        return self.send_command(0x11, [amp_index, mode])

    def set_pump_current(self, amp_index: int, laser_index: int, current: int):
        return self.send_command(0x1B, [amp_index, laser_index, current])

    def set_gain_tilt(self, amp_index: int, tilt: int):
        return self.send_command(0x52, [amp_index, tilt])

    def set_voa_mode(self, amp_index: int, mode: int):
        return self.send_command(0x53, [amp_index, mode])

    def set_gain_stage_mode(self, amp_index: int, mode: int):
        return self.send_command(0x58, [amp_index, mode])

    def close(self):
        self.ser.close()

# Example usage:
if __name__ == '__main__':
    edfa = EDFACommand(port='COM8')
    try:
        if edfa.ser.is_open:
            print("Serial connection established on COM8.")

        # status = edfa.get_pump_laser_status(1, 1)
        # print("Pump Status:", status.hex())

        # mode_status = edfa.get_mode_status(1)
        # print("Mode Status:", mode_status.hex())
    finally:
        edfa.close()
