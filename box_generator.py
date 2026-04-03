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
import shutil

def _imagemagick_cmd(subcommand):
    """ImageMagick argv prefix (convert/identify/composite). IM 7 uses magick.exe on Windows."""
    from game_utils import get_imagemagick_cmd
    return get_imagemagick_cmd(subcommand)

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
        """Validate that ImageMagick is available (uses bundled path on Windows)."""
        try:
            result = subprocess.run(_imagemagick_cmd('convert') + ['-version'],
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
                        font_path = os.path.abspath(font_file)
                        break
                # Also check with exact filename match
                if font_path == font:
                    for filename in os.listdir(custom_fonts_dir):
                        if os.path.splitext(filename)[0] == font:
                            font_path = os.path.abspath(os.path.join(custom_fonts_dir, filename))
                            break

            # Calculate width if not provided (estimate based on text length and font size)
            if width is None:
                # Average character width is ~0.4-0.5 times font size
                avg_char_width = font_size * 0.5
                estimated_width = int(len(text) * avg_char_width * 1.03)  # Add 3% padding
                width = max(200, estimated_width)  # Minimum 200px
            
            # Build command for text generation
            cmd = _imagemagick_cmd('convert') + [
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
            
            # Generate text logo (single line) - use label: instead of caption: to prevent wrapping
            cmd.extend([
                '-size', f'{width}x',
                '-gravity', gravity,
                f'label:{escaped_text}',
                output_path
            ])
            
            logging.info(f"Generating single-line text logo: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode != 0:
                logging.error(f"ImageMagick text generation failed: {result.stderr}")
                return None
            
            # Trim whitespace/padding from the generated image
            temp_trimmed = output_path + '.trimmed'
            cmd_trim = _imagemagick_cmd('convert') + [
                output_path,
                '-trim',
                '+repage',
                temp_trimmed
            ]
            trim_result = subprocess.run(cmd_trim, capture_output=True, text=True, timeout=10)
            if trim_result.returncode == 0:
                # Replace original with trimmed version
                os.replace(temp_trimmed, output_path)
            else:
                logging.warning(f"Failed to trim text logo: {trim_result.stderr}")
                # Continue with original if trim fails
            
            # Add underline if needed
            if text_logo_settings.get('underline', False):
                identify_cmd = _imagemagick_cmd('identify') + ['-format', '%wx%h', output_path]
                dim_result = subprocess.run(identify_cmd, capture_output=True, text=True, timeout=5)
                if dim_result.returncode == 0:
                    logo_width, logo_height = dim_result.stdout.strip().split('x')
                    underline_y = int(logo_height) - 2
                    temp_with_underline = output_path + '.tmp'
                    cmd_underline = _imagemagick_cmd('convert') + [
                        output_path,
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
                cmd = _imagemagick_cmd('convert') + [
                    additional_screenshot_path,
                    '-resize', f'{additional_width}x{additional_height}>',
                    '-bordercolor', self.title_border_color,
                    '-border', f'{self.title_border_size}x{self.title_border_size}',
                    'temp_additional_screenshot.png'
                ]
                subprocess.run(cmd, check=True)
                temp_files.append('temp_additional_screenshot.png')
                # Get actual height for positioning calculations
                identify_cmd = _imagemagick_cmd('identify') + ['-format', '%h', 'temp_additional_screenshot.png']
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
                cmd = _imagemagick_cmd('convert') + [
                    titlescreen_path,
                    '-resize', f'{self.width}x{self.height}^',
                    '-gravity', 'center',
                    '-extent', f'{self.width}x{self.height}',
                    '-blur', f'0x{self.blur_intensity}',
                    'temp_blurred_bg.png'
                ]
                subprocess.run(cmd, check=True)
                temp_files.append('temp_blurred_bg.png')
                base_bg = 'temp_blurred_bg.png'
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
                    cmd = _imagemagick_cmd('convert') + [
                        base_bg,
                        'temp_additional_screenshot.png',
                        '-gravity', 'center',
                        '-geometry', additional_geometry,
                        '-composite', 'temp_bg_with_additional.png'
                    ]
                    subprocess.run(cmd, check=True)
                    temp_files.append('temp_bg_with_additional.png')
                    base_bg = 'temp_bg_with_additional.png'
                else:
                    # Create solid background and add additional screenshot
                    cmd = _imagemagick_cmd('convert') + [
                        '-size', f'{self.width}x{self.height}',
                        f'xc:{self.background_color}',
                        'temp_additional_screenshot.png',
                        '-gravity', 'center',
                        '-geometry', additional_geometry,
                        '-composite', 'temp_bg_with_additional.png'
                    ]
                    subprocess.run(cmd, check=True)
                    temp_files.append('temp_bg_with_additional.png')
                    base_bg = 'temp_bg_with_additional.png'
            
            # Prepare gameplay image with border
            # If additional screenshot exists, resize to fit bottom third only
            if additional_screenshot_path and os.path.exists(additional_screenshot_path):
                # Resize to fit in bottom third (66-100% of height, ~33% of total height)
                # But allow it to be a bit larger to fill the space better
                gameplay_height = int(self.height * 40 / 100)  # Slightly larger than 33% to fill bottom third
                logging.info(f"Resizing gameplay to fit bottom third: {gameplay_width}x{gameplay_height}")
                cmd = _imagemagick_cmd('convert') + [
                    gameplay_path,
                    '-resize', f'{gameplay_width}x{gameplay_height}>',
                    '-bordercolor', self.title_border_color,
                    '-border', f'{self.title_border_size}x{self.title_border_size}',
                    'temp_main.png'
                ]
            else:
                # Normal resize (75% width, full height) - resize to fit while maintaining aspect ratio
                # Remove '>' so smaller images are upscaled to match the target size
                cmd = _imagemagick_cmd('convert') + [
                    gameplay_path,
                    '-resize', f'{gameplay_width}x{self.height}',  # Resize to fit, maintain aspect ratio
                    '-bordercolor', self.title_border_color,
                    '-border', f'{self.title_border_size}x{self.title_border_size}',
                    'temp_main.png'
                ]
            subprocess.run(cmd, check=True)
            temp_files.append('temp_main.png')
            
            # Compose gameplay onto background (now includes additional screenshot if present)
            logging.info(f"Composing gameplay at offset: +0+{gameplay_y_offset} (from center)")
            if self.use_blurred_bg:
                # Use base_bg which may already have additional screenshot
                cmd = _imagemagick_cmd('convert') + [
                    base_bg, 'temp_main.png',
                    '-gravity', 'center',
                    '-geometry', f'+0+{gameplay_y_offset}',
                    '-composite', 'temp_bg.png'
                ]
                subprocess.run(cmd, check=True)
                temp_files.append('temp_bg.png')
            else:
                # Create background with gameplay positioned in lower 2/3
                if base_bg:
                    # base_bg already has additional screenshot, just add gameplay
                    cmd = _imagemagick_cmd('convert') + [
                        base_bg, 'temp_main.png',
                        '-gravity', 'center',
                        '-geometry', f'+0+{gameplay_y_offset}',
                        '-composite', 'temp_bg.png'
                    ]
                else:
                    # No additional screenshot, create normal background
                    cmd = _imagemagick_cmd('convert') + [
                        '-size', f'{self.width}x{self.height}',
                        f'xc:{self.background_color}',
                        'temp_main.png',
                        '-gravity', 'center',
                        '-geometry', f'+0+{gameplay_y_offset}',
                        '-composite', 'temp_bg.png'
                    ]
                subprocess.run(cmd, check=True)
                temp_files.append('temp_bg.png')
            
            # Apply additional blur if requested
            if self.blur_background:
                logging.info("   Applying blur...")
                cmd = _imagemagick_cmd('convert') + ['temp_bg.png', '-blur', '0x2', 'temp_bg.png']
                subprocess.run(cmd, check=True)
            
            # Step 2: Apply vintage effect if requested
            if self.vintage_effect:
                logging.info("2. Applying vintage effect...")
                cmd = _imagemagick_cmd('convert') + [
                    'temp_bg.png',
                    '-modulate', '110,130,100',
                    '-colorize', '10,5,0',
                    '-sigmoidal-contrast', '2,50%',
                    'temp_bg.png'
                ]
                subprocess.run(cmd, check=True)
            
            # Step 3: Add gradient (exactly like bash script)
            logging.info("3. Adding gradient...")
            if self.logo_position == "north":
                cmd = _imagemagick_cmd('convert') + [
                    'temp_bg.png',
                    '(', '-size', f'{self.width}x{self.gradient_height}',
                    'gradient:black-transparent', ')',
                    '-gravity', 'north',
                    '-composite', 'temp_with_gradient.png'
                ]
            elif self.logo_position == "south":
                cmd = _imagemagick_cmd('convert') + [
                    'temp_bg.png',
                    '(', '-size', f'{self.width}x{self.gradient_height}',
                    'gradient:transparent-black', ')',
                    '-gravity', 'south',
                    '-composite', 'temp_with_gradient.png'
                ]
            elif self.logo_position == "center":
                gradient_height = self.height // 3
                cmd = _imagemagick_cmd('convert') + [
                    'temp_bg.png',
                    '(', '-size', f'{self.width}x{gradient_height}',
                    'gradient:transparent-black', ')',
                    '-gravity', 'center',
                    '-composite', 'temp_with_gradient.png'
                ]
            else:
                # No gradient, just copy
                shutil.copy2('temp_bg.png', 'temp_with_gradient.png')
                cmd = None
            
            if cmd:
                subprocess.run(cmd, check=True)
            temp_files.append('temp_with_gradient.png')
            
            # Step 4: Process logos (exactly like bash script)
            logging.info("4. Processing logos...")
            
            # Process main logo
            cmd = _imagemagick_cmd('convert') + [
                logo_path,
                '-resize', f'{self.logo_max_width}x{self.logo_max_height}>',
                '-background', 'transparent',
                'temp_logo.png'
            ]
            subprocess.run(cmd, check=True)
            temp_files.append('temp_logo.png')
            
            # Process secondary logo if provided
            if secondary_logo_path and os.path.exists(secondary_logo_path):
                cmd = _imagemagick_cmd('convert') + [
                    secondary_logo_path,
                    '-resize', f'{self.logo_max_width}x{self.logo_max_height}>',
                    '-background', 'transparent',
                    'temp_secondary_logo.png'
                ]
                subprocess.run(cmd, check=True)
                temp_files.append('temp_secondary_logo.png')
            
            # Step 5: Final composition (exactly like bash script)
            logging.info("5. Final composition...")
            
            # Compose main logo
            cmd = _imagemagick_cmd('convert') + [
                'temp_with_gradient.png',
                'temp_logo.png',
                '-gravity', self.logo_position,
                '-geometry', self.logo_offset,
                '-composite', 'temp_final.png'
            ]
            subprocess.run(cmd, check=True)
            temp_files.append('temp_final.png')
            
            final_temp = 'temp_final.png'
            
            # Compose secondary logo if present
            if secondary_logo_path and os.path.exists(secondary_logo_path):
                cmd = _imagemagick_cmd('convert') + [
                    final_temp,
                    'temp_secondary_logo.png',
                    '-gravity', self.secondary_position,
                    '-geometry', self.secondary_offset,
                    '-composite', 'temp_final_with_secondary.png'
                ]
                subprocess.run(cmd, check=True)
                temp_files.append('temp_final_with_secondary.png')
                final_temp = 'temp_final_with_secondary.png'
            
            # Step 6: Add border if requested (exactly like bash script)
            if self.border_size > 0:
                logging.info("6. Adding border...")
                cmd = _imagemagick_cmd('convert') + [
                    final_temp,
                    '-bordercolor', self.border_color,
                    '-border', f'{self.border_size}x{self.border_size}',
                    output_path
                ]
                subprocess.run(cmd, check=True)
            else:
                # Convert to PNG format when copying
                cmd = _imagemagick_cmd('convert') + [final_temp, output_path]
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
                              text_logo_settings=None, game_name='', enable_foreground_mask=False):
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
        # Use same dir as output for temp files (absolute paths; avoid cwd on Windows)
        temp_dir = os.path.dirname(os.path.abspath(output_path))
        temp_background = os.path.join(temp_dir, 'temp_background.png')
        
        try:
            # Validate inputs
            if not os.path.exists(background_path):
                raise FileNotFoundError(f"Background image not found: {background_path}")
            if not os.path.exists(screenshot_path):
                raise FileNotFoundError(f"Screenshot image not found: {screenshot_path}")
            
            logging.info(f"Generating template box: {output_path}")
            
            # Normalize paths for ImageMagick (avoid mixed slashes on Windows)
            background_path = os.path.normpath(os.path.abspath(background_path))
            screenshot_path = os.path.normpath(os.path.abspath(screenshot_path))
            output_path = os.path.normpath(os.path.abspath(output_path))
            if logo_path:
                logo_path = os.path.normpath(os.path.abspath(logo_path))
            
            # Get background image dimensions
            identify_cmd = _imagemagick_cmd('identify') + ['-format', '%wx%h', background_path]
            dim_result = subprocess.run(identify_cmd, capture_output=True, text=True, timeout=5)
            if dim_result.returncode != 0:
                raise Exception("Failed to get background image dimensions")
            bg_dims = dim_result.stdout.strip().split('x')
            bg_width, bg_height = bg_dims[0], bg_dims[1]
            
            # Use background image as base (copy it first)
            cmd = _imagemagick_cmd('convert') + [background_path, temp_background]
            subprocess.run(cmd, check=True)
            temp_files.append(temp_background)
            
            # Calculate bounding box of the 4 corners to determine target size
            min_x = min(corner1_x, corner2_x, corner3_x, corner4_x)
            max_x = max(corner1_x, corner2_x, corner3_x, corner4_x)
            min_y = min(corner1_y, corner2_y, corner3_y, corner4_y)
            max_y = max(corner1_y, corner2_y, corner3_y, corner4_y)
            
            target_width = max_x - min_x
            target_height = max_y - min_y
            
            # Get screenshot dimensions
            screenshot_dim_cmd = _imagemagick_cmd('identify') + ['-format', '%wx%h', screenshot_path]
            screenshot_dim_result = subprocess.run(screenshot_dim_cmd, capture_output=True, text=True, timeout=5)
            if screenshot_dim_result.returncode != 0:
                raise Exception("Failed to get screenshot dimensions")
            
            screenshot_dims = screenshot_dim_result.stdout.strip().split('x')
            screenshot_width = int(screenshot_dims[0])
            screenshot_height = int(screenshot_dims[1])
            
            # Step 1: Resize screenshot to fit the bounding box dimensions
            # This ensures the screenshot has the correct dimensions before placing
            # Use ! to force exact size (ignore aspect ratio) - this stretches smaller images to fill
            is_smaller = screenshot_width < target_width or screenshot_height < target_height
            logging.info(f"Resizing screenshot from {screenshot_width}x{screenshot_height} to {target_width}x{target_height} (stretching to fill)")
            if is_smaller:
                logging.info(f"Image is smaller than target, will be stretched to fill entire area")
            
            temp_resized = tempfile.NamedTemporaryFile(delete=False, suffix='.png').name
            temp_files.append(temp_resized)
            
            # Use ! to force exact dimensions (stretch to fill, ignore aspect ratio)
            # For smaller images, this will upscale and stretch to fill the target area
            # The ! flag forces ImageMagick to resize to exact dimensions, stretching smaller images
            resize_spec = f'{target_width}x{target_height}!'
            cmd = _imagemagick_cmd('convert') + [
                screenshot_path,
                '-resize', resize_spec,  # ! forces exact size, ignoring aspect ratio (stretches to fill, upscales smaller images)
                temp_resized
            ]
            logging.info(f"Resize command: {' '.join(cmd)}")
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            if result.returncode != 0:
                logging.error(f"Resize failed: {result.stderr}")
                raise Exception(f"Failed to resize screenshot: {result.stderr}")
            logging.info(f"✅ Screenshot resized and stretched to {target_width}x{target_height}")
            
            # Verify the resized image dimensions
            verify_cmd = _imagemagick_cmd('identify') + ['-format', '%wx%h', temp_resized]
            verify_result = subprocess.run(verify_cmd, capture_output=True, text=True, timeout=5)
            if verify_result.returncode == 0:
                resized_dims = verify_result.stdout.strip().split('x')
                resized_width = int(resized_dims[0])
                resized_height = int(resized_dims[1])
                logging.info(f"Verified resized dimensions: {resized_width}x{resized_height}")
                if resized_width != target_width or resized_height != target_height:
                    logging.warning(f"⚠️  Resize dimensions don't match target! Expected {target_width}x{target_height}, got {resized_width}x{resized_height}")
                    # For smaller images, try using scale instead of resize, or use extent to force exact size
                    if is_smaller:
                        logging.info("Image was smaller, trying alternative resize method...")
                        temp_fixed = tempfile.NamedTemporaryFile(delete=False, suffix='.png').name
                        temp_files.append(temp_fixed)
                        # Use scale to force exact dimensions (more aggressive than resize)
                        fix_cmd = _imagemagick_cmd('convert') + [
                            screenshot_path,
                            '-scale', f'{target_width}x{target_height}!',  # scale with ! forces exact dimensions
                            temp_fixed
                        ]
                        logging.info(f"Alternative resize command: {' '.join(fix_cmd)}")
                        fix_result = subprocess.run(fix_cmd, check=True, capture_output=True, text=True)
                        if fix_result.returncode == 0:
                            # Verify the fixed dimensions
                            fix_verify_cmd = _imagemagick_cmd('identify') + ['-format', '%wx%h', temp_fixed]
                            fix_verify_result = subprocess.run(fix_verify_cmd, capture_output=True, text=True, timeout=5)
                            if fix_verify_result.returncode == 0:
                                fix_dims = fix_verify_result.stdout.strip().split('x')
                                fix_width = int(fix_dims[0])
                                fix_height = int(fix_dims[1])
                                if fix_width == target_width and fix_height == target_height:
                                    temp_resized = temp_fixed
                                    logging.info(f"✅ Alternative resize method worked: {fix_width}x{fix_height}")
                                else:
                                    logging.error(f"❌ Alternative resize also failed: {fix_width}x{fix_height}")
                                    raise Exception(f"Resize failed: dimensions don't match target after alternative method")
                            else:
                                raise Exception(f"Failed to verify alternative resize dimensions")
                        else:
                            logging.error(f"Alternative resize failed: {fix_result.stderr}")
                            raise Exception(f"Resize failed: dimensions don't match target")
                    else:
                        logging.error(f"❌ Resize dimensions don't match target! Expected {target_width}x{target_height}, got {resized_width}x{resized_height}")
                        raise Exception(f"Resize failed: dimensions don't match target")
                else:
                    logging.info(f"✅ Dimensions match target: {resized_width}x{resized_height}")
            
            # Step 2: Composite the resized screenshot onto background at the correct position
            # Use composite command with geometry for exact positioning
            # Position at min_x, min_y to align with the corner positions
            logging.info(f"Placing resized screenshot onto background at position ({min_x}, {min_y})")
            if enable_foreground_mask:
                logging.info(f"Using foreground mask: placing background over screenshot")
                temp_canvas = tempfile.NamedTemporaryFile(delete=False, suffix='.png').name
                temp_files.append(temp_canvas)
                
                canvas_cmd = _imagemagick_cmd('convert') + [
                    '-size', f"{bg_width}x{bg_height}", 'xc:none',
                    temp_resized, '-geometry', f'+{min_x}+{min_y}', '-composite',
                    temp_canvas
                ]
                subprocess.run(canvas_cmd, check=True)
                
                cmd = _imagemagick_cmd('composite') + [
                    temp_background,
                    temp_canvas,
                    output_path
                ]
            else:
                cmd = _imagemagick_cmd('composite') + [
                    '-geometry', f'+{min_x}+{min_y}',
                    temp_resized,  # Use the resized image directly
                    temp_background,
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
                                font_path = os.path.abspath(font_file)
                                break
                        # Also check with exact filename match
                        if font_path == font:
                            for filename in os.listdir(custom_fonts_dir):
                                if os.path.splitext(filename)[0] == font:
                                    font_path = os.path.abspath(os.path.join(custom_fonts_dir, filename))
                                    break
                    
                    # Calculate caption width based on zone width
                    caption_width = int(logo_zone_width * 0.95)
                    
                    # Build base command for text generation
                    cmd = _imagemagick_cmd('convert') + [
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
                        identify_cmd = _imagemagick_cmd('identify') + ['-format', '%wx%h', temp_text]
                        dim_result = subprocess.run(identify_cmd, capture_output=True, text=True, timeout=5)
                        if dim_result.returncode == 0:
                            width, height = dim_result.stdout.strip().split('x')
                            underline_y = int(height) - 2
                            cmd_underline = _imagemagick_cmd('convert') + [
                                temp_text,
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
                    cmd = _imagemagick_cmd('convert') + [
                        logo_file_to_use,
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
                    cmd = _imagemagick_cmd('composite') + [
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

    def generate_spine_background(self, box2d_path, spine_width, output_path, debug=False, crop_width=None, spine_color=None):
        """
        Generate a spine background by cropping the left side of a 2D box and mirroring it,
        or by creating a solid color background.
        
        Args:
            box2d_path: Path to the 2D box image (required if spine_color not provided)
            spine_width: Width of the spine in template coordinates (will be used directly as pixel width if crop_width not provided)
            output_path: Path where the generated spine will be saved
            debug: If True, log the command
            crop_width: Optional width of the 2D box crop in pixels (defaults to spine_width, min 1, max box_width)
            spine_color: Optional hex color (e.g., "#FF0000") - if provided, creates solid color spine
        """
        if spine_width <= 0:
            raise Exception(f"Invalid spine width: {spine_width}")
        
        # Get the dimensions of the 2D box (needed for height even if using color)
        if spine_color:
            # If using color, we still need box2d_path to get the height
            if not os.path.exists(box2d_path):
                raise Exception(f"2D box image not found: {box2d_path} (needed for dimensions)")
        else:
            if not os.path.exists(box2d_path):
                raise Exception(f"2D box image not found: {box2d_path}")
        
        # Normalize paths for ImageMagick (avoid mixed slashes on Windows)
        box2d_path = os.path.normpath(os.path.abspath(box2d_path))
        output_path = os.path.normpath(os.path.abspath(output_path))
        
        cmd_info = _imagemagick_cmd('identify') + [
            '-format', '%wx%h',
            box2d_path
        ]
        result = subprocess.run(cmd_info, capture_output=True, text=True, check=True)
        box_dims = result.stdout.strip().split('x')
        box_width = int(box_dims[0])
        box_height = int(box_dims[1])
        
        # If spine_color is provided, create a solid color image
        if spine_color:
            # Validate color format (should be hex like #FF0000 or #ff0000)
            if not spine_color.startswith('#'):
                spine_color = '#' + spine_color
            # Create solid color image in sRGB color space to ensure proper color handling
            cmd = _imagemagick_cmd('convert') + [
                '-size', f'{int(spine_width)}x{box_height}',
                '-colorspace', 'sRGB',
                f'xc:{spine_color}',
                output_path
            ]
            
            if debug:
                logging.info(f"Generating solid color spine background: spine_width={spine_width}, box_height={box_height}, color={spine_color}")
                logging.info(f"Generating spine background: {' '.join(cmd)}")
            
            subprocess.run(cmd, check=True, capture_output=True, text=True)
        else:
            # Use crop_width if provided and not empty/None, otherwise default to spine_width
            if crop_width is None or crop_width == '' or crop_width == 0:
                crop_width = int(spine_width)
            else:
                crop_width = int(crop_width)
                # Ensure crop_width is within bounds: min 1, max box_width
                if crop_width < 1:
                    crop_width = 1
                if crop_width > box_width:
                    crop_width = box_width
            
            # Crop left side: crop from (0,0) with width=crop_width, height=box_height
            # Then flip horizontally with -flop
            cmd = _imagemagick_cmd('convert') + [
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

    def generate_3dbox(self, background_path, box2d_path, output_path, corners, spine_corners=None, spine_image_path=None, spine_logo_path=None, generated_spine_path=None, spine_logo_zone=None, spine_logo_corners=None, spine_text_logo_settings=None, spine_game_name='', spine_from_field=False, debug=False):
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
            spine_logo_path: Optional path to spine logo image
            generated_spine_path: Optional path to generated spine background
            spine_logo_zone: Optional dictionary with spine logo zone positions (same format as corners)
                If provided, logo/text will use full width of zone and be centered vertically in zone
            spine_logo_corners: Optional dictionary with spine logo corner positions (same format as corners)
                If provided, logo/text will be placed using perspective transformation at these exact corners
                Takes precedence over spine_logo_zone if both are provided
            spine_text_logo_settings: Optional dict with text logo settings for spine (color, font_size, font, etc.)
            spine_game_name: Optional game name for spine text logo generation
            spine_from_field: If True, spine comes from a game field and logo/text should never be added
            debug: If True, keep intermediate temp images for debugging
        """
        temp_files = []
        temp_dir = None
        
        try:
            # Normalize paths for ImageMagick (avoid mixed slashes on Windows)
            box2d_path = os.path.normpath(os.path.abspath(box2d_path))
            background_path = os.path.normpath(os.path.abspath(background_path))
            output_path = os.path.normpath(os.path.abspath(output_path))
            
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
            
            # Compute source coordinates (rectangle before distortion)
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
            
            # Step 1-3: Combined resize, perspective distortion, and resize in a single convert command
            # This reduces from 3 separate ImageMagick calls to 1, improving performance
            perspective_str = (
                f'{source_topleft_x},{source_topleft_y} {target_topleft_x},{target_topleft_y}  '
                f'{source_topright_x},{source_topright_y} {target_topright_x},{target_topright_y}  '
                f'{source_bottomright_x},{source_bottomright_y} {target_bottomright_x},{target_bottomright_y}  '
                f'{source_bottomleft_x},{source_bottomleft_y} {target_bottomleft_x},{target_bottomleft_y}'
            )
            
            cmd_combined = _imagemagick_cmd('convert') + [
                box2d_path,
                '-resize', f'{resize_width}x{resize_height}!',
                '-background', 'none',
                '-virtual-pixel', 'transparent',
                '-alpha', 'set',
                '+distort', 'Perspective', perspective_str,
                '-resize', f'{resize_width}x{resize_height}!',
                temp_perspective_resized
            ]
            logging.info(f"3D Box Step 1-3 (Combined) - Resize, Perspective, Resize: {' '.join(cmd_combined)}")
            subprocess.run(cmd_combined, check=True)
            if debug:
                logging.info(f"🔧 DEBUG: Combined processed image saved to: {temp_perspective_resized}")
            
            # Step 4: Composite the distorted 2D box onto the 3D box template
            # Use composite with exact geometry positioning at source top-left coordinates
            cmd_composite = _imagemagick_cmd('composite') + [
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
                            
                            # Check if this is a generated spine (from cropped 2D box) vs uploaded/field spine
                            is_generated_spine = (generated_spine_path and spine_source_image == generated_spine_path)
                            
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
                            
                            # Compute spine source coordinates (needed for perspective)
                            spine_source_topleft_x = spine_target_topleft_x
                            spine_source_topleft_y = spine_target_topright_y
                            spine_source_topright_x = spine_target_topright_x
                            spine_source_topright_y = spine_target_topright_y
                            spine_source_bottomleft_x = spine_target_topleft_x
                            spine_source_bottomleft_y = spine_target_bottomright_y
                            spine_source_bottomright_x = spine_target_topright_x
                            spine_source_bottomright_y = spine_target_bottomright_y
                            
                            spine_perspective_str = (
                                f'{spine_source_topleft_x},{spine_source_topleft_y} {spine_target_topleft_x},{spine_target_topleft_y}  '
                                f'{spine_source_topright_x},{spine_source_topright_y} {spine_target_topright_x},{spine_target_topright_y}  '
                                f'{spine_source_bottomright_x},{spine_source_bottomright_y} {spine_target_bottomright_x},{spine_target_bottomright_y}  '
                                f'{spine_source_bottomleft_x},{spine_source_bottomleft_y} {spine_target_bottomleft_x},{spine_target_bottomleft_y}'
                            )
                            
                            # Never add logo/text if spine is from a field
                            has_logo = False
                            has_text_logo = False
                            # Disable logo corners for now - only use zone
                            use_logo_corners = False
                            if not spine_from_field:
                                has_logo = spine_logo_path and os.path.exists(spine_logo_path)
                                has_text_logo = spine_text_logo_settings and spine_game_name
                            
                            # Generate text logo if needed (before processing spine)
                            # Calculate zone dimensions first to determine logo generation size
                            zone_width_resized = None
                            zone_height_resized = None
                            keep_aspect_ratio = spine_logo_zone.get('keepAspectRatio', False) if spine_logo_zone else False
                            if spine_logo_zone and not spine_from_field:
                                zone_tl = spine_logo_zone.get('topLeft', {'x': 0, 'y': 0})
                                zone_tr = spine_logo_zone.get('topRight', {'x': 0, 'y': 0})
                                zone_bl = spine_logo_zone.get('bottomLeft', {'x': 0, 'y': 0})
                                zone_br = spine_logo_zone.get('bottomRight', {'x': 0, 'y': 0})
                                
                                # Check if zone is actually defined
                                zone_tl_x = zone_tl.get('x', 0)
                                zone_tl_y = zone_tl.get('y', 0)
                                zone_tr_x = zone_tr.get('x', 0)
                                zone_tr_y = zone_tr.get('y', 0)
                                zone_bl_x = zone_bl.get('x', 0)
                                zone_bl_y = zone_bl.get('y', 0)
                                zone_br_x = zone_br.get('x', 0)
                                zone_br_y = zone_br.get('y', 0)
                                
                                zone_is_valid = (zone_tl_x > 0 or zone_tl_y > 0 or zone_tr_x > 0 or zone_tr_y > 0 or
                                               zone_bl_x > 0 or zone_bl_y > 0 or zone_br_x > 0 or zone_br_y > 0)
                                
                                if zone_is_valid:
                                    # Calculate zone dimensions in template space
                                    zone_width_template = zone_tr_x - zone_tl_x
                                    zone_height_template = zone_bl_y - zone_tl_y
                                    
                                    # Map zone to resized spine space
                                    template_spine_width = spine_target_topright_x - spine_target_topleft_x
                                    template_spine_height = spine_target_bottomright_y - spine_target_topright_y
                                    
                                    if template_spine_width > 0 and template_spine_height > 0 and zone_width_template > 0 and zone_height_template > 0:
                                        scale_x = spine_resize_width / template_spine_width
                                        scale_y = spine_resize_height / template_spine_height
                                        
                                        zone_width_resized = int(zone_width_template * scale_x)
                                        zone_height_resized = int(zone_height_template * scale_y)
                            
                            spine_logo_to_use = spine_logo_path
                            is_generated_text_logo = False  # Track if this is a generated text logo that's already been resized
                            
                            # If we have a logo path and keep_aspect_ratio is enabled, it might be a generated text logo
                            # that was created elsewhere (e.g., preview logo). We should treat it as a generated text logo
                            # if keep_aspect_ratio is enabled, since it needs special handling.
                            # Note: When a spine image is provided, has_text_logo might be False even though we have a preview logo
                            logging.info(f"3D Box Spine: Checking for preview text logo - has_text_logo={has_text_logo}, has_logo={has_logo}, keep_aspect_ratio={keep_aspect_ratio}, spine_logo_to_use={spine_logo_to_use}")
                            # Check if we have a logo path and keep_aspect_ratio is enabled (regardless of has_text_logo)
                            # This handles the case where a preview logo is provided but spine_text_logo_settings is None
                            if has_logo and keep_aspect_ratio and spine_logo_to_use:
                                # This is likely a generated text logo passed from outside (e.g., preview)
                                # We need to resize it to match the spine width while maintaining aspect ratio
                                # Calculate zone dimensions first to determine resize size
                                if spine_logo_zone and not spine_from_field:
                                    zone_tl = spine_logo_zone.get('topLeft', {'x': 0, 'y': 0})
                                    zone_tr = spine_logo_zone.get('topRight', {'x': 0, 'y': 0})
                                    zone_bl = spine_logo_zone.get('bottomLeft', {'x': 0, 'y': 0})
                                    zone_br = spine_logo_zone.get('bottomRight', {'x': 0, 'y': 0})
                                    
                                    zone_tl_x = zone_tl.get('x', 0)
                                    zone_tl_y = zone_tl.get('y', 0)
                                    zone_tr_x = zone_tr.get('x', 0)
                                    zone_tr_y = zone_tr.get('y', 0)
                                    zone_bl_x = zone_bl.get('x', 0)
                                    zone_bl_y = zone_bl.get('y', 0)
                                    zone_br_x = zone_br.get('x', 0)
                                    zone_br_y = zone_br.get('y', 0)
                                    
                                    zone_is_valid = (zone_tl_x > 0 or zone_tl_y > 0 or zone_tr_x > 0 or zone_tr_y > 0 or
                                                   zone_bl_x > 0 or zone_bl_y > 0 or zone_br_x > 0 or zone_br_y > 0)
                                    
                                    if zone_is_valid:
                                        zone_width_template = zone_tr_x - zone_tl_x
                                        zone_height_template = zone_bl_y - zone_tl_y
                                        
                                        template_spine_width = spine_target_topright_x - spine_target_topleft_x
                                        template_spine_height = spine_target_bottomright_y - spine_target_topright_y
                                        
                                        if template_spine_width > 0 and template_spine_height > 0 and zone_width_template > 0 and zone_height_template > 0:
                                            scale_x = spine_resize_width / template_spine_width
                                            scale_y = spine_resize_height / template_spine_height
                                            
                                            zone_width_resized = int(zone_width_template * scale_x)
                                            zone_height_resized = int(zone_height_template * scale_y)
                                            
                                            # Resize the preview logo to match spine width (after rotation) while maintaining aspect ratio
                                            effective_zone_width = zone_width_resized
                                            if effective_zone_width and effective_zone_width > 0:
                                                # Create temp file for resized preview logo
                                                if debug:
                                                    output_base = os.path.splitext(os.path.basename(output_path))[0]
                                                    temp_preview_logo_resized = os.path.join(temp_dir, f'{output_base}_preview_logo_resized.png')
                                                else:
                                                    temp_preview_logo_resized = os.path.join(temp_dir, 'preview_logo_resized.png')
                                                temp_files.append(temp_preview_logo_resized)
                                                
                                                # Get original dimensions
                                                orig_dim_cmd = _imagemagick_cmd('identify') + ['-format', '%wx%h', spine_logo_to_use]
                                                orig_dim_result = subprocess.run(orig_dim_cmd, capture_output=True, text=True, timeout=5)
                                                if orig_dim_result.returncode == 0:
                                                    orig_dims = orig_dim_result.stdout.strip().split('x')
                                                    orig_width = int(orig_dims[0])
                                                    orig_height = int(orig_dims[1])
                                                    orig_aspect = orig_width / orig_height if orig_height > 0 else 1
                                                    
                                                    # After rotation, width should be effective_zone_width
                                                    # So before rotation, height should be effective_zone_width
                                                    text_logo_height = effective_zone_width  # This becomes width after rotation
                                                    text_logo_width = int(text_logo_height * orig_aspect)  # Maintain aspect ratio
                                                    
                                                    # Resize by height only to maintain aspect ratio
                                                    cmd_resize = _imagemagick_cmd('convert') + [
                                                        spine_logo_to_use,
                                                        '-background', 'transparent',
                                                        '-alpha', 'set',
                                                        '-resize', f'x{text_logo_height}',  # Scale by height only, maintain aspect ratio
                                                        temp_preview_logo_resized
                                                    ]
                                                    logging.info(f"3D Box Spine: Resizing preview text logo to maintain aspect ratio - height: {text_logo_height}, width: {text_logo_width} (zone width: {effective_zone_width})")
                                                    subprocess.run(cmd_resize, check=True)
                                                    
                                                    # Use the resized version
                                                    spine_logo_to_use = temp_preview_logo_resized
                                                    is_generated_text_logo = True
                                                    logging.info(f"3D Box Spine: Preview text logo resized and marked as generated text logo")
                                                else:
                                                    logging.warning(f"3D Box Spine: Could not get preview logo dimensions, treating as normal logo")
                                                    is_generated_text_logo = False
                                            else:
                                                logging.warning(f"3D Box Spine: Invalid zone width for preview logo resize")
                                                is_generated_text_logo = False
                                        else:
                                            logging.warning(f"3D Box Spine: Zone dimensions not available for preview logo resize, trying with spine dimensions")
                                            # Fallback: use spine dimensions if zone isn't available
                                            if spine_resize_width > 0:
                                                # Create temp file for resized preview logo
                                                if debug:
                                                    output_base = os.path.splitext(os.path.basename(output_path))[0]
                                                    temp_preview_logo_resized = os.path.join(temp_dir, f'{output_base}_preview_logo_resized.png')
                                                else:
                                                    temp_preview_logo_resized = os.path.join(temp_dir, 'preview_logo_resized.png')
                                                temp_files.append(temp_preview_logo_resized)
                                                
                                                # Get original dimensions
                                                orig_dim_cmd = _imagemagick_cmd('identify') + ['-format', '%wx%h', spine_logo_to_use]
                                                orig_dim_result = subprocess.run(orig_dim_cmd, capture_output=True, text=True, timeout=5)
                                                if orig_dim_result.returncode == 0:
                                                    orig_dims = orig_dim_result.stdout.strip().split('x')
                                                    orig_width = int(orig_dims[0])
                                                    orig_height = int(orig_dims[1])
                                                    orig_aspect = orig_width / orig_height if orig_height > 0 else 1
                                                    
                                                    # After rotation, width should be spine_resize_width
                                                    # So before rotation, height should be spine_resize_width
                                                    text_logo_height = spine_resize_width  # This becomes width after rotation
                                                    text_logo_width = int(text_logo_height * orig_aspect)  # Maintain aspect ratio
                                                    
                                                    # Resize by height only to maintain aspect ratio
                                                    cmd_resize = _imagemagick_cmd('convert') + [
                                                        spine_logo_to_use,
                                                        '-background', 'transparent',
                                                        '-alpha', 'set',
                                                        '-resize', f'x{text_logo_height}',  # Scale by height only, maintain aspect ratio
                                                        temp_preview_logo_resized
                                                    ]
                                                    logging.info(f"3D Box Spine: Resizing preview text logo to maintain aspect ratio (using spine width) - height: {text_logo_height}, width: {text_logo_width} (spine width: {spine_resize_width})")
                                                    subprocess.run(cmd_resize, check=True)
                                                    
                                                    # Use the resized version
                                                    spine_logo_to_use = temp_preview_logo_resized
                                                    is_generated_text_logo = True
                                                    logging.info(f"3D Box Spine: Preview text logo resized (fallback) and marked as generated text logo")
                                                else:
                                                    logging.warning(f"3D Box Spine: Could not get preview logo dimensions (fallback), treating as normal logo")
                                                    is_generated_text_logo = False
                                    else:
                                        logging.warning(f"3D Box Spine: No zone or zone invalid for preview logo resize")
                                        is_generated_text_logo = False
                                else:
                                    logging.warning(f"3D Box Spine: spine_logo_zone not available for preview logo resize")
                                    is_generated_text_logo = False
                            
                            if has_text_logo and not has_logo:
                                # Generate text logo for spine
                                if debug:
                                    output_base = os.path.splitext(os.path.basename(output_path))[0]
                                    temp_text_logo = os.path.join(temp_dir, f'{output_base}_spine_text_logo.png')
                                else:
                                    temp_text_logo = os.path.join(temp_dir, 'spine_text_logo.png')
                                temp_files.append(temp_text_logo)
                                
                                # Generate logo with zone height as width, zone width as height
                                # After rotation, this will become zone width x zone height
                                if zone_height_resized and zone_height_resized > 0 and zone_width_resized and zone_width_resized > 0:
                                    if keep_aspect_ratio:
                                        # Keep aspect ratio: generate without width constraint to get natural size
                                        # Then use min(natural_width, zone_height_resized) as maximum
                                        # Don't stretch if logo is smaller than zone_height_resized
                                        text_logo_width = None  # Generate with natural width first
                                        logging.info(f"3D Box Spine: Generating text logo with natural width (keeping aspect ratio, max: {zone_height_resized})")
                                    else:
                                        # Generate with zone height as width (will become height after rotation)
                                        # and zone width as height (will become width after rotation)
                                        text_logo_width = zone_height_resized  # Zone height becomes logo width
                                        text_logo_height = zone_width_resized  # Zone width becomes logo height
                                        logging.info(f"3D Box Spine: Generating text logo with dimensions {text_logo_width}x{text_logo_height} (zone height as width, zone width as height)")
                                else:
                                    # No zone: use spine dimensions swapped
                                    if keep_aspect_ratio:
                                        # Keep aspect ratio: generate without width constraint to get natural size
                                        # Then use min(natural_width, spine_resize_height) as maximum
                                        # Don't stretch if logo is smaller than spine_resize_height
                                        text_logo_width = None  # Generate with natural width first
                                        logging.info(f"3D Box Spine: No zone, generating text logo with natural width (keeping aspect ratio, max: {spine_resize_height})")
                                    else:
                                        text_logo_width = spine_resize_height  # Spine height becomes logo width
                                        text_logo_height = spine_resize_width  # Spine width becomes logo height
                                        logging.info(f"3D Box Spine: No zone, generating text logo with dimensions {text_logo_width}x{text_logo_height}")
                                
                                # Generate single-line text logo with the calculated width
                                # The logo will be generated horizontally, then rotated
                                generated_text_logo = self.generate_single_line_text_logo(
                                    game_name=spine_game_name,
                                    text_logo_settings=spine_text_logo_settings,
                                    output_path=temp_text_logo,
                                    width=text_logo_width
                                )
                                
                                # Resize to exact dimensions (zone height x zone width) if zone is defined
                                # This ensures the logo uses full height and is centered on width
                                # Also handle aspect ratio even when zone uses defaults (zone_width_resized might be None)
                                if generated_text_logo and os.path.exists(generated_text_logo):
                                    # Determine effective zone dimensions (use spine dimensions if zone is None but keep_aspect_ratio is true)
                                    effective_zone_width = zone_width_resized if (zone_width_resized and zone_width_resized > 0) else (spine_resize_width if keep_aspect_ratio else None)
                                    effective_zone_height = zone_height_resized if (zone_height_resized and zone_height_resized > 0) else (spine_resize_height if keep_aspect_ratio else None)
                                    
                                    if effective_zone_width and effective_zone_height:
                                        temp_text_logo_resized = os.path.splitext(temp_text_logo)[0] + '_resized.png'
                                        temp_files.append(temp_text_logo_resized)
                                        
                                        if keep_aspect_ratio:
                                            # Keep aspect ratio: if text logo is bigger than topY-bottomY area (effective_zone_height),
                                            # fix width to effective_zone_height and adapt height to maintain aspect ratio
                                            # Get original dimensions
                                            orig_dim_cmd = _imagemagick_cmd('identify') + ['-format', '%wx%h', generated_text_logo]
                                            orig_dim_result = subprocess.run(orig_dim_cmd, capture_output=True, text=True, timeout=5)
                                            if orig_dim_result.returncode == 0:
                                                orig_dims = orig_dim_result.stdout.strip().split('x')
                                                orig_width = int(orig_dims[0])
                                                orig_height = int(orig_dims[1])
                                                orig_aspect = orig_width / orig_height if orig_height > 0 else 1
                                                
                                                # If text logo width is bigger than effective_zone_height (topY-bottomY),
                                                # fix width to effective_zone_height and calculate height from aspect ratio
                                                max_width = effective_zone_height  # This is zone_height_resized if zone exists, or spine_resize_height if no zone
                                                
                                                if orig_width > max_width:
                                                    # Fix width to max_width (topY-bottomY), adapt height
                                                    text_logo_width = max_width
                                                    text_logo_height = int(text_logo_width / orig_aspect) if orig_aspect > 0 else max_width
                                                    
                                                    # Resize by width to maintain aspect ratio
                                                    cmd_resize = _imagemagick_cmd('convert') + [
                                                        generated_text_logo,
                                                        '-background', 'transparent',
                                                        '-alpha', 'set',
                                                        '-resize', f'{text_logo_width}x',  # Scale by width only, maintain aspect ratio
                                                        temp_text_logo_resized
                                                    ]
                                                    logging.info(f"3D Box Spine: Text logo bigger than zone height ({orig_width} > {max_width}), fixing width to {max_width}, height: {text_logo_height} (aspect: {orig_aspect:.3f})")
                                                    subprocess.run(cmd_resize, check=True)
                                                    generated_text_logo = temp_text_logo_resized
                                                else:
                                                    # Logo is smaller than constraint, use natural size (no resize)
                                                    text_logo_width = orig_width
                                                    logging.info(f"3D Box Spine: Text logo is smaller than max width ({orig_width} < {max_width}), using natural size without stretching")
                                                    # No resize needed, logo is already at the correct size
                                                
                                                is_generated_text_logo = True  # Mark as already resized
                                            else:
                                                # Fallback: use zone dimensions
                                                text_logo_width = effective_zone_height
                                                text_logo_height = effective_zone_width
                                                cmd_resize = _imagemagick_cmd('convert') + [
                                                    generated_text_logo,
                                                    '-background', 'transparent',
                                                    '-alpha', 'set',
                                                    '-resize', f'{text_logo_width}x{text_logo_height}!',
                                                    '-gravity', 'center',
                                                    '-extent', f'{text_logo_width}x{text_logo_height}',
                                                    temp_text_logo_resized
                                                ]
                                                logging.info(f"3D Box Spine: Resizing text logo to {text_logo_width}x{text_logo_height}: {' '.join(cmd_resize)}")
                                                subprocess.run(cmd_resize, check=True)
                                                generated_text_logo = temp_text_logo_resized
                                        else:
                                            # Resize to exact dimensions: zone height (width) x zone width (height)
                                            # Center horizontally, use full height (preserve transparency)
                                            text_logo_width = effective_zone_height
                                            text_logo_height = effective_zone_width
                                            cmd_resize = _imagemagick_cmd('convert') + [
                                                generated_text_logo,
                                                '-background', 'transparent',
                                                '-alpha', 'set',
                                                '-resize', f'{text_logo_width}x{text_logo_height}!',  # Force exact size
                                                '-gravity', 'center',
                                                '-extent', f'{text_logo_width}x{text_logo_height}',  # Center on width, use full height
                                                temp_text_logo_resized
                                            ]
                                            logging.info(f"3D Box Spine: Resizing text logo to {text_logo_width}x{text_logo_height}: {' '.join(cmd_resize)}")
                                            subprocess.run(cmd_resize, check=True)
                                            generated_text_logo = temp_text_logo_resized
                                
                                if generated_text_logo and os.path.exists(generated_text_logo):
                                    spine_logo_to_use = generated_text_logo
                                    has_logo = True
                                    logging.info(f"✅ Generated text logo for spine: {generated_text_logo}")
                                else:
                                    logging.warning(f"Failed to generate text logo for spine")
                            
                            if is_generated_spine:
                                # Generated spine: always use separate steps (no optimization) to ensure perspective works correctly
                                temp_files.extend([temp_spine_resized, temp_spine_perspective, temp_spine_perspective_resized])
                                
                                # Step S1: Resize
                                cmd_spine_resize = _imagemagick_cmd('convert') + [
                                    spine_source_image,
                                    '-resize', f'{spine_resize_width}x{spine_resize_height}!',
                                    temp_spine_resized
                                ]
                                logging.info(f"3D Box Spine Step 1 (Generated) - Resize: {' '.join(cmd_spine_resize)}")
                                subprocess.run(cmd_spine_resize, check=True)
                                
                                # Step S1.5: Add logo to spine if logo is provided (skip if using corners)
                                if has_logo and not use_logo_corners:
                                    logging.info(f"3D Box Spine: Adding logo from {spine_logo_to_use}")
                                    
                                    # Create temp file for rotated and resized logo
                                    if debug:
                                        output_base = os.path.splitext(os.path.basename(output_path))[0]
                                        temp_logo_rotated_resized = os.path.join(temp_dir, f'{output_base}_spine_logo_rotated_resized.png')
                                    else:
                                        temp_logo_rotated_resized = os.path.join(temp_dir, 'spine_logo_rotated_resized.png')
                                    
                                    temp_files.append(temp_logo_rotated_resized)
                                    
                                    # Calculate logo zone dimensions if zone is provided
                                    zone_width_resized = None
                                    zone_height_resized = None
                                    zone_x_resized = None
                                    zone_y_resized = None
                                    
                                    # Check if we should keep aspect ratio (read early so it's available for all logo types)
                                    keep_aspect_ratio = spine_logo_zone.get('keepAspectRatio', False) if spine_logo_zone else False
                                    logging.info(f"3D Box Spine: Logo placement - is_generated_text_logo={is_generated_text_logo}, keep_aspect_ratio={keep_aspect_ratio}")
                                    
                                    if spine_logo_zone:
                                        # Zone coordinates are in template space, need to map to resized spine space
                                        zone_tl = spine_logo_zone.get('topLeft', {'x': 0, 'y': 0})
                                        zone_tr = spine_logo_zone.get('topRight', {'x': 0, 'y': 0})
                                        zone_bl = spine_logo_zone.get('bottomLeft', {'x': 0, 'y': 0})
                                        zone_br = spine_logo_zone.get('bottomRight', {'x': 0, 'y': 0})
                                        
                                        # Check if zone is actually defined (has non-zero coordinates)
                                        zone_tl_x = zone_tl.get('x', 0)
                                        zone_tl_y = zone_tl.get('y', 0)
                                        zone_tr_x = zone_tr.get('x', 0)
                                        zone_tr_y = zone_tr.get('y', 0)
                                        zone_bl_x = zone_bl.get('x', 0)
                                        zone_bl_y = zone_bl.get('y', 0)
                                        zone_br_x = zone_br.get('x', 0)
                                        zone_br_y = zone_br.get('y', 0)
                                        
                                        # Validate zone has valid coordinates (at least one corner is non-zero)
                                        zone_is_valid = (zone_tl_x > 0 or zone_tl_y > 0 or zone_tr_x > 0 or zone_tr_y > 0 or
                                                       zone_bl_x > 0 or zone_bl_y > 0 or zone_br_x > 0 or zone_br_y > 0)
                                        
                                        if zone_is_valid:
                                            # Calculate zone width and height in template space
                                            zone_width_template = zone_tr_x - zone_tl_x
                                            zone_height_template = zone_bl_y - zone_tl_y
                                            
                                            # Map zone to resized spine space
                                            # Zone is relative to spine corners in template space
                                            # For vertical spine, top Y is at spine_target_topright_y
                                            zone_x_offset_template = zone_tl_x - spine_target_topleft_x
                                            zone_y_offset_template = zone_tl_y - spine_target_topright_y
                                            
                                            # Calculate scale factors from template to resized spine
                                            template_spine_width = spine_target_topright_x - spine_target_topleft_x
                                            template_spine_height = spine_target_bottomright_y - spine_target_topright_y
                                            
                                            if template_spine_width > 0 and template_spine_height > 0 and zone_width_template > 0 and zone_height_template > 0:
                                                scale_x = spine_resize_width / template_spine_width
                                                scale_y = spine_resize_height / template_spine_height
                                                
                                                # Zone dimensions in resized spine space
                                                zone_width_resized = int(zone_width_template * scale_x)
                                                zone_height_resized = int(zone_height_template * scale_y)
                                                zone_x_resized = int(zone_x_offset_template * scale_x)
                                                zone_y_resized = int(zone_y_offset_template * scale_y)
                                                
                                                logging.info(f"3D Box Spine: Zone mapped - template: {zone_width_template}x{zone_height_template} at ({zone_tl_x},{zone_tl_y}), resized: {zone_width_resized}x{zone_height_resized} at ({zone_x_resized},{zone_y_resized})")
                                            else:
                                                logging.warning(f"3D Box Spine: Invalid zone or spine dimensions - zone: {zone_width_template}x{zone_height_template}, spine: {template_spine_width}x{template_spine_height}")
                                                zone_width_resized = None
                                                zone_height_resized = None
                                                zone_x_resized = None
                                                zone_y_resized = None
                                        else:
                                            logging.info(f"3D Box Spine: Zone coordinates are all zero, ignoring zone")
                                            zone_width_resized = None
                                            zone_height_resized = None
                                            zone_x_resized = None
                                            zone_y_resized = None
                                    
                                    # Process logo: resize first to zone dimensions (height as width, width as height), then rotate
                                    # Skip resize if this is a generated text logo that's already been resized with keep_aspect_ratio
                                    if is_generated_text_logo and keep_aspect_ratio:
                                        # Generated text logo is already correctly sized, just use it as-is
                                        # DO NOT resize it again - it's already been resized to maintain aspect ratio
                                        temp_logo_resized = spine_logo_to_use
                                        # Get dimensions for positioning
                                        logo_dim_cmd = _imagemagick_cmd('identify') + ['-format', '%wx%h', spine_logo_to_use]
                                        logo_dim_result = subprocess.run(logo_dim_cmd, capture_output=True, text=True, timeout=5)
                                        if logo_dim_result.returncode == 0:
                                            orig_dims = logo_dim_result.stdout.strip().split('x')
                                            logo_pre_rotate_width = int(orig_dims[0])
                                            logo_pre_rotate_height = int(orig_dims[1])
                                            logging.info(f"3D Box Spine: Using pre-resized generated text logo (skipping resize) - pre-rotate: {logo_pre_rotate_width}x{logo_pre_rotate_height}")
                                        else:
                                            # Fallback: treat as normal logo
                                            logging.warning(f"3D Box Spine: Could not get generated text logo dimensions, treating as normal logo")
                                            is_generated_text_logo = False
                                    
                                    # Only resize if this is NOT a generated text logo with keep_aspect_ratio
                                    # Generated text logos are already correctly sized and should not be resized again
                                    should_resize_logo = not (is_generated_text_logo and keep_aspect_ratio)
                                    logging.info(f"3D Box Spine: should_resize_logo={should_resize_logo} (is_generated_text_logo={is_generated_text_logo}, keep_aspect_ratio={keep_aspect_ratio})")
                                    
                                    if should_resize_logo:
                                        # Normal logo processing: calculate dimensions and resize
                                        if zone_width_resized and zone_width_resized > 0 and zone_height_resized and zone_height_resized > 0:
                                            # Zone is defined
                                            if keep_aspect_ratio:
                                                # Keep aspect ratio: if logo is bigger than topY-bottomY area (zone_height_resized),
                                                # fix width to zone_height_resized and adapt height to maintain aspect ratio
                                                # Get original logo dimensions
                                                logo_dim_cmd = _imagemagick_cmd('identify') + ['-format', '%wx%h', spine_logo_to_use]
                                                logo_dim_result = subprocess.run(logo_dim_cmd, capture_output=True, text=True, timeout=5)
                                                if logo_dim_result.returncode == 0:
                                                    orig_dims = logo_dim_result.stdout.strip().split('x')
                                                    orig_width = int(orig_dims[0])
                                                    orig_height = int(orig_dims[1])
                                                    orig_aspect = orig_width / orig_height if orig_height > 0 else 1
                                                    
                                                    # If logo width (before rotation) is bigger than zone_height_resized (topY-bottomY),
                                                    # fix width to zone_height_resized and calculate height from aspect ratio
                                                    if orig_width > zone_height_resized:
                                                        # Fix width to zone_height_resized, adapt height
                                                        logo_pre_rotate_width = zone_height_resized
                                                        logo_pre_rotate_height = int(logo_pre_rotate_width / orig_aspect) if orig_aspect > 0 else zone_height_resized
                                                        logging.info(f"3D Box Spine: Logo bigger than zone height ({orig_width} > {zone_height_resized}), fixing width to {zone_height_resized}, height: {logo_pre_rotate_height} (aspect: {orig_aspect:.3f})")
                                                    else:
                                                        # Logo fits within zone height, use current logic
                                                        # After rotation, width should be zone_width_resized
                                                        # So before rotation, height should be zone_width_resized
                                                        logo_pre_rotate_height = zone_width_resized  # This becomes width after rotation
                                                        logo_pre_rotate_width = int(logo_pre_rotate_height * orig_aspect)  # Maintain aspect ratio
                                                        logging.info(f"3D Box Spine: Logo fits in zone height ({orig_width} <= {zone_height_resized}), using zone width logic - pre-rotate: {logo_pre_rotate_width}x{logo_pre_rotate_height}")
                                                    
                                                    logging.info(f"3D Box Spine: Keeping aspect ratio - original: {orig_width}x{orig_height} (aspect: {orig_aspect:.3f}), pre-rotate: {logo_pre_rotate_width}x{logo_pre_rotate_height}")
                                                else:
                                                    # Fallback: use zone dimensions
                                                    logo_pre_rotate_width = zone_height_resized
                                                    logo_pre_rotate_height = zone_width_resized
                                                    logging.warning(f"3D Box Spine: Could not get logo dimensions, using zone dimensions")
                                            else:
                                                # Zone is defined: use zone height as width, zone width as height
                                                # After rotation, this will become zone width x zone height
                                                logo_pre_rotate_width = zone_height_resized  # Zone height becomes logo width
                                                logo_pre_rotate_height = zone_width_resized  # Zone width becomes logo height
                                            
                                            logo_x = zone_x_resized
                                            logging.info(f"3D Box Spine: Using zone dimensions - pre-rotate: {logo_pre_rotate_width}x{logo_pre_rotate_height}, post-rotate: {zone_width_resized}x{zone_height_resized}")
                                        else:
                                            # No zone: use spine dimensions swapped
                                            if keep_aspect_ratio:
                                                # Keep aspect ratio: scale vertically only to match spine width (after rotation)
                                                # After rotation, width should be spine_resize_width
                                                # Get original logo dimensions
                                                logo_dim_cmd = _imagemagick_cmd('identify') + ['-format', '%wx%h', spine_logo_to_use]
                                                logo_dim_result = subprocess.run(logo_dim_cmd, capture_output=True, text=True, timeout=5)
                                                if logo_dim_result.returncode == 0:
                                                    orig_dims = logo_dim_result.stdout.strip().split('x')
                                                    orig_width = int(orig_dims[0])
                                                    orig_height = int(orig_dims[1])
                                                    orig_aspect = orig_width / orig_height if orig_height > 0 else 1
                                                    
                                                    # After rotation, width should be spine_resize_width
                                                    # So before rotation, height should be spine_resize_width
                                                    # Calculate width before rotation to maintain aspect ratio
                                                    logo_pre_rotate_height = spine_resize_width  # This becomes width after rotation
                                                    logo_pre_rotate_width = int(logo_pre_rotate_height * orig_aspect)  # Maintain aspect ratio
                                                    
                                                    logging.info(f"3D Box Spine: No zone, keeping aspect ratio - original: {orig_width}x{orig_height} (aspect: {orig_aspect:.3f}), pre-rotate: {logo_pre_rotate_width}x{logo_pre_rotate_height}")
                                                else:
                                                    # Fallback: use spine dimensions
                                                    logo_pre_rotate_width = spine_resize_height
                                                    logo_pre_rotate_height = spine_resize_width
                                                    logging.warning(f"3D Box Spine: Could not get logo dimensions, using spine dimensions")
                                            else:
                                                logo_pre_rotate_width = spine_resize_height  # Spine height becomes logo width
                                                logo_pre_rotate_height = spine_resize_width  # Spine width becomes logo height
                                            logo_x = 0
                                            logging.info(f"3D Box Spine: No zone, using spine dimensions - pre-rotate: {logo_pre_rotate_width}x{logo_pre_rotate_height}")
                                        
                                        # Step 1: Resize logo to pre-rotate dimensions
                                        temp_logo_resized = os.path.splitext(temp_logo_rotated_resized)[0] + '_pre_rotate.png'
                                        temp_files.append(temp_logo_resized)
                                        
                                        if keep_aspect_ratio:
                                            # Keep aspect ratio: resize to maintain aspect, don't force exact size
                                            # If width was fixed to zone_height_resized, resize by width; otherwise resize by height
                                            if logo_pre_rotate_width == zone_height_resized and zone_height_resized > 0:
                                                # Width was fixed, resize by width
                                                cmd_logo_resize = _imagemagick_cmd('convert') + [
                                                    spine_logo_to_use,
                                                    '-background', 'transparent',
                                                    '-alpha', 'set',
                                                    '-resize', f'{logo_pre_rotate_width}x',  # Scale by width only, maintain aspect ratio
                                                    temp_logo_resized
                                                ]
                                            else:
                                                # Height was fixed, resize by height
                                                cmd_logo_resize = _imagemagick_cmd('convert') + [
                                                    spine_logo_to_use,
                                                    '-background', 'transparent',
                                                    '-alpha', 'set',
                                                    '-resize', f'x{logo_pre_rotate_height}',  # Scale by height only, maintain aspect ratio
                                                    temp_logo_resized
                                                ]
                                        else:
                                            # Force exact size (stretch to fill)
                                            cmd_logo_resize = _imagemagick_cmd('convert') + [
                                                spine_logo_to_use,
                                                '-background', 'transparent',
                                                '-alpha', 'set',
                                                '-resize', f'{logo_pre_rotate_width}x{logo_pre_rotate_height}!',  # Force exact size
                                                '-gravity', 'center',
                                                '-extent', f'{logo_pre_rotate_width}x{logo_pre_rotate_height}',  # Center on width, use full height
                                                temp_logo_resized
                                            ]
                                        logging.info(f"3D Box Spine: Resizing logo to {logo_pre_rotate_width}x{logo_pre_rotate_height}: {' '.join(cmd_logo_resize)}")
                                        subprocess.run(cmd_logo_resize, check=True)
                                    
                                    # logo_x will be calculated after rotation when we have the actual logo dimensions
                                    
                                    # Step 2: Rotate 90 degrees (preserve transparency)
                                    # For generated text logos with keep_aspect_ratio, the logo is already correctly sized
                                    # and should only be rotated, not resized
                                    if is_generated_text_logo and keep_aspect_ratio:
                                        logging.info(f"3D Box Spine: Rotating pre-resized generated text logo (no resize, maintaining aspect ratio)")
                                    cmd_logo_rotate = _imagemagick_cmd('convert') + [
                                        temp_logo_resized,
                                        '-background', 'transparent',
                                        '-alpha', 'set',
                                        '-rotate', '90',
                                        temp_logo_rotated_resized
                                    ]
                                    logging.info(f"3D Box Spine: Rotating logo 90 degrees: {' '.join(cmd_logo_rotate)}")
                                    result = subprocess.run(cmd_logo_rotate, capture_output=True, text=True, check=True)
                                    if result.returncode != 0:
                                        logging.error(f"3D Box Spine: Rotation failed: {result.stderr}")
                                    else:
                                        logging.info(f"3D Box Spine: Logo rotated successfully")
                                    
                                    # Get logo dimensions after rotation (for verification)
                                    identify_cmd = _imagemagick_cmd('identify') + ['-format', '%wx%h', temp_logo_rotated_resized]
                                    logo_dim_result = subprocess.run(identify_cmd, capture_output=True, text=True, timeout=5)
                                    if logo_dim_result.returncode == 0:
                                        logo_dims = logo_dim_result.stdout.strip().split('x')
                                        logo_width = int(logo_dims[0])
                                        logo_height = int(logo_dims[1])
                                        
                                        # After rotation, dimensions should be swapped
                                        expected_width = zone_width_resized if zone_width_resized else spine_resize_width
                                        # For generated text logos with keep_aspect_ratio, height is determined by aspect ratio, not zone height
                                        if is_generated_text_logo and keep_aspect_ratio:
                                            expected_height = None  # Height is determined by aspect ratio
                                            logging.info(f"3D Box Spine: Logo after rotation: {logo_width}x{logo_height} (expected width: {expected_width}, height maintains aspect ratio)")
                                        else:
                                            expected_height = zone_height_resized if zone_height_resized else spine_resize_height
                                            logging.info(f"3D Box Spine: Logo after rotation: {logo_width}x{logo_height} (expected: {expected_width}x{expected_height})")
                                        
                                        if expected_height is not None:
                                            if logo_width == expected_width and logo_height == expected_height:
                                                logging.info(f"3D Box Spine: ✅ Logo dimensions correct after rotation")
                                            else:
                                                logging.warning(f"3D Box Spine: ⚠️ Logo dimensions mismatch - got {logo_width}x{logo_height}, expected {expected_width}x{expected_height}")
                                        else:
                                            # For generated text logos with keep_aspect_ratio, only check width
                                            if logo_width == expected_width:
                                                logging.info(f"3D Box Spine: ✅ Logo width correct after rotation (height maintains aspect ratio)")
                                            else:
                                                logging.warning(f"3D Box Spine: ⚠️ Logo width mismatch - got {logo_width}, expected {expected_width}")
                                        
                                        # Calculate position: center horizontally and vertically
                                        # Center horizontally between leftX and rightX of spine
                                        if is_generated_text_logo and keep_aspect_ratio:
                                            # For generated text logos with keep_aspect_ratio, center horizontally
                                            if zone_width_resized and zone_width_resized > 0 and zone_height_resized and zone_height_resized > 0 and zone_x_resized is not None:
                                                # Center within zone
                                                logo_x = zone_x_resized + (zone_width_resized - logo_width) // 2
                                            else:
                                                # Center within full spine width
                                                logo_x = (spine_resize_width - logo_width) // 2
                                        elif zone_width_resized and zone_width_resized > 0 and zone_height_resized and zone_height_resized > 0 and zone_x_resized is not None:
                                            # Use zone x position (existing behavior for non-generated logos)
                                            logo_x = zone_x_resized
                                        else:
                                            # Default: start at 0
                                            logo_x = 0
                                        
                                        # Center vertically
                                        if zone_height_resized and zone_y_resized is not None:
                                            # Center vertically within zone
                                            logo_y = zone_y_resized + (zone_height_resized - logo_height) // 2
                                        elif keep_aspect_ratio:
                                            # When keeping aspect ratio without zone, center vertically within full spine
                                            logo_y = (spine_resize_height - logo_height) // 2
                                        else:
                                            # Default: at 2/3 of spine height, centered vertically
                                            logo_y = int(spine_resize_height * 2 / 3) - (logo_height // 2)
                                        
                                        # Composite logo onto resized spine (before perspective transformation)
                                        # Use convert with composite to ensure sRGB color space is preserved
                                        # This prevents greyscale conversion on white backgrounds
                                        cmd_logo_composite = _imagemagick_cmd('convert') + [
                                            temp_spine_resized,
                                            temp_logo_rotated_resized,
                                            '-colorspace', 'sRGB',
                                            '-geometry', f'+{logo_x}+{logo_y}',
                                            '-composite',
                                            temp_spine_resized
                                        ]
                                        logging.info(f"3D Box Spine: Composite logo at ({logo_x}, {logo_y}): {' '.join(cmd_logo_composite)}")
                                        subprocess.run(cmd_logo_composite, check=True)
                                        logging.info(f"✅ Logo composited onto spine")
                                    else:
                                        logging.warning(f"Failed to get logo dimensions, skipping logo composite")
                                
                                # Step S2: Apply perspective distortion
                                cmd_spine_perspective = _imagemagick_cmd('convert') + [
                                    temp_spine_resized,
                                    '-background', 'none',
                                    '-virtual-pixel', 'transparent',
                                    '-alpha', 'set',
                                    '-distort', 'Perspective', spine_perspective_str,
                                    temp_spine_perspective
                                ]
                                logging.info(f"3D Box Spine Step 2 (Generated) - Perspective: {' '.join(cmd_spine_perspective)}")
                                subprocess.run(cmd_spine_perspective, check=True)
                                
                                # Step S3: Resize perspective image
                                cmd_spine_resize_perspective = _imagemagick_cmd('convert') + [
                                    temp_spine_perspective,
                                    '-resize', f'{spine_resize_width}x{spine_resize_height}!',
                                    temp_spine_perspective_resized
                                ]
                                logging.info(f"3D Box Spine Step 3 (Generated) - Resize: {' '.join(cmd_spine_resize_perspective)}")
                                subprocess.run(cmd_spine_resize_perspective, check=True)
                            else:
                                # Uploaded/field spine: optimize based on whether logo is present
                                if has_logo:
                                    # With logo: resize first (needed for logo compositing), then combine perspective + resize
                                    temp_files.extend([temp_spine_resized, temp_spine_perspective_resized])
                                    
                                    # Step S1: Resize (needed for logo compositing)
                                    cmd_spine_resize = _imagemagick_cmd('convert') + [
                                        spine_source_image,
                                        '-resize', f'{spine_resize_width}x{spine_resize_height}!',
                                        temp_spine_resized
                                    ]
                                    logging.info(f"3D Box Spine Step 1 (Uploaded/Field with logo) - Resize: {' '.join(cmd_spine_resize)}")
                                    subprocess.run(cmd_spine_resize, check=True)
                                    
                                    # Step S1.5: Add logo to spine (skip if using corners - disabled for now)
                                    if use_logo_corners:
                                        logging.info(f"3D Box Spine: Skipping logo compositing (will use corner-based placement)")
                                    else:
                                        logging.info(f"3D Box Spine: Adding logo from {spine_logo_to_use}")
                                        
                                        # Create temp file for rotated and resized logo
                                        if debug:
                                            output_base = os.path.splitext(os.path.basename(output_path))[0]
                                            temp_logo_rotated_resized = os.path.join(temp_dir, f'{output_base}_spine_logo_rotated_resized.png')
                                        else:
                                            temp_logo_rotated_resized = os.path.join(temp_dir, 'spine_logo_rotated_resized.png')
                                        
                                        temp_files.append(temp_logo_rotated_resized)
                                        
                                        # Check if we should keep aspect ratio (read early so it's available for all logo types)
                                        keep_aspect_ratio = spine_logo_zone.get('keepAspectRatio', False) if spine_logo_zone else False
                                        logging.info(f"3D Box Spine (Uploaded/Field): Logo placement - is_generated_text_logo={is_generated_text_logo}, keep_aspect_ratio={keep_aspect_ratio}")
                                        
                                        # Calculate logo zone dimensions if zone is provided
                                        zone_width_resized = None
                                        zone_height_resized = None
                                        zone_x_resized = None
                                        zone_y_resized = None
                                        
                                        if spine_logo_zone:
                                            # Zone coordinates are in template space, need to map to resized spine space
                                            zone_tl = spine_logo_zone.get('topLeft', {'x': 0, 'y': 0})
                                            zone_tr = spine_logo_zone.get('topRight', {'x': 0, 'y': 0})
                                            zone_bl = spine_logo_zone.get('bottomLeft', {'x': 0, 'y': 0})
                                            zone_br = spine_logo_zone.get('bottomRight', {'x': 0, 'y': 0})
                                            
                                            # Check if zone is actually defined (has non-zero coordinates)
                                            zone_tl_x = zone_tl.get('x', 0)
                                            zone_tl_y = zone_tl.get('y', 0)
                                            zone_tr_x = zone_tr.get('x', 0)
                                            zone_tr_y = zone_tr.get('y', 0)
                                            zone_bl_x = zone_bl.get('x', 0)
                                            zone_bl_y = zone_bl.get('y', 0)
                                            zone_br_x = zone_br.get('x', 0)
                                            zone_br_y = zone_br.get('y', 0)
                                            
                                            # Validate zone has valid coordinates (at least one corner is non-zero)
                                            zone_is_valid = (zone_tl_x > 0 or zone_tl_y > 0 or zone_tr_x > 0 or zone_tr_y > 0 or
                                                           zone_bl_x > 0 or zone_bl_y > 0 or zone_br_x > 0 or zone_br_y > 0)
                                            
                                            if zone_is_valid:
                                                # Calculate zone width and height in template space
                                                zone_width_template = zone_tr_x - zone_tl_x
                                                zone_height_template = zone_bl_y - zone_tl_y
                                                
                                                # Map zone to resized spine space
                                                # Zone is relative to spine corners in template space
                                                # For vertical spine, top Y is at spine_target_topright_y
                                                zone_x_offset_template = zone_tl_x - spine_target_topleft_x
                                                zone_y_offset_template = zone_tl_y - spine_target_topright_y
                                                
                                                # Calculate scale factors from template to resized spine
                                                template_spine_width = spine_target_topright_x - spine_target_topleft_x
                                                template_spine_height = spine_target_bottomright_y - spine_target_topright_y
                                                
                                                if template_spine_width > 0 and template_spine_height > 0 and zone_width_template > 0 and zone_height_template > 0:
                                                    scale_x = spine_resize_width / template_spine_width
                                                    scale_y = spine_resize_height / template_spine_height
                                                    
                                                    # Zone dimensions in resized spine space
                                                    zone_width_resized = int(zone_width_template * scale_x)
                                                    zone_height_resized = int(zone_height_template * scale_y)
                                                    zone_x_resized = int(zone_x_offset_template * scale_x)
                                                    zone_y_resized = int(zone_y_offset_template * scale_y)
                                                    
                                                    logging.info(f"3D Box Spine: Zone mapped - template: {zone_width_template}x{zone_height_template} at ({zone_tl_x},{zone_tl_y}), resized: {zone_width_resized}x{zone_height_resized} at ({zone_x_resized},{zone_y_resized})")
                                                else:
                                                    logging.warning(f"3D Box Spine: Invalid zone or spine dimensions - zone: {zone_width_template}x{zone_height_template}, spine: {template_spine_width}x{template_spine_height}")
                                                    zone_width_resized = None
                                                    zone_height_resized = None
                                                    zone_x_resized = None
                                                    zone_y_resized = None
                                            else:
                                                logging.info(f"3D Box Spine: Zone coordinates are all zero, ignoring zone")
                                                zone_width_resized = None
                                                zone_height_resized = None
                                                zone_x_resized = None
                                                zone_y_resized = None
                                        
                                        # Process logo: resize first to zone dimensions (height as width, width as height), then rotate
                                        # Skip resize if this is a generated text logo that's already been resized with keep_aspect_ratio
                                        logo_x = None  # Initialize logo_x
                                        if is_generated_text_logo and keep_aspect_ratio:
                                            # For uploaded/field spines, recalculate text logo size using actual zone dimensions
                                            # The earlier resize might have used fallback dimensions, so we need to check against actual zone
                                            temp_logo_resized = spine_logo_to_use
                                            # Get current dimensions
                                            logo_dim_cmd = _imagemagick_cmd('identify') + ['-format', '%wx%h', spine_logo_to_use]
                                            logo_dim_result = subprocess.run(logo_dim_cmd, capture_output=True, text=True, timeout=5)
                                            if logo_dim_result.returncode == 0:
                                                orig_dims = logo_dim_result.stdout.strip().split('x')
                                                current_width = int(orig_dims[0])
                                                current_height = int(orig_dims[1])
                                                current_aspect = current_width / current_height if current_height > 0 else 1
                                                
                                                # If zone is defined, recalculate using actual zone_height_resized
                                                if zone_width_resized and zone_width_resized > 0 and zone_height_resized and zone_height_resized > 0:
                                                    # Check if current width is bigger than zone_height_resized (topY-bottomY)
                                                    if current_width > zone_height_resized:
                                                        # Fix width to zone_height_resized, adapt height
                                                        new_width = zone_height_resized
                                                        new_height = int(new_width / current_aspect) if current_aspect > 0 else zone_height_resized
                                                        
                                                        # Resize to correct dimensions
                                                        temp_text_logo_recalc = os.path.splitext(temp_logo_resized)[0] + '_recalc.png'
                                                        temp_files.append(temp_text_logo_recalc)
                                                        cmd_recalc = _imagemagick_cmd('convert') + [
                                                            spine_logo_to_use,
                                                            '-background', 'transparent',
                                                            '-alpha', 'set',
                                                            '-resize', f'{new_width}x',  # Scale by width only, maintain aspect ratio
                                                            temp_text_logo_recalc
                                                        ]
                                                        logging.info(f"3D Box Spine (Uploaded/Field): Recalculating text logo size - current: {current_width}x{current_height}, new: {new_width}x{new_height} (zone_height_resized: {zone_height_resized})")
                                                        subprocess.run(cmd_recalc, check=True)
                                                        temp_logo_resized = temp_text_logo_recalc
                                                        logo_pre_rotate_width = new_width
                                                        logo_pre_rotate_height = new_height
                                                    else:
                                                        # Current size is fine, use as-is
                                                        logo_pre_rotate_width = current_width
                                                        logo_pre_rotate_height = current_height
                                                        logging.info(f"3D Box Spine (Uploaded/Field): Text logo size is correct ({current_width} <= {zone_height_resized}), using as-is")
                                                else:
                                                    # No zone, use current dimensions
                                                    logo_pre_rotate_width = current_width
                                                    logo_pre_rotate_height = current_height
                                                    logging.info(f"3D Box Spine (Uploaded/Field): No zone defined, using current text logo dimensions - pre-rotate: {logo_pre_rotate_width}x{logo_pre_rotate_height}")
                                            else:
                                                # Fallback: treat as normal logo
                                                logging.warning(f"3D Box Spine (Uploaded/Field): Could not get generated text logo dimensions, treating as normal logo")
                                                is_generated_text_logo = False
                                                temp_logo_resized = None  # Will be set in resize step below
                                            # logo_x will be calculated after rotation when we have the actual logo dimensions
                                            
                                            # Update spine_logo_to_use to use recalculated logo if it was recalculated
                                            if temp_logo_resized and temp_logo_resized != spine_logo_to_use:
                                                spine_logo_to_use = temp_logo_resized
                                        
                                        # Only resize if this is NOT a generated text logo with keep_aspect_ratio
                                        should_resize_logo = not (is_generated_text_logo and keep_aspect_ratio)
                                        logging.info(f"3D Box Spine (Uploaded/Field): should_resize_logo={should_resize_logo} (is_generated_text_logo={is_generated_text_logo}, keep_aspect_ratio={keep_aspect_ratio})")
                                        
                                        if should_resize_logo:
                                            if zone_width_resized and zone_width_resized > 0 and zone_height_resized and zone_height_resized > 0:
                                                # Zone is defined
                                                if keep_aspect_ratio:
                                                    # Keep aspect ratio: if logo is bigger than topY-bottomY area (zone_height_resized),
                                                    # fix width to zone_height_resized and adapt height to maintain aspect ratio
                                                    # Get original logo dimensions
                                                    logo_dim_cmd = _imagemagick_cmd('identify') + ['-format', '%wx%h', spine_logo_to_use]
                                                    logo_dim_result = subprocess.run(logo_dim_cmd, capture_output=True, text=True, timeout=5)
                                                    if logo_dim_result.returncode == 0:
                                                        orig_dims = logo_dim_result.stdout.strip().split('x')
                                                        orig_width = int(orig_dims[0])
                                                        orig_height = int(orig_dims[1])
                                                        orig_aspect = orig_width / orig_height if orig_height > 0 else 1
                                                        
                                                        # If logo width (before rotation) is bigger than zone_height_resized (topY-bottomY),
                                                        # fix width to zone_height_resized and calculate height from aspect ratio
                                                        if orig_width > zone_height_resized:
                                                            # Fix width to zone_height_resized, adapt height
                                                            logo_pre_rotate_width = zone_height_resized
                                                            logo_pre_rotate_height = int(logo_pre_rotate_width / orig_aspect) if orig_aspect > 0 else zone_height_resized
                                                            logging.info(f"3D Box Spine (Uploaded/Field): Logo bigger than zone height ({orig_width} > {zone_height_resized}), fixing width to {zone_height_resized}, height: {logo_pre_rotate_height} (aspect: {orig_aspect:.3f})")
                                                        else:
                                                            # Logo fits within zone height, use current logic
                                                            # After rotation, width should be zone_width_resized
                                                            # So before rotation, height should be zone_width_resized
                                                            logo_pre_rotate_height = zone_width_resized  # This becomes width after rotation
                                                            logo_pre_rotate_width = int(logo_pre_rotate_height * orig_aspect)  # Maintain aspect ratio
                                                            logging.info(f"3D Box Spine (Uploaded/Field): Logo fits in zone height ({orig_width} <= {zone_height_resized}), using zone width logic - pre-rotate: {logo_pre_rotate_width}x{logo_pre_rotate_height}")
                                                        
                                                        logging.info(f"3D Box Spine (Uploaded/Field): Keeping aspect ratio - original: {orig_width}x{orig_height} (aspect: {orig_aspect:.3f}), pre-rotate: {logo_pre_rotate_width}x{logo_pre_rotate_height}")
                                                    else:
                                                        # Fallback: use zone dimensions
                                                        logo_pre_rotate_width = zone_height_resized
                                                        logo_pre_rotate_height = zone_width_resized
                                                        logging.warning(f"3D Box Spine (Uploaded/Field): Could not get logo dimensions, using zone dimensions")
                                                else:
                                                    # Zone is defined: use zone height as width, zone width as height
                                                    # After rotation, this will become zone width x zone height
                                                    logo_pre_rotate_width = zone_height_resized  # Zone height becomes logo width
                                                    logo_pre_rotate_height = zone_width_resized  # Zone width becomes logo height
                                                logo_x = zone_x_resized
                                                logging.info(f"3D Box Spine: Using zone dimensions - pre-rotate: {logo_pre_rotate_width}x{logo_pre_rotate_height}, post-rotate: {zone_width_resized}x{zone_height_resized}")
                                            else:
                                                # No zone: use spine dimensions swapped
                                                if keep_aspect_ratio:
                                                    # Keep aspect ratio: scale vertically only to match spine width (after rotation)
                                                    # After rotation, width should be spine_resize_width
                                                    # Get original logo dimensions
                                                    logo_dim_cmd = _imagemagick_cmd('identify') + ['-format', '%wx%h', spine_logo_to_use]
                                                    logo_dim_result = subprocess.run(logo_dim_cmd, capture_output=True, text=True, timeout=5)
                                                    if logo_dim_result.returncode == 0:
                                                        orig_dims = logo_dim_result.stdout.strip().split('x')
                                                        orig_width = int(orig_dims[0])
                                                        orig_height = int(orig_dims[1])
                                                        orig_aspect = orig_width / orig_height if orig_height > 0 else 1
                                                        
                                                        # After rotation, width should be spine_resize_width
                                                        # So before rotation, height should be spine_resize_width
                                                        # Calculate width before rotation to maintain aspect ratio
                                                        logo_pre_rotate_height = spine_resize_width  # This becomes width after rotation
                                                        logo_pre_rotate_width = int(logo_pre_rotate_height * orig_aspect)  # Maintain aspect ratio
                                                        
                                                        logging.info(f"3D Box Spine (Uploaded/Field): No zone, keeping aspect ratio - original: {orig_width}x{orig_height} (aspect: {orig_aspect:.3f}), pre-rotate: {logo_pre_rotate_width}x{logo_pre_rotate_height}")
                                                    else:
                                                        # Fallback: use spine dimensions
                                                        logo_pre_rotate_width = spine_resize_height
                                                        logo_pre_rotate_height = spine_resize_width
                                                        logging.warning(f"3D Box Spine (Uploaded/Field): Could not get logo dimensions, using spine dimensions")
                                                else:
                                                    logo_pre_rotate_width = spine_resize_height  # Spine height becomes logo width
                                                    logo_pre_rotate_height = spine_resize_width  # Spine width becomes logo height
                                                logo_x = 0
                                                logging.info(f"3D Box Spine: No zone, using spine dimensions - pre-rotate: {logo_pre_rotate_width}x{logo_pre_rotate_height}")
                                            
                                            # Step 1: Resize logo to pre-rotate dimensions
                                            temp_logo_resized = os.path.splitext(temp_logo_rotated_resized)[0] + '_pre_rotate.png'
                                            temp_files.append(temp_logo_resized)
                                            
                                            if keep_aspect_ratio:
                                                # Keep aspect ratio: resize to maintain aspect, don't force exact size
                                                # If width was fixed to zone_height_resized, resize by width; otherwise resize by height
                                                if logo_pre_rotate_width == zone_height_resized and zone_height_resized > 0:
                                                    # Width was fixed, resize by width
                                                    cmd_logo_resize = _imagemagick_cmd('convert') + [
                                                        spine_logo_to_use,
                                                        '-background', 'transparent',
                                                        '-alpha', 'set',
                                                        '-resize', f'{logo_pre_rotate_width}x',  # Scale by width only, maintain aspect ratio
                                                        temp_logo_resized
                                                    ]
                                                else:
                                                    # Height was fixed, resize by height
                                                    cmd_logo_resize = _imagemagick_cmd('convert') + [
                                                        spine_logo_to_use,
                                                        '-background', 'transparent',
                                                        '-alpha', 'set',
                                                        '-resize', f'x{logo_pre_rotate_height}',  # Scale by height only, maintain aspect ratio
                                                        temp_logo_resized
                                                    ]
                                            else:
                                                # Force exact size (stretch to fill)
                                                cmd_logo_resize = _imagemagick_cmd('convert') + [
                                                    spine_logo_to_use,
                                                    '-background', 'transparent',
                                                    '-alpha', 'set',
                                                    '-resize', f'{logo_pre_rotate_width}x{logo_pre_rotate_height}!',  # Force exact size
                                                    '-gravity', 'center',
                                                    '-extent', f'{logo_pre_rotate_width}x{logo_pre_rotate_height}',  # Center on width, use full height
                                                    temp_logo_resized
                                                ]
                                            logging.info(f"3D Box Spine: Resizing logo to {logo_pre_rotate_width}x{logo_pre_rotate_height}: {' '.join(cmd_logo_resize)}")
                                            subprocess.run(cmd_logo_resize, check=True)
                                        
                                        # logo_x will be calculated after rotation when we have the actual logo dimensions
                                        
                                        # Step 2: Rotate 90 degrees (preserve transparency)
                                        # For generated text logos with keep_aspect_ratio, the logo is already correctly sized
                                        # and should only be rotated, not resized
                                        if is_generated_text_logo and keep_aspect_ratio:
                                            logging.info(f"3D Box Spine (Uploaded/Field): Rotating pre-resized generated text logo (no resize, maintaining aspect ratio)")
                                        cmd_logo_rotate = _imagemagick_cmd('convert') + [
                                            temp_logo_resized,
                                            '-background', 'transparent',
                                            '-alpha', 'set',
                                            '-rotate', '90',
                                            temp_logo_rotated_resized
                                        ]
                                        logging.info(f"3D Box Spine: Rotating logo 90 degrees: {' '.join(cmd_logo_rotate)}")
                                        result = subprocess.run(cmd_logo_rotate, capture_output=True, text=True, check=True)
                                        if result.returncode != 0:
                                            logging.error(f"3D Box Spine: Rotation failed: {result.stderr}")
                                        else:
                                            logging.info(f"3D Box Spine: Logo rotated successfully")
                                        
                                        # Get logo dimensions after rotation (for verification)
                                        identify_cmd = _imagemagick_cmd('identify') + ['-format', '%wx%h', temp_logo_rotated_resized]
                                        logo_dim_result = subprocess.run(identify_cmd, capture_output=True, text=True, timeout=5)
                                        if logo_dim_result.returncode == 0:
                                            logo_dims = logo_dim_result.stdout.strip().split('x')
                                            logo_rotated_width = int(logo_dims[0])
                                            logo_rotated_height = int(logo_dims[1])
                                            
                                            # After rotation, dimensions should be swapped
                                            expected_width = zone_width_resized if zone_width_resized else spine_resize_width
                                            # For logos with keep_aspect_ratio (both generated text and regular logos), height is determined by aspect ratio, not zone height
                                            if keep_aspect_ratio:
                                                expected_height = None  # Height is determined by aspect ratio
                                                logging.info(f"3D Box Spine (Uploaded/Field): Logo after rotation: {logo_rotated_width}x{logo_rotated_height} (expected width: {expected_width}, height maintains aspect ratio)")
                                            else:
                                                expected_height = zone_height_resized if zone_height_resized else spine_resize_height
                                                logging.info(f"3D Box Spine: Logo after rotation: {logo_rotated_width}x{logo_rotated_height} (expected: {expected_width}x{expected_height})")
                                            
                                            if expected_height is not None:
                                                if logo_rotated_width == expected_width and logo_rotated_height == expected_height:
                                                    logging.info(f"3D Box Spine: ✅ Logo dimensions correct after rotation")
                                                else:
                                                    logging.warning(f"3D Box Spine: ⚠️ Logo dimensions mismatch - got {logo_rotated_width}x{logo_rotated_height}, expected {expected_width}x{expected_height}")
                                            else:
                                                # For logos with keep_aspect_ratio, only check width
                                                if logo_rotated_width == expected_width:
                                                    logging.info(f"3D Box Spine (Uploaded/Field): ✅ Logo width correct after rotation (height maintains aspect ratio)")
                                                else:
                                                    logging.warning(f"3D Box Spine (Uploaded/Field): ⚠️ Logo width mismatch - got {logo_rotated_width}, expected {expected_width}")
                                            
                                            # Calculate position: center horizontally and vertically
                                            # Center horizontally between leftX and rightX of spine
                                            if is_generated_text_logo and keep_aspect_ratio:
                                                # For generated text logos with keep_aspect_ratio, center horizontally
                                                if zone_width_resized and zone_width_resized > 0 and zone_height_resized and zone_height_resized > 0 and zone_x_resized is not None:
                                                    # Center within zone
                                                    logo_x = zone_x_resized + (zone_width_resized - logo_rotated_width) // 2
                                                else:
                                                    # Center within full spine width
                                                    logo_x = (spine_resize_width - logo_rotated_width) // 2
                                            elif keep_aspect_ratio:
                                                # For regular logos with keep_aspect_ratio, center horizontally
                                                if zone_width_resized and zone_width_resized > 0 and zone_height_resized and zone_height_resized > 0 and zone_x_resized is not None:
                                                    # Center within zone
                                                    logo_x = zone_x_resized + (zone_width_resized - logo_rotated_width) // 2
                                                else:
                                                    # Center within full spine width
                                                    logo_x = (spine_resize_width - logo_rotated_width) // 2
                                            elif zone_width_resized and zone_width_resized > 0 and zone_height_resized and zone_height_resized > 0 and zone_x_resized is not None:
                                                # Use zone x position (existing behavior for non-keep-aspect-ratio logos)
                                                logo_x = zone_x_resized
                                            else:
                                                # Default: start at 0
                                                logo_x = 0
                                            
                                            # Center vertically
                                            if zone_height_resized and zone_y_resized is not None:
                                                # Center vertically within zone
                                                logo_y = zone_y_resized + (zone_height_resized - logo_rotated_height) // 2
                                            elif keep_aspect_ratio:
                                                # When keeping aspect ratio without zone, center vertically within full spine
                                                logo_y = (spine_resize_height - logo_rotated_height) // 2
                                            else:
                                                # Default: at 2/3 of spine height, centered vertically
                                                logo_y = int(spine_resize_height * 2 / 3) - (logo_rotated_height // 2)
                                            
                                            # Composite logo onto resized spine (before perspective transformation)
                                            # Use convert with composite to ensure sRGB color space is preserved
                                            # This prevents greyscale conversion on white backgrounds
                                            cmd_logo_composite = _imagemagick_cmd('convert') + [
                                                temp_spine_resized,
                                                temp_logo_rotated_resized,
                                                '-colorspace', 'sRGB',
                                                '-geometry', f'+{logo_x}+{logo_y}',
                                                '-composite',
                                                temp_spine_resized
                                            ]
                                            logging.info(f"3D Box Spine: Composite logo at ({logo_x}, {logo_y}): {' '.join(cmd_logo_composite)}")
                                            subprocess.run(cmd_logo_composite, check=True)
                                            logging.info(f"✅ Logo composited onto spine")
                                        else:
                                            logging.warning(f"Failed to get logo dimensions, skipping logo composite")
                                    
                                    # Step S2-3: Combined perspective + resize
                                    cmd_spine_combined = _imagemagick_cmd('convert') + [
                                        temp_spine_resized,
                                        '-background', 'none',
                                        '-virtual-pixel', 'transparent',
                                        '-alpha', 'set',
                                        '-distort', 'Perspective', spine_perspective_str,
                                        '-resize', f'{spine_resize_width}x{spine_resize_height}!',
                                        temp_spine_perspective_resized
                                    ]
                                    logging.info(f"3D Box Spine Step 2-3 (Uploaded/Field with logo) - Perspective, Resize: {' '.join(cmd_spine_combined)}")
                                    subprocess.run(cmd_spine_combined, check=True)
                                else:
                                    # No logo: combine all 3 steps (resize + perspective + resize) for maximum optimization
                                    temp_files.append(temp_spine_perspective_resized)
                                    
                                    cmd_spine_combined = _imagemagick_cmd('convert') + [
                                        spine_source_image,
                                        '-resize', f'{spine_resize_width}x{spine_resize_height}!',
                                        '-background', 'none',
                                        '-virtual-pixel', 'transparent',
                                        '-alpha', 'set',
                                        '-distort', 'Perspective', spine_perspective_str,
                                        '-resize', f'{spine_resize_width}x{spine_resize_height}!',
                                        temp_spine_perspective_resized
                                    ]
                                    logging.info(f"3D Box Spine Step 1-3 (Uploaded/Field, no logo) - Resize, Perspective, Resize: {' '.join(cmd_spine_combined)}")
                                    subprocess.run(cmd_spine_combined, check=True)
                            
                            # Step S5: Composite spine onto the result (which already has front)
                            # Use source coordinates for compositing (exactly like the front surface)
                            cmd_spine_composite = _imagemagick_cmd('composite') + [
                                '-geometry', f'+{spine_source_topleft_x}+{spine_source_topleft_y}',
                                temp_spine_perspective_resized,
                                output_path,
                                output_path
                            ]
                            logging.info(f"3D Box Spine Step 5 - Composite at ({spine_source_topleft_x},{spine_source_topleft_y}): {' '.join(cmd_spine_composite)}")
                            subprocess.run(cmd_spine_composite, check=True)
                            
                            logging.info(f"✅ Spine composited successfully")
                            
                            # Step S6: Add logo using corner-based placement if corners are provided
                            if use_logo_corners and ((has_logo and spine_logo_to_use) or has_text_logo):
                                logging.info(f"3D Box Spine: Adding logo using corner-based placement")
                                
                                # Extract corner coordinates
                                logo_tl = spine_logo_corners.get('topLeft', {'x': 0, 'y': 0})
                                logo_tr = spine_logo_corners.get('topRight', {'x': 0, 'y': 0})
                                logo_bl = spine_logo_corners.get('bottomLeft', {'x': 0, 'y': 0})
                                logo_br = spine_logo_corners.get('bottomRight', {'x': 0, 'y': 0})
                                
                                target_tl_x = int(logo_tl.get('x', 0))
                                target_tl_y = int(logo_tl.get('y', 0))
                                target_tr_x = int(logo_tr.get('x', 0))
                                target_tr_y = int(logo_tr.get('y', 0))
                                target_bl_x = int(logo_bl.get('x', 0))
                                target_bl_y = int(logo_bl.get('y', 0))
                                target_br_x = int(logo_br.get('x', 0))
                                target_br_y = int(logo_br.get('y', 0))
                                
                                # Calculate bounding box dimensions for logo
                                logo_min_x = min(target_tl_x, target_tr_x, target_bl_x, target_br_x)
                                logo_max_x = max(target_tl_x, target_tr_x, target_bl_x, target_br_x)
                                logo_min_y = min(target_tl_y, target_tr_y, target_bl_y, target_br_y)
                                logo_max_y = max(target_tl_y, target_tr_y, target_bl_y, target_br_y)
                                
                                logo_resize_width = logo_max_x - logo_min_x
                                logo_resize_height = logo_max_y - logo_min_y
                                
                                if logo_resize_width > 0 and logo_resize_height > 0:
                                    # Generate or prepare logo
                                    if has_text_logo and not has_logo:
                                        # Generate text logo
                                        if debug:
                                            output_base = os.path.splitext(os.path.basename(output_path))[0]
                                            temp_logo_for_corners = os.path.join(temp_dir, f'{output_base}_spine_logo_corners.png')
                                        else:
                                            temp_logo_for_corners = os.path.join(temp_dir, 'spine_logo_corners.png')
                                        temp_files.append(temp_logo_for_corners)
                                        
                                        # Generate single-line text logo with the calculated width
                                        generated_text_logo = self.generate_single_line_text_logo(
                                            game_name=spine_game_name,
                                            text_logo_settings=spine_text_logo_settings,
                                            output_path=temp_logo_for_corners,
                                            width=logo_resize_width
                                        )
                                        
                                        if generated_text_logo and os.path.exists(generated_text_logo):
                                            logo_file_for_corners = generated_text_logo
                                        else:
                                            logging.warning(f"Failed to generate text logo for corner placement")
                                            logo_file_for_corners = None
                                    else:
                                        # Use existing logo
                                        logo_file_for_corners = spine_logo_to_use
                                    
                                    if logo_file_for_corners and os.path.exists(logo_file_for_corners):
                                        # Create temp file for resized and transformed logo
                                        if debug:
                                            output_base = os.path.splitext(os.path.basename(output_path))[0]
                                            temp_logo_resized = os.path.join(temp_dir, f'{output_base}_spine_logo_corners_resized.png')
                                            temp_logo_transformed = os.path.join(temp_dir, f'{output_base}_spine_logo_corners_transformed.png')
                                        else:
                                            temp_logo_resized = os.path.join(temp_dir, 'spine_logo_corners_resized.png')
                                            temp_logo_transformed = os.path.join(temp_dir, 'spine_logo_corners_transformed.png')
                                        temp_files.extend([temp_logo_resized, temp_logo_transformed])
                                        
                                        # Step 1: Resize logo to fit bounding box
                                        cmd_logo_resize = _imagemagick_cmd('convert') + [
                                            logo_file_for_corners,
                                            '-resize', f'{logo_resize_width}x{logo_resize_height}!',
                                            temp_logo_resized
                                        ]
                                        logging.info(f"3D Box Spine Logo: Resize to {logo_resize_width}x{logo_resize_height}: {' '.join(cmd_logo_resize)}")
                                        subprocess.run(cmd_logo_resize, check=True)
                                        
                                        # Step 2: Apply perspective transformation
                                        # Source coordinates form a rectangle
                                        source_tl_x = 0
                                        source_tl_y = 0
                                        source_tr_x = logo_resize_width
                                        source_tr_y = 0
                                        source_br_x = logo_resize_width
                                        source_br_y = logo_resize_height
                                        source_bl_x = 0
                                        source_bl_y = logo_resize_height
                                        
                                        logo_perspective_str = (
                                            f'{source_tl_x},{source_tl_y} {target_tl_x},{target_tl_y}  '
                                            f'{source_tr_x},{source_tr_y} {target_tr_x},{target_tr_y}  '
                                            f'{source_br_x},{source_br_y} {target_br_x},{target_br_y}  '
                                            f'{source_bl_x},{source_bl_y} {target_bl_x},{target_bl_y}'
                                        )
                                        
                                        cmd_logo_perspective = _imagemagick_cmd('convert') + [
                                            temp_logo_resized,
                                            '-background', 'none',
                                            '-virtual-pixel', 'transparent',
                                            '-alpha', 'set',
                                            '+distort', 'Perspective', logo_perspective_str,
                                            temp_logo_transformed
                                        ]
                                        logging.info(f"3D Box Spine Logo: Apply perspective: {' '.join(cmd_logo_perspective)}")
                                        subprocess.run(cmd_logo_perspective, check=True)
                                        
                                        # Step 3: Composite transformed logo onto final output
                                        # Use convert with composite to ensure sRGB color space is preserved
                                        # This prevents greyscale conversion on white backgrounds
                                        cmd_logo_composite = _imagemagick_cmd('convert') + [
                                            output_path,
                                            temp_logo_transformed,
                                            '-colorspace', 'sRGB',
                                            '-geometry', f'+{logo_min_x}+{logo_min_y}',
                                            '-composite',
                                            output_path
                                        ]
                                        logging.info(f"3D Box Spine Logo: Composite at ({logo_min_x}, {logo_min_y}): {' '.join(cmd_logo_composite)}")
                                        subprocess.run(cmd_logo_composite, check=True)
                                        logging.info(f"✅ Logo composited using corner-based placement")
                                    else:
                                        logging.warning(f"Logo file not available for corner placement")
                                else:
                                    logging.warning(f"Invalid logo corner dimensions: {logo_resize_width}x{logo_resize_height}")
            
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
