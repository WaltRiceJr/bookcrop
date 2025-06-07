from PyQt6.QtWidgets import QLabel, QWidget
from PyQt6.QtCore import Qt, QRect, pyqtSignal, QPoint
from PyQt6.QtGui import QPainter, QPen, QPixmap, QMouseEvent, QCursor

class CropBox:
    """Represents a crop box with position and size in original image coordinates"""
    def __init__(self, x, y, width, height):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        
    def to_dict(self):
        return {
            'x': self.x,
            'y': self.y,
            'width': self.width,
            'height': self.height
        }
        
    @classmethod
    def from_dict(cls, data):
        return cls(data['x'], data['y'], data['width'], data['height'])

class ScaledImageViewer(QLabel):
    """Image viewer that displays crop boxes scaled to preview while maintaining original coordinates"""
    crop_changed = pyqtSignal(dict)
    
    def __init__(self):
        super().__init__()
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setMinimumSize(400, 300)
        self.setStyleSheet("border: 1px solid gray;")
        
        # Image data
        self.current_pixmap = None
        self.original_size = (0, 0)
        self.preview_scale_x = 1.0
        self.preview_scale_y = 1.0
        
        # Mode
        self.is_double_page = False
        
        # Crop boxes (stored in original image coordinates)
        self.left_crop_box = None
        self.right_crop_box = None
        
        # Mouse interaction
        self.dragging = False
        self.resizing = False
        self.drag_start_pos = QPoint()
        self.active_box = None
        self.resize_handle = None
        
    def set_image(self, pixmap, original_size, is_double_page=False):
        """Set the image and scale information"""
        self.current_pixmap = pixmap
        self.original_size = original_size
        self.is_double_page = is_double_page
        
        if pixmap and original_size != (0, 0):
            self.setPixmap(pixmap)
            # Calculate scale factors
            self.preview_scale_x = pixmap.width() / original_size[0]
            self.preview_scale_y = pixmap.height() / original_size[1]
        else:
            self.clear()
            
        self.update()
        
    def set_crop_boxes(self, crop_data):
        """Set crop boxes from original image coordinates"""
        self.left_crop_box = None
        self.right_crop_box = None
        
        if 'left_box' in crop_data:
            self.left_crop_box = CropBox.from_dict(crop_data['left_box'])
            
        if 'right_box' in crop_data and self.is_double_page:
            self.right_crop_box = CropBox.from_dict(crop_data['right_box'])
            
        self.update()
        
    def _original_to_preview(self, original_point):
        """Convert original image coordinates to preview coordinates"""
        return QPoint(
            int(original_point.x() * self.preview_scale_x),
            int(original_point.y() * self.preview_scale_y)
        )
        
    def _preview_to_original(self, preview_point):
        """Convert preview coordinates to original image coordinates"""
        return QPoint(
            int(preview_point.x() / self.preview_scale_x),
            int(preview_point.y() / self.preview_scale_y)
        )
        
    def _get_preview_rect(self, crop_box):
        """Get the preview rectangle for a crop box"""
        if not crop_box:
            return None
            
        # Scale the crop box to preview coordinates
        preview_x = int(crop_box.x * self.preview_scale_x)
        preview_y = int(crop_box.y * self.preview_scale_y)
        preview_width = int(crop_box.width * self.preview_scale_x)
        preview_height = int(crop_box.height * self.preview_scale_y)
        
        return QRect(preview_x, preview_y, preview_width, preview_height)
        
    def _get_image_offset(self):
        """Get offset of image within label"""
        if not self.current_pixmap:
            return QPoint(0, 0)
            
        label_rect = self.rect()
        pixmap_rect = self.current_pixmap.rect()
        
        x_offset = (label_rect.width() - pixmap_rect.width()) // 2
        y_offset = (label_rect.height() - pixmap_rect.height()) // 2
        
        return QPoint(x_offset, y_offset)
        
    def paintEvent(self, event):
        """Draw the image and crop boxes"""
        super().paintEvent(event)
        
        if not self.current_pixmap:
            return
            
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        offset = self._get_image_offset()
        
        # Draw crop boxes
        pen = QPen(Qt.GlobalColor.red, 2)
        painter.setPen(pen)
        
        if self.left_crop_box:
            rect = self._get_preview_rect(self.left_crop_box)
            if rect:
                rect.translate(offset)
                painter.drawRect(rect)
                self._draw_resize_handles(painter, rect)
                
        if self.right_crop_box and self.is_double_page:
            rect = self._get_preview_rect(self.right_crop_box)
            if rect:
                rect.translate(offset)
                painter.drawRect(rect)
                self._draw_resize_handles(painter, rect)
                
    def _draw_resize_handles(self, painter, rect):
        """Draw resize handles on corners"""
        handle_size = 10
        
        corners = [
            rect.topLeft(),
            rect.topRight(),
            rect.bottomLeft(),
            rect.bottomRight()
        ]
        
        for corner in corners:
            handle_rect = QRect(
                corner.x() - handle_size // 2,
                corner.y() - handle_size // 2,
                handle_size,
                handle_size
            )
            painter.fillRect(handle_rect, Qt.GlobalColor.white)
            pen = QPen(Qt.GlobalColor.blue, 2)
            painter.setPen(pen)
            painter.drawRect(handle_rect)
            
    def _get_crop_box_at_point(self, widget_point):
        """Get crop box at widget point"""
        offset = self._get_image_offset()
        image_point = widget_point - offset
        
        if self.left_crop_box:
            rect = self._get_preview_rect(self.left_crop_box)
            if rect and rect.contains(image_point):
                return self.left_crop_box
                
        if self.right_crop_box:
            rect = self._get_preview_rect(self.right_crop_box)
            if rect and rect.contains(image_point):
                return self.right_crop_box
                
        return None
        
    def _get_resize_handle_at_point(self, widget_point, crop_box):
        """Check if point is on a resize handle"""
        if not crop_box:
            return None
            
        offset = self._get_image_offset()
        rect = self._get_preview_rect(crop_box)
        if not rect:
            return None
            
        rect.translate(offset)
        
        handle_size = 10
        tolerance = handle_size // 2
        
        corners = {
            'top_left': rect.topLeft(),
            'top_right': rect.topRight(),
            'bottom_left': rect.bottomLeft(),
            'bottom_right': rect.bottomRight()
        }
        
        for handle, corner in corners.items():
            if abs(widget_point.x() - corner.x()) <= tolerance and abs(widget_point.y() - corner.y()) <= tolerance:
                return handle
                
        return None
        
    def mousePressEvent(self, event):
        """Handle mouse press"""
        if event.button() != Qt.MouseButton.LeftButton:
            return
            
        # Check for resize handles first
        self.active_box = None
        self.resize_handle = None
        
        if self.left_crop_box:
            handle = self._get_resize_handle_at_point(event.pos(), self.left_crop_box)
            if handle:
                self.active_box = self.left_crop_box
                self.resize_handle = handle
                self.resizing = True
                self.setCursor(QCursor(Qt.CursorShape.SizeFDiagCursor))
                self.drag_start_pos = event.pos()
                return
                
        if self.right_crop_box:
            handle = self._get_resize_handle_at_point(event.pos(), self.right_crop_box)
            if handle:
                self.active_box = self.right_crop_box
                self.resize_handle = handle
                self.resizing = True
                self.setCursor(QCursor(Qt.CursorShape.SizeFDiagCursor))
                self.drag_start_pos = event.pos()
                return
                
        # Check for drag
        self.active_box = self._get_crop_box_at_point(event.pos())
        if self.active_box:
            self.dragging = True
            self.setCursor(QCursor(Qt.CursorShape.ClosedHandCursor))
            self.drag_start_pos = event.pos()
            
    def mouseMoveEvent(self, event):
        """Handle mouse move"""
        if self.dragging and self.active_box:
            self._handle_drag(event.pos())
        elif self.resizing and self.active_box:
            self._handle_resize(event.pos())
        else:
            # Update cursor
            handle_found = False
            
            if self.left_crop_box:
                handle = self._get_resize_handle_at_point(event.pos(), self.left_crop_box)
                if handle:
                    self.setCursor(QCursor(Qt.CursorShape.SizeFDiagCursor))
                    handle_found = True
                    
            if not handle_found and self.right_crop_box:
                handle = self._get_resize_handle_at_point(event.pos(), self.right_crop_box)
                if handle:
                    self.setCursor(QCursor(Qt.CursorShape.SizeFDiagCursor))
                    handle_found = True
                    
            if not handle_found:
                crop_box = self._get_crop_box_at_point(event.pos())
                if crop_box:
                    self.setCursor(QCursor(Qt.CursorShape.OpenHandCursor))
                else:
                    self.setCursor(QCursor(Qt.CursorShape.ArrowCursor))
                    
    def mouseReleaseEvent(self, event):
        """Handle mouse release"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragging = False
            self.resizing = False
            self.active_box = None
            self.resize_handle = None
            self.setCursor(QCursor(Qt.CursorShape.ArrowCursor))
            
            self._emit_crop_changed()
            
    def _handle_drag(self, current_pos):
        """Handle dragging of crop box"""
        if not self.active_box:
            return
            
        # Calculate movement in original coordinates
        delta = current_pos - self.drag_start_pos
        original_delta_x = int(delta.x() / self.preview_scale_x)
        original_delta_y = int(delta.y() / self.preview_scale_y)
        
        # Update crop box position
        self.active_box.x += original_delta_x
        self.active_box.y += original_delta_y
        
        # In double page mode, align left and right boxes vertically
        if self.is_double_page and self.left_crop_box and self.right_crop_box:
            if self.active_box == self.left_crop_box:
                self.right_crop_box.y = self.left_crop_box.y
            elif self.active_box == self.right_crop_box:
                self.left_crop_box.y = self.right_crop_box.y
                
        self.drag_start_pos = current_pos
        self.update()
        
    def _handle_resize(self, current_pos):
        """Handle resizing of crop box"""
        if not self.active_box or not self.resize_handle:
            return
            
        # Convert to original coordinates
        offset = self._get_image_offset()
        image_point = current_pos - offset
        original_point = self._preview_to_original(image_point)
        
        # Get current bounds in original coordinates
        left = self.active_box.x
        top = self.active_box.y
        right = self.active_box.x + self.active_box.width
        bottom = self.active_box.y + self.active_box.height
        
        # Modify bounds based on handle
        if 'top' in self.resize_handle:
            top = min(original_point.y(), bottom - 50)  # Min 50px height
        elif 'bottom' in self.resize_handle:
            bottom = max(original_point.y(), top + 50)
            
        if 'left' in self.resize_handle:
            left = min(original_point.x(), right - 50)  # Min 50px width
        elif 'right' in self.resize_handle:
            right = max(original_point.x(), left + 50)
            
        # Update crop box
        self.active_box.x = left
        self.active_box.y = top
        self.active_box.width = right - left
        self.active_box.height = bottom - top
        
        # In double page mode, sync sizes and align vertically
        if self.is_double_page and self.left_crop_box and self.right_crop_box:
            if self.active_box == self.left_crop_box:
                self.right_crop_box.width = self.left_crop_box.width
                self.right_crop_box.height = self.left_crop_box.height
                self.right_crop_box.y = self.left_crop_box.y
            elif self.active_box == self.right_crop_box:
                self.left_crop_box.width = self.right_crop_box.width
                self.left_crop_box.height = self.right_crop_box.height
                self.left_crop_box.y = self.right_crop_box.y
                
        self.update()
        
    def _emit_crop_changed(self):
        """Emit crop changed signal"""
        crop_data = {'is_double_page': self.is_double_page}
        
        if self.left_crop_box:
            crop_data['left_box'] = self.left_crop_box.to_dict()
        if self.right_crop_box:
            crop_data['right_box'] = self.right_crop_box.to_dict()
            
        self.crop_changed.emit(crop_data)