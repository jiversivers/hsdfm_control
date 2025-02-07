import numpy as np
from jupyter_server.extension.utils import get_metadata

from controllers import DOProbe, CMOS, LCTF
import sqlite3
import tkinter as tk
from tkinter import messagebox, ttk, simpledialog, filedialog
import time
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from tifffile import tiff

from controllers.subs import get_metadata_from_user, select_serial_port, update_plot, select_database, \
    select_study_table


def record_do(port=None, study_db=None):
    root = tk.Toplevel()
    root.title("DO Probe Data")

    # Get user input
    port = select_serial_port() if port is None else port
    study_db = select_database() if study_db is None else study_db

    if not study_db:
        print("Error: A database file must be provided!")
        return

    # Create metadata input form
    metadata = get_metadata_from_user()

    if not metadata["sample_name"]:
        print("Error: Sample name is required!")
        return

    sample_name = metadata["sample_name"]

    # Prep plot
    fig, ax = plt.subplots(figsize=(8, 6))
    canvas = FigureCanvasTkAgg(fig, master=root)
    canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    # Create a progress bar
    progress_label = tk.Label(root, text="Timeout Progress:")
    progress_label.pack(pady=5)

    progress_bar = ttk.Progressbar(root, length=300, mode='determinate', maximum=10)
    progress_bar.pack(pady=5)

    # Initialize DO device object
    probe = DOProbe(port=port)

    # Connect to database
    conn = sqlite3.connect(study_db)
    cursor = conn.cursor()

    # Insert study metadata
    cursor.execute("""
        INSERT INTO dissolved_oxygen_study_table (
            start_time, sample_name, solvent, hemoglobin_concentration_mg_mL,
            microsphere_concentration_uL_mL, yeast_stock_added_uL_mL, yeast_concentration_mg_mL
        ) VALUES (CURRENT_TIMESTAMP, ?, ?, ?, ?, ?, ?)
    """, tuple(metadata.values()))

    sample_id = cursor.lastrowid  # Get the inserted study ID

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
                    cursor.execute("""
                        INSERT INTO dissolved_oxygen_records (
                            sample_name, sample_id, time, dissolved_oxygen, nanoamperes, temperature
                        ) VALUES (?, ?, CURRENT_TIMESTAMP, ?, ?, ?)
                    """, (sample_name, sample_id, d[8], d[10], d[12]))

                    cursor.execute(
                        f"SELECT time, dissolved_oxygen, temperature FROM dissolved_oxygen_records WHERE sample_id = ?",
                        (sample_id,))
                    data_queue = cursor.fetchall()
                else:
                    print('Skipped', f'Malformed data:\n{d}')
            conn.commit()

            # Update plot
            try:
                update_plot(fig, ax, data_queue)
                canvas.draw()
            except Exception as e:
                print(f'Failed to update plot:\n{e}')

        else:
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


def focus_camera(cmos=None):
    cmos = CMOS() if cmos is None else cmos
    cmos.view(live=True)


def capture_images(exposures=None, wavelengths=None, port=None, study_db=None):
    cmos = CMOS()

    # Get user input
    port = select_serial_port() if port is None else port
    study_db = select_database() if study_db is None else study_db
    study_name = select_study_table(study_db)
    # User wants to create a new database
    image_name = filedialog.asksaveasfilename(
        title="Save New Image Stack",
        defaultextension=".tiff",
        filetypes=[("TIFF", "*.tiff"), ("All Files", "*.*")]
    )

    # Check if the user provided valid input
    if not port or not study_name or not study_db:
        print("Error: All inputs (port, study name, and database) are required!")
        return

    lctf = LCTF(port=port)

    conn = sqlite3.connect(study_db)
    c = conn.cursor()
    c.execute(f"""
    CREATE TABLE IF NOT EXISTS {study_name}_index (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        image_name TEXT NOT NULL,
        time DATETIME DEFAULT CURRENT_TIMESTAMP)""")
    conn.commit()

    c.execute(f"""
    CREATE TABLE IF NOT EXISTS {study_name}_details (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        image_name TEXT NOT NULL,
        exposure_time FLOAT NOT NULL,
        lambda INT NOT NULL,
        time DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (image_name) REFERENCES {study_name}_index (image_name)) """)
    conn.commit()

    c.execute(f"""INSERT INTO {study_name}_index (image_name) (?)""", (image_name,))
    conn.commit()

    c.execute(f"""SELECT * FROM {study_name}_index WHERE image_name={image_name}""")
    image_metadata = c.fetchone()

    if exposures is None and wavelengths is None:
        exposures = [cmos.exposure_time]
        wavelengths = [lctf.wavelength]
    elif exposures is None:
        exposures = [cmos.exposure_time] * len(wavelengths)
    elif wavelengths is None:
        wavelengths = [lctf.wavelength] * len(exposures)

    frame = []
    for tau, lam in zip(exposures, wavelengths):
        lctf.wavelength = lam
        cmos.exposure_time = tau
        frame.append(cmos.capture())

        c.execute(f"""
        INSERT INTO {study_name}_details (image_name, exposure_time, lambda), (?, ?, ?)""", (image_name, tau, lam))
    frame = np.array(frame)
    tiff.imwrite(image_name, frame)


    ## TODO: Add option to feed straight into analysis tools


def synchronized_phantom_measurement():
    tk.messagebox.showwarning('Not implemented')
