from tkinter import messagebox

from PIL._tkinter_finder import tk
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

        # Extract time, dissolved oxygen, and temperature from data_queue
        t = [convert_time_to_seconds(data[7]) for data in data_queue]  # Convert MM:SS to total seconds
        do = [data[8] for data in data_queue]  # Dissolved Oxygen
        temp = [data[12] for data in data_queue]  # Temperature

        # Left Y-axis (Dissolved Oxygen)
        ax.plot(t, do, label='Dissolved Oxygen', color='b')
        ax.set_xlabel('Time (Seconds)')
        ax.set_ylabel('Dissolved Oxygen (mg/L)', color='b')
        ax.tick_params(axis='y', labelcolor='b')

        # Right Y-axis (Temperature)
        ax2 = ax.twinx()  # Create a second y-axis
        ax2.clear()
        ax2.plot(t, temp, label='Temperature', color='r')
        ax2.set_ylabel('Temperature (°C)', color='r')
        ax2.tick_params(axis='y', labelcolor='r')

        # Add a legend
        ax.legend(loc='upper left')
        ax2.legend(loc='upper right')

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
