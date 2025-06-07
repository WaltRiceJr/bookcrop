import os
from pathlib import Path
from PIL import Image

class ImageExporter:
    def __init__(self, source_folder, output_folder, crop_data):
        self.source_folder = source_folder
        self.output_folder = output_folder
        self.crop_data = crop_data
        
    def export_all(self):
        """Export all images with crop data applied"""
        # Ensure output folder exists
        os.makedirs(self.output_folder, exist_ok=True)
        
        for filename, crop_info in self.crop_data.items():
            self._export_image(filename, crop_info)
            
    def _export_image(self, filename, crop_info):
        """Export a single image with cropping applied"""
        source_path = os.path.join(self.source_folder, filename)
        
        if not os.path.exists(source_path):
            print(f"Source file not found: {source_path}")
            return
            
        try:
            with Image.open(source_path) as img:
                name, ext = os.path.splitext(filename)
                
                if crop_info.get('is_double_page', False):
                    # Double page mode - export left and right pages
                    if 'left_box' in crop_info:
                        left_img = self._extract_crop_with_padding(img, crop_info['left_box'])
                        left_filename = f"{name}_left{ext}"
                        left_path = os.path.join(self.output_folder, left_filename)
                        left_img.save(left_path, quality=95)
                        
                    if 'right_box' in crop_info:
                        right_img = self._extract_crop_with_padding(img, crop_info['right_box'])
                        right_filename = f"{name}_right{ext}"
                        right_path = os.path.join(self.output_folder, right_filename)
                        right_img.save(right_path, quality=95)
                else:
                    # Single page mode
                    if 'left_box' in crop_info:
                        cropped_img = self._extract_crop_with_padding(img, crop_info['left_box'])
                        output_path = os.path.join(self.output_folder, filename)
                        cropped_img.save(output_path, quality=95)
                        
        except Exception as e:
            print(f"Error exporting {filename}: {e}")
            
    def _extract_crop_with_padding(self, img, box_data):
        """Extract crop area, filling out-of-bounds areas with white"""
        crop_x = box_data['x']
        crop_y = box_data['y']
        crop_width = box_data['width']
        crop_height = box_data['height']
        
        img_width, img_height = img.size
        
        # Calculate the intersection of crop box with image
        left = max(0, crop_x)
        top = max(0, crop_y)
        right = min(img_width, crop_x + crop_width)
        bottom = min(img_height, crop_y + crop_height)
        
        # Create a white canvas of the desired crop size
        result = Image.new('RGB', (crop_width, crop_height), 'white')
        
        # If there's any intersection with the image, paste that part
        if left < right and top < bottom:
            # Crop the intersecting area from the original image
            cropped_section = img.crop((left, top, right, bottom))
            
            # Calculate where to paste this section on the white canvas
            paste_x = left - crop_x
            paste_y = top - crop_y
            
            result.paste(cropped_section, (paste_x, paste_y))
        
        return result