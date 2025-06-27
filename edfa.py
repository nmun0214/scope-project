# Ciena EDFA Serial Command Encoder
# Assumes UART serial: 115200 baud, 8 data bits, no parity, 1 stop bit
# Supports encoding of GET commands based on provided frame format

import struct
import serial
import crcmod
import time

# CRC-16/CCITT-FALSE (poly 0x1021, init 0xFFFF)
crc16 = crcmod.mkCrcFun(0x11021, initCrc=0xFFFF, rev=False)

class EDFACommand:
    SYNC_BYTE = 0x68
    def __init__(self, port='COM7', device_address=None):
        if device_address is None:
            device_address = [0x00, 0x03]  # Default, but can be changed
        self.DEVICE_ADDRESS = device_address
        self.ser = serial.Serial(
            port=port,
            baudrate=115200,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=1
        )

    def _build_frame(self, cmd_id: int, args: list[int]) -> bytes:
        """Builds a command frame with CRC matching Ciena protocol."""
        # Frame: SYNC + ADDR + SYNC + CMD + ARGS + CRC
        frame_data = [self.SYNC_BYTE] + self.DEVICE_ADDRESS + [self.SYNC_BYTE, cmd_id] + args
        frame_bytes = bytes(frame_data)
        crc = crc16(frame_bytes)
        crc_bytes = struct.pack('>H', crc)  # big-endian
        return frame_bytes + crc_bytes

    def send_command(self, cmd_id: int, args: list[int], expected_response_size: int = 64) -> bytes:
        """Sends a command and reads the response."""
        frame = self._build_frame(cmd_id, args)
        print(f"Sending: {frame.hex().upper()}")
        self.ser.write(frame)
        time.sleep(0.2)  # Slightly longer delay for device processing
        response = self.ser.read(expected_response_size)
        print(f"Received ({len(response)} bytes): {response.hex().upper()}")
        if len(response) == 0:
            raise TimeoutError("No response received from device")
        return response

    def send_raw_command(self, hexstr: str, expected_response_size: int = None) -> bytes:
        """
        Sends a raw hex string command (e.g., '680005683a005601019216') to the device.
        Args:
            hexstr: Hex string of the command (spaces optional, case-insensitive)
            expected_response_size: Number of bytes to read from the device. If None, read all available bytes after a short delay.
        Returns:
            Raw response bytes
        """
        hexstr = hexstr.replace(' ', '')
        frame = bytes.fromhex(hexstr)
        print(f"Sending raw: {frame.hex().upper()}")
        self.ser.write(frame)
        time.sleep(0.2)
        if expected_response_size is not None:
            response = self.ser.read(expected_response_size)
        else:
            time.sleep(0.2)  # Give device time to respond
            response = self.ser.read_all()
        print(f"Received ({len(response)} bytes): {response.hex().upper()}")
        if len(response) == 0:
            print("No response received from device")
        return response

    def send_gui_raw_command(self, cmd_type: str, amp_index: int, stage_index: int, expected_response_size: int = None) -> bytes:
        """
        Sends a raw command for a given command type (e.g., 'get_mode', 'get_module_status', 'get_pump_laser_status')
        using a lookup table of known-good raw hex commands from the GUI.
        Args:
            cmd_type: One of 'get_mode', 'get_module_status', 'get_pump_laser_status'
            amp_index: Amplifier index (int)
            stage_index: Stage index (int)
            expected_response_size: Optional, number of bytes to read
        Returns:
            Raw response bytes
        """
        # Lookup table for known-good raw commands (add more as needed)
        gui_commands = {
            ('get_mode', 1, 1): '6800056831005f01019216',
            ('get_module_status', 1, 1): '6800056830006001019216',
            ('get_module_status', 0, 1): '6800056830006d00019e16',
            ('get_module_status', 2, 1): '6800056830006f0201a216',
            ('get_module_status', 0, 2): '680005683000710002a316',
            ('get_module_status', 1, 2): '680005683000720102a516',
            ('get_module_status', 2, 2): '680005683000730202a716',
            # Add more as needed, e.g. ('get_pump_laser_status', 1, 1): '...'
        }
        # For 'get_module_status' response:
        #   Response size: 8 bits (bitmap) if Argument 1 > 0, 8 bits * TotalAMPs if Argument 1 = 0
        #   Bit 0: Amp is disabled
        #   Bit 1: Amp is in APR (eye-safe mode)
        #   Bit 2: Amp is gain-limited
        #   Bit 3: Amp is power clamping
        #   Bits 4-7: Reserved
        key = (cmd_type, amp_index, stage_index)
        if key not in gui_commands:
            raise ValueError(f"No raw command found for {cmd_type} amp={amp_index} stage={stage_index}")
        hexstr = gui_commands[key]
        return self.send_raw_command(hexstr, expected_response_size)

    def parse_pump_laser_status_response(self, response: bytes):
        """
        Parses the pump laser status response and prints values in human-readable format.
        Expects a response of at least 33 bytes (including header and CRC).
        """
        if len(response) < 33:
            print("Response too short to parse.")
            return
        # Data starts at byte 7 (index 6), ends at byte 31 (index 30), CRC is last 2 bytes
        data = response[7:-2]  # Exclude header and CRC
        if len(data) < 24:
            print("Not enough data for all fields.")
            return
        # Unpack 8 shorts, 1 unsigned int, 2 shorts (24 bytes)
        fields = struct.unpack('>hhhhhhhhIhh', data)
        print("--- Pump Laser Status ---")
        print(f"1. Laser current: {fields[0]/10:.2f} mA")
        print(f"2. End-of-life current: {fields[1]/10:.2f} mA")
        print(f"3. Back facet current: {fields[2]} uA")
        print(f"4. Laser power: {fields[3]/10:.2f} mW")
        print(f"5. Thermo-electric cooler current: {fields[4]/10:.2f} mA")
        print(f"6. Thermo-electric cooler voltage: {fields[5]/10:.2f} mV")
        print(f"7. Laser temperature: {fields[6]/10:.2f} °C")
        print(f"8. Laser current set point: {fields[7]/10:.2f} mA")
        print(f"9. Number of hours operating: {fields[8]}")
        print(f"10. Average laser current over life: {fields[9]/10:.2f} mA")
        print(f"11. Reserved: {fields[10]}")
        print("-------------------------")

    def parse_mode_status_response(self, response: bytes):
        """
        Parses the mode status response for command 0x31 (Get Mode).
        Handles both 2-byte and 4-byte data responses.
        """
        if len(response) < 12:
            print("Response too short to parse.")
            return
        data = response[7:-2]
        if len(data) < 2:
            print("Not enough data for all fields.")
            return
        amp_index = data[0]
        mode = data[1]
        mode_map = {1: 'Disable', 2: 'Manual', 3: 'Constant Gain', 4: 'Constant Power', 5: 'Clamping', 6: 'ASE Enable Const Output Power', 7: 'ASE Enable Const Drive Current', 8: 'ASE Safe', 9: 'AFC Const Gain', 10: 'AFC Const Power'}
        print("--- Amplifier Mode Status ---")
        print(f"Amplifier Index: {amp_index}")
        print(f"Mode: {mode_map.get(mode, f'Unknown ({mode})')}")
        print("-----------------------------")

    def parse_module_status_response(self, response: bytes):
        """
        Parses the module status response for command 0x30 (Get Module Status).
        Expects a response of at least 10 bytes (including header and CRC).
        """
        if len(response) < 10:
            print("Response too short to parse.")
            return
        # Data starts at byte 7 (index 6), ends at byte 7 (index 7), CRC is last 2 bytes
        # Example: 68 00 04 68 30 04 5d 01 92 16
        # Data = response[7:-2] = 5d
        data = response[7:-2]
        if len(data) < 1:
            print("Not enough data for all fields.")
            return
        status = data[0]
        print("--- Module Status ---")
        print(f"Raw status byte: 0x{status:02X}")
        print(f"Amp is disabled: {bool(status & 0x01)}")
        print(f"Amp is in APR (eye-safe mode): {bool(status & 0x02)}")
        print(f"Amp is gain-limited: {bool(status & 0x04)}")
        print(f"Amp is power clamping: {bool(status & 0x08)}")
        print(f"Reserved bits (4-7): {status >> 4}")
        print("----------------------")

    def parse_power_response(self, response: bytes, label: str = "Power"):
        """
        Parses a power response (input/output/signal) for commands 0x35, 0x36, 0x37.
        Handles both single and multi-amp responses.
        """
        if len(response) < 12:
            print(f"{label}: Response too short to parse.")
            return
        data = response[7:-2]
        if len(data) < 2:
            print(f"{label}: Not enough data for all fields.")
            return
        # Each 2 bytes is a signed 16-bit value, Input/Output/Signal Power * 100 (dBm)
        n = len(data) // 2
        print(f"--- {label} ---")
        for i in range(n):
            val = struct.unpack('>h', data[2*i:2*i+2])[0]
            print(f"{i+1}/{n} queried {label}: {val/100:.2f} dBm")
        print("-------------------")

    # TEST FUNCTIONS, REFER TO CIENA EDFA MANUAL
    def get_pump_laser_status(self, sub_addr: int, amp_index: int, laser_index: int, expected_response_size: int = 31):
        """
        Command 0x3A: Get Pump Laser Status
        Args:
            sub_addr: The sub-address byte (e.g., 0x50, 0x53, 0x55)
            amp_index: Amplifier index (usually 1)
            laser_index: Pump laser index (usually 1)
        """
        return self.send_command(0x3A, [0x00, sub_addr, amp_index, laser_index], expected_response_size)

    def get_mode_status(self, amp_index: int, stage_index: int, expected_response_size: int = 12):
        """
        Command 0x31: Get Mode
        Args:
            amp_index: Amplifier index (usually 1)
            stage_index: Gain stage index (1 or 2)
        """
        return self.send_command(0x31, [amp_index, stage_index], expected_response_size)

    def get_module_status(self, amp_index: int, stage_index: int, expected_response_size: int = 10):
        """
        Command 0x30: Get Module Status
        Args:
            amp_index: Amplifier index (usually 1)
            stage_index: Gain stage index (1 or 2)
        """
        return self.send_command(0x30, [amp_index, stage_index], expected_response_size)

    def close(self):
        """Closes the serial connection if open."""
        if self.ser and self.ser.is_open:
            self.ser.close()
            print("Serial connection closed.")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

# Example usage:
if __name__ == '__main__':
    with EDFACommand(port='COM7') as edfa:
        if edfa.ser.is_open:
            print("Serial connection established on COM7.")
        try:
            # Get and print amplifier mode
            mode_response = edfa.send_gui_raw_command('get_mode', 1, 1)
            edfa.parse_mode_status_response(mode_response)

            # Run through all variants of get_module_status in the lookup table
            module_status_variants = [
                (0, 1), (1, 1), (2, 1), (0, 2), (1, 2), (2, 2),
            ]
            for amp_index, stage_index in module_status_variants:
                print(f"\n--- get_module_status amp={amp_index} stage={stage_index} ---")
                module_response = edfa.send_gui_raw_command('get_module_status', amp_index, stage_index)
                edfa.parse_module_status_response(module_response)

            # Get Input Power (0x35)
            print("\n--- Get Input Power ---")
            input_power_resp = edfa.send_raw_command('6800056835008c0001c216')
            edfa.parse_power_response(input_power_resp, label="Input Power")

            # Get Output Power (0x36)
            print("\n--- Get Output Power ---")
            output_power_resp = edfa.send_raw_command('6800056836008e0001c516')
            edfa.parse_power_response(output_power_resp, label="Output Power")

            # Get Output Signal Power (0x37)
            print("\n--- Get Output Signal Power ---")
            signal_power_resp = edfa.send_raw_command('680005683700910001c916')
            edfa.parse_power_response(signal_power_resp, label="Signal Power")

        except Exception as e:
            print("Error:", e)