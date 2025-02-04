from controllers import DOProbe
import sqlite3
import tkinter as tk
from tkinter import filedialog, simpledialog
import time
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import numpy as np


def update_plot(fig, ax, data_queue):
    if len(data_queue) > 0:
        ax.clear()
        t = [data[3] for data in data_queue]
        do = [data[0] for data in data_queue]
        temp = [data[1] for data in data_queue]
        ax.plot(t, do, label='Dissolved Oxygen')
        ax.plot(t, temp, label='Temperature')
        ax.set_xlabel('Time')
        ax.set_ylabel('Oxygen/Temperature')
        ax.legend(loc='upper right')

        fig.canvas.draw()


def record_do():
    root = tk.Tk()
    root.title("DO Probe Data")

    # Get user input
    port = simpledialog.askstring("Port", "Enter the COM port for the DO device (e.g., COM3, /dev/ttyUSB0):")
    study_name = simpledialog.askstring("Input", "Enter the study name for the database table:")
    study_db = filedialog.askopenfilename(title="Select Database File",
                                          filetypes=[("SQLite Files", "*.db"), ("All Files", "*.*")])
    if not study_db:
        study_db = filedialog.asksaveasfilename(title="Save New Database", defaultextension=".db",
                                                filetypes=[("SQLite Files", "*.db"), ("All Files", "*.*")])

    # Check if the user provided valid input
    if not port or not study_name or not study_db:
        print("Error: All inputs (port, study name, and database) are required!")
        return

    # Prep plot
    fig, ax = plt.subplots(figsize=(8, 6))
    canvas = FigureCanvasTkAgg(fig, master=root)
    canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    # Make DO device object
    probe = DOProbe(port=port)

    # Connect to database
    conn = sqlite3.connect(study_db)
    cursor = conn.cursor()

    # Make study table
    cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS {study_name} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            dissolved_oxygen INTEGER DEFAULT NULL,
            temperature INTEGER DEFAULT NULL,
            nanoamperes INTEGER DEFAULT NULL,
            time_from_start TIMESTAMP DEFAULT NULL)
            """)

    data_queue = []
    while probe.in_waiting > 0:
        data = probe.read().split(',')
        data = [d.strip() for d in data]

        # Write data to database
        cursor.execute(f"""
            INSERT INTO {study_name} (
            dissolved_oxygen, temperature, nanoamperes, time_from_start) 
            VALUES (?, ?, ?, ?)
            """, *data)
        data_queue.append(data)
        conn.commit()

        # (Update) plot of out-coming data stream
        data_queue.append(data)
        update_plot(fig, ax, data_queue)

        # Hesitate before fulling breaking
        delay = 0
        while probe.in_waiting == 0 and delay < 10:
            time.sleep(1)
            delay += 1
    conn.close()
    print('Probe stopped sending data. Recording closed and data saved.')


def capture_images(exposures=None, wavelengths=None):
    return None


def synchronized_phantom_measurement():
    return None
