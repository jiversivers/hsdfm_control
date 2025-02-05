from controllers import DOProbe
import sqlite3
import tkinter as tk
from tkinter import messagebox, ttk
import time
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from controllers.subs import select_serial_port, update_plot, select_database, select_study_table


def record_do(port=None, study_db=None):
    root = tk.Toplevel()
    root.title("DO Probe Data")

    # Get user input
    port = select_serial_port() if port is None else port
    study_db = select_database() if study_db is None else study_db
    study_name = select_study_table()

    # Check if the user provided valid input
    if not port or not study_name or not study_db:
        print("Error: All inputs (port, study name, and database) are required!")
        return

    # Prep plot
    fig, ax = plt.subplots(figsize=(8, 6))
    canvas = FigureCanvasTkAgg(fig, master=root)
    canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    # Create a progress bar
    progress_label = tk.Label(root, text="Timeout Progress:")
    progress_label.pack(pady=5)

    progress_bar = ttk.Progressbar(root, length=300, mode='determinate', maximum=10)
    progress_bar.pack(pady=5)

    # Make DO device object
    probe = DOProbe(port=port)

    # Connect to database
    conn = sqlite3.connect(study_db)
    cursor = conn.cursor()

    # Make study table
    cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS {study_name} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            time DATETIME DEFAULT CURRENT_TIMESTAMP,
            time_from_start TIMESTAMP DEFAULT NULL,
            dissolved_oxygen INTEGER DEFAULT NULL,
            nanoamperes INTEGER DEFAULT NULL,
            temperature INTEGER DEFAULT NULL
            )
            """)

    data_queue = []
    delay = 0
    while delay < 10:
        # Update progress bar
        progress_bar["value"] = delay
        root.update_idletasks()  # Force GUI update

        if probe.in_waiting > 0:
            delay = 0
            data = probe.read()

            # Write data to database
            cursor.execute("BEGIN TRANSACTION")
            for d in data:
                if len(d) > 12:
                    cursor.execute(f"""
                        INSERT INTO {study_name} (
                        time_from_start, dissolved_oxygen, nanoamperes, temperature) 
                        VALUES (?, ?, ?, ?)
                        """, (d[7], d[8], d[10], d[12]))
                    data_queue.append(d)
                else:
                    messagebox.showwarning('Skipped', f'Malformed data:\n{d}')
            conn.commit()

            # Update plot
            update_plot(fig, ax, data_queue)
            canvas.draw()

        else:
            # Wait a second
            time.sleep(1)
            delay += 1

    conn.close()
    print('Probe stopped sending data. Recording closed and data saved.')

    # Ask user if they want to record another study
    retry = messagebox.askyesno("Continue?", "Would you like to record another study in the same database?")

    if retry:
        root.destroy()
        record_do(port=port, study_db=study_db)
    else:
        root.destroy()


def capture_images(exposures=None, wavelengths=None):
    tk.messagebox.showwarning('Not implemented')


def synchronized_phantom_measurement():
    tk.messagebox.showwarning('Not implemented')
