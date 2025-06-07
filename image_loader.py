import os
from pathlib import Path
from PyQt6.QtGui import QPixmap
from PyQt6.QtCore import QSize
from PIL import Image

class ImageLoader:
    SUPPORTED_FORMATS = {'.jpg', '.jpeg', '.png', '.tiff', '.tif', '.bmp'}
    PREVIEW_MAX_SIZE = (800, 600)
    
    def __init__(self, folder_path):
        self.folder_path = folder_path
        self.image_files = []
        self.preview_cache = {}
        self.original_sizes = {}
        
        self._scan_folder()
        
    def _scan_folder(self):
        """Scan folder for supported image files"""
        folder = Path(self.folder_path)
        
        for file_path in sorted(folder.iterdir()):
            if file_path.is_file() and file_path.suffix.lower() in self.SUPPORTED_FORMATS:
                relative_path = file_path.name
                self.image_files.append(relative_path)
                
                # Store original image size
                try:
                    with Image.open(file_path) as img:
                        self.original_sizes[relative_path] = img.size
                except Exception as e:
                    print(f"Error reading {file_path}: {e}")
                    
    def get_preview(self, filename):
        """Get preview pixmap for an image file"""
        if filename in self.preview_cache:
            return self.preview_cache[filename]
            
        file_path = os.path.join(self.folder_path, filename)
        
        try:
            # Load image with PIL for better format support
            with Image.open(file_path) as img:
                # Handle different image modes properly
                original_mode = img.mode
                
                # For TIFF files and other complex formats, ensure proper conversion
                if original_mode in ('CMYK', 'LAB', 'YCbCr'):
                    img = img.convert('RGB')
                elif original_mode in ('L', 'P'):
                    img = img.convert('RGB')  # Convert grayscale and palette to RGB
                elif original_mode == '1':
                    img = img.convert('RGB')  # Convert 1-bit to RGB
                elif original_mode not in ('RGB', 'RGBA'):
                    img = img.convert('RGB')  # Fallback conversion
                
                # Create preview maintaining aspect ratio
                img.thumbnail(self.PREVIEW_MAX_SIZE, Image.Resampling.LANCZOS)
                
                # Convert PIL image to QPixmap using a more reliable method
                # Save to temporary format and load with Qt
                import io
                buffer = io.BytesIO()
                
                # Always save as PNG for reliable Qt loading
                if img.mode == 'RGBA':
                    img.save(buffer, format='PNG')
                else:
                    # Ensure RGB mode for JPEG
                    if img.mode != 'RGB':
                        img = img.convert('RGB')
                    img.save(buffer, format='JPEG', quality=95)
                
                buffer.seek(0)
                
                # Load with QPixmap
                pixmap = QPixmap()
                if pixmap.loadFromData(buffer.getvalue()):
                    self.preview_cache[filename] = pixmap
                    return pixmap
                else:
                    print(f"Failed to load pixmap data for {filename}")
                    
        except Exception as e:
            print(f"Error loading preview for {filename}: {e}")
            import traceback
            traceback.print_exc()
            
        return None
        
    def get_original_size(self, filename):
        """Get original dimensions of an image"""
        return self.original_sizes.get(filename, (0, 0))
        
    def get_scale_factor(self, filename, preview_size):
        """Calculate scale factor from preview to original"""
        original_size = self.get_original_size(filename)
        if original_size[0] == 0 or original_size[1] == 0:
            return 1.0, 1.0
            
        scale_x = original_size[0] / preview_size.width()
        scale_y = original_size[1] / preview_size.height()
        
        return scale_x, scale_y