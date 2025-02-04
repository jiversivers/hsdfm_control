import serial


class Device(serial.Serial):
    def __init__(self, port=None, encoding='utf-8', **kwargs):
        super().__init__(port, **kwargs)
        self.encoding = encoding

    def read(self, bytes_to_read):
        # Read from the device
        bytes_read = super().read(bytes_to_read)
        return bytes_read.decode(self.encoding)

    def write(self, command):
        # Send to the device
        return super().write(command.encode(self.encoding))

    def read_until(self, expected=serial.CR, size=None):
        line = super().read_until(expected=expected, size=size)
        return line.decode(self.encoding).strip()

