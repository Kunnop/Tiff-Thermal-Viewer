import tkinter as tk
from tkinter import filedialog, ttk, simpledialog
import rasterio
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.patches import Rectangle
import matplotlib.patheffects as plt_effects
import warnings
import re, subprocess
import ttkbootstrap as ttkb
import tkinter.messagebox
import os

# Global variables for annotations
annotations = []
is_drawing = False
rect_start = None
current_rect = None
annotation_mode = False
is_panning = False

# Add canvas_widget to global variables at the top
canvas_widget = None

# Add to global variables at the top
point_annotation_mode = False
point_annotations = []

# At the top, define your 4:3 box size (in pixels)
BOX_WIDTH = 800
BOX_HEIGHT = 600

# Add at the top of your file:
colorbar = None

#BY KUNNOP KOETYAEM 05/20/2025
def open_file():
    file_path = filedialog.askopenfilename(filetypes=[("TIFF files", "*.tif;*.tiff")])
    if file_path:
        file_label.config(text=f"📁 File: {file_path.split('/')[-1]}")  # Show only file name
        process_thermal_image(file_path)

def convert_to_decimal_degrees(gps_str):
    try:
        # Split the string into lat and lon parts by comma
        lat_str, lon_str = gps_str.split(',')
        
        # Process latitude
        lat_parts = lat_str.strip().split()
        lat_deg = float(lat_parts[0])
        lat_min = float(lat_parts[2].replace("'", ""))
        lat_sec = float(lat_parts[3].replace('"', ""))
        lat_dir = lat_parts[4]
        
        # Process longitude
        lon_parts = lon_str.strip().split()
        lon_deg = float(lon_parts[0])
        lon_min = float(lon_parts[2].replace("'", ""))
        lon_sec = float(lon_parts[3].replace('"', ""))
        lon_dir = lon_parts[4]
        
        # Convert to decimal degrees
        lat_decimal = lat_deg + (lat_min / 60) + (lat_sec / 3600)
        lon_decimal = lon_deg + (lon_min / 60) + (lon_sec / 3600)
        
        # Apply direction
        if lat_dir == 'S':
            lat_decimal = -lat_decimal
        if lon_dir == 'W':
            lon_decimal = -lon_decimal
            
        return f"{lat_decimal:.6f}°, {lon_decimal:.6f}°"
    except Exception as e:
        print(f"Error converting GPS coordinates: {e}")
    return "GPS: Unknown"

def get_gps_position(tiff_path):
    try:
        result = subprocess.run(["exiftool", tiff_path], capture_output=True, text=True)
        output = result.stdout
        
        gps_match = re.search(r"GPS Position\s+: (.+)", output)
        if gps_match:
            gps_str = gps_match.group(1)
            decimal_coords = convert_to_decimal_degrees(gps_str)
            gps_text.config(state='normal')  # Enable editing
            gps_text.delete("1.0", tk.END)
            gps_text.insert("1.0", f"{decimal_coords}")
            gps_text.config(state='disabled')  # Make it read-only again
            return decimal_coords
    except Exception as e:
        print(f"Error extracting GPS data: {e}")
        gps_text.config(state='normal')
        gps_text.delete("1.0", tk.END)
        gps_text.insert("1.0", "📍 GPS: Unknown")
        gps_text.config(state='disabled')
    return "GPS: Unknown"

def get_date_taken(tiff_path):
    try:
        result = subprocess.run(["exiftool", tiff_path], capture_output=True, text=True)
        output = result.stdout
        
        # Try to find the date in different EXIF tags
        date_match = re.search(r"Date/Time Original\s+: (.+)", output)
        if not date_match:
            date_match = re.search(r"Create Date\s+: (.+)", output)
        if not date_match:
            date_match = re.search(r"Modify Date\s+: (.+)", output)
            
        if date_match:
            date_str = date_match.group(1)
            # Parse the date string (assuming format like "2024:02:13 15:30:45")
            try:
                # Split the date and time parts
                date_part, time_part = date_str.split()
                # Split the date into year, month, day
                year, month, day = date_part.split(':')
                # Format as DD/MM/YYYY HH:mm:ss
                formatted_date = f"{day}/{month}/{year} {time_part}"
                
                date_text.config(state='normal')
                date_text.delete("1.0", tk.END)
                date_text.insert("1.0", f"{formatted_date}")
                date_text.config(state='disabled')
                return formatted_date
            except Exception as e:
                print(f"Error formatting date: {e}")
                # If parsing fails, return original format
                date_text.config(state='normal')
                date_text.delete("1.0", tk.END)
                date_text.insert("1.0", f"{date_str}")
                date_text.config(state='disabled')
                return date_str
    except Exception as e:
        print(f"Error extracting date: {e}")
        date_text.config(state='normal')
        date_text.delete("1.0", tk.END)
        date_text.insert("1.0", "📅 Date: Unknown")
        date_text.config(state='disabled')
    return "Date: Unknown"

def reset_view():
    ax.set_xlim(0, thermal_data.shape[1])
    ax.set_ylim(thermal_data.shape[0], 0)  # Keep Y-axis inverted for correct image orientation

    update_image()

img_display = None

def update_image():
    global img_display, fig, ax, canvas, canvas_widget, colorbar

    vmin = vmin_slider.get()
    vmax = vmax_slider.get()
    cmap = cmap_var.get()
    display_data = np.clip(thermal_data, vmin, vmax)

    # Only recreate the figure/canvas if the shape changes
    if (not hasattr(update_image, 'current_shape')) or (update_image.current_shape != display_data.shape):
        update_image.current_shape = display_data.shape

        if canvas_widget is not None:
            canvas_widget.destroy()

        fig, ax = plt.subplots()
        fig.subplots_adjust(left=0.1, right=0.85, top=1, bottom=0, wspace=0, hspace=0)
        img_display = ax.imshow(display_data, cmap=cmap, vmin=vmin, vmax=vmax, interpolation='nearest')
        ax.set_xlim(0, thermal_data.shape[1])
        ax.set_ylim(thermal_data.shape[0], 0)
        ax.set_aspect('equal')
        ax.axis("off")

        # Create colorbar and keep reference
        colorbar = fig.colorbar(img_display, ax=ax, fraction=0.05, pad=0.02, label='Temperature (°C)')
        colorbar.ax.tick_params(labelsize=10)

        canvas = FigureCanvasTkAgg(fig, master=frame)
        canvas_widget = canvas.get_tk_widget()
        canvas_widget.pack(fill=tk.BOTH, expand=True)

        # Re-bind events
        canvas.mpl_connect("button_press_event", on_mouse_press)
        canvas.mpl_connect("motion_notify_event", on_mouse_motion)
        canvas.mpl_connect("button_release_event", on_mouse_release)
        canvas_widget.bind("<MouseWheel>", on_scroll)
    else:
        img_display.set_data(display_data)
        img_display.set_cmap(cmap)
        img_display.set_clim(vmin, vmax)
        if colorbar is not None:
            colorbar.update_normal(img_display)
            colorbar.ax.figure.canvas.draw_idle()

def on_mouse_press(event):
    global is_drawing, rect_start, current_rect, is_panning
    if event.inaxes != ax:  # Ignore clicks outside the axes
        return
        
    # Point annotation mode (left click)
    if point_annotation_mode and event.button == 1:
        if event.xdata is not None and event.ydata is not None:
            add_point_annotation(event.xdata, event.ydata)
        return
        
    # Right click for box annotations
    if event.button == 3 and annotation_mode:
        is_drawing = True
        rect_start = (event.xdata, event.ydata)
        # Create white rectangle with black edge
        current_rect = Rectangle(rect_start, 0, 0, fill=False, edgecolor='white', linewidth=1)
        current_rect.set_path_effects([plt_effects.withStroke(linewidth=2, foreground='black')])
        ax.add_patch(current_rect)
        canvas.draw()
    # Left click for temperature display and panning
    elif event.button == 1 and not point_annotation_mode:
        #if event.xdata is not None and event.ydata is not None:
        #    x, y = int(event.xdata), int(event.ydata)
        #    if 0 <= x < thermal_data.shape[1] and 0 <= y < thermal_data.shape[0]:
        #        temp = thermal_data[y, x]
        #        temp_label.config(text=f"Temperature: {temp:.2f} °C")
        # Start pan operation
        canvas_widget.old_coords = event.x, event.y
        is_panning = True

def on_mouse_motion(event):
    global current_rect
    if event.inaxes != ax:  # Ignore motion outside the axes
        return
        
    # Handle annotation drawing (right-click drag)
    if annotation_mode and is_drawing and rect_start is not None:
        if event.xdata is not None and event.ydata is not None:
            width = event.xdata - rect_start[0]
            height = event.ydata - rect_start[1]
            current_rect.set_width(width)
            current_rect.set_height(height)
            canvas.draw()
    # Handle panning (left-click drag)
    elif is_panning and hasattr(canvas_widget, 'old_coords') and event.x is not None and event.y is not None:
        dx = event.x - canvas_widget.old_coords[0]
        dy = event.y - canvas_widget.old_coords[1]
        xlim = ax.get_xlim()
        ylim = ax.get_ylim()
        ax.set_xlim([x - dx for x in xlim])
        # Invert vertical panning direction
        ax.set_ylim([y + dy for y in ylim])  # Changed minus to plus to invert
        canvas_widget.old_coords = event.x, event.y
        canvas.draw()
    
    # Always show temperature on hover
    if event.xdata is not None and event.ydata is not None:
        x, y = int(event.xdata), int(event.ydata)
        if 0 <= x < thermal_data.shape[1] and 0 <= y < thermal_data.shape[0]:
            temp = thermal_data[y, x]
            hover_label.config(text=f"🎯 Temp: {temp:.2f} °C")

def find_min_max_temps(x_start, y_start, width, height):
    # Convert to integer coordinates
    x1 = max(0, int(x_start))
    y1 = max(0, int(y_start))
    x2 = min(thermal_data.shape[1], int(x_start + width))
    y2 = min(thermal_data.shape[0], int(y_start + height))
    
    # Get the region of interest
    region = thermal_data[y1:y2, x1:x2]
    
    if region.size == 0:
        return (None, None, None), (None, None, None)
    
    # Find min and max temperatures and their positions
    min_temp = np.min(region)
    max_temp = np.max(region)
    
    # Get coordinates of min and max points
    min_pos = np.where(region == min_temp)
    max_pos = np.where(region == max_temp)
    
    if len(min_pos[0]) == 0 or len(max_pos[0]) == 0:
        return (None, None, None), (None, None, None)
        
    # Convert back to image coordinates
    min_y, min_x = min_pos[0][0] + y1, min_pos[1][0] + x1
    max_y, max_x = max_pos[0][0] + y1, max_pos[1][0] + x1
    
    return (min_x, min_y, min_temp), (max_x, max_y, max_temp)

def find_box_average_temp(x_start, y_start, width, height):
    # Convert to integer coordinates
    x1 = max(0, int(x_start))
    y1 = max(0, int(y_start))
    x2 = min(thermal_data.shape[1], int(x_start + width))
    y2 = min(thermal_data.shape[0], int(y_start + height))
    
    # Get the region of interest
    region = thermal_data[y1:y2, x1:x2]
    
    if region.size == 0:
        return None
    
    # Calculate average temperature
    avg_temp = np.mean(region)
    return avg_temp

def on_mouse_release(event):
    global is_drawing, current_rect, rect_start, is_panning
    
    # Handle left-click release for panning
    if event.button == 1:
        is_panning = False
        if hasattr(canvas_widget, 'old_coords'):
            delattr(canvas_widget, 'old_coords')
        return
        
    # Handle right-click release for annotations
    if not annotation_mode or not is_drawing or event.button != 3:
        return
        
    if event.inaxes != ax:  # Ignore releases outside the axes
        if current_rect:
            current_rect.remove()
            canvas.draw()
        is_drawing = False
        current_rect = None
        rect_start = None
        return
        
    is_drawing = False
    if current_rect and rect_start:
        # Get annotation name from user using custom dialog
        name = get_annotation_name("Box Name", "Enter a name for this region:")
        if name is None or name.strip() == "":  # User cancelled or empty name
            current_rect.remove()
            canvas.draw()
            return
            
        width = event.xdata - rect_start[0]
        height = event.ydata - rect_start[1]
        
        # Find min and max temperatures in the region
        min_point, max_point = find_min_max_temps(rect_start[0], rect_start[1], width, height)
        
        # Calculate average temperature
        avg_temp = find_box_average_temp(rect_start[0], rect_start[1], width, height)
        
        if min_point and max_point:
            # Add circles for min and max temperatures with black borders
            min_circle = plt.Circle((min_point[0], min_point[1]), radius=2, color='blue', fill=True)
            min_circle.set_path_effects([plt_effects.withStroke(linewidth=1.5, foreground='black')])
            max_circle = plt.Circle((max_point[0], max_point[1]), radius=2, color='red', fill=True)
            max_circle.set_path_effects([plt_effects.withStroke(linewidth=1.5, foreground='black')])
            ax.add_patch(min_circle)
            ax.add_patch(max_circle)
            
            # Add temperature labels for min and max points with white text and black outline
            min_text = ax.text(min_point[0], min_point[1] - 10, f'Min: {min_point[2]:.1f}°C', 
                   color='white', fontsize=7, ha='center', fontweight='bold')
            min_text.set_path_effects([plt_effects.withStroke(linewidth=2, foreground='black')])
            
            max_text = ax.text(max_point[0], max_point[1] - 10, f'Max: {max_point[2]:.1f}°C', 
                   color='white', fontsize=7, ha='center', fontweight='bold')
            max_text.set_path_effects([plt_effects.withStroke(linewidth=2, foreground='black')])
        
        # Store annotation data
        annotation = {
            'name': name,
            'rect': current_rect,
            'coords': (rect_start[0], rect_start[1], width, height),
            'min_circle': min_circle if min_point else None,
            'max_circle': max_circle if max_point else None,
            'min_temp': min_point[2] if min_point else None,
            'max_temp': max_point[2] if max_point else None,
            'avg_temp': avg_temp
        }
        annotations.append(annotation)
        
        # Add name label
        name_text = ax.text(rect_start[0], rect_start[1] - 22, name.upper(),
                     color='white', fontsize=8, ha='center', fontweight='bold')
        name_text.set_path_effects([plt_effects.withStroke(linewidth=2, foreground='black')])
        
        # Add average temperature label
        if avg_temp is not None:
            temp_text = ax.text(rect_start[0], rect_start[1] - 15, f'Avg: {avg_temp:.1f}°C',
                         color='white', fontsize=7, ha='center', fontweight='bold')
            temp_text.set_path_effects([plt_effects.withStroke(linewidth=2, foreground='black')])
        
        canvas.draw()
        root.after(100, update_temperature_table)  # Update table after a short delay
    
    current_rect = None
    rect_start = None

def toggle_annotation_mode():
    global annotation_mode
    annotation_mode = not annotation_mode
    if annotation_mode:
        btn_annotate.config(text="✏️ Drawing Mode (ON)")
    else:
        btn_annotate.config(text="✏️ Drawing Mode (OFF)")

scroll_after_id = None
def on_scroll(event):
    global scroll_after_id
    def zoom():
        # Invert zoom direction (negative delta means zoom in now)
        scale = 0.9 if event.delta > 0 else 1.1
        xlim, ylim = ax.get_xlim(), ax.get_ylim()
        ax.set_xlim([x * scale for x in xlim])
        ax.set_ylim([y * scale for y in ylim])
        clamp_view()
        canvas.draw()
    if scroll_after_id:
        canvas_widget.after_cancel(scroll_after_id)
    scroll_after_id = canvas_widget.after(50, zoom)

def get_additional_exif_data(tiff_path):
    try:
        result = subprocess.run(["exiftool", tiff_path], capture_output=True, text=True)
        output = result.stdout
        
        # Extract additional EXIF data
        altitude_match = re.search(r"GPS Altitude\s+: (.+)", output)
        
        # Print the data
        print("\nAdditional EXIF Data:")
        print("-" * 40)
        if altitude_match:
            print(f"Altitude ASL: {altitude_match.group(1)}")
        print("-" * 40)

    except Exception as e:
        print(f"Error extracting additional EXIF data: {e}")

def process_thermal_image(tiff_path):
    global thermal_data, vmin_slider, vmax_slider
    
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=rasterio.errors.NotGeoreferencedWarning)
        with rasterio.open(tiff_path) as dataset:
            thermal_data = dataset.read(1)  # Read the first band
            min_val = thermal_data.min()
            max_val = thermal_data.max()

    gps_info = get_gps_position(tiff_path)
    date_info = get_date_taken(tiff_path)
    get_additional_exif_data(tiff_path)  # Add this line to get additional EXIF data
    print(f"Min Temp: {min_val:.2f} °C, Max Temp: {max_val:.2f} °C")

    # Set slider range based on minimum temperature
    slider_min = 0 if min_val < 0 else min_val
    vmin_slider.config(from_=slider_min, to=max_val)
    vmax_slider.config(from_=slider_min, to=max_val)
    
    # Set default values
    vmin_slider.set(slider_min)
    vmax_slider.set(max_val)
    update_image()
    reset_view()

def on_closing():
    root.quit()
    root.destroy()

def validate_temp_input(value, min_val, max_val, previous_val):
    try:
        temp = float(value)
        if min_val <= temp <= max_val:
            return temp
    except ValueError:
        pass
    return previous_val

def on_min_temp_click(event):
    current_val = vmin_slider.get()
    # Create a small entry window at the label's position
    entry = ttkb.Entry(control_panel, width=10)
    entry.insert(0, f"{current_val:.1f}")
    entry.select_range(0, 'end')
    
    # Calculate position for entry widget
    x = vmin_value_label.winfo_x()
    y = vmin_value_label.winfo_y()
    entry.place(x=x, y=y)
    
    def on_enter(event):
        new_val = validate_temp_input(entry.get(), vmin_slider.cget('from'), vmin_slider.cget('to'), current_val)
        vmin_slider.set(new_val)
        update_slider_label(new_val, "vmin")
        entry.destroy()
    
    def on_focus_out(event):
        new_val = validate_temp_input(entry.get(), vmin_slider.cget('from'), vmin_slider.cget('to'), current_val)
        vmin_slider.set(new_val)
        update_slider_label(new_val, "vmin")
        entry.destroy()
    
    entry.bind('<Return>', on_enter)
    entry.bind('<FocusOut>', on_focus_out)
    entry.focus_set()

def on_max_temp_click(event):
    current_val = vmax_slider.get()
    # Create a small entry window at the label's position
    entry = ttkb.Entry(control_panel, width=10)
    entry.insert(0, f"{current_val:.1f}")
    entry.select_range(0, 'end')
    
    # Calculate position for entry widget
    x = vmax_value_label.winfo_x()
    y = vmax_value_label.winfo_y()
    entry.place(x=x, y=y)
    
    def on_enter(event):
        new_val = validate_temp_input(entry.get(), vmax_slider.cget('from'), vmax_slider.cget('to'), current_val)
        vmax_slider.set(new_val)
        update_slider_label(new_val, "vmax")
        entry.destroy()
    
    def on_focus_out(event):
        new_val = validate_temp_input(entry.get(), vmax_slider.cget('from'), vmax_slider.cget('to'), current_val)
        vmax_slider.set(new_val)
        update_slider_label(new_val, "vmax")
        entry.destroy()
    
    entry.bind('<Return>', on_enter)
    entry.bind('<FocusOut>', on_focus_out)
    entry.focus_set()

def update_slider_label(val, slider_type):
    try:
        val = float(val)
        if slider_type == "vmin":
            vmin_value_label.config(text=f"{val:.1f} °C")
        elif slider_type == "vmax":
            vmax_value_label.config(text=f"{val:.1f} °C")
        update_image()
    except ValueError:
        pass  # Ignore invalid values

def update_temperature_table():
    # Clear existing table
    for widget in table_frame.winfo_children():
        widget.destroy()
    
    # Create header
    header = ttkb.Label(table_frame, text="Temperature Values", font=("Arial", 10, "bold"))
    header.pack(pady=(0, 5))
    
    # Add point temperatures
    for i, point in enumerate(point_annotations, 1):
        point_frame = ttkb.Frame(table_frame)
        point_frame.pack(fill=tk.X, pady=2)
        
        # Point name
        name_label = ttkb.Label(point_frame, text=f"P{i}", width=5, font=("Arial", 9))
        name_label.pack(side=tk.LEFT, padx=(0, 5))
        
        # Value label
        value_label = ttkb.Label(point_frame, text="VALUE", width=8, font=("Arial", 9))
        value_label.pack(side=tk.LEFT, padx=(0, 5))
        
        # Temperature value
        temp_label = ttkb.Label(point_frame, text=f"{point['temp']:.1f}℃", width=8, font=("Arial", 9))
        temp_label.pack(side=tk.LEFT)
    
    # Add box temperatures
    for i, box in enumerate(annotations, 1):
        box_frame = ttkb.Frame(table_frame)
        box_frame.pack(fill=tk.X, pady=2)
        
        # Box name
        name_label = ttkb.Label(box_frame, text=f"B{i}", width=5, font=("Arial", 9))
        name_label.pack(side=tk.LEFT, padx=(0, 5))
        
        # Min temperature
        min_frame = ttkb.Frame(box_frame)
        min_frame.pack(fill=tk.X, pady=1)
        min_label = ttkb.Label(min_frame, text="MIN", width=8, font=("Arial", 9))
        min_label.pack(side=tk.LEFT, padx=(0, 5))
        min_temp = ttkb.Label(min_frame, text=f"{box['min_temp']:.1f}℃", width=8, font=("Arial", 9))
        min_temp.pack(side=tk.LEFT)
        
        # Average temperature
        avg_frame = ttkb.Frame(box_frame)
        avg_frame.pack(fill=tk.X, pady=1)
        avg_label = ttkb.Label(avg_frame, text="AVERAGE", width=8, font=("Arial", 9))
        avg_label.pack(side=tk.LEFT, padx=(0, 5))
        avg_temp = ttkb.Label(avg_frame, text=f"{box['avg_temp']:.1f}℃", width=8, font=("Arial", 9))
        avg_temp.pack(side=tk.LEFT)
        
        # Max temperature
        max_frame = ttkb.Frame(box_frame)
        max_frame.pack(fill=tk.X, pady=1)
        max_label = ttkb.Label(max_frame, text="MAX", width=8, font=("Arial", 9))
        max_label.pack(side=tk.LEFT, padx=(0, 5))
        max_temp = ttkb.Label(max_frame, text=f"{box['max_temp']:.1f}℃", width=8, font=("Arial", 9))
        max_temp.pack(side=tk.LEFT)
    
    # Force update of the table frame
    table_frame.update_idletasks()

def clear_annotations():
    global annotations
    # Remove all box annotation rectangles, circles, and text from the plot
    for annotation in annotations:
        # Remove rectangle
        if annotation['rect']:
            annotation['rect'].remove()
        # Remove min/max circles if they exist
        if annotation.get('min_circle'):
            annotation['min_circle'].remove()
        if annotation.get('max_circle'):
            annotation['max_circle'].remove()
    
    # Clear all text annotations that belong to boxes
    texts_to_remove = []
    for text in ax.texts:
        # Check if the text is part of a box annotation
        for annotation in annotations:
            if text.get_text().startswith(annotation['name'].upper()) or text.get_text().startswith('Min:') or text.get_text().startswith('Max:') or text.get_text().startswith('Avg:'):
                texts_to_remove.append(text)
                break
    
    # Remove the collected texts
    for text in texts_to_remove:
        text.remove()
    
    # Clear the box annotations list
    annotations = []
    canvas.draw()
    root.after(100, update_temperature_table)  # Update table after a short delay

def on_window_resize(event=None):
    global canvas_widget
    if event and event.widget == root:
        # Get the new size of the frame
        width = frame.winfo_width()
        height = frame.winfo_height()
        
        if width > 1 and height > 1 and canvas_widget is not None:  # Check if canvas exists
            # Update the figure size to match the new frame size
            fig.set_size_inches(width/fig.dpi, height/fig.dpi)
            canvas.draw()

def copy_to_clipboard():
    try:
        gps_value = gps_text.get("1.0", tk.END).strip()
        date_value = date_text.get("1.0", tk.END).strip()
        # Format for Google Sheets column
        clipboard_text = f"{gps_value}\n{date_value}"
        root.clipboard_clear()
        root.clipboard_append(clipboard_text)
    except Exception as e:
        print(f"Error copying values: {e}")

def export_current_view():
    try:
        # Get the current view's limits
        xlim = ax.get_xlim()
        ylim = ax.get_ylim()
        
        # Create a new figure with the same size as the current view
        export_fig = plt.figure(figsize=(fig.get_size_inches()))
        export_ax = export_fig.add_subplot(111)
        
        # Copy the current image data
        export_ax.imshow(img_display.get_array(), cmap=img_display.get_cmap(), 
                        vmin=img_display.get_clim()[0], vmax=img_display.get_clim()[1])
        
        # Copy all box annotations
        for annotation in annotations:
            # Copy rectangle
            rect = annotation['rect']
            new_rect = Rectangle(rect.get_xy(), rect.get_width(), rect.get_height(),
                               fill=False, edgecolor='white', linewidth=1)
            new_rect.set_path_effects([plt_effects.withStroke(linewidth=2, foreground='black')])
            export_ax.add_patch(new_rect)
            
            # Copy min/max circles if they exist
            if annotation.get('min_circle'):
                min_circle = annotation['min_circle']
                new_min_circle = plt.Circle(min_circle.center, min_circle.radius,
                                          color='blue', fill=True)
                new_min_circle.set_path_effects([plt_effects.withStroke(linewidth=1.5, foreground='black')])
                export_ax.add_patch(new_min_circle)
                
                # Copy min temperature label
                min_text = export_ax.text(min_circle.center[0], min_circle.center[1] - 10,
                                        f'Min: {annotation["min_temp"]:.1f}°C',
                                        color='white', fontsize=7, ha='center', fontweight='bold')
                min_text.set_path_effects([plt_effects.withStroke(linewidth=2, foreground='black')])
            
            if annotation.get('max_circle'):
                max_circle = annotation['max_circle']
                new_max_circle = plt.Circle(max_circle.center, max_circle.radius,
                                          color='red', fill=True)
                new_max_circle.set_path_effects([plt_effects.withStroke(linewidth=1.5, foreground='black')])
                export_ax.add_patch(new_max_circle)
                
                # Copy max temperature label
                max_text = export_ax.text(max_circle.center[0], max_circle.center[1] - 10,
                                        f'Max: {annotation["max_temp"]:.1f}°C',
                                        color='white', fontsize=7, ha='center', fontweight='bold')
                max_text.set_path_effects([plt_effects.withStroke(linewidth=2, foreground='black')])
            
            # Copy name label
            name_text = export_ax.text(rect.get_xy()[0], rect.get_xy()[1] - 22,
                                     annotation['name'].upper(),
                                     color='white', fontsize=8, ha='center', fontweight='bold')
            name_text.set_path_effects([plt_effects.withStroke(linewidth=2, foreground='black')])
            
            # Copy average temperature label
            if annotation['avg_temp'] is not None:
                avg_text = export_ax.text(rect.get_xy()[0], rect.get_xy()[1] - 15,
                                        f'Avg: {annotation["avg_temp"]:.1f}°C',
                                        color='white', fontsize=7, ha='center', fontweight='bold')
                avg_text.set_path_effects([plt_effects.withStroke(linewidth=2, foreground='black')])
        
        # Copy all point annotations as crosshair/circle with gap at center
        for point_annotation in point_annotations:
            x, y = point_annotation['coords']
            # Draw transparent circle
            circle = plt.Circle((x, y), radius=3, edgecolor='white', facecolor='none', linewidth=1, zorder=10)
            circle.set_path_effects([plt_effects.withStroke(linewidth=2, foreground='black')])
            export_ax.add_patch(circle)
            # Draw crosshair lines with gap at center
            line_length = 7
            gap = 5
            h_line_left = export_ax.plot([x - line_length, x - gap], [y, y], color='white', linewidth=1, zorder=11)[0]
            h_line_left.set_path_effects([plt_effects.withStroke(linewidth=2, foreground='black')])
            h_line_right = export_ax.plot([x + gap, x + line_length], [y, y], color='white', linewidth=1, zorder=11)[0]
            h_line_right.set_path_effects([plt_effects.withStroke(linewidth=2, foreground='black')])
            v_line_top = export_ax.plot([x, x], [y - line_length, y - gap], color='white', linewidth=1, zorder=11)[0]
            v_line_top.set_path_effects([plt_effects.withStroke(linewidth=2, foreground='black')])
            v_line_bottom = export_ax.plot([x, x], [y + gap, y + line_length], color='white', linewidth=1, zorder=11)[0]
            v_line_bottom.set_path_effects([plt_effects.withStroke(linewidth=2, foreground='black')])
            # Copy temperature text
            temp_text = point_annotation['temp_text']
            new_temp_text = export_ax.text(x, y - 12,
                                         temp_text.get_text(), color='white', fontsize=7,
                                         ha='center', fontweight='bold')
            new_temp_text.set_path_effects([plt_effects.withStroke(linewidth=2, foreground='black')])
            # Copy name text
            name_text = point_annotation['name_text']
            new_name_text = export_ax.text(x, y - 20,
                                         name_text.get_text(), color='white', fontsize=8,
                                         ha='center', fontweight='bold')
            new_name_text.set_path_effects([plt_effects.withStroke(linewidth=2, foreground='black')])
        
        # Set the same view limits
        export_ax.set_xlim(xlim)
        export_ax.set_ylim(ylim)
        export_ax.axis('off')
        
        # Get the current file name and create export name
        current_file = file_label.cget("text").split(": ")[-1]
        export_name = f"export_{current_file.rsplit('.', 1)[0]}.png"
        
        # Set export path
        export_path = r"C:\Users\Kunnop.ko\Desktop\Thermal\M3T\Export PNG"
        
        # Create directory if it doesn't exist
        os.makedirs(export_path, exist_ok=True)
        
        # Full path for the export file
        full_export_path = os.path.join(export_path, export_name)
        
        # Save the figure
        export_fig.savefig(full_export_path, bbox_inches='tight', dpi=300)
        plt.close(export_fig)
        
        # Show success message
        tk.messagebox.showinfo("Export Successful", f"Image exported as {export_name}")
        
    except Exception as e:
        tk.messagebox.showerror("Export Error", f"Failed to export image: {str(e)}")

def toggle_point_annotation_mode():
    global point_annotation_mode, annotation_mode
    point_annotation_mode = not point_annotation_mode
    if point_annotation_mode:
        btn_point_annotate.config(text="📍 Point Mode (ON)")
        annotation_mode = False  # Turn off box annotation mode
        btn_annotate.config(text="✏️ Drawing Mode (OFF)")
    else:
        btn_point_annotate.config(text="📍 Point Mode (OFF)")

def get_annotation_name(title, prompt):
    # Create a custom dialog window
    dialog = ttkb.Toplevel(root)
    dialog.title(title)
    dialog.geometry("300x120")
    dialog.transient(root)  # Make dialog stay on top of main window
    dialog.grab_set()  # Make dialog modal
    
    # Center the dialog on the main window
    dialog.update_idletasks()
    x = root.winfo_x() + (root.winfo_width() - dialog.winfo_width()) // 2
    y = root.winfo_y() + (root.winfo_height() - dialog.winfo_height()) // 2
    dialog.geometry(f"+{x}+{y}")
    
    # Create and pack widgets
    frame = ttkb.Frame(dialog, padding=20)
    frame.pack(fill=tk.BOTH, expand=True)
    
    label = ttkb.Label(frame, text=prompt, font=("Arial", 10))
    label.pack(pady=(0, 10))
    
    entry = ttkb.Entry(frame, width=30, font=("Arial", 10))
    entry.pack(pady=(0, 10))
    entry.focus_set()
    
    result = [None]  # Use list to store result
    
    def on_ok():
        result[0] = entry.get()
        dialog.destroy()
    
    def on_cancel():
        dialog.destroy()
    
    # Create button frame
    button_frame = ttkb.Frame(frame)
    button_frame.pack(fill=tk.X, pady=(10, 0))
    
    # Add OK and Cancel buttons
    ok_button = ttkb.Button(button_frame, text="OK", command=on_ok, width=10)
    ok_button.pack(side=tk.LEFT, padx=(0, 5))
    
    cancel_button = ttkb.Button(button_frame, text="Cancel", command=on_cancel, width=10)
    cancel_button.pack(side=tk.LEFT)
    
    # Bind Enter key to OK button
    entry.bind('<Return>', lambda e: on_ok())
    # Bind Escape key to Cancel
    dialog.bind('<Escape>', lambda e: on_cancel())
    
    # Wait for the dialog to be destroyed
    dialog.wait_window()
    return result[0]

def add_point_annotation(x, y):
    global point_annotations
    if 0 <= x < thermal_data.shape[1] and 0 <= y < thermal_data.shape[0]:
        temp = thermal_data[int(y), int(x)]
        # Get point name from user using custom dialog
        name = get_annotation_name("Point Name", "Enter a name for this point:")
        if name is None or name.strip() == "":  # User cancelled or empty name
            return
        
        # Draw crosshair-style point marker with larger gap at center
        circle = plt.Circle((x, y), radius=3, edgecolor='white', facecolor='none', linewidth=1, zorder=10)
        circle.set_path_effects([plt_effects.withStroke(linewidth=2, foreground='black')])
        ax.add_patch(circle)
        
        line_length = 7
        gap = 5  # Larger gap for bigger hole
        # Horizontal left
        h_line_left = ax.plot([x - line_length, x - gap], [y, y], color='white', linewidth=1, zorder=11)[0]
        h_line_left.set_path_effects([plt_effects.withStroke(linewidth=2, foreground='black')])
        # Horizontal right
        h_line_right = ax.plot([x + gap, x + line_length], [y, y], color='white', linewidth=1, zorder=11)[0]
        h_line_right.set_path_effects([plt_effects.withStroke(linewidth=2, foreground='black')])
        # Vertical top
        v_line_top = ax.plot([x, x], [y - line_length, y - gap], color='white', linewidth=1, zorder=11)[0]
        v_line_top.set_path_effects([plt_effects.withStroke(linewidth=2, foreground='black')])
        # Vertical bottom
        v_line_bottom = ax.plot([x, x], [y + gap, y + line_length], color='white', linewidth=1, zorder=11)[0]
        v_line_bottom.set_path_effects([plt_effects.withStroke(linewidth=2, foreground='black')])
        
        # Add temperature label
        temp_text = ax.text(x, y - 12, f'{temp:.1f}°C', 
                      color='white', fontsize=7, ha='center', fontweight='bold')
        temp_text.set_path_effects([plt_effects.withStroke(linewidth=2, foreground='black')])
        
        # Add name label
        name_text = ax.text(x, y - 20, name.upper(),
                      color='white', fontsize=8, ha='center', fontweight='bold')
        name_text.set_path_effects([plt_effects.withStroke(linewidth=2, foreground='black')])
        
        # Store annotation
        point_annotations.append({
            'circle': circle,
            'h_line_left': h_line_left,
            'h_line_right': h_line_right,
            'v_line_top': v_line_top,
            'v_line_bottom': v_line_bottom,
            'temp_text': temp_text,
            'name_text': name_text,
            'coords': (x, y),
            'temp': temp,
            'name': name
        })
        canvas.draw()
        root.after(100, update_temperature_table)  # Update table after a short delay

def clear_point_annotations():
    global point_annotations
    # Remove all point annotations
    for point_annotation in point_annotations:
        if point_annotation.get('circle'):
            point_annotation['circle'].remove()
        if point_annotation.get('h_line_left'):
            point_annotation['h_line_left'].remove()
        if point_annotation.get('h_line_right'):
            point_annotation['h_line_right'].remove()
        if point_annotation.get('v_line_top'):
            point_annotation['v_line_top'].remove()
        if point_annotation.get('v_line_bottom'):
            point_annotation['v_line_bottom'].remove()
        if point_annotation.get('temp_text'):
            point_annotation['temp_text'].remove()
        if point_annotation.get('name_text'):
            point_annotation['name_text'].remove()
    
    # Clear the point annotations list
    point_annotations = []
    canvas.draw()
    root.after(100, update_temperature_table)  # Update table after a short delay

def copy_temperature_data():
    try:
        clipboard_text = ""
        
        # Add point temperatures
        for i, point in enumerate(point_annotations, 1):
            clipboard_text += f"P{i}\tVALUE\t{point['temp']:.1f}\t\t\t\t\n"
        
        # Add box temperatures
        for i, box in enumerate(annotations, 1):
            clipboard_text += f"B{i}\tMIN\t{box['min_temp']:.1f}\t\t\t\t\n"
            clipboard_text += f"B{i}\tAVERAGE\t{box['avg_temp']:.1f}\t\t\t\t\n"
            clipboard_text += f"B{i}\tMAX\t{box['max_temp']:.1f}\t\t\t\t\n"
        
        # Copy to clipboard
        root.clipboard_clear()
        root.clipboard_append(clipboard_text)
        
        # Show success message
        tk.messagebox.showinfo("Success", "Temperature data copied to clipboard!")
        
    except Exception as e:
        tk.messagebox.showerror("Error", f"Failed to copy data: {str(e)}")

def clamp_view():
    # Clamp the axes limits to the image bounds
    xlim = list(ax.get_xlim())
    ylim = list(ax.get_ylim())
    width = thermal_data.shape[1]
    height = thermal_data.shape[0]

    # Clamp x
    xlim[0] = max(0, min(xlim[0], width))
    xlim[1] = max(0, min(xlim[1], width))
    # Clamp y
    ylim[0] = max(0, min(ylim[0], height))
    ylim[1] = max(0, min(ylim[1], height))

    ax.set_xlim(xlim)
    ax.set_ylim(ylim)

# Create Tkinter window
root = tk.Tk()
root.title("R-Tiff Viewer by KNP")
root.geometry("1300x900")  # Set initial window size
root.protocol("WM_DELETE_WINDOW", on_closing) 

# Create main container with grid
main_container = tk.Frame(root)
main_container.pack(fill=tk.BOTH, expand=True)

# Top frame for buttons and labels
top_frame = tk.Frame(main_container)
top_frame.pack(fill=tk.X, padx=10, pady=5)

btn_open = ttkb.Button(top_frame, text="Open Thermal Image", command=open_file)
btn_open.pack(side=tk.LEFT, padx=5)

file_label = ttkb.Label(top_frame, text="📁 File: No file selected", font=("Arial", 12, "italic"))
file_label.pack(side=tk.LEFT, padx=5)

# Replace GPS label with Text widget
gps_frame = tk.Frame(top_frame)
gps_frame.pack(side=tk.LEFT, padx=5)
gps_text = tk.Text(gps_frame, height=1, width=25, font=("Arial", 12))
gps_text.pack(side=tk.LEFT)
gps_text.insert("1.0", "GPS: Not Available")
gps_text.config(state='disabled')

# Date frame
date_frame = tk.Frame(top_frame)
date_frame.pack(side=tk.LEFT, padx=5)
date_text = tk.Text(date_frame, height=1, width=20, font=("Arial", 12))
date_text.pack(side=tk.LEFT)
date_text.insert("1.0", "Date: Not Available")
date_text.config(state='disabled')

# Single copy button for both values
copy_btn = ttkb.Button(top_frame, text="📋", width=3, command=copy_to_clipboard)
copy_btn.pack(side=tk.LEFT, padx=5)

hover_label = ttkb.Label(top_frame, text="🎯 Temp: Move cursor over image", font=("Arial", 12))
hover_label.pack(side=tk.LEFT, padx=5)

#temp_label = ttkb.Label(top_frame, text="Temperature: Click on image", font=("Arial", 12))
#temp_label.pack(side=tk.LEFT, padx=5)

# Main content area with image and control panel
content_frame = tk.Frame(main_container)
content_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

# Image frame (left side)
frame = tk.Frame(content_frame)
frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

# Control panel (right side)
control_panel = ttkb.Frame(content_frame, padding=10)
control_panel.pack(side=tk.RIGHT, fill=tk.Y, padx=(10, 0))

style = ttkb.Style()

# 🎨 Custom Style for Min Temp Slider (Blue)
style.configure("Blue.Horizontal.TScale",
                troughcolor="#FF4C4C",  # Light Blue Background
                sliderthickness=12, 
                background="#D0E8FF")

# Create sliders for adjusting vmin and vmax
ttkb.Label(control_panel, text="Min Temp", font=("Arial", 10)).pack(anchor="w", pady=(5, 0))
vmin_slider = ttkb.Scale(control_panel, from_=0, to=100, length=200, orient='horizontal',
                         command=lambda val: update_slider_label(val, "vmin"), style='Blue.Horizontal.TScale')
vmin_slider.pack()
vmin_value_label = ttkb.Label(control_panel, text="0.0 °C", font=("Arial", 10))
vmin_value_label.pack(anchor="e")
vmin_value_label.bind('<Button-1>', on_min_temp_click)

ttkb.Label(control_panel, text="Max Temp", font=("Arial", 10)).pack(anchor="w", pady=(10, 0))
vmax_slider = ttkb.Scale(control_panel, from_=0, to=100, length=200, orient='horizontal',
                         command=lambda val: update_slider_label(val, "vmax"), style='Blue.Horizontal.TScale')
vmax_slider.pack()
vmax_value_label = ttkb.Label(control_panel, text="100.0 °C", font=("Arial", 10))
vmax_value_label.pack(anchor="e")
vmax_value_label.bind('<Button-1>', on_max_temp_click)

cmap_frame = tk.Frame(root)
cmap_frame.pack(pady=10)

cmap_var = tk.StringVar(value='inferno')
cmap_options = ['inferno', 'jet', 'hot', 'gray', 'viridis', 'plasma', 'magma', 'cividis', 'nipy_spectral', 'turbo', 'prism']

# Create colormap selection dropdown
ttkb.Label(control_panel, text="Colormap", font=("Arial", 10)).pack(anchor="w", pady=(15, 0))
cmap_dropdown = ttkb.Combobox(control_panel, textvariable=cmap_var,
                              values=cmap_options, state='readonly')
cmap_dropdown.pack(fill="x")
cmap_dropdown.bind("<<ComboboxSelected>>", update_image)

# Reset Button
btn_reset = ttkb.Button(control_panel, text="Reset View", command=reset_view)
btn_reset.pack(pady=15)

# Clear annotations button
btn_clear = ttkb.Button(control_panel, text="🗑️ Clear Boxs", command=clear_annotations)
btn_clear.pack(pady=5)

# Annotation Button
btn_annotate = ttkb.Button(control_panel, text="✏️ Drawing Mode (OFF)", command=toggle_annotation_mode)
btn_annotate.pack(pady=15)

# Export button
btn_export = ttkb.Button(control_panel, text="💾 Export View", command=export_current_view)
btn_export.pack(pady=5)

# Point annotation button
btn_point_annotate = ttkb.Button(control_panel, text="📍 Point Mode (OFF)", command=toggle_point_annotation_mode)
btn_point_annotate.pack(pady=5)

# Clear points button
btn_clear_points = ttkb.Button(control_panel, text="🗑️ Clear Points", command=clear_point_annotations)
btn_clear_points.pack(pady=5)

# Add this after creating the control panel
table_frame = ttkb.Frame(control_panel)
table_frame.pack(fill=tk.X, pady=10)

# Add copy button for temperature data
btn_copy_temp = ttkb.Button(control_panel, text="📋 Copy Temperature Data", command=copy_temperature_data)
btn_copy_temp.pack(pady=5)

# Run the application
root.mainloop()