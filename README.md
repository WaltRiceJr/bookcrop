# BookCrop - Book Scan Image Processor

A desktop GUI application for processing book scan images with precise cropping capabilities. Designed specifically for book digitization workflows where covers are single pages and interior pages are double-page spreads.

## Key Features

- **Per-Image Mode Control**: Each image can be individually set to single page or double page mode
- **Sequential Processing**: Mode and position changes apply to current page and all subsequent unprocessed pages
- **Precise Crop Dimensions**: User-defined pixel dimensions ensure consistent output sizes across all images
- **Smart Coordinate System**: Crop boxes work in original image coordinates while displaying scaled on previews
- **Boundary-Free Cropping**: Crop boxes can extend beyond image borders with white padding in exports
- **Drag & Drop Interface**: Simply drop a folder of images to start processing
- **Interactive Crop Boxes**: 
  - Visual crop box overlays with drag and resize functionality
  - Handle-based resizing updates global dimensions in real-time
  - Precise positioning for optimal page alignment
- **Preview System**: Fast loading with lower-resolution previews for quick navigation
- **Persistent Settings**: Complete project state saved automatically and can be reloaded
- **Unified Export**: All cropped images exported to a single output folder

## Requirements

- Python 3.8+
- PyQt6
- Pillow (PIL)

## Installation

1. Clone or download the project

2. Create and activate a virtual environment:
   ```bash
   # Create virtual environment
   python -m venv venv
   
   # Activate virtual environment
   # On macOS/Linux:
   source venv/bin/activate
   
   # On Windows:
   venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

1. Make sure your virtual environment is activated:
   ```bash
   # On macOS/Linux:
   source venv/bin/activate
   
   # On Windows:
   venv\Scripts\activate
   ```

2. Run the application:
   ```bash
   python main.py
   ```

3. **Load Images**: 
   - Drag and drop a folder containing image files, or
   - Use "Open Folder" button to select a folder

4. **Set Crop Dimensions**: 
   - Enter desired width and height in pixels for consistent output size
   - All exported images will be exactly these dimensions

5. **Configure Per-Image Mode**:
   - **Single Page**: For covers and individual page scans
   - **Double Page**: For book spread scans (creates left/right crop boxes)
   - Mode changes apply to current image and all subsequent unprocessed images

6. **Adjust Crop Boxes**:
   - Drag boxes to reposition anywhere (can extend beyond image borders)
   - Drag corner handles to resize (updates global dimensions)
   - In double page mode, boxes stay aligned vertically and maintain same dimensions
   - Position changes apply to subsequent unprocessed pages

7. **Navigate**: Use Previous/Next buttons to move between images
   - UI automatically shows the correct mode for each image
   - Crop boxes display at proper scale relative to original image

8. **Save Settings**: Click "Save Crops" to preserve complete project state

9. **Export**: Click "Export Cropped Images" to generate final cropped images

## Typical Book Scanning Workflow

1. Load all scanned images (cover, interior pages, back cover)
2. **First image (front cover)**: Set to Single Page mode
3. **Second image (first spread)**: Set to Double Page mode  
4. Continue through interior pages (inherit Double Page mode)
5. **Last image (back cover)**: Set to Single Page mode
6. Adjust crop positions as needed - changes apply to subsequent pages
7. Export all images

## Output Structure

All exported images are saved to a single output folder:
- Single page images: `original_filename.jpg`
- Double page images: `original_filename_left.jpg` and `original_filename_right.jpg`

## Supported Formats

- JPEG (.jpg, .jpeg)
- PNG (.png)
- TIFF (.tiff, .tif)
- BMP (.bmp)

## Creating Windows Executable

To compile this application into a standalone Windows executable:

1. Install PyInstaller:
   ```bash
   pip install pyinstaller
   ```

2. Create executable:
   ```bash
   pyinstaller --onefile --windowed main.py
   ```

3. Add icon (optional):
   ```bash
   pyinstaller --onefile --windowed --icon=icon.ico main.py
   ```

The `--windowed` flag prevents console window from appearing. Output will be in `dist/` folder.

## Advanced Features

### Per-Image Mode System
- Each image stores its own single/double page mode
- Mode changes propagate only to subsequent unprocessed images
- Perfect for mixed content (covers + spreads)

### Intelligent Sequential Processing
- Adjusting position/mode on page N applies to pages N+1, N+2, etc.
- Only affects pages that haven't been manually adjusted
- Tracks which pages have been customized by the user

### Precise Dimension Control
- User-defined pixel dimensions (width/height input boxes)
- All exported images are exactly the specified size
- Resizing crop boxes updates global dimensions in real-time

### Smart Coordinate System
- Crop boxes stored in original image coordinates
- Preview display automatically scales for different image sizes
- Maintains accuracy regardless of preview zoom level

### Boundary-Free Cropping
- Crop boxes can extend beyond image edges
- Out-of-bounds areas filled with white pixels in exports
- Useful for consistent framing across variable scan sizes

### Complete State Persistence
- Saves crop dimensions, per-image modes, positions, and processing state
- `crop_data.json` in source folder contains complete project
- Automatic loading when reopening the same folder

### Enhanced Double Page Mode
- Two crop boxes maintain synchronized dimensions
- Vertical alignment enforced automatically
- Left/right boxes can be positioned independently horizontally
- Ideal for book spine variations and binding irregularities