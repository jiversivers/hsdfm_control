import time

import numpy as np
import serial
from PIL import Image, ImageTk
import tkinter as tk
from hamamatsu.dcam import dcam, Stream, copy_frame
import cv2


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


class CMOS:
    def __init__(self, camera_index=0):
        # Instantiate DCAM and enter context
        self.dcam = dcam
        self.dcam.__enter__()
        self.camera = self.dcam[camera_index]
        self.camera.__enter__()

        self.streaming = False
        self.root = None

    def __del__(self):
        self.camera.__exit__(None, None, None)
        self.dcam.__exit__(None, None, None)

    # TODO: Add a getitem method to self.camera so that dict calls automatically open the context and all attributes of
    #  the camera class will be accessible through cmos (like exposure time and binning currently are)

    @property
    def exposure_time(self):
        with self.camera as camera:
            return camera["exposure_time"].value

    @exposure_time.setter
    def exposure_time(self, exposure_time):
        with self.camera as camera:
            camera["exposure_time"] = exposure_time

    @property
    def binning(self):
        with self.camera as camera:
            return camera["binning"].value

    @binning.setter
    def binning(self, binning):
        with self.camera as camera:
            camera["binning"] = binning


    def capture(self, nb_frames=1):
        with Stream(self.camera, nb_frames) as stream:
            self.camera.start()
            frames = []
            try:
                for i, frame_buffer in enumerate(stream):
                    frame = copy_frame(frame_buffer)
                    frames.append(frame)
            finally:
                self.camera.stop()
        if nb_frames == 1:
            return frames[0]
        return frames

    def stream(self):
        while self.streaming:
            try:
                yield self.capture(1)
            except Exception as e:
                print(f"Error during streaming: {e}")
                self.streaming = False
            finally:
                self.camera.stop()

    def view(self, live=True):
        if not live:
            frame = self.capture(nb_frames=1)
            frame = self._display_frame(frame)
            cv2.imshow("CMOS View", np.array(frame))
            cv2.waitKey(0)
            cv2.destroyAllWindows()
            return

        # Initialize Tkinter window
        self.root = tk.Toplevel()  # Use Toplevel() so this can be called from other GUIs
        self.root.title("CMOS Camera Stream")
        self.root.geometry('800x800')

        container = tk.Frame(self.root)
        container.pack(pady=10)

        # Create a label to display the camera feed
        self.video_label = tk.Label(container, width=640, height=640)
        self.video_label.pack()

        # OK Button to stop streaming
        stop_button = tk.Button(self.root, text="OK", command=self.stop_stream, width=10, height=2)
        stop_button.pack(pady=10)

        self.streaming = True  # Start streaming
        self.update_frame()  # Start updating frames
        self.root.mainloop()  # Start Tkinter event loop

    cv2.destroyAllWindows()

    def update_frame(self):
        """Capture a frame from the camera and update the Tkinter label."""
        if self.streaming:
            try:
                frame = next(self.stream())  # Get the next frame
                frame = self._display_frame(frame)  # Convert for display

                # Update Tkinter label with new frame
                self.video_label.configure(image=frame)
                self.video_label.image = frame  # Keep reference

            except ValueError as e:
                print(f"Error during streaming: {e}")

            # Schedule the next frame update
            self.root.after(10, self.update_frame)

    def stop_stream(self):
        """Stop the live stream and close the Tkinter window."""
        self.streaming = False
        self.camera.stop()
        if self.root:
            self.root.destroy()
            self.root = None  # Reset the reference

    def _display_frame(self, frame):
        image = np.array(frame, dtype=np.uint8)

        # Convert grayscale to BGR
        if len(image.shape) == 2:
            image = cv2.cvtColor(image, cv2.COLOR_GRAY2RGB)

        # Convert to PIL image and then to Tkinter-compatible format
        image = Image.fromarray(image)
        return ImageTk.PhotoImage(image)