# Thermal Image Viewer

## Overview
For image that has been converted to TIFF from RJPG of a DJI drone.
**Thermal Image Viewer** is a Python application that allows users to visualize **thermal TIFF images**. The application provides real-time temperature readings at selected pixels, enables **zooming and panning**, and includes adjustable **color maps** and **temperature scaling**. The program also extracts **GPS position** from image metadata using `ExifTool`.

## Features
- **Load Thermal TIFF Images**
- **Right-click to Display Temperature** at selected pixels
- **Zoom & Pan Support**
- **Adjustable Color Maps** (Inferno, Jet, Gray, Viridis, etc.)
- **Min/Max Temperature Adjustment** via Sliders
- **Extracts GPS Position** from image metadata
- **Reset View Button** to restore the original zoom & pan state

## Requirements
Ensure the following Python libraries are installed:
```
pip install rasterio numpy matplotlib tk exiftool ttkbootstrap
```
## Author
Develop by Kunnop
