import tkinter as tk
from tkinter import filedialog, ttk
import rasterio
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import warnings
import re, subprocess

#BY KUNNOP KOETYAEM 02/13/2025
def open_file():
    file_path = filedialog.askopenfilename(filetypes=[("TIFF files", "*.tif;*.tiff")])
    if file_path:
        process_thermal_image(file_path)

def get_gps_position(tiff_path):
    try:
        result = subprocess.run(["exiftool", tiff_path], capture_output=True, text=True)
        output = result.stdout
        
        gps_match = re.search(r"GPS Position\s+: (.+)", output)
        if gps_match:
            return f"GPS Position: {gps_match.group(1)}"
    except Exception as e:
        print(f"Error extracting GPS data: {e}")
    return "GPS Position: Unknown"

def reset_view():
    update_image()

def update_image(val=None):
    vmin = vmin_slider.get()
    vmax = vmax_slider.get()
    cmap = cmap_var.get()
    
    fig, ax = plt.subplots(figsize=(10, 6))
    img = ax.imshow(thermal_data, cmap=cmap, vmin=vmin, vmax=vmax)
    fig.colorbar(img, label='Temperature (°C)')
    ax.set_title("Thermal Image")
    ax.axis("off")

    def on_click(event):
        if event.xdata is not None and event.ydata is not None:
            x, y = int(event.xdata), int(event.ydata)
            if 0 <= x < thermal_data.shape[1] and 0 <= y < thermal_data.shape[0]:
                temp = thermal_data[y, x]
                temp_label.config(text=f"Temperature: {temp:.2f} °C")

    def on_scroll(event):
        scale_factor = 1.1 if event.delta > 0 else 0.9
        xlim = ax.get_xlim()
        ylim = ax.get_ylim()
        ax.set_xlim([xlim[0] * scale_factor, xlim[1] * scale_factor])
        ax.set_ylim([ylim[0] * scale_factor, ylim[1] * scale_factor])
        canvas.draw()
    
    def on_press(event):
        canvas_widget.old_coords = event.x, event.y
    
    def on_drag(event):
        if hasattr(canvas_widget, 'old_coords'):
            dx = event.x - canvas_widget.old_coords[0]
            dy = event.y - canvas_widget.old_coords[1]
            xlim = ax.get_xlim()
            ylim = ax.get_ylim()
            ax.set_xlim([x - dx for x in xlim])
            ax.set_ylim([y - dy for y in ylim])
            canvas_widget.old_coords = event.x, event.y
            canvas.draw()
    
    for widget in frame.winfo_children():
        widget.destroy()
    
    canvas = FigureCanvasTkAgg(fig, master=frame)
    canvas_widget = canvas.get_tk_widget()
    canvas_widget.pack()
    canvas.draw()
    canvas.mpl_connect("button_press_event", on_click)  # Right-click to get temperature
    canvas_widget.bind("<MouseWheel>", on_scroll)
    canvas_widget.bind("<ButtonPress-1>", on_press)
    canvas_widget.bind("<B1-Motion>", on_drag)
    plt.close(fig)

def process_thermal_image(tiff_path):
    global thermal_data, vmin_slider, vmax_slider
    
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=rasterio.errors.NotGeoreferencedWarning)
        with rasterio.open(tiff_path) as dataset:
            thermal_data = dataset.read(1)  # Read the first band
            min_val = thermal_data.min()
            max_val = thermal_data.max()

    gps_info = get_gps_position(tiff_path)
    print(f"Min Temp: {min_val:.2f} °C, Max Temp: {max_val:.2f} °C")
    gps_label.config(text=gps_info)

    vmin_slider.config(from_=min_val, to=max_val)
    vmax_slider.config(from_=min_val, to=max_val)
    
    vmin_slider.set(min_val)
    vmax_slider.set(max_val)
    update_image()

def on_closing():
    root.quit()
    root.destroy()

# Create Tkinter window
root = tk.Tk()
root.title("Thermal Image Viewer")
root.geometry("1000x850")  # Set window size
root.protocol("WM_DELETE_WINDOW", on_closing) 

# Create UI elements
btn_open = tk.Button(root, text="Open Thermal Image", command=open_file)
btn_open.pack(pady=10)

gps_label = tk.Label(root, text="GPS Position: Unknown")
gps_label.pack(pady=5)

temp_label = tk.Label(root, text="Temperature: Right Click on Image")
temp_label.pack(pady=5)

frame = tk.Frame(root)
frame.pack()

# Create sliders for adjusting vmin and vmax
slider_frame = tk.Frame(root)
slider_frame.pack(pady=10)

vmin_slider = tk.Scale(slider_frame, from_=0, to=100, resolution=0.1, orient='horizontal', label='Vmin', command=update_image)
vmin_slider.pack(side='left', padx=10)

vmax_slider = tk.Scale(slider_frame, from_=0, to=100, resolution=0.1, orient='horizontal', label='Vmax', command=update_image)
vmax_slider.pack(side='left', padx=10)

# Create colormap selection dropdown
cmap_frame = tk.Frame(root)
cmap_frame.pack(pady=10)

cmap_var = tk.StringVar(value='inferno')
cmap_label = tk.Label(cmap_frame, text='Colormap:')
cmap_label.pack(side='left', padx=5)

cmap_options = ['inferno', 'jet', 'hot', 'gray', 'viridis', 'plasma', 'magma', 'cividis']
cmap_dropdown = ttk.Combobox(cmap_frame, textvariable=cmap_var, values=cmap_options, state='readonly')
cmap_dropdown.pack(side='left', padx=5)
cmap_dropdown.bind("<<ComboboxSelected>>", update_image)

btn_reset = tk.Button(cmap_frame, text="Reset View", command=reset_view)
btn_reset.pack(side='left', padx=10)

# Run the application
root.mainloop()