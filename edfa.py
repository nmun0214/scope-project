#!/usr/bin/env python3
"""
Ciena EDFA Serial Command Interface
Supports UART serial communication with EDFA amplifiers
Protocol: 115200 baud, 8 data bits, no parity, 1 stop bit
"""

import struct
import serial
import crcmod
import time
from typing import Tuple, Optional, List


class EDFAController:
    """Controller for Ciena EDFA amplifiers via serial interface"""
    
    # Protocol constants
    SYNC_BYTE = 0x68
    DEVICE_ADDRESS = [0x00, 0x03]
    
    def __init__(self, port: str = 'COM7', timeout: float = 2.0):
        """
        Initialize EDFA controller
        
        Args:
            port: Serial port name (e.g., 'COM7', '/dev/ttyUSB0')
            timeout: Read timeout in seconds
        """
        self.port = port
        self.timeout = timeout
        self.ser = None
        
        # CRC-16/CCITT-FALSE (polynomial 0x1021, initial value 0xFFFF)
        self.crc16 = crcmod.mkCrcFun(0x11021, initCrc=0xFFFF, rev=False)
        
        self._connect()
    
    def _connect(self):
        """Establish serial connection"""
        try:
            self.ser = serial.Serial(
                port=self.port,
                baudrate=115200,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=self.timeout
            )
            print(f"Connected to {self.port}")
        except serial.SerialException as e:
            raise ConnectionError(f"Failed to connect to {self.port}: {e}")
    
    def _build_frame(self, cmd_id: int, args: List[int] = None) -> bytes:
        """
        Build command frame according to protocol
        
        Frame format: SYNC + ADDR + SYNC + CMD + ARGS + CRC
        
        Args:
            cmd_id: Command identifier
            args: Command arguments (optional)
            
        Returns:
            Complete frame as bytes
        """
        if args is None:
            args = []
            
        # Build frame without CRC
        frame_data = [self.SYNC_BYTE] + self.DEVICE_ADDRESS + [self.SYNC_BYTE, cmd_id] + args
        frame_bytes = bytes(frame_data)
        
        # Calculate and append CRC
        crc = self.crc16(frame_bytes)
        crc_bytes = struct.pack('>H', crc)  # Big-endian 16-bit CRC
        
        return frame_bytes + crc_bytes
    
    def _send_command(self, cmd_id: int, args: List[int] = None, 
                     expected_response_size: int = 64) -> bytes:
        """
        Send command and receive response
        
        Args:
            cmd_id: Command identifier
            args: Command arguments
            expected_response_size: Expected response length in bytes
            
        Returns:
            Raw response bytes
        """
        if not self.ser or not self.ser.is_open:
            raise ConnectionError("Serial connection not established")
        
        # Clear input buffer
        self.ser.reset_input_buffer()
        
        # Build and send frame
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
    
    def _parse_temperature_response(self, response: bytes) -> Tuple[Optional[float], Optional[float]]:
        """
        Parse temperature response according to protocol specification
        
        Expected format:
        - Size: 4 bytes total data
        - Value 1: Ambient Temperature * 10 (°C) - 16 bits signed
        - Value 2: Erbium Coil Temperature * 10 (°C) - 16 bits signed
        
        Args:
            response: Raw response bytes
            
        Returns:
            Tuple of (ambient_temp, erbium_temp) in Celsius
        """
        if len(response) < 10:  # Need at least header + 4 data bytes + CRC
            print(f"Response too short: {len(response)} bytes")
            return None, None
        
        try:
            # Skip protocol header (typically first 6 bytes: SYNC + ADDR + SYNC + CMD + STATUS)
            # Extract 4 bytes of temperature data
            temp_data = response[6:10]
            
            if len(temp_data) < 4:
                print("Insufficient temperature data in response")
                return None, None
            
            # Parse as two 16-bit signed integers (big-endian)
            ambient_raw, erbium_raw = struct.unpack('>hh', temp_data)
            
            # Convert from raw values (multiply by 10) to actual temperature
            ambient_temp = ambient_raw / 10.0
            erbium_temp = erbium_raw / 10.0
            
            return ambient_temp, erbium_temp
            
        except struct.error as e:
            print(f"Error parsing temperature data: {e}")
            return None, None
    
    def get_amplifier_temperature(self) -> Tuple[Optional[float], Optional[float]]:
        """
        Get amplifier ambient and erbium coil temperatures
        
        Command: 0x34 (Get Amplifier Temperature)
        Arguments: None required based on your working GUI command
        
        Returns:
            Tuple of (ambient_temperature, erbium_temperature) in Celsius
        """
        try:
            # Based on your working GUI command, it seems no arguments are needed
            # GUI command: 680003683400013516 suggests args might be [0x00, 0x01]
            response = self._send_command(0x34, [0x00, 0x01], expected_response_size=16)
            return self._parse_temperature_response(response)
            
        except Exception as e:
            print(f"Error getting temperature: {e}")
            return None, None
    
    # Additional command methods for future use
    def get_pump_laser_status(self, amp_index: int, laser_index: int) -> bytes:
        """Get pump laser status"""
        return self._send_command(0x3A, [amp_index, laser_index], expected_response_size=24)
    
    def get_mode_status(self, amp_index: int) -> bytes:
        """Get amplifier mode status"""
        return self._send_command(0x31, [amp_index], expected_response_size=9)
    
    def get_input_power(self, amp_index: int) -> bytes:
        """Get input power reading"""
        return self._send_command(0x35, [amp_index], expected_response_size=10)
    
    def get_output_power(self, amp_index: int) -> bytes:
        """Get output power reading"""
        return self._send_command(0x36, [amp_index], expected_response_size=10)
    
    def set_mode(self, amp_index: int, mode: int) -> bytes:
        """Set amplifier mode"""
        return self._send_command(0x11, [amp_index, mode])
    
    def close(self):
        """Close serial connection"""
        if self.ser and self.ser.is_open:
            self.ser.close()
            print("Serial connection closed")
    
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()


def main():
    """Example usage and testing"""
    try:
        with EDFAController(port='COM7') as edfa:
            print("Testing temperature reading...")
            
            ambient, erbium = edfa.get_amplifier_temperature()
            
            if ambient is not None and erbium is not None:
                print(f"✓ Ambient Temperature: {ambient:.2f} °C")
                print(f"✓ Erbium Coil Temperature: {erbium:.2f} °C")
            else:
                print("✗ Failed to read temperatures")
                
    except Exception as e:
        print(f"Error: {e}")


if __name__ == '__main__':
    main()