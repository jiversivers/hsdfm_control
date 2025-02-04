import time

from controllers import Device
import serial


class DOProbe(Device):
    def __init__(self, port):
        super().__init__(port=port,
                         baud_rate=115200,
                         bytesize=serial.EIGHTBITS,
                         parity=serial.PARITY_NONE,
                         stopbits=serial.STOPBITS_ONE,
                         xonxoff=False,
                         rtsscts=False,
                         dsrdtr=False)

        # Set controls for manual management
        self.device.dtr = True
        self.device.rts = True

    def read(self, bytes_to_read):
        out = super().read(bytes_to_read)

        out_lines = out.splitlines()
        out_split = [line.split(':') for line in out_lines]

        max_len = max(len(line) for line in out_split)

        data = [line + [''] * (max_len - len(line)) for line in out_split]
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

    def wavelength(self, wavelength=None):
        if wavelength is None:
            return self.query('W')
        command = f'W {wavelength}.000'
        self.write(command)

        self.query('W')
        self.check_status(command)

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
