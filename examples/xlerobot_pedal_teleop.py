import serial
import logging
import serial.tools.list_ports

class XlerobotPedalTeleop:
    def __init__(self, vid = 1155, pid = 22336, baudrate = 115200, timeout = 0.1):
        self.vid = vid
        self.pid = pid
        self.baudrate = baudrate
        self.timeout = timeout
        self.pedal_mapping = {
            '3': 'forward',
            '2': 'backward',
            '1': 'left',
            '0': 'right',
        }

    def connect(self):
        self.port = self.__find_and_open_port()

    def get_action(self):

        data = self.port.read(1)
        if not data:
            return []
        
        data = data[0]
        pressed_pedals = []
        for i in range(len(self.pedal_mapping)):
            if data >> i & 1:
                pressed_pedals.append(self.pedal_mapping[str(i)])
        return pressed_pedals

    def __find_device_by_vid_pid(self):
        """
        Searches for a device with the given VID and PID.

        :return: The device port name (e.g., 'COM3' or '/dev/ttyUSB0'), or None if not found.
        """
        ports = serial.tools.list_ports.comports()
        for port in ports:
            if port.vid == self.vid and port.pid == self.pid:
                return port.device
        logging.error("No device found")
        return None

    def __find_and_open_port(self):
        """
        Finds the device by VID/PID and opens the serial port.

        :return: A serial.Serial object or None if the device is not found.
        """
        device_port = self.__find_device_by_vid_pid()
        if device_port:
            logging.info(f"Device found on port: {device_port}")
            try:
                port = serial.Serial(
                    device_port, baudrate=self.baudrate, timeout=self.timeout
                )
                if port.isOpen():
                    logging.info(f"Port {device_port} opened successfully")
                    return port
            except Exception as e:
                logging.error(f"Failed to open port {device_port}: {e}")
        logging.error("No device found")
        return None