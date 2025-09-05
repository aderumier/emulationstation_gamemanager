#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GameManager - Game Collection Management System
Copyright (C) 2024 Alexandre Derumier <aderumier@gmail.com>

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.

2D Box Generator using ImageMagick (direct command execution)
Based on the bash script from: https://gist.github.com/aderumier/014aba1e764e21aeb519c48d3d20e4cc
"""

import os
import tempfile
import subprocess
import logging

class BoxGenerator:
    def __init__(self, width=600, height=800, logo_position="north", logo_offset="+0+60", 
                 gradient_height=400, border_size=2, border_color="#333333", 
                 blur_background=False, vintage_effect=False, use_blurred_bg=True,
                 blur_intensity=30, background_color="black", secondary_logo="",
                 secondary_position="north", secondary_offset="+0+30", 
                 title_border_size=3, title_border_color="black"):
        """
        Initialize the 2D Box Generator with default parameters
        """
        self.width = width
        self.height = height
        self.logo_position = logo_position
        self.logo_offset = logo_offset
        self.gradient_height = gradient_height
        self.border_size = border_size
        self.border_color = border_color
        self.blur_background = blur_background
        self.vintage_effect = vintage_effect
        self.use_blurred_bg = use_blurred_bg
        self.blur_intensity = blur_intensity
        self.background_color = background_color
        self.secondary_logo = secondary_logo
        self.secondary_position = secondary_position
        self.secondary_offset = secondary_offset
        self.title_border_size = title_border_size
        self.title_border_color = title_border_color
        
        # Calculate derived values
        self.logo_max_width = int(self.width * 80 / 100)
        self.logo_max_height = int(self.height * 25 / 100)
        
    def validate_dependencies(self):
        """Validate that ImageMagick is available"""
        try:
            # Test if convert command is available
            result = subprocess.run(['convert', '-version'], 
                                  capture_output=True, text=True, timeout=5)
            return result.returncode == 0
        except Exception as e:
            logging.error(f"ImageMagick not available: {e}")
            return False
    
    def generate_2d_box(self, titlescreen_path, gameplay_path, logo_path, output_path, 
                       secondary_logo_path=None):
        """
        Generate 2D box art from titlescreen, gameplay, and logo images
        Following the exact logic from the bash script
        
        Args:
            titlescreen_path: Path to titlescreen image
            gameplay_path: Path to gameplay image  
            logo_path: Path to logo image
            output_path: Path for output 2D box
            secondary_logo_path: Optional secondary logo path
        """
        temp_files = []
        
        try:
            # Validate inputs
            for path in [titlescreen_path, gameplay_path, logo_path]:
                if not os.path.exists(path):
                    raise FileNotFoundError(f"Required image not found: {path}")
            
            logging.info(f"Generating 2D box: {output_path}")
            
            # Calculate 75% width for gameplay image (as in bash script)
            gameplay_width = int(self.width * 75 / 100)
            
            # Step 1: Prepare background (exactly like bash script)
            logging.info("1. Preparing background...")
            
            if self.use_blurred_bg:
                # Create blurred background from titlescreen
                cmd = [
                    'convert', titlescreen_path,
                    '-resize', f'{self.width}x{self.height}^',
                    '-gravity', 'center',
                    '-extent', f'{self.width}x{self.height}',
                    '-blur', f'0x{self.blur_intensity}',
                    'temp_blurred_bg.jpg'
                ]
                subprocess.run(cmd, check=True)
                temp_files.append('temp_blurred_bg.jpg')
                
                # Prepare gameplay image with border (75% width)
                cmd = [
                    'convert', gameplay_path,
                    '-resize', f'{gameplay_width}x{self.height}>',
                    '-bordercolor', self.title_border_color,
                    '-border', f'{self.title_border_size}x{self.title_border_size}',
                    'temp_main.jpg'
                ]
                subprocess.run(cmd, check=True)
                temp_files.append('temp_main.jpg')
                
                # Compose gameplay on blurred background (centered in lower 2/3)
                gameplay_y_offset = self.height // 6  # 1/6 down (as in bash script)
                cmd = [
                    'convert', 'temp_blurred_bg.jpg', 'temp_main.jpg',
                    '-gravity', 'center',
                    '-geometry', f'+0+{gameplay_y_offset}',
                    '-composite', 'temp_bg.jpg'
                ]
                subprocess.run(cmd, check=True)
                temp_files.append('temp_bg.jpg')
            else:
                # Original mode with solid background
                gameplay_y_offset = self.height // 6
                
                # Prepare gameplay image with border
                cmd = [
                    'convert', gameplay_path,
                    '-resize', f'{gameplay_width}x{self.height}>',
                    '-bordercolor', self.title_border_color,
                    '-border', f'{self.title_border_size}x{self.title_border_size}',
                    'temp_main.jpg'
                ]
                subprocess.run(cmd, check=True)
                temp_files.append('temp_main.jpg')
                
                # Create background with gameplay positioned in lower 2/3
                cmd = [
                    'convert', 
                    '-size', f'{self.width}x{self.height}',
                    f'xc:{self.background_color}',
                    'temp_main.jpg',
                    '-gravity', 'center',
                    '-geometry', f'+0+{gameplay_y_offset}',
                    '-composite', 'temp_bg.jpg'
                ]
                subprocess.run(cmd, check=True)
                temp_files.append('temp_bg.jpg')
            
            # Apply additional blur if requested
            if self.blur_background:
                logging.info("   Applying blur...")
                cmd = ['convert', 'temp_bg.jpg', '-blur', '0x2', 'temp_bg.jpg']
                subprocess.run(cmd, check=True)
            
            # Step 2: Apply vintage effect if requested
            if self.vintage_effect:
                logging.info("2. Applying vintage effect...")
                cmd = [
                    'convert', 'temp_bg.jpg',
                    '-modulate', '110,130,100',
                    '-colorize', '10,5,0',
                    '-sigmoidal-contrast', '2,50%',
                    'temp_bg.jpg'
                ]
                subprocess.run(cmd, check=True)
            
            # Step 3: Add gradient (exactly like bash script)
            logging.info("3. Adding gradient...")
            if self.logo_position == "north":
                cmd = [
                    'convert', 'temp_bg.jpg',
                    '(', '-size', f'{self.width}x{self.gradient_height}',
                    'gradient:black-transparent', ')',
                    '-gravity', 'north',
                    '-composite', 'temp_with_gradient.jpg'
                ]
            elif self.logo_position == "south":
                cmd = [
                    'convert', 'temp_bg.jpg',
                    '(', '-size', f'{self.width}x{self.gradient_height}',
                    'gradient:transparent-black', ')',
                    '-gravity', 'south',
                    '-composite', 'temp_with_gradient.jpg'
                ]
            elif self.logo_position == "center":
                gradient_height = self.height // 3
                cmd = [
                    'convert', 'temp_bg.jpg',
                    '(', '-size', f'{self.width}x{gradient_height}',
                    'gradient:transparent-black', ')',
                    '-gravity', 'center',
                    '-composite', 'temp_with_gradient.jpg'
                ]
            else:
                # No gradient, just copy
                cmd = ['cp', 'temp_bg.jpg', 'temp_with_gradient.jpg']
            
            subprocess.run(cmd, check=True)
            temp_files.append('temp_with_gradient.jpg')
            
            # Step 4: Process logos (exactly like bash script)
            logging.info("4. Processing logos...")
            
            # Process main logo
            cmd = [
                'convert', logo_path,
                '-resize', f'{self.logo_max_width}x{self.logo_max_height}>',
                '-background', 'transparent',
                'temp_logo.png'
            ]
            subprocess.run(cmd, check=True)
            temp_files.append('temp_logo.png')
            
            # Process secondary logo if provided
            if secondary_logo_path and os.path.exists(secondary_logo_path):
                cmd = [
                    'convert', secondary_logo_path,
                    '-resize', f'{self.logo_max_width}x{self.logo_max_height}>',
                    '-background', 'transparent',
                    'temp_secondary_logo.png'
                ]
                subprocess.run(cmd, check=True)
                temp_files.append('temp_secondary_logo.png')
            
            # Step 5: Final composition (exactly like bash script)
            logging.info("5. Final composition...")
            
            # Compose main logo
            cmd = [
                'convert', 'temp_with_gradient.jpg',
                'temp_logo.png',
                '-gravity', self.logo_position,
                '-geometry', self.logo_offset,
                '-composite', 'temp_final.jpg'
            ]
            subprocess.run(cmd, check=True)
            temp_files.append('temp_final.jpg')
            
            final_temp = 'temp_final.jpg'
            
            # Compose secondary logo if present
            if secondary_logo_path and os.path.exists(secondary_logo_path):
                cmd = [
                    'convert', 'temp_final.jpg',
                    'temp_secondary_logo.png',
                    '-gravity', self.secondary_position,
                    '-geometry', self.secondary_offset,
                    '-composite', 'temp_final_with_secondary.jpg'
                ]
                subprocess.run(cmd, check=True)
                temp_files.append('temp_final_with_secondary.jpg')
                final_temp = 'temp_final_with_secondary.jpg'
            
            # Step 6: Add border if requested (exactly like bash script)
            if self.border_size > 0:
                logging.info("6. Adding border...")
                cmd = [
                    'convert', final_temp,
                    '-bordercolor', self.border_color,
                    '-border', f'{self.border_size}x{self.border_size}',
                    output_path
                ]
                subprocess.run(cmd, check=True)
            else:
                cmd = ['cp', final_temp, output_path]
                subprocess.run(cmd, check=True)
            
            logging.info(f"✅ 2D box generated successfully: {output_path}")
            return True
            
        except subprocess.CalledProcessError as e:
            logging.error(f"ImageMagick command failed: {e}")
            raise Exception(f"Image generation failed: {e}")
        except Exception as e:
            logging.error(f"Error generating 2D box: {e}")
            raise
        finally:
            # Cleanup temp files
            for temp_file in temp_files:
                try:
                    if os.path.exists(temp_file):
                        os.remove(temp_file)
                except Exception as e:
                    logging.warning(f"Could not remove temp file {temp_file}: {e}")

def generate_2d_box_simple(titlescreen_path, gameplay_path, logo_path, output_path, 
                          width=600, height=800, logo_position="north"):
    """
    Simple wrapper function for basic 2D box generation
    """
    generator = BoxGenerator(width=width, height=height, logo_position=logo_position)
    return generator.generate_2d_box(titlescreen_path, gameplay_path, logo_path, output_path)

if __name__ == "__main__":
    # Test the generator
    import sys
    
    if len(sys.argv) < 5:
        print("Usage: python box_generator.py <titlescreen> <gameplay> <logo> <output>")
        sys.exit(1)
    
    titlescreen = sys.argv[1]
    gameplay = sys.argv[2]
    logo = sys.argv[3]
    output = sys.argv[4]
    
    generator = BoxGenerator()
    if generator.validate_dependencies():
        try:
            generator.generate_2d_box(titlescreen, gameplay, logo, output)
            print(f"Successfully generated: {output}")
        except Exception as e:
            print(f"Error: {e}")
            sys.exit(1)
    else:
        print("ImageMagick not available")
        sys.exit(1)
