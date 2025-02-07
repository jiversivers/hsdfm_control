import datetime
import tkinter as tk
from tkinter import messagebox, filedialog, simpledialog
import sqlite3

import numpy as np
from serial.tools import list_ports


def convert_time_to_seconds(time_str):
    """Convert time from MM:SS format to total seconds."""
    try:
        minutes, seconds = map(int, time_str.split(':'))
        return minutes * 60 + seconds  # Convert to total seconds
    except ValueError:
        return 0  # If the time is malformed, return 0


def update_plot(fig, ax, data_queue):
    if len(data_queue) > 0:
        ax.clear()
        ax2 = ax.twinx()

        # Extract time, dissolved oxygen, and temperature from data_queue
        # Calculate pO2 for each reading
        Hcc = 3.2e-2
        R = 8314  # LPaK-1mol-1
        m = 31.999  # g/mol
        t0 = datetime.datetime.strptime(data_queue[0][0], '%Y-%m-%d %H:%M:%S')
        times, do, T = zip(*data_queue)
        times = [datetime.datetime.strptime(t, '%Y-%m-%d %H:%M:%S') - t0 for t in times]
        t = np.asarray([t.total_seconds() for t in times])
        do = np.asarray(do) / 1000 / m  # mol/L
        T = np.asarray(T) + 273.15  # K
        kH = Hcc / (R * T)  # molL-1Pa-1
        pO2 = 7.5 * (do / kH) / 1000  # mmHg

        # Ensure data is sorted by time
        sorted_data = sorted(zip(t, pO2), key=lambda x: x[0])
        # Unpack sorted values
        t, pO2 = zip(*sorted_data)
        t = np.asarray(t)
        pO2 = np.asarray(pO2)

        h = 2.7
        p50 = 27
        sO2 = 100 * (pO2 ** h) / ((p50 ** h) + (pO2 ** h))

        # Left Y-axis (Dissolved Oxygen)
        ax.scatter(t, pO2, label='Oxygen Partial Pressure', color='b', marker='o')
        ax.set_xlabel('Time (Seconds)')
        ax.set_ylabel('Oxygen Partial Pressure (mmHg)', color='b')
        ax.tick_params(axis='y', labelcolor='b')
        ax.set_ylim(0, 160)

        ax2.scatter(t, sO2, label='Oxygen Saturation', color='r', marker='^')
        ax2.set_xlabel('Time (Seconds)')
        ax2.set_ylabel('Oxygen Saturation (%)', color='r')
        ax2.set_ylim(0, 100)

        fig.canvas.draw()


def select_serial_port():
    """GUI for selecting a serial port."""
    ports = list(list_ports.comports())
    ports = [port for port in ports if port.description != 'n/a']

    if not ports:
        messagebox.showerror("No Devices Found", "No serial devices detected. Check connections and try again.")
        return None

    # Create a new Tkinter window
    port_selection_window = tk.Toplevel()
    port_selection_window.title("Select Serial Port")
    port_selection_window.geometry("400x300")

    # Label at the top
    tk.Label(port_selection_window, text="Available Serial Ports:", font=("Arial", 12, "bold")).grid(row=0, column=0,
                                                                                                     columnspan=2,
                                                                                                     pady=5)

    # Listbox to display available ports
    listbox = tk.Listbox(port_selection_window, width=50, height=min(10, len(ports)))  # Limit height to 10 items
    for port in ports:
        listbox.insert(tk.END, f"{port.name} - {port.device} ({port.description})")
    listbox.grid(row=1, column=0, columnspan=2, pady=5)

    # Variable to store the selected port
    selected_port = tk.StringVar()

    def confirm_selection():
        """Handles the selection of a port."""
        selected_index = listbox.curselection()
        if selected_index:
            selected_text = listbox.get(selected_index)
            selected_port.set(selected_text.split(" - ")[1].split(" ")[0])  # Extract port.device
            port_selection_window.destroy()
        else:
            messagebox.showwarning("No Selection", "Please select a port.")

    # Confirm button
    tk.Button(port_selection_window, text="Select", command=confirm_selection, width=15).grid(row=2, column=0,
                                                                                              columnspan=2, pady=10)

    # Run the Tkinter event loop
    port_selection_window.wait_window()

    return selected_port.get() if selected_port.get() else None


def select_database():
    """Prompt the user to select or create a database file."""
    choice = messagebox.askyesno("Database Selection", "Do you want to create a new database?")

    if choice:
        # User wants to create a new database
        study_db = filedialog.asksaveasfilename(
            title="Save New Database",
            defaultextension=".db",
            filetypes=[("SQLite Files", "*.db"), ("All Files", "*.*")]
        )
    else:
        # User wants to select an existing database
        study_db = filedialog.askopenfilename(
            title="Select Existing Database",
            filetypes=[("SQLite Files", "*.db"), ("All Files", "*.*")]
        )
    return study_db


def select_study_table(db_path):
    """Prompt the user to select an existing study table or create a new one."""
    # Connect to the database and get the list of tables
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [row[0] for row in cursor.fetchall()]
    conn.close()

    # Add option to create a new table
    tables.append("Create New Table...")

    # Create a Tkinter dialog for selection
    root = tk.Toplevel()
    root.withdraw()  # Hide the main window

    study_name = simpledialog.askstring(
        "Select Study Table",
        f"Existing tables:\n\n{', '.join(tables[:-1])}\n\n"
        f"Enter a table name to create a new one, or select an existing one.",
    )

    if study_name and study_name not in tables[:-1]:
        messagebox.showinfo("New Table", f"Creating new table: {study_name}")

    return study_name
