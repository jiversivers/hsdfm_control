import tkinter as tk
from tkinter import messagebox

from controllers.routines import record_do, capture_images, synchronized_phantom_measurement

root = tk.Tk()
root.title("What do you want to do?")
root.geometry("400x300")

# Create buttons for different routines
button1 = tk.Button(root, text="Track DO", width=20, height=2, command=record_do)
button1.pack(pady=10)

button2 = tk.Button(root, text="Capture Images", width=20, height=2, command=capture_images)
button2.pack(pady=10)

button3 = tk.Button(root, text="Synced Phantom Measuring", width=20, height=2, command=synchronized_phantom_measurement)
button3.pack(pady=10)

# Start the Tkinter event loop
root.mainloop()