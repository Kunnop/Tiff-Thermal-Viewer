import tkinter as tk
from tkinter import filedialog, ttk
import rasterio
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import warnings
import re, subprocess
import ttkbootstrap as ttkb

#BY KUNNOP KOETYAEM 02/13/2025
def open_file():
    file_path = filedialog.askopenfilename(filetypes=[("TIFF files", "*.tif;*.tiff")])
    if file_path:
        file_label.config(text=f"📁 File: {file_path.split('/')[-1]}")  # Show only file name
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

    def on_hover(event):
        if thermal_data is not None and event.xdata is not None and event.ydata is not None:
            x, y = int(event.xdata), int(event.ydata)
            if 0 <= x < thermal_data.shape[1] and 0 <= y < thermal_data.shape[0]:
                temp = thermal_data[y, x]
                hover_label.config(text=f"🎯 Temp: {temp:.2f} °C")
    
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
    canvas.mpl_connect("motion_notify_event", on_hover)
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

def update_slider_label(val, slider_type):
    """ Updates the displayed number next to the sliders """
    if slider_type == "vmin":
        vmin_value_label.config(text=f"{float(val):.1f} °C")
    elif slider_type == "vmax":
        vmax_value_label.config(text=f"{float(val):.1f} °C")
    update_image()

# Create Tkinter window
root = tk.Tk()
root.title("Thermal Image Viewer")
root.geometry("1000x900")  # Set window size
root.protocol("WM_DELETE_WINDOW", on_closing) 

# Create UI elements
btn_open = ttkb.Button(root, text="Open Thermal Image", command=open_file)
btn_open.pack(pady=10)

file_label = ttkb.Label(root, text="📁 File: No file selected", font=("Arial", 12, "italic"))
file_label.pack(pady=5)

gps_label = ttkb.Label(root, text="📍 GPS: Not Available", font=("Arial", 12))
gps_label.pack(pady=5)

hover_label = ttkb.Label(root, text="🎯 Temp: Move cursor over image", font=("Arial", 12))
hover_label.pack(pady=5)

#temp_label = tk.Label(root, text="Temperature: Right Click on Image")
#temp_label.pack(pady=5)

frame = tk.Frame(root)
frame.pack()

style = ttkb.Style()

# 🎨 Custom Style for Min Temp Slider (Blue)
style.configure("Blue.Horizontal.TScale",
                troughcolor="#FF4C4C",  # Light Blue Background
                sliderthickness=12, 
                background="#D0E8FF")

# Create sliders for adjusting vmin and vmax
slider_frame = ttkb.Frame(root, padding=10)
slider_frame.pack(pady=10)

vmin_label = ttkb.Label(slider_frame, text="Min Temp", font=("Arial", 10))
vmin_label.pack(side="left", padx=5)

vmin_slider = ttkb.Scale(slider_frame, from_=0, to=100, length=200, orient='horizontal', command=lambda val: update_slider_label(val, "vmin"), style='Blue.Horizontal.TScale')
vmin_slider.pack(side='left', padx=15)

vmin_value_label = ttkb.Label(slider_frame, text="0.0 °C", font=("Arial", 10))  # Default Value
vmin_value_label.pack(side="left", padx=5)

vmax_label = ttkb.Label(slider_frame, text="Max Temp", font=("Arial", 10))
vmax_label.pack(side="left", padx=5)

vmax_slider = ttkb.Scale(slider_frame, from_=0, to=100, length=200, orient='horizontal', command=lambda val: update_slider_label(val, "vmax"), style='Blue.Horizontal.TScale')
vmax_slider.pack(side='left', padx=15)

vmax_value_label = ttkb.Label(slider_frame, text="100.0 °C", font=("Arial", 10))  # Default Value
vmax_value_label.pack(side="left", padx=5)

# Create colormap selection dropdown
cmap_frame = tk.Frame(root)
cmap_frame.pack(pady=10)

cmap_var = tk.StringVar(value='inferno')
cmap_label = tk.Label(cmap_frame, text='Colormap:')
cmap_label.pack(side='left', padx=5)

cmap_options = ['inferno', 'jet', 'hot', 'gray', 'viridis', 'plasma', 'magma', 'cividis', 'nipy_spectral', 'turbo', 'prism']
cmap_dropdown = ttkb.Combobox(cmap_frame, textvariable=cmap_var, values=cmap_options, state='readonly')
cmap_dropdown.pack(side='left', padx=5)
cmap_dropdown.bind("<<ComboboxSelected>>", update_image)

btn_reset = ttkb.Button(cmap_frame, text="Reset View", command=reset_view)
btn_reset.pack(side='left', padx=10)


# Run the application
root.mainloop()