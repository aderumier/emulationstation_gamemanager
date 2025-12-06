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
                       secondary_logo_path=None, additional_screenshot_path=None):
        """
        Generate 2D box art from titlescreen, gameplay, and logo images
        Following the exact logic from the bash script
        
        Args:
            titlescreen_path: Path to titlescreen image
            gameplay_path: Path to gameplay image  
            logo_path: Path to logo image
            output_path: Path for output 2D box
            secondary_logo_path: Optional secondary logo path
            additional_screenshot_path: Optional additional screenshot to place in middle, under logo and above gameplay
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
            
            # Process additional screenshot first if provided (needed for positioning calculations)
            additional_screenshot_height = 0
            if additional_screenshot_path and os.path.exists(additional_screenshot_path):
                logging.info("0. Processing additional screenshot...")
                # Resize additional screenshot to fit in middle third (1/3 of height)
                additional_width = int(self.width * 50 / 100)  # 50% width
                additional_height = int(self.height * 30 / 100)  # ~30% height to fit in middle third
                cmd = [
                    'convert', additional_screenshot_path,
                    '-resize', f'{additional_width}x{additional_height}>',
                    '-bordercolor', self.title_border_color,
                    '-border', f'{self.title_border_size}x{self.title_border_size}',
                    'temp_additional_screenshot.jpg'
                ]
                subprocess.run(cmd, check=True)
                temp_files.append('temp_additional_screenshot.jpg')
                # Get actual height for positioning calculations
                identify_cmd = ['identify', '-format', '%h', 'temp_additional_screenshot.jpg']
                dim_result = subprocess.run(identify_cmd, capture_output=True, text=True, timeout=5)
                if dim_result.returncode == 0:
                    additional_screenshot_height = int(dim_result.stdout.strip())
            
            # Step 1: Prepare background (exactly like bash script)
            logging.info("1. Preparing background...")
            
            # Calculate positions: divide height into thirds
            # Top third (0-33%): Logo
            # Middle third (33-66%): Additional screenshot - positioned at ~38% from top
            # Bottom third (66-100%): Gameplay - positioned slightly higher
            if additional_screenshot_path and os.path.exists(additional_screenshot_path):
                # Position gameplay slightly higher than original 66% (around 64% from top)
                # With -gravity center, positive offset moves down from center
                # 64% from top = center (50%) + 14% = +14% offset from center
                gameplay_y_offset = int(self.height * 10 / 100)  # +14%: move down from center to 64%
            else:
                gameplay_y_offset = self.height // 6  # 1/6 down (as in bash script)
            
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
                base_bg = 'temp_blurred_bg.jpg'
            else:
                # Original mode with solid background
                base_bg = None  # Will create it below
            
            # Compose additional screenshot onto base background FIRST (if present)
            if additional_screenshot_path and os.path.exists(additional_screenshot_path):
                # Position additional screenshot in middle third, slightly below logo to avoid overlap
                # Target: ~38% from top (just under logo with some spacing)
                # With -gravity center, 38% from top = center (50%) - 12% = -12% offset from center
                additional_y_offset = int(self.height * -12 / 100)  # -12%: move up from center to 38%
                # Format geometry string correctly for negative offsets
                if additional_y_offset >= 0:
                    additional_geometry = f'+0+{additional_y_offset}'
                else:
                    additional_geometry = f'+0{additional_y_offset}'  # Negative: +0-136
                logging.info(f"Composing additional screenshot at geometry: {additional_geometry}")
                if self.use_blurred_bg:
                    cmd = [
                        'convert', base_bg,
                        'temp_additional_screenshot.jpg',
                        '-gravity', 'center',
                        '-geometry', additional_geometry,
                        '-composite', 'temp_bg_with_additional.jpg'
                    ]
                    subprocess.run(cmd, check=True)
                    temp_files.append('temp_bg_with_additional.jpg')
                    base_bg = 'temp_bg_with_additional.jpg'
                else:
                    # Create solid background and add additional screenshot
                    cmd = [
                        'convert',
                        '-size', f'{self.width}x{self.height}',
                        f'xc:{self.background_color}',
                        'temp_additional_screenshot.jpg',
                        '-gravity', 'center',
                        '-geometry', additional_geometry,
                        '-composite', 'temp_bg_with_additional.jpg'
                    ]
                    subprocess.run(cmd, check=True)
                    temp_files.append('temp_bg_with_additional.jpg')
                    base_bg = 'temp_bg_with_additional.jpg'
            
            # Prepare gameplay image with border
            # If additional screenshot exists, resize to fit bottom third only
            if additional_screenshot_path and os.path.exists(additional_screenshot_path):
                # Resize to fit in bottom third (66-100% of height, ~33% of total height)
                # But allow it to be a bit larger to fill the space better
                gameplay_height = int(self.height * 40 / 100)  # Slightly larger than 33% to fill bottom third
                logging.info(f"Resizing gameplay to fit bottom third: {gameplay_width}x{gameplay_height}")
                cmd = [
                    'convert', gameplay_path,
                    '-resize', f'{gameplay_width}x{gameplay_height}>',
                    '-bordercolor', self.title_border_color,
                    '-border', f'{self.title_border_size}x{self.title_border_size}',
                    'temp_main.jpg'
                ]
            else:
                # Normal resize (75% width, full height) - resize to fit while maintaining aspect ratio
                # Remove '>' so smaller images are upscaled to match the target size
                cmd = [
                    'convert', gameplay_path,
                    '-resize', f'{gameplay_width}x{self.height}',  # Resize to fit, maintain aspect ratio
                    '-bordercolor', self.title_border_color,
                    '-border', f'{self.title_border_size}x{self.title_border_size}',
                    'temp_main.jpg'
                ]
            subprocess.run(cmd, check=True)
            temp_files.append('temp_main.jpg')
            
            # Compose gameplay onto background (now includes additional screenshot if present)
            logging.info(f"Composing gameplay at offset: +0+{gameplay_y_offset} (from center)")
            if self.use_blurred_bg:
                # Use base_bg which may already have additional screenshot
                cmd = [
                    'convert', base_bg, 'temp_main.jpg',
                    '-gravity', 'center',
                    '-geometry', f'+0+{gameplay_y_offset}',
                    '-composite', 'temp_bg.jpg'
                ]
                subprocess.run(cmd, check=True)
                temp_files.append('temp_bg.jpg')
            else:
                # Create background with gameplay positioned in lower 2/3
                if base_bg:
                    # base_bg already has additional screenshot, just add gameplay
                    cmd = [
                        'convert', base_bg, 'temp_main.jpg',
                        '-gravity', 'center',
                        '-geometry', f'+0+{gameplay_y_offset}',
                        '-composite', 'temp_bg.jpg'
                    ]
                else:
                    # No additional screenshot, create normal background
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
                    'convert', final_temp,
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
                # Convert to PNG format when copying
                cmd = ['convert', final_temp, output_path]
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

    def generate_template_box(self, background_path, screenshot_path, output_path, 
                              corner1_x, corner1_y, corner2_x, corner2_y,
                              corner3_x, corner3_y, corner4_x, corner4_y,
                              logo_source='none', logo_path=None, logo_corners=None, 
                              text_logo_settings=None, game_name=''):
        """
        Generate box using a template with background image and screenshot positioned at specific corners
        
        Args:
            background_path: Path to background image (defines output dimensions)
            screenshot_path: Path to screenshot image
            output_path: Path for output box
            corner1_x, corner1_y: Top-left corner position
            corner2_x, corner2_y: Top-right corner position
            corner3_x, corner3_y: Bottom-right corner position
            corner4_x, corner4_y: Bottom-left corner position
            logo_source: 'none', 'marquee', or 'text'
            logo_path: Path to logo image (for marquee source)
            logo_corners: Dict with logo corner positions (x1, y1, x2, y2, x3, y3, x4, y4)
            text_logo_settings: Dict with text logo settings (color, font_size, font, etc.)
            game_name: Game name for text logo generation
        """
        temp_files = []
        
        try:
            # Validate inputs
            if not os.path.exists(background_path):
                raise FileNotFoundError(f"Background image not found: {background_path}")
            if not os.path.exists(screenshot_path):
                raise FileNotFoundError(f"Screenshot image not found: {screenshot_path}")
            
            logging.info(f"Generating template box: {output_path}")
            
            # Get background image dimensions
            identify_cmd = ['identify', '-format', '%wx%h', background_path]
            dim_result = subprocess.run(identify_cmd, capture_output=True, text=True, timeout=5)
            if dim_result.returncode != 0:
                raise Exception("Failed to get background image dimensions")
            
            # Use background image as base (copy it first)
            cmd = ['convert', background_path, 'temp_background.jpg']
            subprocess.run(cmd, check=True)
            temp_files.append('temp_background.jpg')
            
            # Calculate bounding box of the 4 corners to determine target size
            min_x = min(corner1_x, corner2_x, corner3_x, corner4_x)
            max_x = max(corner1_x, corner2_x, corner3_x, corner4_x)
            min_y = min(corner1_y, corner2_y, corner3_y, corner4_y)
            max_y = max(corner1_y, corner2_y, corner3_y, corner4_y)
            
            target_width = max_x - min_x
            target_height = max_y - min_y
            
            # Get screenshot dimensions
            screenshot_dim_cmd = ['identify', '-format', '%wx%h', screenshot_path]
            screenshot_dim_result = subprocess.run(screenshot_dim_cmd, capture_output=True, text=True, timeout=5)
            if screenshot_dim_result.returncode != 0:
                raise Exception("Failed to get screenshot dimensions")
            
            screenshot_dims = screenshot_dim_result.stdout.strip().split('x')
            screenshot_width = int(screenshot_dims[0])
            screenshot_height = int(screenshot_dims[1])
            
            # Step 1: Resize screenshot to fit the bounding box dimensions
            # This ensures the screenshot has the correct dimensions before placing
            logging.info(f"Resizing screenshot from {screenshot_width}x{screenshot_height} to {target_width}x{target_height}")
            temp_resized = tempfile.NamedTemporaryFile(delete=False, suffix='.png').name
            temp_files.append(temp_resized)
            
            cmd = [
                'convert', screenshot_path,
                '-resize', f'{target_width}x{target_height}!',  # ! forces exact size, ignoring aspect ratio
                '-quality', '100',  # High quality resize
                temp_resized
            ]
            subprocess.run(cmd, check=True)
            logging.info(f"✅ Screenshot resized to {target_width}x{target_height}")
            
            # Verify the resized image dimensions
            verify_cmd = ['identify', '-format', '%wx%h', temp_resized]
            verify_result = subprocess.run(verify_cmd, capture_output=True, text=True, timeout=5)
            if verify_result.returncode == 0:
                resized_dims = verify_result.stdout.strip().split('x')
                resized_width = int(resized_dims[0])
                resized_height = int(resized_dims[1])
                logging.info(f"Verified resized dimensions: {resized_width}x{resized_height}")
            
            # Step 2: Composite the resized screenshot onto background at the correct position
            # Use composite command with geometry for exact positioning
            # Position at min_x, min_y to align with the corner positions
            logging.info(f"Placing resized screenshot onto background at position ({min_x}, {min_y})")
            cmd = [
                'composite',
                '-geometry', f'+{min_x}+{min_y}',
                temp_resized,  # Use the resized image directly
                'temp_background.jpg',
                output_path
            ]
            subprocess.run(cmd, check=True)
            logging.info(f"✅ Screenshot placed successfully")
            
            # Step 3: Handle logo if configured
            if logo_source != 'none' and logo_corners:
                logo_min_x = min(logo_corners.get('x1', 0), logo_corners.get('x2', 0), 
                               logo_corners.get('x3', 0), logo_corners.get('x4', 0))
                logo_max_x = max(logo_corners.get('x1', 0), logo_corners.get('x2', 0), 
                               logo_corners.get('x3', 0), logo_corners.get('x4', 0))
                logo_min_y = min(logo_corners.get('y1', 0), logo_corners.get('y2', 0), 
                               logo_corners.get('y3', 0), logo_corners.get('y4', 0))
                logo_max_y = max(logo_corners.get('y1', 0), logo_corners.get('y2', 0), 
                               logo_corners.get('y3', 0), logo_corners.get('y4', 0))
                
                logo_zone_width = logo_max_x - logo_min_x
                logo_zone_height = logo_max_y - logo_min_y
                
                if logo_source == 'marquee' and logo_path and os.path.exists(logo_path):
                    # Resize and place marquee logo
                    logging.info(f"Placing marquee logo at position ({logo_min_x}, {logo_min_y})")
                    temp_logo = tempfile.NamedTemporaryFile(delete=False, suffix='.png').name
                    temp_files.append(temp_logo)
                    
                    # Resize logo to fit zone
                    cmd = [
                        'convert', logo_path,
                        '-resize', f'{logo_zone_width}x{logo_zone_height}!',
                        '-quality', '100',
                        temp_logo
                    ]
                    subprocess.run(cmd, check=True)
                    
                    # Composite logo onto output
                    cmd = [
                        'composite',
                        '-geometry', f'+{logo_min_x}+{logo_min_y}',
                        temp_logo,
                        output_path,
                        output_path
                    ]
                    subprocess.run(cmd, check=True)
                    logging.info(f"✅ Marquee logo placed successfully")
                    
                elif logo_source == 'text' and text_logo_settings and game_name:
                    # Generate text logo using helper functions
                    # Get settings
                    font_size = text_logo_settings.get('fontSize', 72)
                    color = text_logo_settings.get('color', '#ffffff')
                    font = text_logo_settings.get('font', 'Arial')
                    bold = text_logo_settings.get('bold', False)
                    italic = text_logo_settings.get('italic', False)
                    underline = text_logo_settings.get('underline', False)
                    uppercase = text_logo_settings.get('uppercase', False)
                    
                    # Calculate max chars per line from font size and zone width
                    # Average character width is approximately 0.6 * font_size
                    avg_char_width = font_size * 0.6
                    max_chars_per_line = max(5, int(logo_zone_width / avg_char_width))
                    
                    # Clean and prepare text
                    text = self._clean_game_name(game_name)
                    if uppercase:
                        text = text.upper()
                    
                    # Wrap text
                    text_lines = self._wrap_text_to_lines(text, max_chars_per_line=max_chars_per_line)
                    multiline_text = '\n'.join(text_lines)
                    
                    # Escape text for ImageMagick
                    escaped_text = multiline_text.replace('\\', '\\\\').replace('"', '\\"')
                    
                    # Generate text logo
                    logging.info(f"Generating text logo with font size {font_size}, max chars {max_chars_per_line}")
                    temp_logo = tempfile.NamedTemporaryFile(delete=False, suffix='.png').name
                    temp_files.append(temp_logo)
                    
                    # Check for custom font
                    font_path = font
                    custom_fonts_dir = 'var/fonts'
                    if os.path.exists(custom_fonts_dir):
                        font_extensions = ['.ttf', '.otf', '.woff', '.woff2', '.ttc', '.eot']
                        for ext in font_extensions:
                            font_file = os.path.join(custom_fonts_dir, f"{font}{ext}")
                            if os.path.exists(font_file):
                                font_path = font_file
                                break
                            for filename in os.listdir(custom_fonts_dir):
                                if os.path.splitext(filename)[0] == font:
                                    font_path = os.path.join(custom_fonts_dir, filename)
                                    break
                    
                    # Build font style
                    font_style = []
                    if bold:
                        font_style.append('Bold')
                    if italic:
                        font_style.append('Italic')
                    if font_style:
                        font_path = f"{font_path}-{'-'.join(font_style)}"
                    
                    # Calculate caption width based on zone width
                    caption_width = int(logo_zone_width * 0.95)  # Use 95% of zone width
                    
                    # Generate text logo
                    cmd = [
                        'convert',
                        '-background', 'transparent',
                        '-fill', color,
                        '-font', font_path,
                        '-pointsize', str(font_size),
                        '-size', f'{caption_width}x',
                        '-gravity', 'center',
                        f'caption:{escaped_text}',
                        temp_logo
                    ]
                    
                    if underline:
                        # Add underline using -annotate or -draw
                        cmd.insert(-1, '-annotate')
                        cmd.insert(-1, '+0+0')
                        cmd.insert(-1, escaped_text)
                    
                    subprocess.run(cmd, check=True)
                    
                    # Resize logo to fit zone height if needed
                    identify_cmd = ['identify', '-format', '%h', temp_logo]
                    logo_height_result = subprocess.run(identify_cmd, capture_output=True, text=True, timeout=5)
                    if logo_height_result.returncode == 0:
                        logo_height = int(logo_height_result.stdout.strip())
                        if logo_height > logo_zone_height:
                            # Scale down to fit height
                            scale_factor = logo_zone_height / logo_height
                            new_width = int(caption_width * scale_factor)
                            cmd_resize = [
                                'convert', temp_logo,
                                '-resize', f'{new_width}x{logo_zone_height}',
                                temp_logo
                            ]
                            subprocess.run(cmd_resize, check=True)
                    
                    # Composite logo onto output
                    cmd = [
                        'composite',
                        '-geometry', f'+{logo_min_x}+{logo_min_y}',
                        temp_logo,
                        output_path,
                        output_path
                    ]
                    subprocess.run(cmd, check=True)
                    logging.info(f"✅ Text logo generated and placed successfully")
            
            logging.info(f"✅ Template box generated successfully: {output_path}")
            return True
            
        except subprocess.CalledProcessError as e:
            logging.error(f"ImageMagick command failed: {e}")
            raise Exception(f"Image generation failed: {e}")
        except Exception as e:
            logging.error(f"Error generating template box: {e}")
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
