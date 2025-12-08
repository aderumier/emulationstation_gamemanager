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
    
    def _clean_game_name(self, text):
        """
        Remove text between parentheses () and brackets [] at the end of the text,
        including the brackets/parentheses themselves.
        Handles multiple occurrences (e.g., "Game (USA) [Rev 1]" -> "Game")
        """
        import re
        if not text:
            return text
        
        cleaned = text
        while True:
            # Try to remove trailing () or []
            new_cleaned = re.sub(r'\s*[\[\(][^\[\]\(\)]*[\]\)]\s*$', '', cleaned)
            if new_cleaned == cleaned:
                break
            cleaned = new_cleaned
        
        return cleaned.strip()
    
    def _wrap_text_to_lines(self, text, max_chars_per_line=15):
        """
        Wrap text into multiple lines, keeping around max_chars_per_line characters per line.
        Never splits words - only splits on spaces.
        Tries to distribute text evenly across lines and avoid last lines with less than 5 characters.
        Returns a list of lines.
        """
        if not text:
            return ['']
        
        words = text.split()
        if not words:
            return ['']
        
        # If text fits on one line, return it
        total_length = sum(len(word) for word in words) + len(words) - 1
        if total_length <= max_chars_per_line:
            return [' '.join(words)]
        
        # Calculate optimal number of lines
        num_lines = max(1, (total_length + max_chars_per_line - 1) // max_chars_per_line)
        target_chars_per_line = total_length / num_lines
        
        lines = []
        current_line = []
        current_length = 0
        
        for i, word in enumerate(words):
            word_length = len(word)
            
            should_wrap = False
            if current_length > 0:
                # If adding this word would exceed max, wrap
                if current_length + 1 + word_length > max_chars_per_line:
                    should_wrap = True
                # If we're past target and have more words, consider wrapping
                elif current_length >= target_chars_per_line and i < len(words) - 1:
                    should_wrap = True
            
            if should_wrap:
                lines.append(' '.join(current_line))
                current_line = [word]
                current_length = word_length
            else:
                if current_length > 0:
                    current_length += 1  # For space
                current_line.append(word)
                current_length += word_length
        
        # Add the last line
        if current_line:
            last_line = ' '.join(current_line)
            # If last line is too short and we have previous lines, merge with previous
            if len(last_line) < 5 and lines:
                lines[-1] = lines[-1] + ' ' + last_line
            else:
                lines.append(last_line)
        
        return lines if lines else ['']
    
    def generate_single_line_text_logo(self, game_name, text_logo_settings, output_path, width=None):
        """
        Generate a single-line text logo image from game name.
        
        Args:
            game_name: Name of the game
            text_logo_settings: Dict with text logo settings (color, font_size, font, alignment, etc.)
            output_path: Path where the generated logo will be saved
            width: Optional width for the logo (if None, will be auto-calculated)
        
        Returns:
            Path to generated logo file, or None if generation failed
        """
        try:
            # Get settings
            font_size = text_logo_settings.get('fontSize') or 72
            color = text_logo_settings.get('color') or '#ffffff'
            font = text_logo_settings.get('font') or 'Arial'
            alignment = text_logo_settings.get('alignment', 'center')
            
            # Convert alignment to ImageMagick gravity
            gravity_map = {
                'left': 'west',
                'center': 'center',
                'right': 'east'
            }
            gravity = gravity_map.get(alignment, 'center')
            
            # Clean and prepare text (single line, no wrapping)
            text = self._clean_game_name(game_name)
            if text_logo_settings.get('uppercase', False):
                text = text.upper()
            
            # Escape text for ImageMagick
            escaped_text = text.replace('\\', '\\\\').replace('"', '\\"')
            
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
                # Also check with exact filename match
                if font_path == font:
                    for filename in os.listdir(custom_fonts_dir):
                        if os.path.splitext(filename)[0] == font:
                            font_path = os.path.join(custom_fonts_dir, filename)
                            break
            
            # Calculate width if not provided (estimate based on text length and font size)
            if width is None:
                # Average character width is ~0.4-0.5 times font size
                avg_char_width = font_size * 0.5
                estimated_width = int(len(text) * avg_char_width * 1.2)  # Add 20% padding
                width = max(200, estimated_width)  # Minimum 200px
            
            # Build command for text generation
            cmd = [
                'convert',
                '-background', 'none',
                '-fill', color,
                '-font', font_path,
                '-pointsize', str(font_size),
            ]
            
            # Simulate bold using stroke
            if text_logo_settings.get('bold', False):
                cmd.extend(['-stroke', color, '-strokewidth', '1'])
            
            # Add shear for italic effect
            if text_logo_settings.get('italic', False):
                cmd.extend(['-shear', '15x0'])
            
            # Generate text logo (single line)
            cmd.extend([
                '-size', f'{width}x',
                '-gravity', gravity,
                f'caption:{escaped_text}',
                output_path
            ])
            
            logging.info(f"Generating single-line text logo: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode != 0:
                logging.error(f"ImageMagick text generation failed: {result.stderr}")
                return None
            
            # Add underline if needed
            if text_logo_settings.get('underline', False):
                identify_cmd = ['identify', '-format', '%wx%h', output_path]
                dim_result = subprocess.run(identify_cmd, capture_output=True, text=True, timeout=5)
                if dim_result.returncode == 0:
                    logo_width, logo_height = dim_result.stdout.strip().split('x')
                    underline_y = int(logo_height) - 2
                    temp_with_underline = output_path + '.tmp'
                    cmd_underline = [
                        'convert', output_path,
                        '-stroke', color,
                        '-strokewidth', '2',
                        '-draw', f'line 0,{underline_y} {logo_width},{underline_y}',
                        temp_with_underline
                    ]
                    logging.info(f"Adding underline: {' '.join(cmd_underline)}")
                    subprocess.run(cmd_underline, check=True)
                    os.replace(temp_with_underline, output_path)
            
            if os.path.exists(output_path):
                logging.info(f"✅ Single-line text logo generated: {output_path}")
                return output_path
            else:
                logging.error(f"Text logo file was not created: {output_path}")
                return None
                
        except Exception as e:
            logging.error(f"Error generating single-line text logo: {e}")
            import traceback
            traceback.print_exc()
            return None
    
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
                
                # Determine the logo file to use (either existing marquee or generated text logo)
                logo_file_to_use = None
                logo_placement_gravity = 'center'  # Default gravity for logo placement
                
                if logo_source == 'marquee' and logo_path and os.path.exists(logo_path):
                    # Use existing marquee logo
                    logo_file_to_use = logo_path
                    logging.info(f"Using existing marquee logo: {logo_path}")
                    
                elif logo_source == 'text' and text_logo_settings and game_name:
                    # Generate text logo to a temporary file first
                    logging.info(f"Generating text logo for: {game_name}")
                    
                    # Get settings (use 'or' to handle None values explicitly)
                    font_size = text_logo_settings.get('fontSize') or 72
                    color = text_logo_settings.get('color') or '#ffffff'
                    font = text_logo_settings.get('font') or 'Arial'
                    bold = text_logo_settings.get('bold', False)
                    italic = text_logo_settings.get('italic', False)
                    underline = text_logo_settings.get('underline', False)
                    uppercase = text_logo_settings.get('uppercase', False)
                    alignment = text_logo_settings.get('alignment', 'middle')
                    user_max_chars = text_logo_settings.get('maxCharsPerLine', None)
                    
                    # Convert alignment to ImageMagick gravity
                    gravity_map = {
                        'top-left': 'northwest',
                        'top-middle': 'north',
                        'top-right': 'northeast',
                        'middle-left': 'west',
                        'middle': 'center',
                        'middle-right': 'east',
                        'bottom-left': 'southwest',
                        'bottom-middle': 'south',
                        'bottom-right': 'southeast',
                        # Legacy support for old values
                        'left': 'west',
                        'center': 'center',
                        'right': 'east'
                    }
                    gravity = gravity_map.get(alignment, 'center')
                    
                    # Use user-specified max chars per line, or calculate from font size and zone width
                    # Minimum of 5 characters per line is enforced in all cases
                    if user_max_chars and user_max_chars > 0:
                        max_chars_per_line = max(5, user_max_chars)
                    else:
                        # Average character width for proportional fonts is ~0.4-0.5 times font size
                        # Using 0.4 as it's more accurate for most fonts and allows better text fitting
                        avg_char_width = font_size * 0.4
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
                    
                    logging.info(f"Text logo settings: font_size={font_size}, max_chars={max_chars_per_line}, alignment={alignment}, text='{multiline_text}'")
                    
                    # Create temp file for generated text logo
                    temp_generated_logo = tempfile.NamedTemporaryFile(delete=False, suffix='.png').name
                    temp_files.append(temp_generated_logo)
                    
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
                        # Also check with exact filename match
                        if font_path == font:
                            for filename in os.listdir(custom_fonts_dir):
                                if os.path.splitext(filename)[0] == font:
                                    font_path = os.path.join(custom_fonts_dir, filename)
                                    break
                    
                    # Calculate caption width based on zone width
                    caption_width = int(logo_zone_width * 0.95)
                    
                    # Build base command for text generation
                    cmd = [
                        'convert',
                        '-background', 'none',
                        '-fill', color,
                        '-font', font_path,
                        '-pointsize', str(font_size),
                    ]
                    
                    # Simulate bold using stroke
                    if bold:
                        cmd.extend(['-stroke', color, '-strokewidth', '1'])
                    
                    # Add shear for italic effect
                    if italic:
                        cmd.extend(['-shear', '15x0'])
                    
                    # For underline, we need to draw it separately
                    if underline:
                        temp_text = tempfile.NamedTemporaryFile(delete=False, suffix='.png').name
                        temp_files.append(temp_text)
                        
                        cmd_text = cmd + [
                            '-size', f'{caption_width}x',
                            '-gravity', gravity,
                            f'caption:{escaped_text}',
                            temp_text
                        ]
                        logging.info(f"Generating text logo (text step): {' '.join(cmd_text)}")
                        result = subprocess.run(cmd_text, capture_output=True, text=True, timeout=30)
                        if result.returncode != 0:
                            logging.error(f"ImageMagick text generation failed: {result.stderr}")
                            raise Exception(f"ImageMagick text generation failed: {result.stderr}")
                        
                        # Get text dimensions and draw underline
                        identify_cmd = ['identify', '-format', '%wx%h', temp_text]
                        dim_result = subprocess.run(identify_cmd, capture_output=True, text=True, timeout=5)
                        if dim_result.returncode == 0:
                            width, height = dim_result.stdout.strip().split('x')
                            underline_y = int(height) - 2
                            cmd_underline = [
                                'convert', temp_text,
                                '-stroke', color,
                                '-strokewidth', '2',
                                '-draw', f'line 0,{underline_y} {width},{underline_y}',
                                temp_generated_logo
                            ]
                            logging.info(f"Adding underline: {' '.join(cmd_underline)}")
                            subprocess.run(cmd_underline, check=True)
                        else:
                            import shutil
                            shutil.copy(temp_text, temp_generated_logo)
                    else:
                        # No underline - generate directly
                        cmd.extend([
                            '-size', f'{caption_width}x',
                            '-gravity', gravity,
                            f'caption:{escaped_text}',
                            temp_generated_logo
                        ])
                        logging.info(f"Generating text logo: {' '.join(cmd)}")
                        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                        if result.returncode != 0:
                            logging.error(f"ImageMagick text generation failed: {result.stderr}")
                            raise Exception(f"ImageMagick text generation failed: {result.stderr}")
                    
                    # Verify the generated logo exists
                    if os.path.exists(temp_generated_logo):
                        logo_file_to_use = temp_generated_logo
                        # Store the gravity for text logo placement (to preserve alignment)
                        logo_placement_gravity = gravity
                        logging.info(f"✅ Text logo generated successfully: {temp_generated_logo}")
                    else:
                        logging.error(f"Text logo file was not created: {temp_generated_logo}")
                
                # Now place the logo (same code for both marquee and text logo)
                if logo_file_to_use and os.path.exists(logo_file_to_use):
                    logging.info(f"Placing logo at position ({logo_min_x}, {logo_min_y}), zone size: {logo_zone_width}x{logo_zone_height}")
                    
                    # Create temp file for resized logo
                    temp_logo = tempfile.NamedTemporaryFile(delete=False, suffix='.png').name
                    temp_files.append(temp_logo)
                    
                    # Resize logo to fit zone
                    # Uses logo_placement_gravity (alignment-based for text logos, center for marquee)
                    cmd = [
                        'convert', logo_file_to_use,
                        '-resize', f'{logo_zone_width}x{logo_zone_height}',
                        '-background', 'none',
                        '-gravity', logo_placement_gravity,
                        '-extent', f'{logo_zone_width}x{logo_zone_height}',
                        '-quality', '100',
                        temp_logo
                    ]
                    logging.info(f"Resizing logo with gravity '{logo_placement_gravity}': {' '.join(cmd)}")
                    subprocess.run(cmd, check=True)
                    
                    # Composite logo onto output (same as marquee)
                    cmd = [
                        'composite',
                        '-geometry', f'+{logo_min_x}+{logo_min_y}',
                        temp_logo,
                        output_path,
                        output_path
                    ]
                    logging.info(f"Compositing logo: {' '.join(cmd)}")
                    subprocess.run(cmd, check=True)
                    logging.info(f"✅ Logo placed successfully")
            
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

    def generate_spine_background(self, box2d_path, spine_width, output_path, debug=False):
        """
        Generate a spine background by cropping the left side of a 2D box and mirroring it.
        
        Args:
            box2d_path: Path to the 2D box image
            spine_width: Width of the spine in template coordinates (will be used directly as pixel width)
            output_path: Path where the generated spine will be saved
            debug: If True, log the command
        """
        if not os.path.exists(box2d_path):
            raise Exception(f"2D box image not found: {box2d_path}")
        
        if spine_width <= 0:
            raise Exception(f"Invalid spine width: {spine_width}")
        
        # Get the dimensions of the 2D box
        cmd_info = [
            'identify',
            '-format', '%wx%h',
            box2d_path
        ]
        result = subprocess.run(cmd_info, capture_output=True, text=True, check=True)
        box_dims = result.stdout.strip().split('x')
        box_width = int(box_dims[0])
        box_height = int(box_dims[1])
        
        # Use spine_width directly as the crop width (in pixels)
        crop_width = int(spine_width)
        
        # Ensure crop_width is within bounds
        if crop_width <= 0:
            crop_width = max(1, int(box_width * 0.1))  # Default to 10% of box width
        if crop_width > box_width:
            crop_width = box_width
        
        # Crop left side: crop from (0,0) with width=crop_width, height=box_height
        # Then flip horizontally with -flop
        cmd = [
            'convert',
            box2d_path,
            '-crop', f'{crop_width}x{box_height}+0+0',  # Crop from left: width x height +x +y
            '-flop',  # Mirror horizontally
            output_path
        ]
        
        if debug:
            logging.info(f"Generating spine background: box={box_width}x{box_height}, spine_width={spine_width}, crop_width={crop_width}")
            logging.info(f"Generating spine background: {' '.join(cmd)}")
        
        subprocess.run(cmd, check=True, capture_output=True, text=True)
        
        if not os.path.exists(output_path):
            raise Exception(f"Generated spine background file was not created: {output_path}")
        
        logging.info(f"✅ Spine background generated successfully: {output_path}")
        return output_path

    def generate_3dbox(self, background_path, box2d_path, output_path, corners, spine_corners=None, spine_image_path=None, spine_logo_path=None, generated_spine_path=None, debug=False):
        """
        Generate a 3D box by applying perspective distortion to a 2D box image
        and compositing it onto a 3D box template.
        
        Args:
            background_path: Path to the 3D box template image
            box2d_path: Path to the 2D box image to be placed
            output_path: Path where the generated 3D box will be saved
            corners: Dictionary with front corner positions:
                {
                    'topLeft': {'x': int, 'y': int},
                    'topRight': {'x': int, 'y': int},
                    'bottomLeft': {'x': int, 'y': int},
                    'bottomRight': {'x': int, 'y': int}
                }
            spine_corners: Optional dictionary with spine corner positions (same format as corners)
            debug: If True, keep intermediate temp images for debugging
        """
        temp_files = []
        temp_dir = None
        
        try:
            # Extract corner coordinates
            tl = corners.get('topLeft', {'x': 0, 'y': 0})
            tr = corners.get('topRight', {'x': 0, 'y': 0})
            bl = corners.get('bottomLeft', {'x': 0, 'y': 0})
            br = corners.get('bottomRight', {'x': 0, 'y': 0})
            
            target_topleft_x = int(tl.get('x', 0))
            target_topleft_y = int(tl.get('y', 0))
            target_topright_x = int(tr.get('x', 0))
            target_topright_y = int(tr.get('y', 0))
            target_bottomleft_x = int(bl.get('x', 0))
            target_bottomleft_y = int(bl.get('y', 0))
            target_bottomright_x = int(br.get('x', 0))
            target_bottomright_y = int(br.get('y', 0))
            
            # Calculate resize dimensions
            # width = target_topright_x - target_topleft_x
            # height = target_bottomleft_y - target_topleft_y
            resize_width = target_topright_x - target_topleft_x
            resize_height = target_bottomleft_y - target_topleft_y
            
            if resize_width <= 0 or resize_height <= 0:
                raise Exception(f"Invalid corner positions: calculated resize {resize_width}x{resize_height}")
            
            logging.info(f"3D Box: Resize dimensions {resize_width}x{resize_height}")
            logging.info(f"3D Box: Target corners - TL({target_topleft_x},{target_topleft_y}) TR({target_topright_x},{target_topright_y}) BL({target_bottomleft_x},{target_bottomleft_y}) BR({target_bottomright_x},{target_bottomright_y})")
            
            # Create temp directory - use fixed location for debug mode
            if debug:
                temp_dir = 'var/debug/3dbox'
                os.makedirs(temp_dir, exist_ok=True)
                # Use output filename as base for debug files
                output_base = os.path.splitext(os.path.basename(output_path))[0]
                temp_resized = os.path.join(temp_dir, f'{output_base}_1_resized.png')
                temp_perspective = os.path.join(temp_dir, f'{output_base}_2_perspective.png')
                temp_perspective_resized = os.path.join(temp_dir, f'{output_base}_3_perspective_resized.png')
                logging.info(f"🔧 DEBUG MODE: Keeping intermediate files in {temp_dir}")
            else:
                temp_dir = tempfile.mkdtemp(prefix='3dbox_')
                temp_resized = os.path.join(temp_dir, 'resized_2dbox.png')
                temp_perspective = os.path.join(temp_dir, 'perspective_2dbox.png')
                temp_perspective_resized = os.path.join(temp_dir, 'perspective_resized_2dbox.png')
            
            temp_files.append(temp_resized)
            temp_files.append(temp_perspective)
            temp_files.append(temp_perspective_resized)
            
            # Step 1: Resize the 2D box to fit the target area (no aspect ratio)
            cmd_resize = [
                'convert',
                box2d_path,
                '-resize', f'{resize_width}x{resize_height}!',
                temp_resized
            ]
            logging.info(f"3D Box Step 1 - Resize: {' '.join(cmd_resize)}")
            subprocess.run(cmd_resize, check=True)
            if debug:
                logging.info(f"🔧 DEBUG: Resized image saved to: {temp_resized}")
            
            # Step 2: Compute source coordinates (rectangle before distortion)
            # The source coordinates form a rectangle at the target position
            # This rectangle will be distorted to match the target quadrilateral
            source_topleft_x = target_topleft_x
            source_topleft_y = target_topleft_y
            source_topright_x = target_topright_x
            source_topright_y = target_topleft_y
            source_bottomleft_x = target_topleft_x
            source_bottomleft_y = target_bottomleft_y
            source_bottomright_x = target_topright_x
            source_bottomright_y = target_bottomleft_y
            
            logging.info(f"3D Box: Source rectangle - TL({source_topleft_x},{source_topleft_y}) TR({source_topright_x},{source_topright_y}) BL({source_bottomleft_x},{source_bottomleft_y}) BR({source_bottomright_x},{source_bottomright_y})")
            
            # Step 3: Apply perspective distortion
            # The perspective distortion maps source rectangle corners to target quadrilateral corners
            perspective_str = (
                f'{source_topleft_x},{source_topleft_y} {target_topleft_x},{target_topleft_y}  '
                f'{source_topright_x},{source_topright_y} {target_topright_x},{target_topright_y}  '
                f'{source_bottomright_x},{source_bottomright_y} {target_bottomright_x},{target_bottomright_y}  '
                f'{source_bottomleft_x},{source_bottomleft_y} {target_bottomleft_x},{target_bottomleft_y}'
            )
            
            cmd_perspective = [
                'convert',
                temp_resized,
                '-background', 'none',
                '-virtual-pixel', 'transparent',
                '-alpha', 'set',
                '+distort', 'Perspective', perspective_str,
                temp_perspective
            ]
            logging.info(f"3D Box Step 2 - Perspective: {' '.join(cmd_perspective)}")
            subprocess.run(cmd_perspective, check=True)
            if debug:
                logging.info(f"🔧 DEBUG: Perspective image saved to: {temp_perspective}")
            
            # Step 4: Resize perspective image back to the same dimensions as the first resize
            # Use -resize (not -extent) to scale without cropping
            cmd_resize_perspective = [
                'convert',
                temp_perspective,
                '-resize', f'{resize_width}x{resize_height}!',
                temp_perspective_resized
            ]
            logging.info(f"3D Box Step 3 - Resize to {resize_width}x{resize_height}: {' '.join(cmd_resize_perspective)}")
            subprocess.run(cmd_resize_perspective, check=True)
            if debug:
                logging.info(f"🔧 DEBUG: Resized perspective image saved to: {temp_perspective_resized}")
            
            # Step 5: Composite the distorted 2D box onto the 3D box template
            # Use composite with exact geometry positioning at source top-left coordinates
            cmd_composite = [
                'composite',
                '-geometry', f'+{source_topleft_x}+{source_topleft_y}',
                temp_perspective_resized,
                background_path,
                output_path
            ]
            logging.info(f"3D Box Step 4 - Composite front at ({source_topleft_x},{source_topleft_y}): {' '.join(cmd_composite)}")
            subprocess.run(cmd_composite, check=True)
            
            # Process spine if spine_corners are provided and not all zero
            if spine_corners:
                spine_tl = spine_corners.get('topLeft', {'x': 0, 'y': 0})
                spine_tr = spine_corners.get('topRight', {'x': 0, 'y': 0})
                spine_bl = spine_corners.get('bottomLeft', {'x': 0, 'y': 0})
                spine_br = spine_corners.get('bottomRight', {'x': 0, 'y': 0})
                
                spine_has_corners = (
                    (spine_tl.get('x', 0) > 0 or spine_tl.get('y', 0) > 0) or
                    (spine_tr.get('x', 0) > 0 or spine_tr.get('y', 0) > 0) or
                    (spine_bl.get('x', 0) > 0 or spine_bl.get('y', 0) > 0) or
                    (spine_br.get('x', 0) > 0 or spine_br.get('y', 0) > 0)
                )
                
                if spine_has_corners:
                    logging.info(f"3D Box: Processing spine surface")
                    
                    spine_target_topleft_x = int(spine_tl.get('x', 0))
                    spine_target_topleft_y = int(spine_tl.get('y', 0))
                    spine_target_topright_x = int(spine_tr.get('x', 0))
                    spine_target_topright_y = int(spine_tr.get('y', 0))
                    spine_target_bottomleft_x = int(spine_bl.get('x', 0))
                    spine_target_bottomleft_y = int(spine_bl.get('y', 0))
                    spine_target_bottomright_x = int(spine_br.get('x', 0))
                    spine_target_bottomright_y = int(spine_br.get('y', 0))
                    
                    # Use new resize dimensions for spine: width = target_topright_x - target_topleft_x, height = target_bottomright_y - target_topright_y
                    spine_resize_width = spine_target_topright_x - spine_target_topleft_x
                    spine_resize_height = spine_target_bottomright_y - spine_target_topright_y
                    
                    if spine_resize_width > 0 and spine_resize_height > 0:
                        # Determine which image to use for spine
                        # Use generated_spine_path if provided (same workflow as when no spine is provided)
                        # Otherwise use spine_image_path if provided, else fallback to box2d_path
                        if generated_spine_path and os.path.exists(generated_spine_path):
                            spine_source_image = generated_spine_path
                        elif spine_image_path and os.path.exists(spine_image_path):
                            spine_source_image = spine_image_path
                        else:
                            spine_source_image = box2d_path
                        if not os.path.exists(spine_source_image):
                            logging.warning(f"Spine source image not found: {spine_source_image}, skipping spine")
                        else:
                            # Create temp files for spine
                            if debug:
                                output_base = os.path.splitext(os.path.basename(output_path))[0]
                                temp_spine_resized = os.path.join(temp_dir, f'{output_base}_spine_1_resized.png')
                                temp_spine_perspective = os.path.join(temp_dir, f'{output_base}_spine_2_perspective.png')
                                temp_spine_perspective_resized = os.path.join(temp_dir, f'{output_base}_spine_3_perspective_resized.png')
                            else:
                                temp_spine_resized = os.path.join(temp_dir, 'spine_resized.png')
                                temp_spine_perspective = os.path.join(temp_dir, 'spine_perspective.png')
                                temp_spine_perspective_resized = os.path.join(temp_dir, 'spine_perspective_resized.png')
                            
                            temp_files.extend([temp_spine_resized, temp_spine_perspective, temp_spine_perspective_resized])
                            
                            # Step S1: Resize the spine image (or 2D box if no spine image) to fit the target area
                            cmd_spine_resize = [
                                'convert',
                                spine_source_image,
                                '-resize', f'{spine_resize_width}x{spine_resize_height}!',
                                temp_spine_resized
                            ]
                            logging.info(f"3D Box Spine Step 1 - Resize {spine_source_image} to {spine_resize_width}x{spine_resize_height}: {' '.join(cmd_spine_resize)}")
                            subprocess.run(cmd_spine_resize, check=True)
                            
                            # Step S1.5: Add logo to spine if using uploaded spine and logo is provided
                            if spine_logo_path and os.path.exists(spine_logo_path) and spine_image_path and os.path.exists(spine_image_path):
                                # Logo should only be added when using uploaded spine (not from game's spine field)
                                logging.info(f"3D Box Spine: Adding logo from {spine_logo_path}")
                                
                                # Create temp file for rotated and resized logo
                                if debug:
                                    output_base = os.path.splitext(os.path.basename(output_path))[0]
                                    temp_logo_rotated_resized = os.path.join(temp_dir, f'{output_base}_spine_logo_rotated_resized.png')
                                else:
                                    temp_logo_rotated_resized = os.path.join(temp_dir, 'spine_logo_rotated_resized.png')
                                
                                temp_files.append(temp_logo_rotated_resized)
                                
                                # Rotate logo 90 degrees and resize to 80% of spine width (maintain aspect ratio)
                                logo_target_width = int(spine_resize_width * 0.8)  # 80% of spine width
                                cmd_logo_rotate_resize = [
                                    'convert',
                                    spine_logo_path,
                                    '-rotate', '90',
                                    '-resize', f'{logo_target_width}x',  # Resize to 80% of spine width, maintain aspect ratio
                                    temp_logo_rotated_resized
                                ]
                                logging.info(f"3D Box Spine: Rotate and resize logo to {logo_target_width}px width (80% of spine width): {' '.join(cmd_logo_rotate_resize)}")
                                subprocess.run(cmd_logo_rotate_resize, check=True)
                                
                                # Get logo dimensions after rotation and resize
                                identify_cmd = ['identify', '-format', '%wx%h', temp_logo_rotated_resized]
                                logo_dim_result = subprocess.run(identify_cmd, capture_output=True, text=True, timeout=5)
                                if logo_dim_result.returncode == 0:
                                    logo_dims = logo_dim_result.stdout.strip().split('x')
                                    logo_width = int(logo_dims[0])
                                    logo_height = int(logo_dims[1])
                                    
                                    # Calculate position: centered horizontally, at 2/3 of spine height
                                    logo_x = (spine_resize_width - logo_width) // 2  # Center horizontally
                                    logo_y = int(spine_resize_height * 2 / 3) - (logo_height // 2)  # At 2/3 height, centered vertically
                                    
                                    # Composite logo onto resized spine
                                    cmd_logo_composite = [
                                        'composite',
                                        '-geometry', f'+{logo_x}+{logo_y}',
                                        temp_logo_rotated_resized,
                                        temp_spine_resized,
                                        temp_spine_resized
                                    ]
                                    logging.info(f"3D Box Spine: Composite logo at ({logo_x}, {logo_y}): {' '.join(cmd_logo_composite)}")
                                    subprocess.run(cmd_logo_composite, check=True)
                                    logging.info(f"✅ Logo composited onto spine")
                                else:
                                    logging.warning(f"Failed to get logo dimensions, skipping logo composite")
                            
                            # Step S2: Compute spine source coordinates (new formula)
                            # source_topright_x = target_topright_x, source_topright_y = target_topright_y
                            # source_bottomright_x = target_topright_x, source_bottomright_y = target_bottomright_y
                            # source_topleft_x = target_topleft_x, source_topleft_y = target_topright_y
                            # source_bottomleft_x = target_topleft_x, source_bottomleft_y = target_bottomright_y
                            spine_source_topleft_x = spine_target_topleft_x
                            spine_source_topleft_y = spine_target_topright_y
                            spine_source_topright_x = spine_target_topright_x
                            spine_source_topright_y = spine_target_topright_y
                            spine_source_bottomleft_x = spine_target_topleft_x
                            spine_source_bottomleft_y = spine_target_bottomright_y
                            spine_source_bottomright_x = spine_target_topright_x
                            spine_source_bottomright_y = spine_target_bottomright_y
                            
                            # Step S3: Apply perspective distortion to spine
                            spine_perspective_str = (
                                f'{spine_source_topleft_x},{spine_source_topleft_y} {spine_target_topleft_x},{spine_target_topleft_y}  '
                                f'{spine_source_topright_x},{spine_source_topright_y} {spine_target_topright_x},{spine_target_topright_y}  '
                                f'{spine_source_bottomright_x},{spine_source_bottomright_y} {spine_target_bottomright_x},{spine_target_bottomright_y}  '
                                f'{spine_source_bottomleft_x},{spine_source_bottomleft_y} {spine_target_bottomleft_x},{spine_target_bottomleft_y}'
                            )
                            
                            cmd_spine_perspective = [
                                'convert',
                                temp_spine_resized,
                                '-background', 'none',
                                '-virtual-pixel', 'transparent',
                                '-alpha', 'set',
                                '-distort', 'Perspective', spine_perspective_str,
                                temp_spine_perspective
                            ]
                            logging.info(f"3D Box Spine Step 2 - Perspective: {' '.join(cmd_spine_perspective)}")
                            subprocess.run(cmd_spine_perspective, check=True)
                            
                            # Step S4: Resize perspective image back to the same dimensions as the first resize
                            cmd_spine_resize_perspective = [
                                'convert',
                                temp_spine_perspective,
                                '-resize', f'{spine_resize_width}x{spine_resize_height}!',
                                temp_spine_perspective_resized
                            ]
                            logging.info(f"3D Box Spine Step 3 - Resize: {' '.join(cmd_spine_resize_perspective)}")
                            subprocess.run(cmd_spine_resize_perspective, check=True)
                            
                            # Step S5: Composite spine onto the result (which already has front)
                            # Use source coordinates for compositing (exactly like the front surface)
                            cmd_spine_composite = [
                                'composite',
                                '-geometry', f'+{spine_source_topleft_x}+{spine_source_topleft_y}',
                                temp_spine_perspective_resized,
                                output_path,
                                output_path
                            ]
                            logging.info(f"3D Box Spine Step 4 - Composite at ({spine_source_topleft_x},{spine_source_topleft_y}): {' '.join(cmd_spine_composite)}")
                            subprocess.run(cmd_spine_composite, check=True)
                            
                            logging.info(f"✅ Spine composited successfully")
            
            logging.info(f"✅ 3D Box generated successfully: {output_path}")
            if debug:
                logging.info(f"🔧 DEBUG: Final output saved to: {output_path}")
                logging.info(f"🔧 DEBUG: All intermediate files kept in: {temp_dir}")
            return True
            
        except subprocess.CalledProcessError as e:
            logging.error(f"ImageMagick command failed: {e}")
            raise Exception(f"3D box generation failed: {e}")
        except Exception as e:
            logging.error(f"Error generating 3D box: {e}")
            raise
        finally:
            # Cleanup temp files only if not in debug mode
            if not debug:
                for temp_file in temp_files:
                    try:
                        if os.path.exists(temp_file):
                            os.remove(temp_file)
                    except Exception as e:
                        logging.warning(f"Could not remove temp file {temp_file}: {e}")
                # Also cleanup temp directory
                if temp_dir and os.path.exists(temp_dir) and temp_dir.startswith('/tmp'):
                    try:
                        import shutil
                        shutil.rmtree(temp_dir)
                    except Exception as e:
                        logging.warning(f"Could not remove temp dir {temp_dir}: {e}")


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
