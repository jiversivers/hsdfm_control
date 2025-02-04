import time
import serial

class Device(serial.Serial):
    def __init__(self, port=None, encoding='utf-8', **kwargs):
        super().__init__(port, **kwargs)
        self.encoding = encoding

    def read(self, size=1):
        out = super().read(size)
        return out.decode(self.encoding, errors='ignore')

    def write(self, command):
        # Send to the device
        return super().write(command.encode(self.encoding))

    def read_until(self, expected=serial.CR, size=None):
        line = super().read_until(expected=expected, size=size)
        return line.decode(self.encoding).strip()


class DOProbe(Device):
    def __init__(self, port):
        super().__init__(port=port,
                         baudrate=115200,
                         bytesize=serial.EIGHTBITS,
                         parity=serial.PARITY_NONE,
                         stopbits=serial.STOPBITS_ONE,
                         xonxoff=False,
                         rtscts=False,
                         dsrdtr=False)

        # Set controls for manual management
        self.dtr = True
        self.rts = True
        self.bytesize = serial.EIGHTBITS

    def read(self, bytes_to_read='all'):
        if bytes_to_read == 'all':
            bytes_to_read = self.in_waiting
        out = super().read(bytes_to_read)

        out_lines = out.splitlines()
        out_split = [line.split(';') for line in out_lines]
        data = []
        for out in out_split:
            data.append([d for d in out if d])

        return data


class LCTF(Device):
    def __init__(self, port):
        super().__init__(port=port,
                         baudrate=115200,
                         timeout=1,
                         parity=serial.PARITY_NONE,
                         bytesize=serial.EIGHTBITS,
                         stopbits=serial.STOPBITS_ONE
                         )

        # Configure CR line terminator
        self.expected = serial.CR  # Line terminator

        # Wake up the LCTF
        self.wake()

    def write(self, command):
        super().write(command)
        super().read()  # Clear the written command form the buffer

    def read(self):
        return super().read_until(self.expected, size=None)

    def wake(self):
        # Wake up LCTF
        self.write('A')  # Send wakeup command
        time.sleep(0.1)

        # Enusre it is awake
        self.query('A')  # Query wake status
        self.check_status('a     0')
        self.write('R 1')  # Reset LED and clear errors

    def query(self, quest):
        self.write(quest + ' ?')
        time.sleep(0.1)
        return self.read()

    @property
    def wavelength(self):
        if self._wavelength is None:
            self._wavelength = self.query('W')
        return self._wavelength

    @wavelength.setter
    def wavelength(self, wavelength):
        command = f'W {wavelength}.000'
        self.write(command)

        self.query('W')
        self.check_status(command)
        self._wavelength = wavelength

    def check_status(self, check_status):
        try_count = 0
        status = None
        while status != f'{check_status}':
            status = self.read()

            try_count += 1
            if try_count > 10:
                break

            if '*' in status:
                raise ValueError('Filter failed/cannot execute command. Parameter out of boounds or filter is asleep.')

        if status != f'{check_status}':
            raise ValueError('Failed to validate LCTF Status. No/unexpected response.')

class CMOS():
    def __init__(self):
        pass

    @property
    def exposure(self):
        return self._exposure

    @exposure.setter
    def exposure(self, exposure):
        self._exposure = exposure
        # Set actual hardware exposure

    def capture(self, exposure=None):
        exposure = self.exposure if exposure is None else exposure
        pass