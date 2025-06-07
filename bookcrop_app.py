import os
import json
from pathlib import Path
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                            QPushButton, QLabel, QButtonGroup, QRadioButton,
                            QFileDialog, QMessageBox, QScrollArea, QFrame,
                            QSpinBox, QGroupBox)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QDragEnterEvent, QDropEvent, QPixmap

from image_viewer import ScaledImageViewer
from image_loader import ImageLoader

class BookCropApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.image_loader = None
        self.current_image_index = 0
        self.crop_data = {}
        self.folder_path = None
        
        # Global crop settings
        self.crop_width = 800
        self.crop_height = 1200
        
        # Track which pages have been manually adjusted by user
        self.manually_adjusted_pages = set()
        
        # Flag to prevent dimension updates during handle resizing
        self.updating_dimensions_from_resize = False
        
        # Per-image mode storage - tracks which images use double page mode
        self.image_modes = {}  # filename -> bool (True for double page)
        
        # Master crop box positions (in original image coordinates) for both modes
        # These are used as templates for pages that haven't been manually adjusted
        self.master_single_position = {'x': 0, 'y': 0}  # Relative to image center
        self.master_left_position = {'x': 0, 'y': 0}    # Relative to 1/4 point
        self.master_right_position = {'x': 0, 'y': 0}   # Relative to 3/4 point
        
        self.init_ui()
        
    def init_ui(self):
        self.setWindowTitle("BookCrop - Scan Image Processor")
        self.setGeometry(100, 100, 1200, 800)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout(central_widget)
        
        # Top controls
        controls_layout = QHBoxLayout()
        
        # Crop dimensions input
        crop_dims_group = QGroupBox("Crop Dimensions (pixels)")
        crop_dims_layout = QHBoxLayout(crop_dims_group)
        
        crop_dims_layout.addWidget(QLabel("Width:"))
        self.width_spinbox = QSpinBox()
        self.width_spinbox.setRange(100, 5000)
        self.width_spinbox.setValue(self.crop_width)
        self.width_spinbox.valueChanged.connect(self.on_crop_dimensions_changed)
        crop_dims_layout.addWidget(self.width_spinbox)
        
        crop_dims_layout.addWidget(QLabel("Height:"))
        self.height_spinbox = QSpinBox()
        self.height_spinbox.setRange(100, 5000)
        self.height_spinbox.setValue(self.crop_height)
        self.height_spinbox.valueChanged.connect(self.on_crop_dimensions_changed)
        crop_dims_layout.addWidget(self.height_spinbox)
        
        controls_layout.addWidget(crop_dims_group)
        
        # Mode selection
        mode_group = QButtonGroup(self)
        self.single_page_radio = QRadioButton("Single Page")
        self.double_page_radio = QRadioButton("Double Page")
        self.single_page_radio.setChecked(True)
        
        mode_group.addButton(self.single_page_radio)
        mode_group.addButton(self.double_page_radio)
        
        self.single_page_radio.toggled.connect(self.on_mode_changed)
        
        controls_layout.addWidget(QLabel("Mode:"))
        controls_layout.addWidget(self.single_page_radio)
        controls_layout.addWidget(self.double_page_radio)
        controls_layout.addStretch()
        
        # Navigation buttons
        self.prev_button = QPushButton("Previous")
        self.next_button = QPushButton("Next")
        self.prev_button.clicked.connect(self.prev_image)
        self.next_button.clicked.connect(self.next_image)
        self.prev_button.setEnabled(False)
        self.next_button.setEnabled(False)
        
        controls_layout.addWidget(self.prev_button)
        controls_layout.addWidget(self.next_button)
        
        # File operations
        self.open_folder_button = QPushButton("Open Folder")
        self.save_crops_button = QPushButton("Save Crops")
        self.export_button = QPushButton("Export Cropped Images")
        
        self.open_folder_button.clicked.connect(self.open_folder)
        self.save_crops_button.clicked.connect(self.save_crop_data)
        self.export_button.clicked.connect(self.export_images)
        
        self.save_crops_button.setEnabled(False)
        self.export_button.setEnabled(False)
        
        controls_layout.addWidget(self.open_folder_button)
        controls_layout.addWidget(self.save_crops_button)
        controls_layout.addWidget(self.export_button)
        
        layout.addLayout(controls_layout)
        
        # Image info
        self.image_info_label = QLabel("Drop a folder of images here or use Open Folder")
        self.image_info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.image_info_label)
        
        # Image viewer
        self.image_viewer = ScaledImageViewer()
        self.image_viewer.crop_changed.connect(self.on_crop_changed)
        
        scroll_area = QScrollArea()
        scroll_area.setWidget(self.image_viewer)
        scroll_area.setWidgetResizable(True)
        scroll_area.setMinimumHeight(600)
        
        layout.addWidget(scroll_area)
        
        # Enable drag and drop
        self.setAcceptDrops(True)
        
    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()
            
    def dropEvent(self, event: QDropEvent):
        urls = event.mimeData().urls()
        if urls:
            folder_path = urls[0].toLocalFile()
            if os.path.isdir(folder_path):
                self.load_folder(folder_path)
            else:
                QMessageBox.warning(self, "Invalid Drop", "Please drop a folder containing images.")
                
    def open_folder(self):
        folder_path = QFileDialog.getExistingDirectory(self, "Select Image Folder")
        if folder_path:
            self.load_folder(folder_path)
            
    def load_folder(self, folder_path):
        self.folder_path = folder_path
        self.image_loader = ImageLoader(folder_path)
        
        if not self.image_loader.image_files:
            QMessageBox.warning(self, "No Images", "No image files found in the selected folder.")
            return
            
        self.current_image_index = 0
        self.load_crop_data()
        
        # Initialize crop boxes for all images if no existing data
        if not self.crop_data:
            self._initialize_all_crop_boxes()
            
        self.update_image_display()
        self.update_navigation_buttons()
        
        self.save_crops_button.setEnabled(True)
        self.export_button.setEnabled(True)
        
    def load_crop_data(self):
        crop_file = os.path.join(self.folder_path, "crop_data.json")
        if os.path.exists(crop_file):
            try:
                with open(crop_file, 'r') as f:
                    saved_data = json.load(f)
                    
                # Extract global settings
                if '_settings' in saved_data:
                    settings = saved_data['_settings']
                    
                    # Restore crop dimensions
                    if 'crop_width' in settings:
                        self.crop_width = settings['crop_width']
                        self.width_spinbox.setValue(self.crop_width)
                    if 'crop_height' in settings:
                        self.crop_height = settings['crop_height']
                        self.height_spinbox.setValue(self.crop_height)
                        
                    # Restore mode
                    if 'is_double_page' in settings:
                        is_double_page = settings['is_double_page']
                        self.double_page_radio.setChecked(is_double_page)
                        self.single_page_radio.setChecked(not is_double_page)
                        
                    # Restore manually adjusted pages
                    if 'manually_adjusted_pages' in settings:
                        self.manually_adjusted_pages = set(settings['manually_adjusted_pages'])
                        
                    # Restore per-image modes
                    if 'image_modes' in settings:
                        self.image_modes = settings['image_modes']
                        
                    # Restore master positions
                    if 'master_positions' in settings:
                        positions = settings['master_positions']
                        self.master_single_position = positions.get('single', {'x': 0, 'y': 0})
                        self.master_left_position = positions.get('left', {'x': 0, 'y': 0})
                        self.master_right_position = positions.get('right', {'x': 0, 'y': 0})
                    
                    # Remove settings from saved_data to get crop_data
                    del saved_data['_settings']
                    
                # Set crop data
                self.crop_data = saved_data
                    
            except Exception as e:
                print(f"Error loading crop data: {e}")
                self.crop_data = {}
        else:
            self.crop_data = {}
            
    def save_crop_data(self):
        if not self.folder_path:
            return
            
        crop_file = os.path.join(self.folder_path, "crop_data.json")
        try:
            # Prepare complete save data including settings
            save_data = self.crop_data.copy()
            
            # Add global settings
            save_data['_settings'] = {
                'crop_width': self.crop_width,
                'crop_height': self.crop_height,
                'is_double_page': self.double_page_radio.isChecked(),
                'manually_adjusted_pages': list(self.manually_adjusted_pages),
                'image_modes': self.image_modes,
                'master_positions': {
                    'single': self.master_single_position,
                    'left': self.master_left_position,
                    'right': self.master_right_position
                }
            }
            
            with open(crop_file, 'w') as f:
                json.dump(save_data, f, indent=2)
            QMessageBox.information(self, "Saved", "Crop data saved successfully.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save crop data: {e}")
            
    def update_image_display(self):
        if not self.image_loader or not self.image_loader.image_files:
            return
            
        current_file = self.image_loader.image_files[self.current_image_index]
        pixmap = self.image_loader.get_preview(current_file)
        
        if pixmap:
            original_size = self.image_loader.get_original_size(current_file)
            
            # Get the mode for this specific image
            is_double_page = self.image_modes.get(current_file, self.double_page_radio.isChecked())
            
            # Update UI to reflect current image's mode
            self.double_page_radio.blockSignals(True)
            self.single_page_radio.blockSignals(True)
            self.double_page_radio.setChecked(is_double_page)
            self.single_page_radio.setChecked(not is_double_page)
            self.double_page_radio.blockSignals(False)
            self.single_page_radio.blockSignals(False)
            
            # Set image with scaling info
            self.image_viewer.set_image(pixmap, original_size, is_double_page)
            
            # Load crop data (already in original coordinates)
            crop_info = self.crop_data.get(current_file, {})
            if crop_info:
                self.image_viewer.set_crop_boxes(crop_info)
            
            # Update info label
            self.image_info_label.setText(
                f"Image {self.current_image_index + 1} of {len(self.image_loader.image_files)}: {current_file}"
            )
        
    def update_navigation_buttons(self):
        if not self.image_loader:
            return
            
        self.prev_button.setEnabled(self.current_image_index > 0)
        self.next_button.setEnabled(self.current_image_index < len(self.image_loader.image_files) - 1)
        
    def prev_image(self):
        if self.current_image_index > 0:
            self.current_image_index -= 1
            self.update_image_display()
            self.update_navigation_buttons()
            
    def next_image(self):
        if self.current_image_index < len(self.image_loader.image_files) - 1:
            self.current_image_index += 1
            self.update_image_display()
            self.update_navigation_buttons()
            
    def on_mode_changed(self):
        if hasattr(self, 'image_viewer') and hasattr(self, 'image_loader') and self.image_loader:
            current_file = self.image_loader.image_files[self.current_image_index]
            is_double_page = self.double_page_radio.isChecked()
            
            # Store the mode for this image
            self.image_modes[current_file] = is_double_page
            
            # Apply this mode to all subsequent pages that haven't been manually adjusted
            self._apply_mode_to_subsequent_pages(is_double_page)
            
            # Recreate crop boxes for current image with new mode
            original_size = self.image_loader.get_original_size(current_file)
            crop_data = self._create_crop_boxes_for_image(original_size, self.current_image_index)
            self.crop_data[current_file] = crop_data
            
            # Mark as manually adjusted and update master positions
            self.manually_adjusted_pages.add(self.current_image_index)
            self._update_master_positions(crop_data, current_file)
            self._apply_to_subsequent_pages()
            
            # Refresh display
            self.update_image_display()
            
    def on_crop_changed(self, crop_data):
        if not self.image_loader:
            return
            
        current_file = self.image_loader.image_files[self.current_image_index]
        
        # Set flag to indicate we're updating from a resize operation
        self.updating_dimensions_from_resize = True
        
        # Update global crop dimensions from the resized boxes
        if 'left_box' in crop_data:
            self.crop_width = crop_data['left_box']['width']
            self.crop_height = crop_data['left_box']['height']
            # Update UI without triggering the spinbox change handler
            self.width_spinbox.blockSignals(True)
            self.height_spinbox.blockSignals(True)
            self.width_spinbox.setValue(self.crop_width)
            self.height_spinbox.setValue(self.crop_height)
            self.width_spinbox.blockSignals(False)
            self.height_spinbox.blockSignals(False)
        
        # Store crop data (already in original coordinates from new viewer)
        self.crop_data[current_file] = crop_data
        
        # Mark this page as manually adjusted
        self.manually_adjusted_pages.add(self.current_image_index)
        
        # Update master positions based on current adjustment
        self._update_master_positions(crop_data, current_file)
        
        # Apply the new dimensions to subsequent pages that haven't been manually adjusted
        self._apply_to_subsequent_pages()
        
        # Clear the flag
        self.updating_dimensions_from_resize = False
        
    def export_images(self):
        if not self.folder_path or not self.crop_data:
            QMessageBox.warning(self, "No Data", "No crop data to export.")
            return
            
        output_folder = QFileDialog.getExistingDirectory(self, "Select Output Folder")
        if not output_folder:
            return
            
        try:
            from image_exporter import ImageExporter
            exporter = ImageExporter(self.folder_path, output_folder, self.crop_data)
            exporter.export_all()
            QMessageBox.information(self, "Export Complete", "Images exported successfully.")
        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"Failed to export images: {e}")
            
    def on_crop_dimensions_changed(self):
        """Handle changes to crop dimension inputs"""
        # Don't process if this change is coming from a resize operation
        if self.updating_dimensions_from_resize:
            return
            
        old_width = self.crop_width
        old_height = self.crop_height
        
        self.crop_width = self.width_spinbox.value()
        self.crop_height = self.height_spinbox.value()
        
        # Update all existing crop boxes to new dimensions
        if self.image_loader and self.image_loader.image_files:
            self._update_all_crop_dimensions()
            self.update_image_display()
            
    def _update_all_crop_dimensions(self):
        """Update dimensions of all crop boxes while preserving positions"""
        for filename in self.image_loader.image_files:
            if filename in self.crop_data:
                crop_data = self.crop_data[filename]
                if 'left_box' in crop_data:
                    crop_data['left_box']['width'] = self.crop_width
                    crop_data['left_box']['height'] = self.crop_height
                if 'right_box' in crop_data:
                    crop_data['right_box']['width'] = self.crop_width
                    crop_data['right_box']['height'] = self.crop_height
            
    def _create_crop_boxes_for_image(self, image_size, page_index):
        """Create crop boxes for a specific image using master positions"""
        filename = self.image_loader.image_files[page_index]
        is_double_page = self.image_modes.get(filename, self.double_page_radio.isChecked())
        crop_data = {'is_double_page': is_double_page}
        
        if is_double_page:
            # Calculate positions based on master positions
            quarter_point = image_size[0] // 4
            three_quarter_point = (image_size[0] * 3) // 4
            
            left_x = quarter_point - (self.crop_width // 2) + self.master_left_position['x']
            left_y = (image_size[1] - self.crop_height) // 2 + self.master_left_position['y']
            
            right_x = three_quarter_point - (self.crop_width // 2) + self.master_right_position['x']
            right_y = left_y  # Always aligned with left box
            
            crop_data['left_box'] = {
                'x': left_x,
                'y': left_y,
                'width': self.crop_width,
                'height': self.crop_height
            }
            
            crop_data['right_box'] = {
                'x': right_x,
                'y': right_y,
                'width': self.crop_width,
                'height': self.crop_height
            }
        else:
            # Single page mode
            center_x = (image_size[0] - self.crop_width) // 2 + self.master_single_position['x']
            center_y = (image_size[1] - self.crop_height) // 2 + self.master_single_position['y']
            
            crop_data['left_box'] = {
                'x': center_x,
                'y': center_y,
                'width': self.crop_width,
                'height': self.crop_height
            }
            
        return crop_data
        
    def _apply_mode_to_subsequent_pages(self, is_double_page):
        """Apply the current mode to all subsequent pages that haven't been manually adjusted"""
        current_index = self.current_image_index
        
        for i in range(current_index + 1, len(self.image_loader.image_files)):
            if i not in self.manually_adjusted_pages:
                filename = self.image_loader.image_files[i]
                self.image_modes[filename] = is_double_page
        
    def _initialize_all_crop_boxes(self):
        """Initialize crop boxes for all images using default positions"""
        for i, filename in enumerate(self.image_loader.image_files):
            original_size = self.image_loader.get_original_size(filename)
            if original_size != (0, 0):
                crop_data = self._create_crop_boxes_for_image(original_size, i)
                self.crop_data[filename] = crop_data
        
    def _update_master_positions(self, crop_data, filename):
        """Update master positions based on current crop adjustments"""
        original_size = self.image_loader.get_original_size(filename)
        if original_size == (0, 0):
            return
            
        is_double_page = crop_data.get('is_double_page', False)
        
        if is_double_page:
            if 'left_box' in crop_data:
                left_box = crop_data['left_box']
                quarter_point = original_size[0] // 4
                default_left_x = quarter_point - (self.crop_width // 2)
                default_left_y = (original_size[1] - self.crop_height) // 2
                
                self.master_left_position['x'] = left_box['x'] - default_left_x
                self.master_left_position['y'] = left_box['y'] - default_left_y
                
            if 'right_box' in crop_data:
                right_box = crop_data['right_box']
                three_quarter_point = (original_size[0] * 3) // 4
                default_right_x = three_quarter_point - (self.crop_width // 2)
                
                self.master_right_position['x'] = right_box['x'] - default_right_x
                # Y position is always aligned with left box, so use left box Y offset
                
        else:
            if 'left_box' in crop_data:
                single_box = crop_data['left_box']
                default_center_x = (original_size[0] - self.crop_width) // 2
                default_center_y = (original_size[1] - self.crop_height) // 2
                
                self.master_single_position['x'] = single_box['x'] - default_center_x
                self.master_single_position['y'] = single_box['y'] - default_center_y
                
    def _apply_to_subsequent_pages(self):
        """Apply master positions to all subsequent pages that haven't been manually adjusted"""
        current_index = self.current_image_index
        
        for i in range(current_index + 1, len(self.image_loader.image_files)):
            if i not in self.manually_adjusted_pages:
                filename = self.image_loader.image_files[i]
                original_size = self.image_loader.get_original_size(filename)
                if original_size != (0, 0):
                    new_crop_data = self._create_crop_boxes_for_image(original_size, i)
                    self.crop_data[filename] = new_crop_data
            
    def _convert_to_original_coordinates(self, crop_data, filename):
        """Convert preview coordinates to original image coordinates"""
        if not self.image_loader:
            return crop_data
            
        original_size = self.image_loader.get_original_size(filename)
        if original_size == (0, 0):
            return crop_data
            
        # Get preview size from current pixmap
        current_pixmap = self.image_loader.get_preview(filename)
        if not current_pixmap:
            return crop_data
            
        preview_size = current_pixmap.size()
        scale_x, scale_y = self.image_loader.get_scale_factor(filename, preview_size)
        
        converted_data = crop_data.copy()
        
        # Convert left box if present
        if 'left_box' in crop_data:
            box = crop_data['left_box'].copy()
            box['x'] = int(box['x'] * scale_x)
            box['y'] = int(box['y'] * scale_y)
            box['width'] = int(box['width'] * scale_x)
            box['height'] = int(box['height'] * scale_y)
            converted_data['left_box'] = box
            
        # Convert right box if present
        if 'right_box' in crop_data:
            box = crop_data['right_box'].copy()
            box['x'] = int(box['x'] * scale_x)
            box['y'] = int(box['y'] * scale_y)
            box['width'] = int(box['width'] * scale_x)
            box['height'] = int(box['height'] * scale_y)
            converted_data['right_box'] = box
            
        return converted_data
        
    def _sync_crop_boxes_across_images(self, reference_crop_data):
        """Apply crop box changes to all images to maintain consistent crop dimensions"""
        if not self.image_loader or not reference_crop_data:
            return
            
        # Get the dimensions from the reference crop box
        if 'left_box' in reference_crop_data:
            ref_box = reference_crop_data['left_box']
            self.crop_width = ref_box['width']
            self.crop_height = ref_box['height']
            
            # Update the UI spinboxes
            self.width_spinbox.setValue(self.crop_width)
            self.height_spinbox.setValue(self.crop_height)
            
        # Update only the dimensions of existing crop boxes, preserve positions
        for filename in self.image_loader.image_files:
            if filename in self.crop_data:
                crop_data = self.crop_data[filename]
                if 'left_box' in crop_data:
                    crop_data['left_box']['width'] = self.crop_width
                    crop_data['left_box']['height'] = self.crop_height
                if 'right_box' in crop_data:
                    crop_data['right_box']['width'] = self.crop_width
                    crop_data['right_box']['height'] = self.crop_height