# Fallbacks in the Codebase

This document lists all fallback mechanisms found in the codebase. Based on the "no fallback" guideline, these should be reviewed and potentially removed or made explicit.

## 1. LaunchBox Matching Fallbacks

### Location: `app.py:1492-1497`
**Fallback**: Try without parentheses if exact match fails
```python
# Fallback: Try without parentheses (search in the same index)
normalized_no_parens = normalize_game_name(game_name, remove_paranthesis=True, remove_articles=False)
if normalized_no_parens and normalized_no_parens != normalized_with_parens and normalized_no_parens in partition_index[target_platform]:
    launchboxid = partition_index[target_platform][normalized_no_parens]
    print(f"🔧 DEBUG: Found LaunchBox ID {launchboxid} without parentheses match (fallback)")
    return launchboxid
```

## 2. MobyGames Matching Fallback

### Location: `app.py:4179-4184`
**Fallback**: Fallback to name matching if ID lookup fails
```python
# Fallback to name matching
game_name = game.get('name', '')
if not game_name:
    return None
# Use exact match for scrapper tasks
```

## 3. Gamelist XML Writing Fallback

### Location: `app.py:12018-12024`
**Fallback**: Direct write if formatted write fails
```python
except Exception as e:
    print(f"Error saving formatted gamelist.xml: {e}")
    # Fallback to direct write if formatting fails
    try:
        tree.write(gamelist_path, encoding='utf-8', xml_declaration=True)
        print(f"Fallback: Direct write completed to {gamelist_path}")
    except Exception as fallback_error:
        print(f"Fallback write also failed: {fallback_error}")
        raise fallback_error
```

## 4. LaunchBox Metadata XML Fallback

### Location: `app.py:12553-12558`
**Fallback**: Look for any XML file if Metadata.xml not found
```python
if not os.path.exists(metadata_xml_path):
    # Fallback: look for any XML file if Metadata.xml not found
    metadata_files = [f for f in os.listdir(temp_dir) if f.endswith('.xml')]
    if not metadata_files:
        return jsonify({'error': 'No Metadata.xml or XML file found in downloaded zip'}), 400
    extracted_metadata = os.path.join(temp_dir, metadata_files[0])
    print(f"DEBUG: Using fallback XML file: {metadata_files[0]}")
```

## 5. YouTube Search Fallback

### Location: `app.py:15903-15904`
**Fallback**: Web scraping if YouTube API key not configured
```python
if not youtube_api_key:
    print("YouTube API key not configured, falling back to web scraping")
    return search_youtube_with_web_scraping(search_query)
```

### Location: `app.py:16538-16544`
**Fallback**: HTML parsing if JSON extraction fails
```python
# Method 4: Fallback to HTML parsing with better selectors
print("Falling back to HTML parsing with enhanced selectors...")
videos = extract_from_html_enhanced(soup)
```

## 6. LaunchBox Boxart Mapping Fallback

### Location: `app.py:11139`
**Fallback**: Default boxart types if mapping not configured
```python
boxart_types = image_type_mappings.get('boxart', ['Box - Front'])  # Fallback to old behavior
```

## 7. LaunchBox Media Types Cache Fallback

### Location: `app.py:6410-6416` and `6419-6424`
**Fallback**: Hardcoded list if cache doesn't exist or fails to load
```python
else:
    # Fallback to hardcoded list if cache doesn't exist
    launchbox_media_types = [
        "Box - Front", "Box - Back", "Box - 3D", "Clear Logo",
        "Screenshot - Game Title", "Screenshot - Gameplay", 
        "Fanart - Background", "Cart - Front", "Disc",
        "Arcade - Cabinet", "Fanart - Cart - Front"
    ]
except Exception as e:
    print(f"Error loading LaunchBox media types cache: {e}")
    # Fallback to hardcoded list
    launchbox_media_types = [...]
```

## 8. IGDB Media Types Fallback

### Location: `app.py:6552-6553`
**Fallback**: Default values if file doesn't exist
```python
except FileNotFoundError:
    # Fallback to default values if file doesn't exist
    igdb_media_types = ['cover', 'screenshots', 'artworks', 'logos']
```

## 9. Steam Media Types Fallback

### Location: `app.py:7823-7824`
**Fallback**: Default values if file doesn't exist
```python
except FileNotFoundError:
    # Fallback to default values if file doesn't exist
    steam_media_types = ['capsule', 'logo', 'hero', 'screenshot']
```

## 10. SteamGridDB Media Types Fallback

### Location: `app.py:6737-6738`
**Fallback**: Default values if file doesn't exist
```python
except FileNotFoundError:
    # Fallback to default values if file doesn't exist
    steamgriddb_media_types = ['grids', 'logos', 'heroes']
```

## 11. LaunchBox Platforms Fallback

### Location: `app.py:7923-7924`
**Fallback**: Empty list if metadata.xml not available
```python
# Fallback: return empty list if metadata.xml is not available
return jsonify({'success': True, 'platforms': []})
```

## 12. Async Event Loop Fallback

### Location: `app.py:10354-10372`
**Fallback**: Thread-based execution if event loop conflict detected
```python
if "cannot be called from a running event loop" in str(e):
    # We're in an async context, need to use thread
    print(f"🔧 DEBUG: Event loop conflict detected, using thread fallback")
    # ... thread-based execution
```

## 13. Media File Extension Fallback

### Location: `app.py:16066-16078`
**Fallback**: Try to get extension from URL, default to .jpg
```python
# Fallback: try to get extension from URL
parsed_url = urlparse(media_url)
url_path = parsed_url.path.lower()
if url_path.endswith(('.jpg', '.jpeg')):
    file_extension = '.jpg'
elif url_path.endswith('.png'):
    file_extension = '.png'
# ...
else:
    file_extension = '.jpg'  # Default fallback
```

### Location: `app.py:16084`
**Fallback**: Use game name if ROM path not found
```python
# Fallback: use game name if ROM path not found
```

## 14. ScreenScraper Media Mapping Fallback

### Location: `app.py:14977-14984`
**Fallback**: Heuristic mapping if no explicit mapping found
```python
# Fallback heuristics if no mapping found
if not mapped_field:
    if media_type in ['ss', 'sstitle']:
        mapped_field = 'image'
    elif media_type in ['screenmarquee', 'fanart']:
        mapped_field = 'marquee'
    elif media_type in ['video', 'video-normalized']:
        mapped_field = 'video'
```

## 15. Steam Header Image Fallback

### Location: `app.py:14840-14841`
**Fallback**: Use capsule field for header image
```python
# Use capsule field for header image as fallback
media_fields.setdefault(capsule_field, []).append(steam_data['header_image'])
```

## 16. yt-dlp Path Fallback

### Location: `app.py:889-890`
**Fallback**: System yt-dlp if tools version doesn't exist
```python
else:
    # Fallback to system yt-dlp if tools version doesn't exist
    return 'yt-dlp'
```

## 17. Discord Authentication Fallback

### Location: `app.py:453-455`
**Fallback**: Guild membership check only if bot token not found
```python
if not bot_token:
    print(f"[DISCORD DEBUG] No bot token found in credentials - falling back to guild membership only")
    # Fall back to guild membership check only
    return _check_guild_membership_only(discord_id, access_token, required_guild_id, required_role_name)
```

## 18. Task Creation Fallbacks

### Location: `app.py:2363, 2382, 2401, 2421, 2441, 2461, 2484, 2509, 2532, 2554, 2578, 2602, 2631, 2660, 2680, 2702`
**Fallback**: Create new task if existing one not found
```python
# Fallback: create new task if existing one not found
```

## 19. Image Dimensions Fallback

### Location: `app.py:2935`
**Fallback**: Logging if image dimensions can't be read
```python
# Fallback logging if image dimensions can't be read
```

## 20. JavaScript Fallbacks (Frontend)

### Location: `static/js/app.js`

#### Media Fields Fallback (line 4071-4072)
```javascript
// Fallback to default media fields if API call fails
const fallbackFields = ['marquee', 'boxart', 'image', 'cartridge', 'fanart', 'titleshot', 'manual', 'boxback', 'thumbnail'];
```

#### Grid State Restore Fallback (line 971, 979, 984, 2904)
```javascript
// Also try to restore state after a short delay as fallback
// Additional fallback for task grid
// Fallback: Enable state saving after a timeout even if restore fails
```

#### LaunchBox Video URL Fallback (line 5114)
```javascript
// For LaunchBox, check VideoURL fields first, then fallback to url
```

#### Video Playback Fallback (line 5242)
```javascript
// For Chrome and other browsers, we'll try to play with HLS.js or fallback to store page
```

#### Image HTML Fallback (line 7674)
```javascript
// Create image HTML with fallback
```

#### Game Path Fallbacks (lines 8349, 8420, 8491, 8562, 8633, 8710)
```javascript
// Fallback to game_path if available
```

#### Video Error Handler Fallback (lines 4236, 10734)
```javascript
// Add error handler as fallback in case video fails to load after HEAD check
```

#### Container Dimensions Fallback (line 11959)
```javascript
// Fallback if container dimensions are not available yet
```

#### Hardcoded Fields Fallback (line 13680-13681)
```javascript
// Fallback to hardcoded fields if config fetch fails
const fallbackFields = [...]
```

## Summary

**Total Fallbacks Found**: ~40+ fallback mechanisms

**Categories**:
1. **Matching Fallbacks** (LaunchBox, MobyGames, ScreenScraper) - 3
2. **File I/O Fallbacks** (XML writing, metadata loading) - 3
3. **API/Service Fallbacks** (YouTube, Discord) - 3
4. **Configuration Fallbacks** (media types, mappings) - 6
5. **Media Processing Fallbacks** (extensions, paths) - 3
6. **Async/Threading Fallbacks** - 1
7. **Task Management Fallbacks** - 15+
8. **Frontend/JavaScript Fallbacks** - 10+

**Recommendation**: Review each fallback to determine if it should:
- Be removed (fail explicitly)
- Be made configurable
- Be logged as an error/warning
- Be documented as expected behavior

